chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "CHECK_TRADEMARK") {
    const url = `https://owaspblt.org/api/trademarks/search?query=${encodeURIComponent(msg.keyword)}`;

    fetch(url)
      .then(res => res.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.toString() }));

    return true; // async response
  }
});

