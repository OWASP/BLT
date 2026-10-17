(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;
    const SimulationStates = Object.freeze({
        IDENTIFY: 'identify',
        EXPLAIN: 'explain',
        FIX: 'fix',
        COMPLETE: 'complete'
    });

    const orderedStates = [
        SimulationStates.IDENTIFY,
        SimulationStates.EXPLAIN,
        SimulationStates.FIX,
        SimulationStates.COMPLETE
    ];

    const storageKey = 'blt-lab-progress';

    function isPlainObject(value) {
        return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
    }

    function createSimulationState(initialState = SimulationStates.IDENTIFY) {
        let state = orderedStates.includes(initialState) ? initialState : SimulationStates.IDENTIFY;

        return {
            get value() {
                return state;
            },
            transition(nextState) {
                if (!orderedStates.includes(nextState)) {
                    return state;
                }

                const currentIndex = orderedStates.indexOf(state);
                const nextIndex = orderedStates.indexOf(nextState);
                // Learner-driven progress may only stay put or advance exactly one stage: never
                // skip ahead past unfinished work, never regress. Stage-pill navigation needs
                // arbitrary jumps, so it calls set() instead.
                if (nextIndex >= currentIndex && nextIndex <= currentIndex + 1) {
                    state = nextState;
                }

                return state;
            },
            set(nextState) {
                if (orderedStates.includes(nextState)) {
                    state = nextState;
                }

                return state;
            }
        };
    }

    function readLabData() {
        const dataElement = document.getElementById('lab-data');
        if (!dataElement) {
            return [];
        }

        try {
            const parsed = JSON.parse(dataElement.textContent || '[]');
            return Array.isArray(parsed) ? parsed : [];
        } catch (_error) {
            // Malformed embedded JSON should degrade to "no tasks" rather than break the page.
            return [];
        }
    }

    function labIdFromPage() {
        const pathSegments = window.location.pathname.replace(/\/$/, '').split('/').filter(Boolean);
        return pathSegments[pathSegments.length - 1] || 'lab';
    }

    function createHintController(hints = []) {
        let nextIndex = 0;

        return {
            next() {
                if (nextIndex >= hints.length) {
                    return hints[hints.length - 1] || '';
                }

                const hint = hints[nextIndex];
                nextIndex += 1;
                return hint;
            }
        };
    }

    function getStoredSimulationProgress() {
        try {
            const parsed = JSON.parse(localStorage.getItem(storageKey) || '{}');
            return isPlainObject(parsed) ? parsed : {};
        } catch (_error) {
            // Corrupt stored JSON, or localStorage blocked in private browsing: treat progress
            // as empty so the lab still loads.
            return {};
        }
    }

    function getSimulationProgress(labId, taskIndex) {
        const labProgress = getStoredSimulationProgress()[labId];
        return isPlainObject(labProgress)
            ? labProgress[taskIndex] || null
            : null;
    }

    function setSimulationProgress(labId, taskIndex, value) {
        const progress = getStoredSimulationProgress();
        const existingLabProgress = progress[labId];
        const labProgress = isPlainObject(existingLabProgress)
            ? existingLabProgress
            : {};
        const existingTaskProgress = labProgress[taskIndex];

        labProgress[taskIndex] = {
            ...(isPlainObject(existingTaskProgress)
                ? existingTaskProgress
                : {}),
            ...value
        };

        progress[labId] = labProgress;
        try {
            localStorage.setItem(storageKey, JSON.stringify(progress));
        } catch (_error) {
            // Quota exhausted or storage disabled: losing saved progress must not interrupt
            // the learner mid-simulation, so report failure instead of throwing.
            return false;
        }

        return true;
    }

    Object.assign(BltLabs, {
        SimulationStates,
        createSimulationState,
        readLabData,
        labIdFromPage,
        createHintController,
        getStoredSimulationProgress,
        getSimulationProgress,
        setSimulationProgress
    });
}());
