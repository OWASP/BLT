"""Check orchestration entrypoint for webhook-triggered check execution dispatch."""

from __future__ import annotations

import json
import logging

from checks_api import build_create_check_run_payload, build_update_check_run_payloads

CHECK_ORCHESTRATOR_NAME = "BLT Check Orchestrator"
_PR_DISPATCH_ACTIONS = {"opened", "synchronize", "reopened"}
_logger = logging.getLogger(__name__)


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

    Returns the number of dispatch requests successfully completed.
    """
    dispatch_requests = build_check_dispatch_requests(event, action, payload)
    successful_dispatches = 0

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

        create_data = {}
        try:
            create_data = json.loads(await create_resp.text())
        except (json.JSONDecodeError, ValueError) as exc:
            _logger.error(
                "check-orchestrator: failed to parse create check-run response "
                "for %s/%s pr=%s status=%s error=%s",
                owner,
                repo_name,
                pr_number,
                create_resp.status,
                exc,
            )

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

        patch_path = f"/repos/{owner}/{repo_name}/check-runs/{check_run_id}"
        try:
            patch_resp = await github_api(
                "PATCH",
                patch_path,
                token,
                update_payload,
            )
        except Exception as exc:
            _logger.error(
                "check-orchestrator: patch request failed for %s/%s check_run_id=%s payload=%s error=%s",
                owner,
                repo_name,
                check_run_id,
                update_payload,
                exc,
            )
            patch_resp = None

        if not patch_resp or patch_resp.status not in (200, 201):
            _logger.error(
                "check-orchestrator: patch response failed for %s/%s check_run_id=%s status=%s payload=%s",
                owner,
                repo_name,
                check_run_id,
                getattr(patch_resp, "status", "<exception>"),
                update_payload,
            )
            corrective_payload = build_update_check_run_payloads(
                status="completed",
                title="Checks Dispatch Entrypoint",
                summary=(
                    f"Dispatch encountered an internal error while finalizing check run "
                    f"for `{event}.{action}` on PR #{pr_number}."
                ),
                conclusion="failure",
            )[0]
            try:
                await github_api(
                    "PATCH",
                    patch_path,
                    token,
                    corrective_payload,
                )
            except Exception as exc:
                _logger.error(
                    "check-orchestrator: corrective patch failed for %s/%s check_run_id=%s payload=%s error=%s",
                    owner,
                    repo_name,
                    check_run_id,
                    corrective_payload,
                    exc,
                )
            continue

        successful_dispatches += 1

    return successful_dispatches
