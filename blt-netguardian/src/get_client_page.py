"""Landing copy for /get-client (Worker serves HTML; assets are flaky)."""

GET_CLIENT_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NetGuardian client — run locally</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #0d0000; --red: #ff2020; --gold: #c9a227; --muted: #888; }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; background: var(--bg); color: #eee;
      font-family: "Share Tech Mono", ui-monospace, monospace; padding: 32px 24px;
    }
    main { max-width: 720px; margin: 0 auto; }
    h1 { font-family: Orbitron, sans-serif; color: var(--red); letter-spacing: 0.16em; font-size: 1rem; }
    p, li { color: var(--muted); font-size: 13px; line-height: 1.55; }
    a { color: var(--gold); }
    code, pre {
      color: var(--gold); font-size: 11px; word-break: break-all;
      white-space: pre-wrap; background: #1a0000; padding: 12px; display: block;
      border: 1px solid #400;
    }
    .back { color: var(--muted); font-size: 12px; }
  </style>
</head>
<body>
  <main>
    <p class="back"><a href="/">← NetGuardian</a></p>
    <h1>CLIENT (YOUR MACHINE)</h1>
    <p>
      This is a desktop/web <strong style="color:#eee">app you run locally</strong>, not a page on this Worker.
      Scanning from the NetGuardian site is disabled. After you start it, the UI is on
      <strong style="color:#eee">your computer</strong> — usually <a href="http://localhost:8888">http://localhost:8888</a>
      (Chrome) or a macOS window. Triage stays on this site.
    </p>
    <p>Needs <a href="https://flutter.dev/docs/get-started/install">Flutter</a> on PATH.</p>
    <pre>git clone https://gitlab.com/owasp-blt/blt-netguardian.git
cd blt-netguardian/client
flutter pub get

# See the GUI in Chrome (this machine only):
flutter run -d chrome --web-port=8888
# then open http://localhost:8888

# Real device-side scan (no browser CORS): macOS / Windows / Linux desktop
flutter run -d macos</pre>
    <p>
      Production orgs: the <strong style="color:#eee">site owner</strong> registers with
      BLT / NetGuardian and issues HMAC + payload + triage keys to researchers.
      The client alone is not enough without those org keys.
      Docs:
      <a href="https://gitlab.com/owasp-blt/blt-netguardian/-/blob/main/README.md">README</a>
      ·
      <a href="https://gitlab.com/owasp-blt/blt-netguardian/-/tree/main/docs/spec">docs/spec</a>.
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
      <a href="https://gitlab.com/owasp-blt/blt-netguardian/-/tree/main/client">client/</a>
      ·
      <a href="https://gitlab.com/owasp-blt/blt-netguardian/-/archive/main/blt-netguardian-main.zip">zip of repo</a>
    </p>
    <p>
      Headless alternative (not the GUI):
      <code style="display:inline;padding:2px 6px">curl -fsSL https://netguardian.owaspblt.org/install.sh | sh -s -- https://example.com</code>
    </p>
  </main>
</body>
</html>
'''
