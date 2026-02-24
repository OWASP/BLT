// Global error reporter: forwards uncaught JS errors to the backend,
// which relays them to the configured SLACK_ERROR_WEBHOOK.
(function () {
    function reportError(errorType, message, stack, extra) {
        try {
            var payload = Object.assign({ error_type: errorType, message: message, stack: stack || '' }, extra || {});
            navigator.sendBeacon('/api/client-error', JSON.stringify(payload));
        } catch (e) { /* ignore reporting failures */ }
    }
    window.addEventListener('error', function (event) {
        reportError(
            (event.error && event.error.name) || 'Error',
            event.message || String(event.error),
            (event.error && event.error.stack) || '',
            { url: location.href, line: event.lineno, col: event.colno }
        );
    });
    window.addEventListener('unhandledrejection', function (event) {
        var reason = event.reason || {};
        reportError(
            (reason.name) || 'UnhandledRejection',
            reason.message || String(reason),
            reason.stack || '',
            { url: location.href }
        );
    });
})();
