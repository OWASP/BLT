"""Check orchestration entrypoint for webhook-triggered check execution dispatch."""

from __future__ import annotations

import json

from checks_api import build_create_check_run_payload, build_update_check_run_payloads

CHECK_ORCHESTRATOR_NAME = "BLT Check Orchestrator"
_PR_DISPATCH_ACTIONS = {"opened", "synchronize", "reopened"}


def should_dispatch_check_orchestrator_event(event: str, action: str) -> bool:
    """Return True when webhook event/action should trigger check dispatch."""
    return (event == "pull_request" and action in _PR_DISPATCH_ACTIONS) or (
        event == "check_suite" and action == "rerequested"
    )


def build_check_dispatch_requests(event: str, action: str, payload: dict) -> list[dict]:
    """Build normalized dispatch requests for orchestrated check execution."""
    if not should_dispatch_check_orchestrator_event(event, action):
        return []

    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login", "")
    repo_name = repo.get("name", "")
    if not owner or not repo_name:
        return []

    requests: list[dict] = []

    if event == "pull_request":
        pr = payload.get("pull_request") or {}
        head_sha = ((pr.get("head") or {}).get("sha") or "").strip()
        pr_number = pr.get("number")
        if head_sha and pr_number:
            requests.append(
                {
                    "owner": owner,
                    "repo": repo_name,
                    "head_sha": head_sha,
                    "pr_number": pr_number,
                    "trigger_event": event,
                    "trigger_action": action,
                    "details_url": pr.get("html_url") or "",
                }
            )
        return requests

    check_suite = payload.get("check_suite") or {}
    head_sha = (check_suite.get("head_sha") or "").strip()
    if not head_sha:
        return []

    for pr in check_suite.get("pull_requests") or []:
        pr_number = pr.get("number")
        if not pr_number:
            continue
        requests.append(
            {
                "owner": owner,
                "repo": repo_name,
                "head_sha": head_sha,
                "pr_number": pr_number,
                "trigger_event": event,
                "trigger_action": action,
                "details_url": pr.get("html_url") or "",
            }
        )

    return requests


async def dispatch_check_orchestrator_event(
    event: str,
    action: str,
    payload: dict,
    token: str,
    github_api,
) -> int:
    """Create and complete orchestrator check-runs for each dispatch request.

    Returns the number of dispatch requests attempted.
    """
    dispatch_requests = build_check_dispatch_requests(event, action, payload)

    for request in dispatch_requests:
        owner = request["owner"]
        repo_name = request["repo"]
        pr_number = request["pr_number"]

        create_payload = build_create_check_run_payload(
            name=CHECK_ORCHESTRATOR_NAME,
            head_sha=request["head_sha"],
            details_url=request.get("details_url") or None,
            external_id=f"{event}:{action}:pr-{pr_number}",
            status="in_progress",
        )

        create_resp = await github_api(
            "POST",
            f"/repos/{owner}/{repo_name}/check-runs",
            token,
            create_payload,
        )

        if create_resp.status not in (200, 201):
            continue

        create_data = json.loads(await create_resp.text())
        check_run_id = create_data.get("id")
        if not check_run_id:
            continue

        summary = (
            f"Received dispatch trigger `{event}.{action}` for PR #{pr_number}. "
            "Tool-level checks are orchestrated by subsequent feature branches."
        )

        update_payload = build_update_check_run_payloads(
            status="completed",
            title="Checks Dispatch Entrypoint",
            summary=summary,
            conclusion="neutral",
        )[0]

        await github_api(
            "PATCH",
            f"/repos/{owner}/{repo_name}/check-runs/{check_run_id}",
            token,
            update_payload,
        )

    return len(dispatch_requests)
