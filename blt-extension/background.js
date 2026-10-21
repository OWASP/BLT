const TRADEMARK_SEARCH_UNAVAILABLE =
  "Trademark search is not available yet: it is moving to the new BLT platform.";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "CHECK_TRADEMARK") {
    // The trademark search lived in the old BLT app (legacy.owaspblt.org), which is offline
    // while its data is migrated, and the new BLT API has no trademark search yet.
    // Answer right away instead of sending page keywords to a server that isn't there.
    sendResponse({ ok: false, error: TRADEMARK_SEARCH_UNAVAILABLE });
    return false;
  }

  if (msg.action === "takeScreenshot") {
    chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      chrome.downloads.download({
        url: dataUrl,
        filename: "screenshot.png"
      });
    });
  }
});
