"""PR review asks: link extraction, ledger and GitHub review parsing, the channel filter,
dedupe, Slack retries, the waitUntil hand-off and the 24-hour follow-up."""

import json
from urllib.parse import parse_qsl, urlparse

import pytest

from src import worker
from tests.test_reminders import NOW, SqliteD1, _Env, _Request, run

CHANNEL = "C0BLT"
OTHER = "C0OTHER"


def pull_md(title="Fix login", status="open", author="alice", author_key="k-alice", merged_at=""):
    lines = ["---", "title: " + title, "status: " + status, "authorName: " + author, "author: " + author_key, "ts: 1760000000000"]
    if merged_at:
        lines.append("mergedAt: " + merged_at)
    return "\n".join(lines + ["---", "", "Body text: with a colon."])


def review_md(author="bob", author_key="k-bob", state="approved", kind="review"):
    return "\n".join(["---", "type: " + kind, "state: " + state, "authorName: " + author, "author: " + author_key, "ts: 1760000100000", "---", "LGTM"])


@pytest.fixture(autouse=True)
def clear_caches():
    worker._PR_REVIEW_CHANNEL_IDS.clear()
    worker._PR_REVIEW_OTHER_CHANNELS.clear()
    yield
    worker._PR_REVIEW_CHANNEL_IDS.clear()
    worker._PR_REVIEW_OTHER_CHANNELS.clear()


@pytest.fixture
def env():
    value = _Env()
    value.DB = SqliteD1()
    return value


@pytest.fixture
def net(monkeypatch):
    """Fake forge ledger, GitHub, and Slack. ledger[ref][number] = {file name: text}."""
    state = {
        "ledger": {"forkmesh/pulls": {}},
        "github": {},
        "channels": {CHANNEL: "owasp-blt", OTHER: "random"},
        "requests": [],
        "posts": [],
        "post_error": "",
    }

    async def fake_token(env, team_id="", channel_id="", app_id=""):
        return "xoxb-" + team_id if team_id else ""

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        state["requests"].append(url)
        parsed = urlparse(url)
        query = parse_qsl(parsed.query)
        if parsed.netloc == "git.owaspblt.org":
            params = dict(query)
            ref = params.get("ref", "")
            folders = state["ledger"].get(ref, {})
            if parsed.path.endswith("/tree"):
                number = params["path"].rsplit("/", 1)[1]
                files = folders.get(number)
                if files is None:
                    return False, {"error": "not_found"}, 404
                entries = [{"name": name, "type": "blob", "oid": "o" + name} for name in files]
                return True, {"commit": ref + "@c1", "entries": entries}, 200
            if parsed.path.endswith("/blobs"):
                commit_ref = ref.split("@")[0]
                blobs = {}
                for key, path in query:
                    if key == "path":
                        _, _, number, name = path.split("/")
                        text = state["ledger"][commit_ref][number].get(name)
                        blobs[path] = {"content": text, "encoding": "utf-8"}
                return True, {"blobs": blobs}, 200
        if parsed.netloc == "api.github.com":
            assert headers["Authorization"] == "Bearer ghp-test"
            key = parsed.path
            if key in state["github"]:
                return True, state["github"][key], 200
            return False, {"message": "Not Found"}, 404
        if url.startswith("https://slack.com/api/conversations.info"):
            name = state["channels"].get(dict(query)["channel"])
            return True, ({"ok": True, "channel": {"name": name}} if name else {"ok": False, "error": "channel_not_found"}), 200
        if url == "https://slack.com/api/chat.postMessage":
            payload = json.loads(body)
            state["posts"].append({"auth": headers["Authorization"], **payload})
            if state["post_error"]:
                return True, {"ok": False, "error": state["post_error"]}, 200
            return True, {"ok": True, "ts": "9.9"}, 200
        raise AssertionError("unexpected fetch " + url)

    monkeypatch.setattr(worker, "workspace_slack_token", fake_token)
    monkeypatch.setattr(worker, "fetch_json", fake_fetch_json)
    return state


def message(text, channel=CHANNEL, ts="1700000000.000100", **extra):
    event = {"type": "message", "channel": channel, "channel_type": "channel", "user": "U1", "text": text, "ts": ts}
    event.update(extra)
    return event


def handle(env, event, now=NOW):
    links = worker.pr_review_candidate_links(env, event, "T1")
    if not links:
        return None
    return run(worker.handle_pr_review_links(env, event, links, team_id="T1", app_id="A1", now=now))


# --- link extraction -----------------------------------------------------------------


def test_extract_pr_links_forge_and_github_forms():
    text = (
        "please look <https://git.owaspblt.org/BLT/pulls/12|PR 12> and "
        "https://git.owaspblt.org/owasp-blt/BLT/pulls/13/files and "
        "<https://github.com/OWASP-BLT/BLT-Sammich/pull/7> "
        "https://git.owaspblt.org/BLT/pulls/12 (again)"
    )
    links = worker.extract_pr_links(text)
    assert [link["key"] for link in links] == [
        "forge:owasp-blt/BLT#12",
        "forge:owasp-blt/BLT#13",
        "github:owasp-blt/blt-sammich#7",
    ]
    assert links[0]["url"] == "https://git.owaspblt.org/BLT/pulls/12"
    assert links[1]["url"] == "https://git.owaspblt.org/BLT/pulls/13"
    assert links[2]["url"] == "https://github.com/OWASP-BLT/BLT-Sammich/pull/7"
    assert (links[2]["owner"], links[2]["repo"], links[2]["number"]) == ("OWASP-BLT", "BLT-Sammich", 7)


def test_extract_pr_links_ignores_other_links_and_caps_at_three():
    assert worker.extract_pr_links(
        "https://git.owaspblt.org/BLT/issues/3 https://git.owaspblt.org/BLT/pulls/12abc "
        "https://github.com/OWASP-BLT/BLT/issues/9 https://example.com/BLT/pulls/4 BLT/pulls/5"
    ) == []
    text = " ".join("https://git.owaspblt.org/BLT/pulls/{0}".format(n) for n in range(1, 6))
    assert [link["number"] for link in worker.extract_pr_links(text)] == [1, 2, 3]


# --- review state ----------------------------------------------------------------------


def forge(files):
    return worker.parse_forge_pull(12, files)


def test_forge_pull_without_reviews_needs_one():
    pr = forge({"pull.md": pull_md()})
    assert pr == {"number": 12, "title": "Fix login", "author": "alice", "state": "open", "draft": False, "peer_reviewers": []}
    assert worker.pr_needs_peer_review(pr)


def test_forge_review_by_the_author_does_not_count():
    pr = forge({"pull.md": pull_md(), "0001-review.md": review_md(author="alice", author_key="k-alice")})
    assert pr["peer_reviewers"] == [] and worker.pr_needs_peer_review(pr)
    # Same key under a different display name is still the author.
    pr = forge({"pull.md": pull_md(), "0001-review.md": review_md(author="Alice A.", author_key="k-alice")})
    assert worker.pr_needs_peer_review(pr)


def test_forge_peer_review_counts_in_any_state():
    for state in ("approved", "changes_requested", "commented"):
        pr = forge({"pull.md": pull_md(), "0001-review.md": review_md(author="alice", author_key="k-alice"),
                    "0002-review.md": review_md(state=state)})
        assert pr["peer_reviewers"] == ["bob"]
        assert not worker.pr_needs_peer_review(pr)


def test_forge_bot_and_non_review_events_do_not_count():
    pr = forge({"pull.md": pull_md(), "0001-review.md": review_md(author="coderabbit[bot]", author_key="k-cr"),
                "0002-review.md": review_md(kind="comment")})
    assert worker.pr_needs_peer_review(pr)


def test_forge_merged_closed_and_deleted_pulls():
    merged = forge({"pull.md": pull_md(status="merged", merged_at="1760000200000")})
    assert merged["state"] == "merged" and not worker.pr_needs_peer_review(merged)
    assert forge({"pull.md": pull_md(status="open", merged_at="1760000200000")})["state"] == "merged"
    closed = forge({"pull.md": pull_md(status="closed")})
    assert closed["state"] == "closed" and not worker.pr_needs_peer_review(closed)
    assert forge({"pull.md": pull_md(status="deleted")}) is None
    assert forge({"pull.md": ""}) is None


def test_github_review_parsing():
    pull = {"number": 7, "title": "Add X", "state": "open", "merged": False, "draft": False, "user": {"login": "alice"}}
    assert worker.pr_needs_peer_review(worker.parse_github_pull(pull, []))
    own = [{"user": {"login": "Alice"}, "state": "COMMENTED"}, {"user": {"login": "x[bot]", "type": "Bot"}, "state": "APPROVED"},
           {"user": {"login": "bob"}, "state": "PENDING"}]
    assert worker.pr_needs_peer_review(worker.parse_github_pull(pull, own))
    peer = worker.parse_github_pull(pull, own + [{"user": {"login": "bob"}, "state": "APPROVED"}])
    assert peer["peer_reviewers"] == ["bob"] and not worker.pr_needs_peer_review(peer)
    assert worker.parse_github_pull({**pull, "state": "closed", "merged": True}, [])["state"] == "merged"
    assert not worker.pr_needs_peer_review(worker.parse_github_pull({**pull, "draft": True}, []))


# --- forge reads -----------------------------------------------------------------------


def test_fetch_forge_pull_reads_the_ledger_in_two_requests(net):
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md(), "0001-review.md": review_md(),
                                             "changes.patch": "diff", "0002-comment.md": "---\ntype: comment\n---"}
    pr = run(worker.fetch_forge_pull(12))
    assert pr["peer_reviewers"] == ["bob"]
    assert len(net["requests"]) == 2
    blobs = dict(parse_qsl(urlparse(net["requests"][1]).query))
    paths = [v for k, v in parse_qsl(urlparse(net["requests"][1]).query) if k == "path"]
    assert paths == [".forkmesh/pulls/12/pull.md", ".forkmesh/pulls/12/0001-review.md"]
    assert blobs["ref"] == "forkmesh/pulls@c1"  # the immutable commit of the listing


def test_fetch_forge_pull_falls_back_to_the_pull_ref_then_gives_up(net):
    net["ledger"]["forkmesh/pull/14"] = {"14": {"pull.md": pull_md(title="New one")}}
    assert run(worker.fetch_forge_pull(14))["title"] == "New one"
    assert len(net["requests"]) == 3
    net["requests"].clear()
    assert run(worker.fetch_forge_pull(99)) is None
    assert len(net["requests"]) == 2


# --- asking in the thread ----------------------------------------------------------------


def test_asks_in_the_thread_once_per_day(env, net):
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md(title="Fix <login> & more")}
    event = message("review please <https://git.owaspblt.org/BLT/pulls/12>")
    summary = handle(env, event)
    assert summary["asked"] == ["forge:owasp-blt/BLT#12"]
    [post] = net["posts"]
    assert post["auth"] == "Bearer xoxb-T1"
    assert (post["channel"], post["thread_ts"], post["unfurl_links"]) == (CHANNEL, "1700000000.000100", False)
    assert post["text"].startswith(
        ":eyes: *<https://git.owaspblt.org/BLT/pulls/12|Fix &lt;login&gt; &amp; more>* by alice needs a peer review"
    )
    assert "How to review" in post["text"]
    row = env.DB.rows("SELECT * FROM pr_review_asks")[0]
    assert (row["team_id"], row["pr_key"], row["asked_at"], row["nudge_due_at"]) == ("T1", "forge:owasp-blt/BLT#12", NOW, NOW + 86400)

    # Posted again within 24 hours: one indexed read, no forge request, no post.
    net["requests"].clear()
    env.DB.queries.clear()
    again = handle(env, message("bump https://git.owaspblt.org/BLT/pulls/12", ts="1700000100.0"), now=NOW + 3600)
    assert again["skipped"] == {"forge:owasp-blt/BLT#12": "asked_recently"}
    assert net["requests"] == [] and len(net["posts"]) == 1
    assert env.DB.queries == [worker.PR_REVIEW_RECENT_QUERY]

    # A day later it may ask again, in the new thread.
    later = handle(env, message("https://git.owaspblt.org/BLT/pulls/12", ts="1700090000.0"), now=NOW + 86400 + 1)
    assert later["asked"] == ["forge:owasp-blt/BLT#12"]
    assert net["posts"][-1]["thread_ts"] == "1700090000.0"
    assert len(env.DB.rows("SELECT * FROM pr_review_asks")) == 1


def test_claim_is_atomic(env, net):
    link = worker.extract_pr_links("https://git.owaspblt.org/BLT/pulls/12")[0]
    assert run(worker.db_claim_pr_review_ask(env, "T1", "A1", link, CHANNEL, "1.0", NOW))
    assert not run(worker.db_claim_pr_review_ask(env, "T1", "A1", link, CHANNEL, "2.0", NOW + 10))
    assert run(worker.db_claim_pr_review_ask(env, "T2", "A1", link, CHANNEL, "2.0", NOW + 10))  # another team


def test_silent_for_reviewed_merged_closed_and_unknown_pulls(env, net):
    pulls = net["ledger"]["forkmesh/pulls"]
    pulls["1"] = {"pull.md": pull_md(), "0001-review.md": review_md()}
    pulls["2"] = {"pull.md": pull_md(status="merged", merged_at="1760000200000")}
    pulls["3"] = {"pull.md": pull_md(status="closed")}
    text = " ".join("https://git.owaspblt.org/BLT/pulls/{0}".format(n) for n in (1, 2, 3))
    assert handle(env, message(text))["skipped"] == {
        "forge:owasp-blt/BLT#1": "reviewed", "forge:owasp-blt/BLT#2": "merged", "forge:owasp-blt/BLT#3": "closed",
    }
    assert handle(env, message("https://git.owaspblt.org/BLT/pulls/404"))["skipped"] == {"forge:owasp-blt/BLT#404": "unknown"}
    assert net["posts"] == []
    assert env.DB.rows("SELECT * FROM pr_review_asks") == []  # no writes when not acting


def test_a_failed_post_releases_the_claim(env, net):
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md()}
    net["post_error"] = "not_in_channel"
    assert handle(env, message("https://git.owaspblt.org/BLT/pulls/12"))["skipped"] == {"forge:owasp-blt/BLT#12": "not_in_channel"}
    net["post_error"] = ""
    assert handle(env, message("https://git.owaspblt.org/BLT/pulls/12"), now=NOW + 60)["asked"] == ["forge:owasp-blt/BLT#12"]


def test_github_links_use_the_token_or_are_skipped(env, net):
    path = "/repos/OWASP-BLT/BLT-Sammich/pulls/7"
    net["github"][path] = {"number": 7, "title": "Add X", "state": "open", "draft": False, "user": {"login": "alice"}}
    net["github"][path + "/reviews"] = [{"user": {"login": "alice"}, "state": "COMMENTED"}]
    event = message("<https://github.com/OWASP-BLT/BLT-Sammich/pull/7>")
    assert handle(env, event)["skipped"] == {"github:owasp-blt/blt-sammich#7": "unknown"}  # no GITHUB_TOKEN
    assert not any("api.github.com" in url for url in net["requests"])
    env.GITHUB_TOKEN = "ghp-test"
    assert handle(env, event)["asked"] == ["github:owasp-blt/blt-sammich#7"]
    assert "Files changed" in net["posts"][0]["text"]


# --- which messages count ----------------------------------------------------------------


def test_bots_edits_dms_and_thread_replies_are_ignored(env):
    link = "https://git.owaspblt.org/BLT/pulls/12"
    candidates = lambda event: worker.pr_review_candidate_links(env, event, "T1")  # noqa: E731
    assert len(candidates(message(link))) == 1
    assert candidates(message(link, bot_id="B1")) == []
    assert candidates(message(link, subtype="bot_message")) == []
    assert candidates(message(link, subtype="message_changed")) == []
    assert candidates(message(link, channel="D123", channel_type="im")) == []
    assert candidates(message("no links here")) == []
    reply = message(link, ts="2.0", thread_ts="1.0")
    assert candidates(reply) == []
    assert len(candidates(message(link, ts="1.0", thread_ts="1.0"))) == 1  # a thread's parent
    env.PR_REVIEW_THREAD_REPLIES = "1"
    assert len(candidates(reply)) == 1


def test_channel_filter_resolves_the_name_once(env, net):
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md()}
    link = "https://git.owaspblt.org/BLT/pulls/12"
    assert handle(env, message(link, channel=OTHER))["skipped"] == {"*": "other_channel"}
    # Known non-matching channel: filtered before any I/O.
    assert worker.pr_review_candidate_links(env, message(link, channel=OTHER), "T1") == []
    assert handle(env, message(link))["asked"] == ["forge:owasp-blt/BLT#12"]
    assert worker._PR_REVIEW_CHANNEL_IDS == {"T1": CHANNEL}
    info_calls = [url for url in net["requests"] if "conversations.info" in url]
    assert len(info_calls) == 2
    # Once resolved, every other channel is filtered without a lookup.
    assert worker.pr_review_candidate_links(env, message(link, channel="C0NEW"), "T1") == []


def test_channel_id_and_name_settings(env, net):
    link = "https://git.owaspblt.org/BLT/pulls/12"
    env.PR_REVIEW_CHANNEL_ID = OTHER
    assert worker.pr_review_candidate_links(env, message(link), "T1") == []
    assert len(worker.pr_review_candidate_links(env, message(link, channel=OTHER), "T1")) == 1
    del env.PR_REVIEW_CHANNEL_ID
    env.PR_REVIEW_CHANNEL = "off"
    assert worker.pr_review_candidate_links(env, message(link), "T1") == []
    env.PR_REVIEW_CHANNEL = "#Random"
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md()}
    assert handle(env, message(link, channel=OTHER))["asked"] == ["forge:owasp-blt/BLT#12"]


# --- the Slack event path ----------------------------------------------------------------


class _Ctx:
    def __init__(self):
        self.waited = []

    def waitUntil(self, awaitable):
        self.waited.append(awaitable)


def test_event_hands_the_lookup_to_wait_until_and_skips_retries(env, net, monkeypatch):
    monkeypatch.setattr(worker, "json_response", lambda payload, status=200: {"status": status, "payload": payload})
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md()}
    payload = {"type": "event_callback", "team_id": "T1", "api_app_id": "A1",
               "event": message("https://git.owaspblt.org/BLT/pulls/12")}

    async def scenario():
        ctx = _Ctx()
        response = await worker.handle_event_payload(payload, env, ctx=ctx, retry_num="1")
        assert ctx.waited == [] and response["status"] == 200
        response = await worker.handle_event_payload(payload, env, ctx=ctx)
        assert response["status"] == 200
        assert len(ctx.waited) == 1 and net["posts"] == []  # nothing posted before the response
        await ctx.waited[0]
        assert len(net["posts"]) == 1

    run(scenario())


def test_request_passes_the_retry_header(env, monkeypatch):
    seen = {}

    async def fake_handle(payload, env, ctx=None, retry_num=""):
        seen.update(ctx=ctx, retry_num=retry_num)
        return "ok"

    async def no_record(*args, **kwargs):
        return None

    monkeypatch.setattr(worker, "handle_event_payload", fake_handle)
    monkeypatch.setattr(worker, "record_activity", no_record)
    monkeypatch.setattr(worker, "verify_slack_signature", lambda *args: True)

    async def no_secret(env, app_id=""):
        return ""

    monkeypatch.setattr(worker, "db_get_slack_app_signing_secret", no_secret)
    request = _Request("POST", "https://sammich.owaspblt.org/slack/events",
                       headers={"content-type": "application/json", "X-Slack-Retry-Num": "2"},
                       body=json.dumps({"type": "event_callback", "event": {"type": "message"}}))
    ctx = _Ctx()
    assert run(worker.handle_request(request, env, ctx)) == "ok"
    assert seen == {"ctx": ctx, "retry_num": "2"}


# --- follow-up nudge -------------------------------------------------------------------


def test_nudge_after_a_day_if_still_unreviewed(env, net):
    pulls = net["ledger"]["forkmesh/pulls"]
    pulls["12"] = {"pull.md": pull_md()}
    pulls["13"] = {"pull.md": pull_md(title="Other")}
    handle(env, message("https://git.owaspblt.org/BLT/pulls/12 https://git.owaspblt.org/BLT/pulls/13"))
    assert len(net["posts"]) == 2

    env.DB.queries.clear()
    assert run(worker.process_pr_review_nudges(env, now=NOW + 3600)) == {"due": 0, "nudged": 0}
    assert env.DB.queries == [worker.PR_REVIEW_NUDGE_DUE_QUERY]

    pulls["13"]["0001-review.md"] = review_md()
    assert run(worker.process_pr_review_nudges(env, now=NOW + 86400)) == {"due": 2, "nudged": 1}
    nudge = net["posts"][-1]
    assert nudge["text"].startswith(":wave: Still looking for a reviewer: *<https://git.owaspblt.org/BLT/pulls/12|Fix login>*")
    assert nudge["thread_ts"] == "1700000000.000100"
    rows = {row["pr_key"]: row for row in env.DB.rows("SELECT pr_key, nudge_due_at, nudged_at FROM pr_review_asks")}
    assert rows["forge:owasp-blt/BLT#12"] == {"pr_key": "forge:owasp-blt/BLT#12", "nudge_due_at": None, "nudged_at": NOW + 86400}
    assert rows["forge:owasp-blt/BLT#13"]["nudged_at"] is None
    assert run(worker.process_pr_review_nudges(env, now=NOW + 2 * 86400))["due"] == 0
    assert len(net["posts"]) == 3


def test_nudges_can_be_turned_off_and_respect_the_limit(env, net):
    net["ledger"]["forkmesh/pulls"]["12"] = {"pull.md": pull_md()}
    env.PR_REVIEW_NUDGE = "0"
    handle(env, message("https://git.owaspblt.org/BLT/pulls/12"))
    assert env.DB.rows("SELECT nudge_due_at FROM pr_review_asks") == [{"nudge_due_at": None}]
    env.DB.queries.clear()
    assert run(worker.process_pr_review_nudges(env, now=NOW, limit=0)) == {"due": 0, "nudged": 0}
    assert env.DB.queries == []


def test_queries_use_indexes(env):
    plan = lambda sql, params: " ".join(str(row["detail"]) for row in env.DB.rows("EXPLAIN QUERY PLAN " + sql, params))  # noqa: E731
    recent = plan(worker.PR_REVIEW_RECENT_QUERY, ("T1", "k"))
    assert "USING INDEX sqlite_autoindex_pr_review_asks_1" in recent and "SCAN" not in recent
    due = plan(worker.PR_REVIEW_NUDGE_DUE_QUERY, (NOW, 3))
    assert "idx_pr_review_asks_nudge_due" in due and "SCAN pr_review_asks" not in due.replace("USING INDEX", "")
