/**
 * OWASP BLT – Analytics (PostHog)
 *
 * Loads and initialises PostHog using the project key and host from BLT_CONFIG.
 * Must be loaded after js/config.js.
 * License: AGPLv3
 */

/* ── PostHog async loader stub ─────────────────────────────────────────────
   Defines window.posthog as a stub that queues calls until the real library
   arrives. Copied verbatim from https://posthog.com/docs/libraries/js        */
/* eslint-disable */
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","ui.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+" (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys getNextSurveyStep onSessionId setPersonPropertiesForFlags".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||(window.posthog=[]));
/* eslint-enable */

(function () {
  var key     = (typeof BLT_CONFIG !== "undefined" && BLT_CONFIG.POSTHOG_KEY)     || "";
  var host    = (typeof BLT_CONFIG !== "undefined" && BLT_CONFIG.POSTHOG_HOST)    || "https://us.i.posthog.com";
  var uiHost  = (typeof BLT_CONFIG !== "undefined" && BLT_CONFIG.POSTHOG_UI_HOST) || "https://us.posthog.com";

  if (!key) {
    /* Replace posthog with a no-op stub so callers never need to guard. */
    window.posthog = {
      capture: function () {},
      identify: function () {},
      reset: function () {},
      __loaded: false,
    };
    return;
  }

  posthog.init(key, {
    api_host: host,
    ui_host: uiHost,
    defaults: "2026-01-30",
    person_profiles: "identified_only",
    capture_pageview: true,
    capture_pageleave: true,
  });
})();

/**
 * Safe wrapper around posthog.capture().
 * Works whether PostHog is fully loaded, still in stub mode, or disabled.
 *
 * @param {string} event  - Event name
 * @param {Object} [props] - Optional properties
 */
function bltCapture(event, props) {
  try {
    if (typeof posthog !== "undefined") {
      posthog.capture(event, props || {});
    }
  } catch (e) {
    /* Silently swallow analytics errors to never break the page. */
  }
}
