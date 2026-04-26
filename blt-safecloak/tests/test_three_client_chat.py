"""
E2E test: three clients join the same video-chat room, chat with each other,
a participant disconnects, a new client joins and receives the full
chat history from one of the remaining peers.

Scenario
--------
1.  Three browser contexts (Client 1, Client 2, Client 3) open the same
    video-room URL and form a full-mesh (each sees the other two).
2.  Each client sends a unique chat message and the test verifies that all
    three messages appear in the chat panel of every connected client.
3.  Client 3 closes its page, simulating a disconnect.
4.  A new browser context (Client 4) joins the room by calling Client 1.
5.  The test asserts that Client 4's chat panel shows all three messages that
    were exchanged *before* it joined – chat history received from a peer.

Infrastructure reuse
--------------------
This test shares the ``app_server_url`` and ``peerjs_server`` session-scoped
fixtures defined in ``test_video_chat.py``.  Both files must be collected in
the same pytest session (the default when running ``pytest tests/``).

Local setup::

    npm install
    pip install -r requirements-dev.txt
    playwright install chromium --with-deps

Run::

    pytest tests/ -v -k chat
"""

import pytest
from playwright.sync_api import sync_playwright

# Reuse infrastructure constants and helpers from the existing test module.
# Use a bare module name (not ``tests.test_video_chat``) because the tests/
# directory is not a Python package: pytest's default import mode adds it
# directly to sys.path, so only the bare name resolves correctly in CI.
from test_video_chat import (
    TIMEOUT_MS,
    _BROWSER_ARGS,
    _MOCK_GET_USER_MEDIA,
    _STREAM_CHECK_JS,
    _accept_consent,
    _new_context,
    _peer_id,
    app_server_url,  # noqa: F401 – imported so pytest can discover the fixture
    peerjs_server,   # noqa: F401 – imported so pytest can discover the fixture
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Unique sentinel strings used to identify each client's outgoing message.
_MSG1 = "hello-from-client-one"
_MSG2 = "hello-from-client-two"
_MSG3 = "hello-from-client-three"


def _send_chat(page, text: str) -> None:
    """Type *text* into the chat input and submit the form."""
    page.fill("#chat-input", text)
    page.click("#btn-send-chat")


def _chat_messages_text(page) -> list[str]:
    """Return the text content of all chat message <p> elements (chronological)."""
    return page.evaluate(
        """() => {
            return Array.from(
                document.querySelectorAll('#chat-messages p')
            ).map(el => el.textContent.trim());
        }"""
    )


def _wait_for_chat_message(page, text: str, timeout: int = TIMEOUT_MS) -> None:
    """Block until *text* appears anywhere inside ``#chat-messages``."""
    page.wait_for_function(
        f"""() => {{
            const container = document.getElementById('chat-messages');
            return container && container.textContent.includes({text!r});
        }}""",
        timeout=timeout,
    )


def _accept_consent_if_present(page, timeout: int = 2000) -> None:
    """Click 'I Consent' only when the dialog is actually visible.

    Already-consented peers do not show the dialog on subsequent calls, so
    calling the blocking ``_accept_consent`` helper would time out.  This
    variant uses a short timeout and silently skips when the selector is absent.
    """
    try:
        page.wait_for_selector("#consent-allow", timeout=timeout)
        page.click("#consent-allow")
    except Exception:
        pass  # dialog not present – peer already consented


def _establish_full_mesh(p1, p2, p3, id1, id2, id3) -> None:
    """Wire up a full-mesh between three pages (replicates the pattern from
    ``test_three_clients_connect_and_see_cameras``).

    Raises ``ValueError`` if any peer ID is empty or not unique, catching
    setup mistakes before the mesh wiring even begins.
    """
    peer_ids = (id1, id2, id3)
    if any(not peer_id for peer_id in peer_ids):
        raise ValueError("All peer IDs must be non-empty before establishing the mesh.")
    if len(set(peer_ids)) != 3:
        raise ValueError("Expected three distinct peer IDs for the full-mesh setup.")

    # Step 1: Client 2 → Client 1
    p2.fill("#remote-id", id1)
    p2.click("#btn-call")
    _accept_consent(p2)  # caller consents
    _accept_consent(p1)  # callee consents

    p1.wait_for_function(
        "document.querySelectorAll('.video-wrapper').length >= 2",
        timeout=TIMEOUT_MS,
    )
    p2.wait_for_function(
        "document.querySelectorAll('.video-wrapper').length >= 2",
        timeout=TIMEOUT_MS,
    )

    # Step 2: Client 3 → Client 1 (auto-mesh completes via peer-list exchange)
    p3.fill("#remote-id", id1)
    p3.click("#btn-call")
    _accept_consent(p3)  # caller consents
    # p1 already consented – no second dialog

    # Step 3: Wait for full mesh (3 wrappers each: 1 local + 2 remote)
    for page in (p1, p2, p3):
        page.wait_for_function(
            "document.querySelectorAll('.video-wrapper').length >= 3",
            timeout=TIMEOUT_MS,
        )


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_three_clients_chat_and_new_joiner_receives_history(app_server_url):
    """
    Full scenario:

    1.  Three clients form a full mesh and assert they all see each other's
        camera streams (same assertion as ``test_three_clients_connect_and_see_cameras``).
    2.  Each client sends a unique message; every client must see all three
        messages in its own chat panel.
    3.  Client 3 (the last-joined peer) closes its page (disconnect).
    4.  A new (fourth) client joins the room by calling one of the remaining
        two peers.
    5.  The new client's chat panel must contain all three messages that were
        sent *before* it joined, proving that chat history is correctly
        replayed via the data channel.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=_BROWSER_ARGS)
        try:
            # ── Spin up three browser contexts ───────────────────────────────
            ctx1 = _new_context(browser)
            ctx2 = _new_context(browser)
            ctx3 = _new_context(browser)

            p1 = ctx1.new_page()
            p2 = ctx2.new_page()
            p3 = ctx3.new_page()

            video_url = f"{app_server_url}/video-room?mic=on&cam=on"
            for page in (p1, p2, p3):
                page.goto(video_url)

            # ── Collect peer IDs ─────────────────────────────────────────────
            id1 = _peer_id(p1)
            id2 = _peer_id(p2)
            id3 = _peer_id(p3)
            assert id1 and id2 and id3, "All three clients must receive a peer ID"
            assert len({id1, id2, id3}) == 3, "All peer IDs must be unique"

            # ── Form the full mesh ───────────────────────────────────────────
            _establish_full_mesh(p1, p2, p3, id1, id2, id3)

            # ── Assert camera streams are live on every client ───────────────
            for page, name in ((p1, "Client 1"), (p2, "Client 2"), (p3, "Client 3")):
                page.wait_for_function(_STREAM_CHECK_JS, timeout=TIMEOUT_MS)
                assert page.evaluate(_STREAM_CHECK_JS), (
                    f"{name} should see live streams from both other participants"
                )

            # ── Each client sends a unique message ───────────────────────────
            _send_chat(p1, _MSG1)
            _send_chat(p2, _MSG2)
            _send_chat(p3, _MSG3)

            # ── Every client must receive all three messages ──────────────────
            for page, name in ((p1, "Client 1"), (p2, "Client 2"), (p3, "Client 3")):
                for msg in (_MSG1, _MSG2, _MSG3):
                    _wait_for_chat_message(page, msg)

                panel_texts = _chat_messages_text(page)
                assert any(_MSG1 in t for t in panel_texts), (
                    f"{name}: message from Client 1 not found in chat panel"
                )
                assert any(_MSG2 in t for t in panel_texts), (
                    f"{name}: message from Client 2 not found in chat panel"
                )
                assert any(_MSG3 in t for t in panel_texts), (
                    f"{name}: message from Client 3 not found in chat panel"
                )

            # ── Disconnect Client 3 (deterministic choice) ──────────────────
            # Always disconnect the last-joined peer so the test is reproducible
            # and CI retries converge consistently.
            leaving_page, leaving_ctx, leaving_name = p3, ctx3, "Client 3"
            remaining = [(p1, ctx1, id1, "Client 1"), (p2, ctx2, id2, "Client 2")]

            leaving_page.close()
            leaving_ctx.close()

            # Wait until the remaining peers detect the disconnection and their
            # video-wrapper count drops back to 2 (1 local + 1 remote).
            for page, _, _, name in remaining:
                page.wait_for_function(
                    "document.querySelectorAll('.video-wrapper').length === 2",
                    timeout=TIMEOUT_MS,
                )

            # ── New client (Client 4) joins by calling a remaining peer ───────
            ctx4 = _new_context(browser)
            p4 = ctx4.new_page()
            p4.goto(video_url)

            id4 = _peer_id(p4)
            assert id4, "Client 4 must receive a peer ID"
            assert id4 not in {id1, id2, id3}, "Client 4 must get a unique peer ID"

            # Call the first remaining peer.
            target_page, _target_ctx, target_id, target_name = remaining[0]

            p4.fill("#remote-id", target_id)
            p4.click("#btn-call")
            _accept_consent(p4)                      # new joiner – first call, always shows dialog
            _accept_consent_if_present(target_page)  # already-consented peer – dialog may be absent

            # Wait for Client 4 to be connected to at least one peer.
            # The app's auto-mesh sends Client 1's peer list [id2] to Client 4
            # immediately after the data channel opens, so Client 4 may quickly
            # auto-call Client 2 as well and end up with 3 wrappers (itself +
            # Client 1 + Client 2) rather than pausing at exactly 2.  Use >=
            # to avoid a race where the brief 2-wrapper state is never polled.
            p4.wait_for_function(
                "document.querySelectorAll('.video-wrapper').length >= 2",
                timeout=TIMEOUT_MS,
            )
            # target_page (Client 1) already has 2 wrappers (itself + Client 2)
            # before Client 4 joins.  Wait for a third wrapper to confirm that
            # Client 4's incoming call was actually answered and handled.
            target_page.wait_for_function(
                "document.querySelectorAll('.video-wrapper').length >= 3",
                timeout=TIMEOUT_MS,
            )

            # ── Client 4 must receive the full chat history ───────────────────
            for msg in (_MSG1, _MSG2, _MSG3):
                _wait_for_chat_message(p4, msg)

            history_texts = _chat_messages_text(p4)
            assert any(_MSG1 in t for t in history_texts), (
                "Client 4 should see the message sent by Client 1 in its chat history"
            )
            assert any(_MSG2 in t for t in history_texts), (
                "Client 4 should see the message sent by Client 2 in its chat history"
            )
            assert any(_MSG3 in t for t in history_texts), (
                "Client 4 should see the message sent by Client 3 in its chat history"
            )

        finally:
            browser.close()
