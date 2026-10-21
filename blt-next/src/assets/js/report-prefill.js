// Fill the report form's URL field from ?url= (the browser extension opens
// /pages/report-bug?url=<page it was on>). Only http(s) URLs are used.
document.addEventListener('DOMContentLoaded', () => {
  const field = document.getElementById('bugUrl');
  const value = new URLSearchParams(window.location.search).get('url');
  if (!field || !value || field.value) return;
  try {
    const parsed = new URL(value);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') field.value = parsed.href;
  } catch (e) {
    // not a URL: leave the field empty
  }
});
