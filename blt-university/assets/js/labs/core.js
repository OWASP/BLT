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
            return [];
        }
    }

    function labIdFromPage() {
        const path = window.location.pathname.replace(/\/$/, '').split('/').filter(Boolean);
        return path[path.length - 1] || 'lab';
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
        const storageKey = 'blt-lab-progress';
        try {
            const parsed = JSON.parse(localStorage.getItem(storageKey) || '{}');
            return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    function getSimulationProgress(labId, taskIndex) {
        const labProgress = getStoredSimulationProgress()[labId];
        return labProgress && typeof labProgress === 'object' && !Array.isArray(labProgress)
            ? labProgress[taskIndex] || null
            : null;
    }

    function setSimulationProgress(labId, taskIndex, value) {
        const storageKey = 'blt-lab-progress';
        const progress = getStoredSimulationProgress();
        const existingLabProgress = progress[labId];
        const labProgress = existingLabProgress && typeof existingLabProgress === 'object' && !Array.isArray(existingLabProgress)
            ? existingLabProgress
            : {};
        const existingTaskProgress = labProgress[taskIndex];

        labProgress[taskIndex] = {
            ...(existingTaskProgress && typeof existingTaskProgress === 'object' && !Array.isArray(existingTaskProgress)
                ? existingTaskProgress
                : {}),
            ...value
        };

        progress[labId] = labProgress;
        try {
            localStorage.setItem(storageKey, JSON.stringify(progress));
        } catch (_error) {
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
