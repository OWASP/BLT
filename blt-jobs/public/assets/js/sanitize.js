/**
 * Shared sanitization helpers.
 * Exposed as window.Sanitize = { esc, safeUrl }
 */
(function () {
  /**
   * Escape a value for safe insertion into HTML — both text nodes and
   * quoted attribute values (escapes &, <, >, ", ', ` and NBSP).
   */
  function esc(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/`/g, "&#96;")
      .replace(/\u00a0/g, "&nbsp;");
  }

  /**
   * Validate and normalize a URL. Only http/https are allowed.
   * Returns the parser-normalized u.href on success, or "" on failure.
   */
  function safeUrl(url) {
    if (!url) return "";
    try {
      const u = new URL(url);
      return u.protocol === "https:" || u.protocol === "http:" ? u.href : "";
    } catch (e) {
      return "";
    }
  }

  window.Sanitize = { esc, safeUrl };
})();
