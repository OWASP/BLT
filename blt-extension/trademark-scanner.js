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

// Maximum number of keywords to process per scan to prevent long-running scans
const MAX_TRADEMARK_KEYWORDS = 200;

function checkTrademark(keyword) {
  return new Promise(resolve => {
    chrome.runtime.sendMessage(
      { type: "CHECK_TRADEMARK", keyword },
      (response) => {
        // Check for chrome.runtime.lastError to handle transport failures
        if (chrome.runtime.lastError || !response || !response.ok) {
          if (chrome.runtime.lastError) {
            console.warn('Trademark check failed:', chrome.runtime.lastError.message);
          }
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
  const unique = [...new Set(words)].filter(w => w.length > 2);
  // Limit keywords to prevent multi-minute scans on large pages
  return unique.slice(0, MAX_TRADEMARK_KEYWORDS);
}

function highlightWordOnPage(word) {
  const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`\\b${escaped}\\b`, "g");
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const parent = node.parentNode;
        if (!parent) return NodeFilter.FILTER_REJECT;

        const parentEl =
          parent.nodeType === Node.ELEMENT_NODE ? parent : null;

        // Skip any text already wrapped in our own highlight markup.
        if (
          parentEl &&
          (parentEl.nodeName === "MARK" ||
            parentEl.closest(".tm-highlight"))
        ) {
          return NodeFilter.FILTER_REJECT;
        }

        const tag = parent.nodeName;
        if (
          tag === "SCRIPT" ||
          tag === "STYLE" ||
          tag === "TEXTAREA" ||
          tag === "NOSCRIPT"
        ) {
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

// Flag to prevent overlapping scans
let isTrademarkScanRunning = false;

async function runTrademarkScan() {
  // Prevent concurrent scans if button is clicked multiple times
  if (isTrademarkScanRunning) {
    console.log('Trademark scan already in progress, skipping...');
    return;
  }

  isTrademarkScanRunning = true;
  try {
    const keywords = extractKeywords();

    for (const kw of keywords) {
      const result = await checkTrademark(kw);
      if (result) {
        highlightWordOnPage(kw);
      }
      await new Promise(r => setTimeout(r, 200));
    }
  } finally {
    isTrademarkScanRunning = false;
  }
}

chrome.runtime.onMessage.addListener((msg) => {

  if (msg.action === "RUN_TRADEMARK_SCAN") {
    runTrademarkScan();
  }
});

