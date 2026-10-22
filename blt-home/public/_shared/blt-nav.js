// <blt-nav>: the OWASP BLT top bar, shared by every BLT site. It is the only header a BLT
// site shows: the OWASP BLT brand, then this site's project and its own links and buttons.
//
// One tag per site, served from owaspblt.org:
//   <script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>
// The bar goes first in <body>, or where a <blt-nav></blt-nav> element already is.
// Dependency-free; styles live in a shadow root, so the host page's CSS can't reach in
// and the bar's CSS can't leak out.
//
// Per-site config: attributes on the <blt-nav> element, and the site's own links and
// buttons as its children (they stay in the page's DOM, so the site's own click handlers,
// routers and active-state code keep working on them):
//   <blt-nav project="blt-zero" name="Zero" home="/" data-sticky>
//     <a href="/" aria-current="page">Submit</a>          <- site links: centre of the bar
//     <a href="/docs/security">Security</a>
//     <a href="/admin/onboard" slot="actions">Admin</a>   <- slot="actions": right, before the apps dots
//     <a href="https://git.owaspblt.org/BLT/BLT-Zero" slot="actions" data-primary>Contribute</a>
//   </blt-nav>
//   project="blt-x"   the project's slug: its round symbol is owaspblt.org/_home/symbols/blt-x.svg.
//                     Optional on a *.owaspblt.org site listed in APPS (found from the host name);
//                     project="none" shows no project part (the owaspblt.org bar).
//   name="X"          the project's short name next to its symbol (default: from APPS, "BLT-" dropped)
//   home="/"          where the project's symbol and name link to (default "/")
//   current="auto"    mark the child link to this page (same path) with aria-current="page",
//                     unless the site's own code marks one; aria-current="false" on a child
//                     keeps it unmarked (e.g. a user-name link to the same page)
//   Children: <a> or <button>. slot="actions" puts one on the right; data-primary makes it the
//   red button. aria-current="page" (or class "active") marks the current page. A child the site
//   hides (hidden, class "hidden", display:none) stays hidden. The bar sets their look; site
//   classes for colour, size and spacing are overridden.
// On wide screens the site's links take the centre and the OWASP BLT links (Why BLT, Explore,
// ...) move into a small menu next to the brand. When they don't fit, and on phones, everything
// goes into the menu button: this site's links and buttons first, then the OWASP BLT links.
// With no centre links (only slot="actions" children, or none) the centre keeps the OWASP BLT
// links, as on owaspblt.org. A site's own "Report Bug" child hides the bar's Report Bug.
// Before the script runs the children are plain links in the page; a site can hide them with
//   blt-nav:not(:defined){display:block;min-height:57px}blt-nav:not(:defined)>*{display:none}
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

  // [name, href, file name: the plain round symbol the Explore card, the bar and the apps chooser
  //  show is owaspblt.org/_home/symbols/<file>]
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

  // ---- Per-site config ---------------------------------------------------------
  // get(name) returns an attribute of the <blt-nav> element (or the script tag), or null.
  function shortName(appName) {
    if (appName === "MY-GSOC-TOOL") return "GSoC Tool";
    var s = appName.replace(/^BLT-/i, "").replace(/^OWASP-/, "").replace(/-/g, " ");
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
  function appFor(slug) {
    for (var i = 0; i < APPS.length; i++) if (APPS[i][2] === slug + ".svg") return APPS[i];
    return null;
  }
  function appForHost(hostname) {
    for (var i = 0; i < APPS.length; i++) {
      try { if (new URL(APPS[i][1]).hostname === hostname) return APPS[i]; } catch (e) { /* skip */ }
    }
    return null;
  }
  function resolveConfig(get, hostname) {
    var slug = get("project") || get("data-project");
    if (slug === "none") return { project: null };
    var app = null;
    if (slug) app = appFor(slug);
    else if (!/^(www\.)?owaspblt\.org$/.test(hostname || "")) {
      app = appForHost(hostname);
      if (app) slug = app[2].replace(/\.svg$/, "");
    }
    if (!slug || !/^[a-z0-9-]+$/.test(slug)) return { project: null };
    var home = get("home") || get("data-home") || "/";
    if (/^\s*(javascript|data|vbscript):/i.test(home)) home = "/";
    return {
      project: slug,
      name: get("name") || get("data-name") || shortName(app ? app[0] : slug),
      home: home,
      symbol: BASE + "/_home/symbols/" + slug + ".svg",
    };
  }

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
    ".left{position:relative;display:flex;flex:none;align-items:center;gap:4px;min-width:0}",
    ":host([blt-compact]) .left{flex:0 1 auto}",
    ".brand{display:inline-flex;flex:none;align-items:center;gap:10px}",
    ".brand img{width:32px;height:32px;display:block}",
    ".brand span{font-size:18px;line-height:28px;font-weight:700;letter-spacing:-.025em;color:#111827;white-space:nowrap}",
    ".brand b{color:#dc2626;font-weight:700}",
    // OWASP BLT links menu (sites with their own links)
    ".more{display:none;width:24px;height:28px;flex:none;align-items:center;justify-content:center;border-radius:6px;color:#6b7280}",
    ".more:hover,.more[aria-expanded=true]{background:#f3f4f6;color:#111827}",
    ".more svg{transition:transform .15s}.more[aria-expanded=true] svg{transform:rotate(180deg)}",
    ":host([blt-links]:not([blt-compact])) .more{display:inline-flex}",
    ".bm{position:absolute;left:0;top:100%;margin-top:12px;display:none;flex-direction:column;gap:2px;min-width:14rem;padding:8px;border-radius:16px;border:1px solid #fee2e2;background:#fff;box-shadow:0 25px 50px -12px rgba(254,202,202,.6)}",
    ".bm.open{display:flex;animation:pin .18s ease-out}",
    ".bm a{border-radius:8px;padding:8px 10px;color:#374151;white-space:nowrap}",
    ".bm a:hover{background:#f3f4f6;color:#111827}",
    ".bm a.mreport{margin-top:4px;background:#dc2626;color:#fff;text-align:center;font-weight:600}",
    ".bm a.mreport:hover{background:#b91c1c;color:#fff}",
    // this site's project
    ".sep{flex:none;width:1px;height:22px;margin:0 8px 0 6px;background:#e5e7eb}",
    ".proj{display:inline-flex;align-items:center;gap:8px;min-width:0;border-radius:8px}",
    ".proj img{width:26px;height:26px;flex:none;display:block;border-radius:50%}",
    ".proj span{font-size:16px;line-height:24px;font-weight:600;letter-spacing:-.01em;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".proj:hover span{color:#dc2626}",
    // centre: the OWASP BLT links, or this site's links
    ".links{display:flex;align-items:center;gap:24px}",
    ".links a.blt{color:#4b5563;white-space:nowrap;transition:color .15s}",
    ".links a.blt:hover{color:#111827}",
    ":host([blt-links]) .links{gap:2px}",
    ":host([blt-links]) .links a.blt{display:none}",
    ":host([blt-noreport]) .mreport{display:none}",
    ":host([blt-compact]) .links{display:none}",
    ".right{display:flex;flex:none;align-items:center;gap:8px}",
    ".acts{display:flex;align-items:center;gap:8px}",
    ":host([blt-compact]) .acts{display:none}",
    ".zero{display:none;border-radius:6px;padding:8px 12px;color:#4b5563;white-space:nowrap}",
    ".zero:hover{background:#f3f4f6;color:#111827}",
    ".report{display:none;align-items:center;justify-content:center;border-radius:6px;border-bottom:1.5px solid #b91c1c;background:linear-gradient(#ef4444,#dc2626);padding:8px 16px;font-weight:600;color:#fff;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.05);transition:transform .15s,box-shadow .15s}",
    ".report:hover{transform:translateY(-1px);box-shadow:0 10px 24px -12px rgba(220,38,38,.8)}",
    ".icon{display:flex;width:36px;height:36px;flex:none;align-items:center;justify-content:center;border-radius:8px;color:#6b7280;transition:background .15s,color .15s}",
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
    ".grid img{width:40px;height:40px;object-fit:contain;border-radius:50%;transition:transform .15s}",
    ".grid a:hover img{transform:scale(1.05)}",
    ".grid span{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;line-height:16px;font-weight:500;color:#374151}",
    ".icon .moon,.mtheme .moon{display:block}.icon .sun,.mtheme .sun{display:none}",
    ".burger{display:none;flex-direction:column;gap:5px}",
    ":host([blt-compact]) .burger{display:flex}",
    ".burger i{display:block;width:20px;height:1px;background:#4b5563;transition:transform .2s,opacity .2s}",
    ".burger[aria-expanded=true] i:nth-child(1){transform:translateY(6px) rotate(45deg)}",
    ".burger[aria-expanded=true] i:nth-child(2){opacity:0}",
    ".burger[aria-expanded=true] i:nth-child(3){transform:translateY(-6px) rotate(-45deg)}",
    ".mobile{display:none;flex-direction:column;gap:4px;border-top:1px solid #f3f4f6;background:#fff;padding:12px 16px;max-height:calc(100vh - 80px);overflow-y:auto}",
    ":host([blt-compact]) .mobile.open{display:flex}",
    ".mobile a{border-radius:6px;padding:8px;color:#374151}",
    ".mobile a:hover{background:#f3f4f6}",
    ".mobile a.mreport{margin-top:4px;background:#dc2626;color:#fff;text-align:center;font-weight:600;padding:8px 12px}",
    ".grp{display:flex;flex-direction:column;gap:4px}",
    // No room for the project's name next to the theme toggle: the toggle moves into the menu.
    ".mtheme{display:none;align-items:center;gap:8px;border-radius:6px;padding:8px;color:#374151;text-align:left}",
    ".mtheme:hover{background:#f3f4f6}",
    ".mtheme svg{flex:none}",
    ":host([blt-tight]) .mtheme{display:flex}",
    ":host([blt-tight]) .right .tgl{display:none}",
    ".site{display:none}",
    ":host([blt-site]) .site{display:flex;padding-bottom:12px;margin-bottom:8px;border-bottom:1px solid #f3f4f6}",
    ".gh{display:none;margin:0;padding:4px 8px;font-size:11px;line-height:16px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#9ca3af}",
    ":host([blt-site]) .gh{display:block}",
    // The site's own links and buttons (light DOM, slotted). !important beats the page's own
    // CSS for these properties; display is left to the site so its hidden ones stay hidden.
    "::slotted(*){font-family:inherit!important;font-size:14px!important;line-height:20px!important;font-weight:500!important;font-style:normal!important;letter-spacing:normal!important;text-transform:none!important;text-decoration:none!important;white-space:nowrap!important;color:#4b5563!important;background:transparent!important;border:0!important;border-radius:6px!important;box-shadow:none!important;outline-offset:2px;margin:0!important;padding:6px 10px!important;flex:none!important;width:auto!important;height:auto!important;max-width:none!important;transform:none!important;cursor:pointer;transition:background-color .15s,color .15s}",
    "::slotted(:hover){color:#111827!important;background:#f3f4f6!important}",
    "::slotted(:focus-visible){outline:2px solid #dc2626!important}",
    "::slotted([aria-current]:not([aria-current=false])),::slotted(.active){color:#dc2626!important;background:rgba(254,242,242,.9)!important;font-weight:600!important}",
    ".acts ::slotted(*){padding:8px 12px!important;color:#374151!important}",
    ".acts ::slotted(:hover){color:#111827!important;background:#f3f4f6!important}",
    "::slotted([data-primary]){color:#fff!important;font-weight:600!important;padding:8px 16px!important;background:linear-gradient(#ef4444,#dc2626)!important;border-bottom:1.5px solid #b91c1c!important;box-shadow:0 1px 2px rgba(0,0,0,.05)!important}",
    "::slotted([data-primary]:hover){color:#fff!important;background:linear-gradient(#ef4444,#dc2626)!important;transform:translateY(-1px)!important;box-shadow:0 10px 24px -12px rgba(220,38,38,.8)!important}",
    ".site ::slotted(*){padding:8px!important;text-align:left!important;color:#374151!important;white-space:normal!important}",
    ".site ::slotted([data-primary]){margin-top:4px!important;padding:8px 12px!important;text-align:center!important;color:#fff!important}",
    "@media (max-width:767px){.in{padding:12px 16px}}",
    "@media (min-width:640px){.right{gap:8px}:host(:not([blt-site])) .report{display:inline-flex}}",
    "@media (min-width:768px){:host(:not([blt-site])) .zero{display:inline-flex}}",
    // Phones: the panel spans the screen under the bar instead of hanging off the button.
    "@media (max-width:767px){.panel{position:fixed;left:16px;right:16px;top:var(--blt-apps-top,68px);margin-top:0;width:auto;max-width:none}.scroll{max-height:calc(100vh - var(--blt-apps-top,68px) - 96px)}}",
    // Small phones with a project part: everything a little tighter so the name fits.
    "@media (max-width:479px){:host([blt-project]) .in{gap:6px;padding:12px 10px 12px 12px}:host([blt-project]) .brand{gap:8px}:host([blt-project]) .brand img{width:28px;height:28px}:host([blt-project]) .brand span{font-size:16px}:host([blt-project]) .sep{margin:0 5px 0 2px}:host([blt-project]) .proj{gap:6px}:host([blt-project]) .proj img{width:22px;height:22px}:host([blt-project]) .proj span{font-size:15px}:host([blt-project]) .right{gap:2px}:host([blt-project]) .icon{width:32px}}",
    "@media (max-width:399px){:host([blt-project]) .brand{gap:6px}:host([blt-project]) .brand span{font-size:15px}:host([blt-project]) .proj img{width:20px;height:20px}:host([blt-project]) .proj span{font-size:14px}}",
    // dark
    ":host([dark]){color:#f3f4f6;color-scheme:dark}",
    ":host([dark]) .bar{background:rgba(3,7,18,.85);border-bottom-color:rgba(255,255,255,.1)}",
    ":host([dark]) .brand span,:host([dark]) .proj span{color:#fff}",
    ":host([dark]) .brand b{color:#ef4444}",
    ":host([dark]) .proj:hover span{color:#f87171}",
    ":host([dark]) .sep{background:#374151}",
    ":host([dark]) .links a.blt,:host([dark]) .zero{color:#d1d5db}",
    ":host([dark]) .links a.blt:hover,:host([dark]) .zero:hover,:host([dark]) .icon:hover,:host([dark]) .more:hover,:host([dark]) .more[aria-expanded=true]{color:#fff}",
    ":host([dark]) .zero:hover,:host([dark]) .icon:hover,:host([dark]) .mobile a:hover,:host([dark]) .more:hover,:host([dark]) .more[aria-expanded=true],:host([dark]) .bm a:hover{background:#1f2937}",
    ":host([dark]) .icon,:host([dark]) .more{color:#9ca3af}",
    ":host([dark]) .panel,:host([dark]) .bm{border-color:#1f2937;background:#111827;box-shadow:0 25px 50px -12px rgba(0,0,0,.5)}",
    ":host([dark]) .bm a{color:#e5e7eb}",
    ":host([dark]) .bm a.mreport{color:#fff;background:#dc2626}",
    ":host([dark]) .ph p{color:#fff}",
    ":host([dark]) .ph a{color:#f87171}",
    ":host([dark]) .grid a:hover,:host([dark]) .grid a[aria-current]{background:#1f2937}",
    ":host([dark]) .grid span{color:#d1d5db}",
    ":host([dark]) .icon .moon,:host([dark]) .mtheme .moon{display:none}:host([dark]) .icon .sun,:host([dark]) .mtheme .sun{display:block}",
    ":host([dark]) .burger i{background:#d1d5db}",
    ":host([dark]) .mobile{background:#030712;border-top-color:#1f2937}",
    ":host([dark][blt-site]) .site{border-bottom-color:#1f2937}",
    ":host([dark]) .gh{color:#6b7280}",
    ":host([dark]) .mobile a,:host([dark]) .mtheme{color:#e5e7eb}",
    ":host([dark]) .mtheme:hover{background:#1f2937}",
    ":host([dark]) .mobile a.mreport{color:#fff}",
    ":host([dark]) ::slotted(*){color:#d1d5db!important}",
    ":host([dark]) ::slotted(:hover){color:#fff!important;background:#1f2937!important}",
    ":host([dark]) ::slotted([aria-current]:not([aria-current=false])),:host([dark]) ::slotted(.active){color:#f87171!important;background:rgba(127,29,29,.35)!important}",
    ":host([dark]) .acts ::slotted(*),:host([dark]) .site ::slotted(*){color:#e5e7eb!important}",
    ":host([dark]) ::slotted([data-primary]),:host([dark]) .acts ::slotted([data-primary]),:host([dark]) .site ::slotted([data-primary]){color:#fff!important;background:linear-gradient(#ef4444,#dc2626)!important}",
    "@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}::slotted(*){transition:none!important}}",
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
  function normPath(p) {
    return (p || "/").replace(/\/index\.html?$/, "/").replace(/\.html?$/, "").replace(/\/+$/, "") || "/";
  }
  function bltLinks(cls) {
    return LINKS.map(function (l) { return el("a", { href: l[1], text: l[0], class: cls || null }); });
  }

  // ---- The element -----------------------------------------------------------
  class BltNav extends HTMLElement {
    connectedCallback() { build(this); }
  }
  BltNav.resolveConfig = resolveConfig; // for tests
  BltNav.normPath = normPath;

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
    var cfg = resolveConfig(function (n) { return opt(host, n); }, location.hostname);
    host.toggleAttribute("blt-project", !!cfg.project);

    // brand
    var brandText = el("span", { text: "OWASP " }, [el("b", { text: "BLT" })]);
    var brand = el("a", { class: "brand", href: HOME + "/", "aria-label": "OWASP BLT home" }, [
      el("img", { src: BASE + "/_home/blt-logo.svg", alt: "", width: "32", height: "32" }),
      brandText,
    ]);
    var left = el("div", { class: "left" }, [brand]);

    // OWASP BLT links menu, next to the brand (shown when the site has its own links)
    var moreBtn = null, bm = null, pname = null;
    function setMore(open) {
      if (!bm) return;
      bm.classList.toggle("open", open);
      moreBtn.setAttribute("aria-expanded", String(open));
    }
    if (cfg.project) {
      bm = el("nav", { class: "bm", id: "bm", "aria-label": "OWASP BLT" },
        bltLinks().concat([el("a", { href: ZERO, text: "BLT-Zero" }), el("a", { class: "mreport", href: REPORT, text: "Report Bug" })]));
      moreBtn = el("button", { class: "more", type: "button", "aria-expanded": "false", "aria-controls": "bm", "aria-label": "OWASP BLT links" },
        [svg(null, 14, "0 0 24 24", [["path", { d: "m6 9 6 6 6-6" }]], true)]);
      moreBtn.addEventListener("click", function (e) { e.stopPropagation(); setMore(!bm.classList.contains("open")); });
      left.appendChild(moreBtn);
      left.appendChild(bm);

      // this site's project: its own round symbol and short name
      var sym = el("img", { src: cfg.symbol, alt: "", width: "26", height: "26", decoding: "async" });
      sym.addEventListener("error", function () { sym.remove(); });
      left.appendChild(el("span", { class: "sep", "aria-hidden": "true" }));
      pname = el("span", { text: cfg.name });
      left.appendChild(el("a", { class: "proj", href: cfg.home, part: "project", "aria-label": cfg.name + " home" }, [sym, pname]));
    }

    // centre: the OWASP BLT links; this site's links (the element's children) replace them
    var defSlot = el("slot");
    var actSlot = el("slot", { name: "actions" });
    var links = el("nav", { class: "links", "aria-label": cfg.project ? cfg.name : "OWASP BLT" }, bltLinks("blt").concat([defSlot]));
    var acts = el("div", { class: "acts" }, [actSlot]);

    // apps launcher
    var grid = el("ul", { class: "grid" });
    var built = false;
    function buildApps() {
      if (built) return;
      built = true;
      APPS.forEach(function (p) {
        var a = el("a", { href: p[1] }, [
          el("img", { src: BASE + "/_home/symbols/" + p[2], alt: "", width: "40", height: "40", decoding: "async" }),
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
    appsBtn.addEventListener("click", function (e) { e.stopPropagation(); setMore(false); setApps(!panel.classList.contains("open")); });

    // theme toggle
    var toggle = null, mtoggle = null, mtoggleText = null;
    function themeIcons() {
      return [
        svg("moon", 18, "0 0 24 24", [["path", { d: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" }]], true),
        svg("sun", 18, "0 0 24 24", [["circle", { cx: 12, cy: 12, r: 4 }], ["path", { d: "M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" }]], true),
      ];
    }
    function flipTheme() {
      var dark = !isDark();
      applyTheme(dark, host);
      saveTheme(dark, host);
      window.dispatchEvent(new CustomEvent("blt-theme-change", { detail: { dark: dark } }));
    }
    if (opt(host, "data-theme-toggle") !== "off") {
      toggle = el("button", { class: "icon tgl", type: "button" }, themeIcons());
      toggle.addEventListener("click", flipTheme);
      mtoggleText = el("span");
      mtoggle = el("button", { class: "mtheme", type: "button" }, themeIcons().concat([mtoggleText]));
      mtoggle.addEventListener("click", flipTheme);
    }

    // mobile: this site's links and buttons first, then the OWASP BLT links
    var burger = el("button", { class: "icon burger", type: "button", "aria-label": "Menu", "aria-expanded": "false", "aria-controls": "mobile" },
      [el("i"), el("i"), el("i")]);
    var siteGrp = el("div", { class: "grp site" });
    var bltGrp = el("div", { class: "grp" }, [el("p", { class: "gh", text: "OWASP BLT" })]
      .concat(bltLinks(), [el("a", { href: ZERO, text: "BLT-Zero" }), el("a", { class: "mreport", href: REPORT, text: "Report Bug" }), mtoggle]));
    var mobile = el("nav", { class: "mobile", id: "mobile", "aria-label": cfg.project ? cfg.name + " and OWASP BLT" : "OWASP BLT mobile" }, [siteGrp, bltGrp]);
    function setMobile(open) {
      mobile.classList.toggle("open", open);
      burger.setAttribute("aria-expanded", String(open));
    }
    burger.addEventListener("click", function (e) { e.stopPropagation(); setApps(false); setMobile(!mobile.classList.contains("open")); });

    function closeAll() { setApps(false); setMore(false); setMobile(false); }
    // Clicks inside the bar's shadow reach the document as clicks on the host.
    document.addEventListener("click", function (e) { if (e.target !== host) { setApps(false); setMore(false); } });
    shadow.addEventListener("click", function (e) {
      if (!apps.contains(e.target)) setApps(false);
      if (bm && !bm.contains(e.target)) setMore(false);
      if (e.target.closest && e.target.closest(".mobile a")) setMobile(false);
    });
    // A click on one of the site's own links or buttons (light DOM) closes the menus.
    host.addEventListener("click", function (e) { if (e.target !== host) closeAll(); });

    shadow.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (panel.classList.contains("open")) { setApps(false); appsBtn.focus(); }
      if (bm && bm.classList.contains("open")) { setMore(false); moreBtn.focus(); }
      if (mobile.classList.contains("open")) { setMobile(false); burger.focus(); }
    });
    host.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && e.target !== host && mobile.classList.contains("open")) { setMobile(false); burger.focus(); }
    });

    var right = el("div", { class: "right" }, [
      el("a", { class: "zero", href: ZERO, text: "BLT-Zero" }),
      el("a", { class: "report", href: REPORT, text: "Report Bug" }),
      acts, apps, toggle, burger,
    ]);
    var inner = el("div", { class: "in" }, [left, links, right]);
    shadow.appendChild(el("header", { class: "bar", part: "bar" }, [inner, mobile]));

    // Wide or compact: the site's links sit in the bar when everything fits on one row,
    // else (and always on phones) in the menu.
    var phone = window.matchMedia ? window.matchMedia("(max-width: 767px)") : null;
    var narrow = window.matchMedia ? window.matchMedia("(max-width: 1023px)") : null;
    function layout() {
      // blt-site: the site has links or buttons here; blt-links: some go in the centre (else
      // the centre keeps the OWASP BLT links). A site's own Report Bug hides the bar's.
      var kids = Array.prototype.slice.call(host.children);
      var site = !!cfg.project && kids.length > 0;
      host.toggleAttribute("blt-site", site);
      host.toggleAttribute("blt-links", site && kids.some(function (k) { return !k.getAttribute("slot"); }));
      host.toggleAttribute("blt-noreport", site && kids.some(function (k) { return /^\s*report (a )?bug\s*$/i.test(k.textContent); }));
      host.removeAttribute("blt-compact");
      host.removeAttribute("blt-tight");
      links.appendChild(defSlot);
      acts.appendChild(actSlot);
      var small = site ? phone && phone.matches : narrow && narrow.matches;
      if (small || inner.scrollWidth > inner.clientWidth + 1) {
        host.setAttribute("blt-compact", "");
        siteGrp.appendChild(defSlot);
        siteGrp.appendChild(actSlot);
        if (pname && mtoggle && pname.scrollWidth > pname.clientWidth) host.setAttribute("blt-tight", "");
      } else {
        setMobile(false);
      }
    }
    var queued = false;
    function relayout() {
      if (queued) return;
      queued = true;
      (window.requestAnimationFrame || setTimeout)(function () { queued = false; layout(); });
    }
    layout();
    var lastWidth = 0;
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        var w = inner.clientWidth;
        if (w !== lastWidth) { lastWidth = w; relayout(); }
      }).observe(inner);
    } else window.addEventListener("resize", relayout);
    // The site adds, shows or hides its own links and buttons (signed in / out): the row may
    // fit differently. (Not slotchange: moving the slots in layout() fires it too.)
    new MutationObserver(relayout).observe(host, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["class", "hidden", "style", "slot"] });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(relayout);

    // current="auto": mark the site's link to this page, unless the site marks one itself
    function markCurrent() {
      if (opt(host, "current") !== "auto") return;
      var kids = Array.prototype.slice.call(host.querySelectorAll("a[href]"));
      var mine = function (a) { return a.hasAttribute("data-blt-current"); };
      if (kids.some(function (a) { return !mine(a) && a.hasAttribute("aria-current") && a.getAttribute("aria-current") !== "false"; })) return;
      var here = normPath(location.pathname);
      kids.forEach(function (a) {
        if (!mine(a) && a.getAttribute("aria-current") === "false") return; // never this one
        var match = false;
        try {
          var u = new URL(a.getAttribute("href"), location.href);
          match = u.origin === location.origin && normPath(u.pathname) === here && !u.hash;
        } catch (e) { /* not a URL */ }
        if (match && !a.hasAttribute("aria-current")) { a.setAttribute("aria-current", "page"); a.setAttribute("data-blt-current", ""); }
        else if (!match && a.hasAttribute("data-blt-current")) { a.removeAttribute("aria-current"); a.removeAttribute("data-blt-current"); }
      });
    }
    markCurrent();
    window.addEventListener("popstate", markCurrent);

    // follow the page's theme, whoever changes it
    function sync() {
      var dark = isDark();
      host.toggleAttribute("dark", dark);
      if (toggle) toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      if (mtoggleText) mtoggleText.textContent = dark ? "Light theme" : "Dark theme";
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
