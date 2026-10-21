// HTML-escaping helpers shared by the dashboard pages. DataTables renders cell strings as HTML,
// and the data comes from GitHub (issue titles, repo names) and OWASP project metadata, so every
// value is escaped before it lands in a cell and only http(s) URLs are used as links.
(function (root) {
  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Returns the URL if it is an absolute http(s) URL, otherwise null.
  function safeHref(value) {
    if (typeof value !== "string" || !value.trim()) return null;
    try {
      const url = new URL(value.trim());
      return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
    } catch (e) {
      return null;
    }
  }

  // <a> to an http(s) URL with escaped text; plain escaped text when the URL is unsafe.
  function linkHtml(href, text) {
    const label = escapeHtml(text === undefined ? href : text);
    const url = safeHref(href);
    return url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label;
  }

  // GitHub label colours are 6 hex digits; anything else falls back to grey.
  function safeHexColor(value) {
    return /^[0-9a-fA-F]{6}$/.test(String(value)) ? String(value) : "cccccc";
  }

  const api = { escapeHtml, safeHref, linkHtml, safeHexColor };
  Object.assign(root, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
