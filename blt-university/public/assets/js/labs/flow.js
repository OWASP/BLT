(function () {
    window.BltLabs = window.BltLabs || {};
    const BltLabs = window.BltLabs;
    const {
        SimulationStates,
        createHintController,
        createSimulationState,
        getSimulationProgress,
        setSimulationProgress,
        validateExplainAnswer,
        validateLineSelection,
        buttonClasses,
        createHintElements,
        escapeHtml,
        renderCodeEditor,
        renderFeedback,
        renderHints,
        renderSelectableCodeBlock,
        renderShell
    } = BltLabs;

    function renderIdentify(stage, config, selectedLines, state, rerender, messages) {
        const feedback = document.createElement('p');
        feedback.className = 'hidden';

        const codeMount = document.createElement('div');
        codeMount.append(renderSelectableCodeBlock(config.vulnerable_code || '', selectedLines));
        codeMount.addEventListener('click', event => {
            const lineButton = event.target.closest('[data-line-number]');
            if (!lineButton) {
                return;
            }

            const lineNumber = Number(lineButton.dataset.lineNumber);
            if (selectedLines.has(lineNumber)) {
                selectedLines.delete(lineNumber);
            } else {
                selectedLines.add(lineNumber);
            }
            rerender();
        });

        const validateButton = document.createElement('button');
        validateButton.type = 'button';
        validateButton.className = buttonClasses();
        validateButton.textContent = 'Validate Selection';
        validateButton.addEventListener('click', () => {
            if (validateLineSelection([...selectedLines], config.vulnerable_lines || [])) {
                state.transition(SimulationStates.EXPLAIN);
                rerender();
            } else {
                renderFeedback(feedback, messages.identifyError, 'error');
            }
        });

        stage.innerHTML = `
            <div data-stage-body class="space-y-4">
                <div>
                    <h4 class="m-0 text-base font-bold text-gray-900 dark:text-white">Step 1: Identify Vulnerability</h4>
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(messages.identifyPrompt)}</p>
                </div>
            </div>
        `;
        stage.querySelector('[data-stage-body]').append(codeMount, feedback, validateButton);
    }

    function renderExplain(stage, config, state, rerender, messages, explainState) {
        const explain = config.explain || {};
        const feedback = document.createElement('p');
        feedback.className = 'hidden';

        const answerButtons = document.createElement('div');
        answerButtons.className = 'space-y-3';
        (explain.options || []).forEach(option => {
            const isSelected = explainState.selectedAnswer === option.id;
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.answer = option.id;
            button.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            button.className = 'w-full rounded-xl border p-4 text-left text-sm font-semibold transition ' +
                (isSelected
                    ? 'border-bltRed bg-red-50 text-gray-900 shadow-sm ring-2 ring-bltRed/20 dark:bg-red-900/20 dark:text-white'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-bltRed hover:bg-red-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-red-900/10');
            button.innerHTML = `
                <span class="flex gap-3">
                    <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${isSelected ? 'border-bltRed bg-bltRed text-white' : 'border-gray-300 dark:border-gray-600'}">${isSelected ? '✓' : ''}</span>
                    <span>${escapeHtml(option.label)}</span>
                </span>
            `;
            button.addEventListener('click', () => {
                explainState.selectedAnswer = option.id;
                rerender();
            });
            answerButtons.append(button);
        });

        const validateButton = document.createElement('button');
        validateButton.type = 'button';
        validateButton.className = buttonClasses();
        validateButton.textContent = 'Validate Explanation';
        validateButton.addEventListener('click', () => {
            if (validateExplainAnswer(explainState.selectedAnswer, explain.answer)) {
                explainState.explainDone = true;
                state.transition(SimulationStates.FIX);
                rerender();
            } else {
                renderFeedback(feedback, messages.explainError, 'error');
            }
        });

        stage.innerHTML = `
            <div data-stage-body class="space-y-4">
                <div>
                    <h4 class="m-0 text-base font-bold text-gray-900 dark:text-white">Step 2: Explain</h4>
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(explain.question || 'Why is this vulnerable?')}</p>
                </div>
            </div>
        `;
        stage.querySelector('[data-stage-body]').append(answerButtons, feedback, validateButton);
    }

    function renderFixGuidance(messages, fixGuidance = []) {
        const guidance = fixGuidance.length ? fixGuidance : [
            {
                title: 'Secure Pattern',
                body: messages.fixPrompt,
                code: ''
            }
        ];

        return `
            <details class="group rounded-2xl border border-gray-200 bg-gray-50/70 dark:border-gray-700 dark:bg-gray-800/50">
                <summary class="flex cursor-pointer list-none items-center justify-between gap-4 p-4">
                    <span class="flex items-start gap-3">
                        <span class="mt-0.5 text-lg text-bltRed"><i class="ph-bold ph-lightbulb"></i></span>
                        <span>
                            <span class="block text-sm font-bold text-gray-900 dark:text-white">Show Guidance</span>
                            <span class="block text-xs leading-relaxed text-gray-500 dark:text-gray-400">Get hints and examples to help you implement the fix.</span>
                        </span>
                    </span>
                    <span class="text-gray-500 transition group-open:rotate-180 dark:text-gray-300"><i class="ph-bold ph-caret-down"></i></span>
                </summary>
                <div class="grid gap-3 border-t border-gray-200 p-4 dark:border-gray-700 lg:grid-cols-3">
                    ${guidance.map(item => `
                        <div class="min-w-0 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900/80">
                            <h6 class="m-0 mb-2 text-sm font-bold text-gray-900 dark:text-white">${escapeHtml(item.title)}</h6>
                            <p class="m-0 text-sm leading-relaxed text-gray-600 dark:text-gray-300">${escapeHtml(item.body)}</p>
                            ${item.code ? `<pre class="mt-3 max-h-32 overflow-auto rounded-lg bg-gray-950 p-3 text-[10px] leading-relaxed text-gray-100"><code>${escapeHtml(item.code)}</code></pre>` : ''}
                        </div>
                    `).join('')}
                </div>
            </details>
        `;
    }

    function renderFixOverview(messages, checks = []) {
        return `
            <details class="group rounded-2xl border border-gray-200 bg-gray-50/50 dark:border-gray-700 dark:bg-gray-800/30" open>
                <summary class="flex cursor-pointer list-none items-center justify-between gap-4 p-5">
                    <span class="flex items-start gap-3">
                        <span class="mt-1 text-bltRed"><i class="ph-bold ph-target"></i></span>
                        <span>
                            <span class="block text-[10px] font-bold uppercase tracking-widest text-bltRed">Goal</span>
                            <span class="mt-1 block text-sm leading-relaxed text-gray-700 dark:text-gray-300">${escapeHtml(messages.fixGoal || messages.fixPrompt)}</span>
                        </span>
                    </span>
                    <span class="text-gray-500 transition group-open:rotate-180 dark:text-gray-300"><i class="ph-bold ph-caret-down"></i></span>
                </summary>
                <div class="border-t border-gray-200 px-5 pb-5 pt-4 dark:border-gray-700">
                    <p class="m-0 mb-3 text-[10px] font-bold uppercase tracking-widest text-gray-400">Requirements</p>
                    <div class="grid gap-3 md:grid-cols-3">
                    ${checks.map(check => `
                        <div class="flex min-w-0 items-start gap-2 text-sm text-gray-600 dark:text-gray-300">
                            <span class="mt-0.5 shrink-0 text-green-500"><i class="ph-bold ph-check-circle"></i></span>
                            <span>${escapeHtml(check.label)}</span>
                        </div>
                    `).join('')}
                    </div>
                </div>
            </details>
        `;
    }

    function renderEditorChrome(editor, language = 'JS') {
        const wrapper = document.createElement('div');
        wrapper.className = 'overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-700';
        const chrome = document.createElement('div');
        chrome.className = 'flex items-center justify-end border-b border-gray-200 bg-gray-900 px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:border-gray-700';
        chrome.textContent = language;
        wrapper.append(chrome, editor);
        return wrapper;
    }

    function renderFix(stage, config, context, state, rerender, simulation, hintController) {
        const editor = renderCodeEditor(config.fix_starter_code || '');
        const feedback = document.createElement('div');
        feedback.className = 'hidden';
        const checksList = document.createElement('div');
        checksList.className = 'space-y-2';
        const initialChecks = simulation.validateFix(config.fix_starter_code || '', config).checks;
        const { hintButton, hintBox } = createHintElements(hintController);

        const validateButton = document.createElement('button');
        validateButton.type = 'button';
        validateButton.className = buttonClasses();
        validateButton.innerHTML = '<i class="ph-bold ph-play"></i> Run Validation';
        validateButton.addEventListener('click', () => {
            const result = simulation.validateFix(editor.value, config);
            checksList.innerHTML = result.checks.map(check => `
                <div class="flex items-center gap-2 text-sm ${check.passed ? 'text-green-600 dark:text-green-300' : 'text-bltRed dark:text-red-300'}">
                    <span class="flex h-5 w-5 items-center justify-center rounded-full ${check.passed ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}">${check.passed ? '✓' : '×'}</span>
                    <span>${escapeHtml(check.label)}</span>
                </div>
            `).join('');

            if (result.passed) {
                state.transition(SimulationStates.COMPLETE);
                setSimulationProgress(context.labId, context.taskIndex, {
                    completed: true,
                    engine: simulation.engine,
                    state: SimulationStates.COMPLETE,
                    score: 100
                });
                context.completeTask();
                rerender();
            } else {
                renderFeedback(feedback, simulation.messages.fixError, 'error');
            }
        });

        const resetButton = document.createElement('button');
        resetButton.type = 'button';
        resetButton.className = buttonClasses('secondary');
        resetButton.innerHTML = '<i class="ph-bold ph-arrow-clockwise"></i> Reset Code';
        resetButton.addEventListener('click', () => {
            editor.value = config.fix_starter_code || '';
            checksList.innerHTML = '';
            feedback.className = 'hidden';
            feedback.textContent = '';
        });

        stage.innerHTML = `
            <div class="space-y-5">
                <div>
                    <h4 class="m-0 text-lg font-bold text-gray-900 dark:text-white">Step 3: Fix</h4>
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(simulation.messages.fixPrompt)}</p>
                </div>
                ${renderFixOverview(simulation.messages, initialChecks)}
                <div data-fix-editor class="space-y-4"></div>
                ${renderFixGuidance(simulation.messages, simulation.fixGuidance || config.fix_guidance || [])}
            </div>
        `;
        const actionRow = document.createElement('div');
        actionRow.className = 'flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center';
        actionRow.append(validateButton, resetButton, hintButton);
        stage.querySelector('[data-fix-editor]').append(renderEditorChrome(editor, simulation.language || 'JS'), actionRow, hintBox, checksList, feedback);
    }

    function renderCodeFixSimulation(container, config, context, options) {
        const savedProgress = getSimulationProgress(context.labId, context.taskIndex);
        const state = createSimulationState(savedProgress?.completed ? SimulationStates.COMPLETE : SimulationStates.IDENTIFY);
        const selectedLines = new Set();
        const hintController = createHintController(config.hints || []);
        const explainState = {
            selectedAnswer: null,
            explainDone: Boolean(savedProgress?.completed)
        };

        function rerender() {
            const identifyDone = validateLineSelection([...selectedLines], config.vulnerable_lines || []);
            const explainDone = identifyDone && (explainState.explainDone || [SimulationStates.FIX, SimulationStates.COMPLETE].includes(state.value));
            const navigation = {
                identifyDone,
                explainDone,
                fixDone: state.value === SimulationStates.COMPLETE,
                canVisitExplain: identifyDone,
                canVisitFix: explainDone
            };
            const stage = renderShell(container, state, options.title, navigation, rerender);

            if (state.value === SimulationStates.IDENTIFY) {
                renderIdentify(stage, config, selectedLines, state, rerender, options.messages);
            } else if (state.value === SimulationStates.EXPLAIN) {
                renderExplain(stage, config, state, rerender, options.messages, explainState);
            } else if (state.value === SimulationStates.FIX) {
                renderFix(stage, config, context, state, rerender, options, hintController);
            } else {
                stage.innerHTML = `
                    <div class="rounded-2xl border border-green-200 bg-green-50 p-5 text-green-700 dark:border-green-900/40 dark:bg-green-900/15 dark:text-green-300">
                        <h4 class="m-0 mb-1 text-base font-bold">Simulation Complete</h4>
                        <p class="m-0 text-sm">${escapeHtml(options.messages.complete)}</p>
                    </div>
                `;
            }

            // FIX is excluded because renderFix already places its own hint button inline in
            // the action row; appending here would show a second one.
            if (state.value !== SimulationStates.COMPLETE && state.value !== SimulationStates.FIX) {
                renderHints(stage, hintController);
            }
        }

        rerender();
    }

    Object.assign(BltLabs, {
        renderCodeFixSimulation
    });
}());
