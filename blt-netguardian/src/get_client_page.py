"""Landing copy for /get-client (Worker serves HTML; assets are flaky)."""

GET_CLIENT_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NetGuardian client — run locally</title>
  <script>
    // Before first paint: the saved theme (localStorage "theme", shared with the <blt-nav> bar), else the system preference.
    (function () {
      var saved = null;
      try { saved = localStorage.getItem("theme"); } catch (e) { saved = null; }
      var dark = saved === "dark" || (saved !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
      document.documentElement.classList.toggle("dark", dark);
    })();
  </script>
  <script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>
  <style>
    blt-nav:not(:defined){display:block;min-height:61px}blt-nav:not(:defined)>*{display:none}
    /* owaspblt.org palette: gray surfaces, BLT red accent; html.dark for dark mode */
    :root { --bg: #f9fafb; --panel: #ffffff; --line: #e5e7eb; --ink: #111827; --red: #dc2626; --gold: #b91c1c; --muted: #6b7280; --code-bg: #f3f4f6; }
    :root.dark { color-scheme: dark; --bg: #030712; --panel: #111827; --line: #1f2937; --ink: #f3f4f6; --red: #f87171; --gold: #f87171; --muted: #9ca3af; --code-bg: #111827; }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; background: var(--bg); color: var(--ink);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    main { max-width: 720px; margin: 0 auto; padding: 32px 24px; }
    h1 { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-weight: 800; color: var(--red); letter-spacing: 0.16em; font-size: 1rem; }
    p, li { color: var(--muted); font-size: 13px; line-height: 1.55; }
    a { color: var(--gold); }
    code, pre {
      color: var(--gold); font-size: 11px; word-break: break-all;
      white-space: pre-wrap; background: var(--code-bg); padding: 12px; display: block;
      border: 1px solid var(--line); border-radius: 0.75rem; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    strong.hl { color: var(--ink); }
  </style>
</head>
<body>
  <blt-nav project="blt-netguardian" name="NetGuardian">
    <a href="/get-client" aria-current="page">Client</a>
    <a href="/triage">Triage</a>
    <a href="https://git.owaspblt.org/BLT/BLT-NetGuardian/blob/main/docs/spec/quickstart.md">Quickstart</a>
    <a href="https://git.owaspblt.org/BLT/BLT-NetGuardian" slot="actions">Source</a>
  </blt-nav>
  <main>
    <h1>CLIENT (YOUR MACHINE)</h1>
    <p>
      This is a desktop/web <strong class="hl">app you run locally</strong>, not a page on this Worker.
      Scanning from the NetGuardian site is disabled. After you start it, the UI is on
      <strong class="hl">your computer</strong> — usually <a href="http://localhost:8888">http://localhost:8888</a>
      (Chrome) or a macOS window. Triage stays on this site.
    </p>
    <p>Needs <a href="https://flutter.dev/docs/get-started/install">Flutter</a> on PATH.</p>
    <pre>git clone https://git.owaspblt.org/BLT.git
cd blt-netguardian/client
flutter pub get

# See the GUI in Chrome (this machine only):
flutter run -d chrome --web-port=8888
# then open http://localhost:8888

# Real device-side scan (no browser CORS): macOS / Windows / Linux desktop
flutter run -d macos</pre>
    <p>
      Production orgs: the <strong class="hl">site owner</strong> registers with
      BLT / NetGuardian and issues HMAC + payload + triage keys to researchers.
      The client alone is not enough without those org keys.
      Docs:
      <a href="https://git.owaspblt.org/BLT/BLT-NetGuardian/blob/main/README.md">README</a>
      ·
      <a href="https://git.owaspblt.org/BLT/BLT-NetGuardian/tree/main/docs/spec">docs/spec</a>.
    </p>
    <p>
      In the app, set API base URL to
      <code style="display:inline;padding:2px 6px">https://netguardian.owaspblt.org</code>
      (or your staging Worker) and paste the keys your org issued.
      Staging demos may use shared <code style="display:inline;padding:2px 6px">org-demo</code> keys.
      Chrome on localhost needs that origin listed in
      <code style="display:inline;padding:2px 6px">CORS_ALLOWED_ORIGINS</code>.
      For a fully offline demo, run
      <code style="display:inline;padding:2px 6px">python3 local_dev/serve.py</code>
      and set the base URL to
      <code style="display:inline;padding:2px 6px">http://127.0.0.1:8787</code>.
    </p>
    <p>
      Source:
      <a href="https://git.owaspblt.org/BLT/BLT-NetGuardian/tree/main/client">client/</a>
      ·
      <a href="https://git.owaspblt.org/BLT/archive/main/blt-netguardian-main.zip">zip of repo</a>
    </p>
    <p>
      Headless alternative (not the GUI):
      <code style="display:inline;padding:2px 6px">curl -fsSL https://netguardian.owaspblt.org/install.sh | sh -s -- https://example.com</code>
    </p>
  </main>
</body>
</html>
'''
