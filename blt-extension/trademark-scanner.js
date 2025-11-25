// css
const style = document.createElement("style");
style.textContent = `
.tm-highlight {
  background: #fff3b0 !important;
  padding: 2px 4px;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.15);
  cursor: pointer;
  transition: background 0.2s ease;
}
.tm-highlight:hover {
  background: #ffe27a !important;
}
`;
document.head.appendChild(style);

function checkTrademark(keyword) {
  return new Promise(resolve => {
    chrome.runtime.sendMessage(
      { type: "CHECK_TRADEMARK", keyword },
      (response) => {

        if (!response || !response.ok) {
          resolve(null);
        } else {
          const data = response.data;

          if (data && data.available === false && Array.isArray(data.trademarks) && data.trademarks.length > 0) {
            resolve(data.trademarks);
          } else {
            resolve(null);
          }
        }
      }
    );
  });
}


function extractKeywords() {
  const text = document.body.innerText || "";
  const words = text.match(/\b[A-Z][a-zA-Z0-9]+\b/g) || [];
  return [...new Set(words)].filter(w => w.length > 2);
}

function highlightWordOnPage(word) {
  const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`\\b${escaped}\\b`, "g"); const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const tag = node.parentNode?.nodeName;
        if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEXTAREA" || tag === "NOSCRIPT") {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    }
  );

  let node;
  while ((node = walker.nextNode())) {
    regex.lastIndex = 0;
    if (!regex.test(node.nodeValue)) continue;

    const span = document.createElement('span');
    span.innerHTML = node.nodeValue.replace(
      regex,
      `<mark class="tm-highlight">${word}</mark>`
    );
    node.replaceWith(span);
  }
}

async function runTrademarkScan() {

  const keywords = extractKeywords();

  for (const kw of keywords) {
    const result = await checkTrademark(kw);
    if (result) {
      highlightWordOnPage(kw);
    }
    await new Promise(r => setTimeout(r, 200));
  }
}

chrome.runtime.onMessage.addListener((msg) => {

  if (msg.action === "RUN_TRADEMARK_SCAN") {
    runTrademarkScan();
  }
});
