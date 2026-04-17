// Global error reporter: forwards JS errors to the backend.
(function () {
  function sendPayload(payload) {
    try {
      var body = JSON.stringify(payload);

      // Prefer beacon (best for unload), fallback to fetch if beacon fails.
      var ok = false;
      try {
        ok = navigator.sendBeacon("/api/client-error", body);
      } catch (e) {
        ok = false;
      }

      if (!ok) {
        fetch("/api/client-error", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: body,
          keepalive: true,
        }).catch(function () {});
      }
    } catch (e) {}
  }

  function reportError(errorType, message, stack, extra) {
    var payload = Object.assign(
      { error_type: errorType, message: message, stack: stack || "" },
      extra || {}
    );
    sendPayload(payload);
  }

  window.addEventListener(
    "error",
    function (event) {
      var target = event.target || {};
      var resourceUrl = target.src || target.href;

      if (
        resourceUrl &&
        (target.tagName === "SCRIPT" ||
          target.tagName === "LINK" ||
          target.tagName === "IMG")
      ) {
        reportError(
          "ResourceError",
          "Failed to load or execute resource",
          (event.error && event.error.stack) || "",
          { url: location.href, resource: resourceUrl }
        );
        return;
      }

      reportError(
        (event.error && event.error.name) || "Error",
        event.message ||
          (event.error && event.error.message) ||
          String(event.error) ||
          "Unknown error",
        (event.error && event.error.stack) || "",
        { url: location.href, line: event.lineno, col: event.colno }
      );
    },
    true
  );

  window.addEventListener("unhandledrejection", function (event) {
    var reason = event.reason || {};
    reportError(
      reason.name || "UnhandledRejection",
      reason.message || String(reason),
      reason.stack || "",
      { url: location.href }
    );
  });

  (function hookConsoleError() {
    var original = console.error;
    console.error = function () {
      try {
        var args = Array.prototype.slice.call(arguments);
        var msg = args
          .map(function (a) {
            if (a instanceof Error) {
              return a.name + ": " + a.message + "\n" + (a.stack || "");
            }
            if (typeof a === "object") {
              try { return JSON.stringify(a); } catch (_) { return "[object]"; }
            }
            return String(a);
          })
          .join(" ");

        reportError("ConsoleError", msg.slice(0, 300), msg.slice(0, 2000), {
          url: location.href,
          source: "console.error",
        });
      } catch (e) {}

      return original.apply(console, arguments);
    };
  })();
})();