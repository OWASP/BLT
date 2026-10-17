chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "CHECK_TRADEMARK") {
    const url = `https://owaspblt.org/api/trademarks/search?query=${encodeURIComponent(msg.keyword)}`;

    fetch(url)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.toString() }));
    return true; // async response
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
