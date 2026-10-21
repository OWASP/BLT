// OWASP BLT analytics: the forge's own first-party Analytics (git.owaspblt.org) for every BLT site.
//
// The shared top bar (blt-nav.js) loads this file, so every site with the bar is counted.
// A page without the bar loads it directly:
//   <script src="https://owaspblt.org/_shared/blt-analytics.js" defer></script>
// Opt a page out with data-analytics="off" on that tag or on the blt-nav.js tag.
//
// What is sent: pageviews, page leaves (time on page, scroll depth) and web vitals, to the
// "OWASP BLT sites" project of the Analytics package on git.owaspblt.org. Query strings and
// #fragments are stripped from every URL and referrer. No cookies; the SDK keeps an anonymous
// visitor id and its send queue in this site's localStorage. Nothing loads at all when the
// browser sends Do Not Track or Global Privacy Control, or on localhost.
// No autocapture, heatmaps, session recordings, surveys or error reports.
//
// Pages can send their own events with window.bltTrack(name, properties); calls made before
// the SDK has loaded are queued (also those made to a page's own stub, see below), and calls
// are dropped silently when analytics is off.
//
// Server side: the Analytics package is installed for the owasp-blt organization on
// git.owaspblt.org, and KEY below is that project's public write key (Settings on
// git.owaspblt.org/dashboard/analytics). Write keys are public by design; the project's
// allowed origins decide which sites may use it. With KEY empty this file does nothing.
(function () {
  "use strict";
  if (window.__bltAnalytics) return;
  window.__bltAnalytics = true;

  var FORGE = "https://git.owaspblt.org";
  var KEY = "";

  // A page may define a queueing stub before this loads; its calls are kept:
  //   window.bltTrack = window.bltTrack || function () { (window.bltTrack.q = window.bltTrack.q || []).push([].slice.call(arguments)); };
  var early = window.bltTrack && window.bltTrack.q;
  var queue = Array.isArray(early) ? early.slice(0, 50) : [];
  var sdk = null;
  window.bltTrack = function (event, properties) {
    if (typeof event !== "string" || !event) return;
    if (sdk) { try { sdk.capture(event, properties || {}); } catch (e) { /* never break the page */ } }
    else if (queue && queue.length < 50) queue.push([event, properties || {}]);
  };

  function off() { queue = null; }

  var script = document.currentScript;
  if (script && script.getAttribute("data-analytics") === "off") return off();
  if (!/^fma_[0-9a-f]{40}$/.test(KEY)) return off();
  if (location.protocol !== "https:" || /^(localhost|127\.0\.0\.1|\[::1\])$|\.localhost$/.test(location.hostname)) return off();
  var nav = navigator;
  var dnt = String(nav.doNotTrack || window.doNotTrack || nav.msDoNotTrack || "").toLowerCase();
  if (nav.globalPrivacyControl === true || dnt === "1" || dnt === "yes") return off();

  var tag = document.createElement("script");
  tag.src = FORGE + "/analytics-sdk.js";
  tag.async = true;
  tag.onload = function () {
    var lib = window.ForkMeshAnalyticsSDK;
    if (!lib || !lib.init) return off();
    try {
      sdk = lib.init({
        key: KEY,
        apiHost: FORGE,
        persistence: "localStorage",
        capturePageview: true,
        capturePageleave: true,
        capturePerformance: true,
        autocapture: false,
        heatmaps: false,
        sessionRecording: false,
        surveys: false,
        captureErrors: false,
        respectDoNotTrack: true,
        maskUrlQuery: true,
      });
    } catch (e) { return off(); }
    var pending = queue || [];
    queue = null;
    pending.forEach(function (item) { window.bltTrack(item[0], item[1]); });
  };
  tag.onerror = off;
  (document.head || document.documentElement).appendChild(tag);
})();
