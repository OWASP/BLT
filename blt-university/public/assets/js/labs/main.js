(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;
    const {
        SimulationStates,
        SimulationRegistry,
        createSimulationState,
        escapeHtml,
        getSimulationProgress,
        getStoredSimulationProgress,
        labIdFromPage,
        parseJavaScript,
        readLabData,
        setSimulationProgress,
        validateAuthFix,
        validateCommandFix,
        validateCsrfFix,
        validateExplainAnswer,
        validateIdorFix,
        validateLineSelection,
        validateRedirectFix,
        validateSensitiveDataFix,
        validateSqliFix,
        validateSsrfFix,
        validateUploadFix,
        validateXssFix
    } = BltLabs;

    function initializeLabSimulations() {
        const tasks = readLabData();
        const labRoot = document.querySelector('[data-lab-root]');
        const labId = labRoot?.dataset.labId || labIdFromPage();

        document.querySelectorAll('[data-simulation-root]').forEach(container => {
            const taskIndex = Number(container.dataset.taskIndex);
            const task = tasks[taskIndex];
            const config = task?.simulation || {};
            const engine = config.engine || container.dataset.simulationEngine;
            const renderer = SimulationRegistry[engine];

            if (!renderer) {
                container.innerHTML = `
                    <div class="mt-6 rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm font-semibold text-yellow-800 dark:border-yellow-900/40 dark:bg-yellow-900/10 dark:text-yellow-200">
                        Simulation engine "${escapeHtml(engine || 'unknown')}" is not implemented yet.
                    </div>
                `;
                return;
            }

            renderer(container, config, {
                engine,
                labId,
                taskIndex,
                completeTask() {
                    labRoot?.dispatchEvent(new CustomEvent('lab:task-complete', {
                        bubbles: true,
                        detail: { taskIndex }
                    }));
                }
            });
        });
    }

    // Test-only surface: the jest suites drive these directly rather than through the DOM.
    if (window.__BLT_LAB_TEST_MODE__ === true) {
        window.__BLT_LAB_TESTING__ = {
            SimulationStates,
            createSimulationState,
            getSimulationProgress,
            getStoredSimulationProgress,
            initializeLabSimulations,
            parseJavaScript,
            setSimulationProgress,
            validateAuthFix,
            validateCommandFix,
            validateCsrfFix,
            validateExplainAnswer,
            validateIdorFix,
            validateLineSelection,
            validateRedirectFix,
            validateSensitiveDataFix,
            validateSqliFix,
            validateSsrfFix,
            validateUploadFix,
            validateXssFix
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeLabSimulations);
    } else {
        initializeLabSimulations();
    }
}());
