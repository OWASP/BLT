chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "takeScreenshot") {
    chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      chrome.downloads.download({
        url: dataUrl,
        filename: "screenshot.png"
      });
    });
  }
});
