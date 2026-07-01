(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;
    const { SimulationStates } = BltLabs;
    function buttonClasses(kind = 'primary') {
        if (kind === 'secondary') {
            return 'inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800';
        }

        return 'inline-flex items-center justify-center gap-2 rounded-xl bg-bltRed px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-red-100 transition hover:bg-bltRedHover dark:shadow-none';
    }

    function escapeHtml(value = '') {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderFeedback(element, message, type = 'error') {
        element.className = `rounded-xl px-4 py-3 text-sm font-semibold ${type === 'success'
                ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                : 'bg-red-50 text-bltRed dark:bg-red-900/20 dark:text-red-300'
            }`;
        element.textContent = message;
    }

    function createHintElements(hintController) {
        const hintBox = document.createElement('div');
        hintBox.className = 'hidden rounded-xl border border-red-100 bg-red-50/70 px-4 py-3 text-sm text-gray-700 dark:border-red-900/30 dark:bg-red-900/10 dark:text-gray-300';

        const hintButton = document.createElement('button');
        hintButton.type = 'button';
        hintButton.className = buttonClasses('secondary');
        hintButton.innerHTML = '<i class="ph-bold ph-lightbulb"></i> Show Hint';
        hintButton.addEventListener('click', () => {
            const hint = hintController.next();
            if (hint) {
                hintBox.textContent = hint;
                hintBox.classList.remove('hidden');
            }
        });

        return { hintButton, hintBox };
    }

    function renderCodeEditor(value = '') {
        const textarea = document.createElement('textarea');
        textarea.className = 'min-h-64 w-full resize-y rounded-b-2xl border border-t-0 border-gray-200 bg-gray-950 p-5 font-mono text-sm leading-relaxed text-gray-100 shadow-inner outline-none transition focus:border-bltRed focus:ring-2 focus:ring-bltRed/20 dark:border-gray-700';
        textarea.spellcheck = false;
        textarea.value = value;
        return textarea;
    }

    function renderSelectableCodeBlock(code, selectedLines) {
        const wrapper = document.createElement('div');
        wrapper.className = 'overflow-hidden rounded-2xl border border-gray-200 bg-gray-950 dark:border-gray-700';

        code.split('\n').forEach((line, index) => {
            const lineNumber = index + 1;
            const isSelected = selectedLines.has(lineNumber);
            const row = document.createElement('button');
            row.type = 'button';
            row.dataset.lineNumber = String(lineNumber);
            row.className = 'grid w-full grid-cols-[3.25rem_1fr] border-b border-white/5 text-left font-mono text-xs last:border-b-0 transition-colors hover:bg-red-500/10 ' +
                (isSelected ? 'bg-red-500/20 ring-1 ring-inset ring-bltRed/60' : '');
            row.setAttribute('aria-pressed', isSelected ? 'true' : 'false');

            const gutter = document.createElement('span');
            gutter.className = 'select-none border-r border-white/10 px-3 py-2 text-right ' +
                (isSelected ? 'bg-bltRed text-white' : 'text-gray-500');
            gutter.textContent = String(lineNumber);

            const source = document.createElement('span');
            source.className = 'whitespace-pre-wrap px-3 py-2 ' + (isSelected ? 'text-white' : 'text-gray-100');
            source.textContent = line || ' ';

            row.append(gutter, source);
            wrapper.append(row);
        });

        return wrapper;
    }

    function stagePill(stateName, label, isActive, isDone, canVisit) {
        return `<button type="button" data-stage-target="${stateName}" ${canVisit ? '' : 'disabled'} class="rounded-full px-4 py-1.5 text-xs font-bold transition ${isDone
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                : isActive
                    ? 'border border-bltRed bg-red-50 text-bltRed dark:bg-red-900/20'
                    : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-300'
            } ${canVisit ? 'hover:ring-2 hover:ring-bltRed/30 cursor-pointer' : 'cursor-not-allowed opacity-60'}">${label}</button>`;
    }

    function renderShell(container, state, title, navigation, rerender) {
        container.innerHTML = `
            <div class="mt-8 rounded-3xl border border-gray-100 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900 md:p-7">
                <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <p class="mb-1 text-[10px] font-bold uppercase tracking-widest text-gray-400">Interactive Simulation</p>
                        <h3 class="m-0 text-xl font-bold text-gray-900 dark:text-white">${escapeHtml(title)}</h3>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        ${stagePill(SimulationStates.IDENTIFY, 'Identify', state.value === SimulationStates.IDENTIFY, navigation.identifyDone, true)}
                        ${stagePill(SimulationStates.EXPLAIN, 'Explain', state.value === SimulationStates.EXPLAIN, navigation.explainDone, navigation.canVisitExplain)}
                        ${stagePill(SimulationStates.FIX, 'Fix', state.value === SimulationStates.FIX, navigation.fixDone, navigation.canVisitFix)}
                    </div>
                </div>
                <div data-code-fix-stage></div>
            </div>
        `;

        container.querySelectorAll('[data-stage-target]').forEach(button => {
            button.addEventListener('click', () => {
                state.set(button.dataset.stageTarget);
                rerender();
            });
        });

        return container.querySelector('[data-code-fix-stage]');
    }

    function renderHints(container, hintController) {
        const { hintButton, hintBox } = createHintElements(hintController);
        const row = document.createElement('div');
        row.className = 'mt-5 space-y-3';
        row.append(hintButton, hintBox);
        container.append(row);
    }

    Object.assign(BltLabs, {
        buttonClasses,
        escapeHtml,
        renderFeedback,
        createHintElements,
        renderCodeEditor,
        renderSelectableCodeBlock,
        renderShell,
        renderHints
    });
}());
