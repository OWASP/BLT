// <blt-nav>: the OWASP BLT top bar, shared by every BLT site.
//
// One tag per site, served from owaspblt.org:
//   <script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>
// The bar goes first in <body>, or where a <blt-nav></blt-nav> element already is.
// It mirrors the owaspblt.org header: wasp brand, Why BLT / Explore / Get involved /
// Docs / Leaderboard / GSoC, BLT-Zero, Report Bug, the apps grid, the theme toggle
// and the mobile menu. Dependency-free; styles live in a shadow root, so the host
// page's CSS can't reach in and the bar's CSS can't leak out.
//
// Theme: same contract as owaspblt.org (_home/theme-init.js): class "dark" on <html>,
// saved as localStorage "theme" = "dark" | "light". The choice is also kept in a
// "blt-theme" cookie for .owaspblt.org so it follows you between BLT sites.
// Options, on the <script> tag or on a <blt-nav> element:
//   data-theme-toggle="off"     hide the toggle (the site keeps its own)
//   data-theme-key="name"       also save the choice under this localStorage key
//   data-theme-attr="data-theme" also set this <html> attribute to "dark" | "light"
//   data-sticky                 stick the bar to the top while scrolling
//   data-analytics="off"        don't load the shared analytics (blt-analytics.js)
// Every toggle fires window event "blt-theme-change" with detail { dark }.
// APPS must match the Explore cards in blt-home/public/index.html (a test checks).
(function () {
  "use strict";
  if (window.customElements && customElements.get("blt-nav")) return;

  var script = document.currentScript;
  var BASE = "https://owaspblt.org";
  try { if (script && script.src) BASE = new URL(script.src).origin; } catch (e) { /* keep default */ }
  var HOME = "https://owaspblt.org";
  var root = document.documentElement;

  // ---- Analytics -------------------------------------------------------------
  // The forge's first-party Analytics for every BLT site; what it sends and how to opt out
  // is in _shared/blt-analytics.js. Loaded once, after the bar, never blocking the page.
  (function loadAnalytics() {
    if (window.__bltAnalytics || (script && script.getAttribute("data-analytics") === "off")) return;
    var tag = document.createElement("script");
    tag.src = BASE + "/_shared/blt-analytics.js";
    tag.async = true;
    (document.head || root).appendChild(tag);
  })();

  var LINKS = [
    ["Why BLT", HOME + "/#why"],
    ["Explore", HOME + "/#explore"],
    ["Get involved", HOME + "/#get-involved"],
    ["Docs", "https://docs.owaspblt.org/"],
    ["Leaderboard", "https://pool.owaspblt.org/leaderboard"],
    ["GSoC", "https://gsoc.owaspblt.org/"],
  ];
  var ZERO = "https://zero.owaspblt.org/";
  var REPORT = "https://next.owaspblt.org/pages/report-bug.html";

  // [name, href, logo file in owaspblt.org/_home/logos/]
  var APPS = [
    ["BLT-Next", "https://next.owaspblt.org/", "blt-next.svg"],
    ["BLT-Pages", "https://pages.owaspblt.org/", "blt-pages.svg"],
    ["BLT-Zero", "https://zero.owaspblt.org/", "blt-zero.svg"],
    ["BLT-Extension", "https://extension.owaspblt.org/", "blt-extension.svg"],
    ["BLT-Flutter", "https://flutter.owaspblt.org/", "blt-flutter.svg"],
    ["BLT-CVE", "https://cve.owaspblt.org/", "blt-cve.svg"],
    ["BLT-Toasty", "https://toasty.owaspblt.org/", "blt-toasty.svg"],
    ["BLT-NetGuardian", "https://netguardian.owaspblt.org/", "blt-netguardian.svg"],
    ["BLT-Rewards", "https://rewards.owaspblt.org/", "blt-rewards.svg"],
    ["BLT-Pool", "https://pool.owaspblt.org/", "blt-pool.svg"],
    ["BLT-Hackathons", "https://hackathons.owaspblt.org/", "blt-hackathons.svg"],
    ["BLT-GSoC", "https://gsoc.owaspblt.org/", "blt-gsoc.svg"],
    ["MY-GSOC-TOOL", "https://gsoc-tool.owaspblt.org/", "my-gsoc-tool.svg"],
    ["BLT-Nexus", "https://nexus.owaspblt.org/", "blt-nexus.svg"],
    ["BLT-Profiles", "https://profiles.owaspblt.org/", "blt-profiles.svg"],
    ["BLT-Jobs", "https://jobs.owaspblt.org/", "blt-jobs.svg"],
    ["BLT-Newsletter", "https://newsletter.owaspblt.org/", "blt-newsletter.svg"],
    ["BLT-Lettuce", "https://lettuce.owaspblt.org/", "blt-lettuce.svg"],
    ["BLT-Sammich", "https://sammich.owaspblt.org/", "blt-sammich.svg"],
    ["BLT-Design-Contest", "https://contest.owaspblt.org/", "blt-design-contest.svg"],
    ["BLT-HackerHouse", "https://hackerhouse.owaspblt.org/", "blt-hackerhouse.svg"],
    ["BLT-Gitcaster", "https://gitcaster.owaspblt.org/", "blt-gitcaster.svg"],
    ["BLT-API", "https://api.owaspblt.org/", "blt-api.svg"],
    ["BLT-MCP", "https://mcp.owaspblt.org/", "blt-mcp.svg"],
    ["BLT-Leaf", "https://leaf.owaspblt.org/", "blt-leaf.svg"],
    ["BLT-Preflight", "https://preflight.owaspblt.org/", "blt-preflight.svg"],
    ["BLT-Monitor", "https://monitor.owaspblt.org/", "blt-monitor.svg"],
    ["BLT-Waypoint", "https://waypoint.owaspblt.org/", "blt-waypoint.svg"],
    ["BLT-Dash", "https://dash.owaspblt.org/", "blt-dash.svg"],
    ["BLT-Sizzle", "https://sizzle.owaspblt.org/", "blt-sizzle.svg"],
    ["BLT-Timer", "https://timer.owaspblt.org/", "blt-timer-web.svg"],
    ["BLT-Ketchup", "https://ketchup.owaspblt.org/", "blt-ketchup.svg"],
    ["BLT-SafeCloak", "https://safecloak.owaspblt.org/", "blt-safecloak.svg"],
    ["BLT-Vanish", "https://vanish.owaspblt.org/", "blt-vanish.svg"],
    ["BLT-Enforcement", "https://enforcement.owaspblt.org/", "blt-enforcement.svg"],
    ["BLT-Panini", "https://panini.owaspblt.org/", "blt-panini.svg"],
    ["BLT-OWASP-Bumper", "https://bumper.owaspblt.org/", "blt-owasp-bumper.svg"],
    ["BLT-OWASP-Projects", "https://projects.owaspblt.org/", "blt-owasp-projects.svg"],
    ["BLT-OWASP-Metadata", "https://metadata.owaspblt.org/", "blt-owasp-metadata.svg"],
    ["BLT-OWASP-Wich", "https://wich.owaspblt.org/", "blt-owasp-wich.svg"],
    ["BLT-Tomato", "https://tomato.owaspblt.org/", "blt-tomato.svg"],
    ["BLT-University", "https://university.owaspblt.org/", "blt-university.svg"],
    ["BLT-Docs", "https://docs.owaspblt.org/", "blt-docs.svg"],
    ["BLT-Start", "https://start.owaspblt.org/", "blt-start.svg"],
    ["BLT-OSSH", "https://ossh.owaspblt.org/", "blt-ossh.svg"],
    ["BLT-Byte", "https://byte.owaspblt.org/", "blt-byte.svg"],
    ["BLT-Ideas", "https://ideas.owaspblt.org/", "blt-ideas.svg"],
    ["BLT-Design", "https://design.owaspblt.org/", "blt-design.svg"],
  ];

  var CSS = [
    ":host{all:initial;display:block;position:relative;z-index:1000;font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;font-size:14px;line-height:20px;color:#111827;-webkit-font-smoothing:antialiased}",
    ":host([data-sticky]){position:sticky;top:0}",
    ":host([hidden]){display:none}",
    "*,*::before,*::after{box-sizing:border-box}",
    "a{color:inherit;text-decoration:none}",
    "button{font:inherit;color:inherit;background:none;border:0;padding:0;margin:0;cursor:pointer}",
    "a:focus-visible,button:focus-visible{outline:2px solid #dc2626;outline-offset:2px;border-radius:6px}",
    ".bar{background:rgba(255,255,255,.92);border-bottom:1px solid rgba(0,0,0,.06);-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px)}",
    ".in{max-width:80rem;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 24px}",
    ".brand{display:inline-flex;flex:none;align-items:center;gap:10px}",
    ".brand img{width:32px;height:32px;display:block}",
    ".brand span{font-size:18px;line-height:28px;font-weight:700;letter-spacing:-.025em;color:#111827}",
    ".brand b{color:#dc2626;font-weight:700}",
    ".links{display:none;align-items:center;gap:24px}",
    ".links a{color:#4b5563;transition:color .15s}",
    ".links a:hover{color:#111827}",
    ".right{display:flex;align-items:center;gap:8px}",
    ".zero{display:none;border-radius:6px;padding:8px 12px;color:#4b5563}",
    ".zero:hover{background:#f3f4f6;color:#111827}",
    ".report{display:none;align-items:center;justify-content:center;border-radius:6px;border-bottom:1.5px solid #b91c1c;background:linear-gradient(#ef4444,#dc2626);padding:8px 16px;font-weight:600;color:#fff;box-shadow:0 1px 2px rgba(0,0,0,.05);transition:transform .15s,box-shadow .15s}",
    ".report:hover{transform:translateY(-1px);box-shadow:0 10px 24px -12px rgba(220,38,38,.8)}",
    ".icon{display:flex;width:36px;height:36px;align-items:center;justify-content:center;border-radius:8px;color:#6b7280;transition:background .15s,color .15s}",
    ".icon:hover{background:#f3f4f6;color:#111827}",
    ".icon svg{display:block}",
    ".apps{position:relative;display:block}",
    ".panel{position:absolute;right:0;top:100%;margin-top:12px;display:none;width:26rem;max-width:calc(100vw - 2rem);border-radius:24px;border:1px solid #fee2e2;background:#fff;box-shadow:0 25px 50px -12px rgba(254,202,202,.6)}",
    ".panel.open{display:block;animation:pin .18s ease-out}",
    "@keyframes pin{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}",
    ".ph{display:flex;align-items:center;justify-content:space-between;padding:20px 20px 4px}",
    ".ph p{margin:0;font-weight:600;color:#111827}",
    ".ph a{font-size:12px;font-weight:500;color:#dc2626}",
    ".ph a:hover{text-decoration:underline}",
    ".scroll{max-height:22rem;overflow-y:auto;padding:4px 12px 20px}",
    ".grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));list-style:none;margin:0;padding:0}",
    ".grid a{display:flex;flex-direction:column;align-items:center;gap:6px;border-radius:16px;padding:12px 4px;transition:background .15s}",
    ".grid a:hover,.grid a[aria-current]{background:rgba(254,242,242,.8)}",
    ".grid img{width:40px;height:40px;object-fit:contain;transition:transform .15s}",
    ".grid a:hover img{transform:scale(1.05)}",
    ".grid span{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;line-height:16px;font-weight:500;color:#374151}",
    ".icon .moon{display:block}.icon .sun{display:none}",
    ".burger{display:flex;flex-direction:column;gap:5px}",
    ".burger i{display:block;width:20px;height:1px;background:#4b5563;transition:transform .2s,opacity .2s}",
    ".burger[aria-expanded=true] i:nth-child(1){transform:translateY(6px) rotate(45deg)}",
    ".burger[aria-expanded=true] i:nth-child(2){opacity:0}",
    ".burger[aria-expanded=true] i:nth-child(3){transform:translateY(-6px) rotate(-45deg)}",
    ".mobile{display:none;flex-direction:column;gap:4px;border-top:1px solid #f3f4f6;background:#fff;padding:12px 16px}",
    ".mobile.open{display:flex}",
    ".mobile a{border-radius:6px;padding:8px;color:#374151}",
    ".mobile a:hover{background:#f3f4f6}",
    ".mobile a.mreport{margin-top:4px;background:#dc2626;color:#fff;text-align:center;font-weight:600;padding:8px 12px}",
    "@media (max-width:767px){.in{padding:12px 16px}}",
    "@media (min-width:640px){.right{gap:8px}.report{display:inline-flex}}",
    "@media (min-width:768px){.zero{display:inline-flex}}",
    // Phones: the panel spans the screen under the bar instead of hanging off the button.
    "@media (max-width:767px){.panel{position:fixed;left:16px;right:16px;top:var(--blt-apps-top,68px);margin-top:0;width:auto;max-width:none}.scroll{max-height:calc(100vh - var(--blt-apps-top,68px) - 96px)}}",
    "@media (min-width:1024px){.links{display:flex}.burger,.mobile,.mobile.open{display:none}}",
    // dark
    ":host([dark]){color:#f3f4f6;color-scheme:dark}",
    ":host([dark]) .bar{background:rgba(3,7,18,.85);border-bottom-color:rgba(255,255,255,.1)}",
    ":host([dark]) .brand span{color:#fff}",
    ":host([dark]) .brand b{color:#ef4444}",
    ":host([dark]) .links a,:host([dark]) .zero{color:#d1d5db}",
    ":host([dark]) .links a:hover,:host([dark]) .zero:hover,:host([dark]) .icon:hover{color:#fff}",
    ":host([dark]) .zero:hover,:host([dark]) .icon:hover,:host([dark]) .mobile a:hover{background:#1f2937}",
    ":host([dark]) .icon{color:#9ca3af}",
    ":host([dark]) .panel{border-color:#1f2937;background:#111827;box-shadow:0 25px 50px -12px rgba(0,0,0,.5)}",
    ":host([dark]) .ph p{color:#fff}",
    ":host([dark]) .ph a{color:#f87171}",
    ":host([dark]) .grid a:hover,:host([dark]) .grid a[aria-current]{background:#1f2937}",
    ":host([dark]) .grid span{color:#d1d5db}",
    ":host([dark]) .icon .moon{display:none}:host([dark]) .icon .sun{display:block}",
    ":host([dark]) .burger i{background:#d1d5db}",
    ":host([dark]) .mobile{background:#030712;border-top-color:#1f2937}",
    ":host([dark]) .mobile a{color:#e5e7eb}",
    ":host([dark]) .mobile a.mreport{color:#fff}",
    "@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}",
  ].join("\n");

  function opt(host, name) {
    if (host.hasAttribute(name)) return host.getAttribute(name);
    return script && script.hasAttribute(name) ? script.getAttribute(name) : null;
  }

  // ---- Theme ---------------------------------------------------------------
  var COOKIE = "blt-theme";
  function readCookie() {
    var m = document.cookie.match(/(?:^|;\s*)blt-theme=(dark|light)/);
    return m ? m[1] : null;
  }
  function saved() {
    try { var v = localStorage.getItem("theme"); if (v === "dark" || v === "light") return v; } catch (e) { /* private mode */ }
    return readCookie();
  }
  function isDark() {
    return root.classList.contains("dark") || root.getAttribute("data-theme") === "dark";
  }
  function applyTheme(dark, host) {
    root.classList.toggle("dark", dark);
    var attr = host && opt(host, "data-theme-attr");
    if (attr) root.setAttribute(attr, dark ? "dark" : "light");
  }
  function saveTheme(dark, host) {
    var v = dark ? "dark" : "light";
    try {
      localStorage.setItem("theme", v);
      var key = host && opt(host, "data-theme-key");
      if (key) localStorage.setItem(key, v);
    } catch (e) { /* private mode */ }
    if (/(^|\.)owaspblt\.org$/.test(location.hostname)) {
      document.cookie = COOKIE + "=" + v + "; domain=owaspblt.org; path=/; max-age=31536000; SameSite=Lax; Secure";
    }
  }
  // A saved choice (this site's, else one made on another BLT site) is applied here too,
  // so sites without their own theme script still remember it. With no saved choice the
  // page's own theme script (or its default) decides.
  (function applySaved() {
    var v = saved();
    if (v && (v === "dark") !== isDark()) root.classList.toggle("dark", v === "dark");
  })();

  // ---- DOM helpers -----------------------------------------------------------
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "text") n.textContent = attrs[k];
      else if (k === "class") n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  var SVGNS = "http://www.w3.org/2000/svg";
  function svg(cls, size, viewBox, parts, stroke) {
    var s = document.createElementNS(SVGNS, "svg");
    if (cls) s.setAttribute("class", cls);
    s.setAttribute("width", size); s.setAttribute("height", size);
    s.setAttribute("viewBox", viewBox); s.setAttribute("aria-hidden", "true");
    if (stroke) {
      s.setAttribute("fill", "none"); s.setAttribute("stroke", "currentColor");
      s.setAttribute("stroke-width", "2"); s.setAttribute("stroke-linecap", "round");
    } else s.setAttribute("fill", "currentColor");
    parts.forEach(function (p) {
      var n = document.createElementNS(SVGNS, p[0]);
      for (var k in p[1]) n.setAttribute(k, p[1][k]);
      s.appendChild(n);
    });
    return s;
  }
  function sameSite(href) {
    try {
      var u = new URL(href);
      return u.hostname === location.hostname && (u.pathname === "/" || location.pathname.indexOf(u.pathname) === 0);
    } catch (e) { return false; }
  }

  // ---- The element -----------------------------------------------------------
  class BltNav extends HTMLElement {
    connectedCallback() { build(this); }
  }

  function build(host) {
    if (host._built) return;
    host._built = true;
    var shadow = host.attachShadow({ mode: "open" });
    try {
      var sheet = new CSSStyleSheet();
      sheet.replaceSync(CSS);
      shadow.adoptedStyleSheets = [sheet];
    } catch (e) {
      shadow.appendChild(el("style", { text: CSS }));
    }
    if (opt(host, "data-sticky") !== null) host.setAttribute("data-sticky", "");

    // brand
    var brandText = el("span", { text: "OWASP " }, [el("b", { text: "BLT" })]);
    var brand = el("a", { class: "brand", href: HOME + "/", "aria-label": "OWASP BLT home" }, [
      el("img", { src: BASE + "/_home/blt-logo.svg", alt: "", width: "32", height: "32" }),
      brandText,
    ]);

    var links = el("nav", { class: "links", "aria-label": "OWASP BLT" },
      LINKS.map(function (l) { return el("a", { href: l[1], text: l[0] }); }));

    // apps launcher
    var grid = el("ul", { class: "grid" });
    var built = false;
    function buildApps() {
      if (built) return;
      built = true;
      APPS.forEach(function (p) {
        var a = el("a", { href: p[1] }, [
          el("img", { src: BASE + "/_home/logos/" + p[2], alt: "", width: "40", height: "40", decoding: "async" }),
          el("span", { text: p[0].replace(/^BLT-/, "") }),
        ]);
        if (sameSite(p[1])) a.setAttribute("aria-current", "page");
        grid.appendChild(el("li", null, [a]));
      });
    }
    var panel = el("div", { class: "panel", id: "panel", role: "dialog", "aria-label": "BLT apps" }, [
      el("div", { class: "ph" }, [el("p", { text: "BLT apps" }), el("a", { href: HOME + "/#explore", text: "Browse by category" })]),
      el("div", { class: "scroll" }, [grid]),
    ]);
    var dots = [];
    [5, 12, 19].forEach(function (y) { [5, 12, 19].forEach(function (x) { dots.push(["circle", { cx: x, cy: y, r: 2 }]); }); });
    var appsBtn = el("button", { class: "icon", type: "button", "aria-expanded": "false", "aria-controls": "panel", "aria-label": "All BLT apps" },
      [svg(null, 20, "0 0 24 24", dots)]);
    var apps = el("div", { class: "apps" }, [appsBtn, panel]);
    function setApps(open) {
      if (open) {
        buildApps();
        // On phones the panel is fixed under the bar wherever the page has scrolled.
        var bottom = Math.round(host.getBoundingClientRect().bottom);
        panel.style.setProperty("--blt-apps-top", Math.max(bottom, 0) + 8 + "px");
      }
      panel.classList.toggle("open", open);
      appsBtn.setAttribute("aria-expanded", String(open));
    }
    appsBtn.addEventListener("click", function (e) { e.stopPropagation(); setApps(!panel.classList.contains("open")); });
    document.addEventListener("click", function (e) { if (e.target !== host) setApps(false); });
    shadow.addEventListener("click", function (e) { if (!apps.contains(e.target)) setApps(false); });

    // theme toggle
    var toggle = null;
    if (opt(host, "data-theme-toggle") !== "off") {
      toggle = el("button", { class: "icon", type: "button" }, [
        svg("moon", 18, "0 0 24 24", [["path", { d: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" }]], true),
        svg("sun", 18, "0 0 24 24", [["circle", { cx: 12, cy: 12, r: 4 }], ["path", { d: "M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" }]], true),
      ]);
      toggle.addEventListener("click", function () {
        var dark = !isDark();
        applyTheme(dark, host);
        saveTheme(dark, host);
        window.dispatchEvent(new CustomEvent("blt-theme-change", { detail: { dark: dark } }));
      });
    }

    // mobile
    var burger = el("button", { class: "icon burger", type: "button", "aria-label": "Menu", "aria-expanded": "false", "aria-controls": "mobile" },
      [el("i"), el("i"), el("i")]);
    var mobile = el("nav", { class: "mobile", id: "mobile", "aria-label": "OWASP BLT mobile" },
      LINKS.map(function (l) { return el("a", { href: l[1], text: l[0] }); })
        .concat([el("a", { href: ZERO, text: "BLT-Zero" }), el("a", { class: "mreport", href: REPORT, text: "Report Bug" })]));
    function setMobile(open) {
      mobile.classList.toggle("open", open);
      burger.setAttribute("aria-expanded", String(open));
    }
    burger.addEventListener("click", function () { setMobile(!mobile.classList.contains("open")); });

    shadow.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (panel.classList.contains("open")) { setApps(false); appsBtn.focus(); }
      if (mobile.classList.contains("open")) { setMobile(false); burger.focus(); }
    });

    var right = el("div", { class: "right" }, [
      el("a", { class: "zero", href: ZERO, text: "BLT-Zero" }),
      el("a", { class: "report", href: REPORT, text: "Report Bug" }),
      apps, toggle, burger,
    ]);
    shadow.appendChild(el("header", { class: "bar", part: "bar" }, [el("div", { class: "in" }, [brand, links, right]), mobile]));

    // follow the page's theme, whoever changes it
    function sync() {
      var dark = isDark();
      host.toggleAttribute("dark", dark);
      if (toggle) toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    }
    sync();
    new MutationObserver(sync).observe(root, { attributes: true, attributeFilter: ["class", "data-theme"] });
  }

  customElements.define("blt-nav", BltNav);

  function mount() {
    if (document.querySelector("blt-nav")) return;
    var nav = document.createElement("blt-nav");
    document.body.insertBefore(nav, document.body.firstChild);
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
