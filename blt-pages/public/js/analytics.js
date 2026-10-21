/**
 * OWASP BLT – page events
 *
 * BLT-Pages is measured with the forge's own first-party Analytics on git.owaspblt.org,
 * loaded once for every BLT site by the shared top bar (owaspblt.org/_shared/blt-nav.js
 * loads owaspblt.org/_shared/blt-analytics.js). This file only names BLT-Pages' own events.
 * Until the shared loader runs, calls queue on window.bltTrack.q; it picks them up, and
 * drops them when analytics is off (Do Not Track, Global Privacy Control, no key).
 * License: AGPLv3
 */

window.bltTrack = window.bltTrack || function () {
  var queue = (window.bltTrack.q = window.bltTrack.q || []);
  if (queue.length < 50) queue.push([].slice.call(arguments));
};

/**
 * Record a BLT-Pages event. Never throws.
 *
 * @param {string} event  - Event name
 * @param {Object} [props] - Optional properties
 */
function bltCapture(event, props) {
  try {
    window.bltTrack(event, props || {});
  } catch (e) {
    /* Silently swallow analytics errors to never break the page. */
  }
}
