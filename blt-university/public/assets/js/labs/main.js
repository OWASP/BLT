(function () {
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

    const SimulationRegistry = {
        'sqli-login': renderSqliLoginSimulation,
        'sqli-union': renderSqliUnionSimulation,
        'sqli-blind': renderSqliBlindSimulation,
        'sqli-time': renderSqliTimeSimulation,
        'xss-reflected': renderReflectedXssSimulation,
        'xss-stored': renderStoredXssSimulation,
        'xss-filter-bypass': renderXssFilterBypassSimulation,
        'xss-dom': renderDomXssSimulation,
        'xss-cookie-theft': renderXssCookieTheftSimulation,
        'csrf-form': renderCsrfFormSimulation,
        'csrf-auto-submit': renderCsrfAutoSubmitSimulation,
        'csrf-image': renderCsrfImageSimulation,
        'csrf-ajax': renderCsrfAjaxSimulation,
        'legacy-payload': renderLegacyPayloadSimulation
    };

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
                if (nextIndex >= currentIndex) {
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
            return JSON.parse(dataElement.textContent || '[]');
        } catch (_error) {
            return [];
        }
    }

    function labIdFromPage() {
        const path = window.location.pathname.replace(/\/$/, '').split('/').filter(Boolean);
        return path[path.length - 1] || 'lab';
    }

    function normalizeLines(lines = []) {
        return lines.map(Number).filter(Number.isFinite).sort((a, b) => a - b);
    }

    function validateLineSelection(selectedLines, expectedLines) {
        const selected = normalizeLines(selectedLines);
        const expected = normalizeLines(expectedLines);

        return selected.length === expected.length && selected.every((line, index) => line === expected[index]);
    }

    function validateExplainAnswer(selectedAnswer, expectedAnswer) {
        return String(selectedAnswer || '') === String(expectedAnswer || '');
    }

    // Regex-based validation.
    function hasParameterizedQuery(code) {
        return /(\?|:\w+|\$\d+)/.test(code) && /\b(execute|query|prepare|preparedstatement)\b/i.test(code);
    }

    function hasSeparateParameterBinding(code) {
        return /\[[^\]]+\]/i.test(code) ||
            /\.(setString|setInt|bindValue|bindParam)\s*\(/i.test(code);
    }

    function hasSqlConcatenation(code) {
        return /select[\s\S]*\+/i.test(code) ||
            /where[\s\S]*\$\{[^}]+}/i.test(code);
    }

    function loginBypassStillWorks(code, payloads = []) {
        if (!hasSqlConcatenation(code)) {
            return false;
        }

        return payloads.some(payload => /or\s+['"]?1['"]?\s*=\s*['"]?1/i.test(payload));
    }

    function validateSqliFix(code, config = {}) {
        const checks = [
            {
                label: 'User input is not concatenated into the SQL string',
                passed: !hasSqlConcatenation(code)
            },
            {
                label: 'Parameterized query or prepared statement detected',
                passed: hasParameterizedQuery(code)
            },
            {
                label: 'User values are passed separately from the SQL string',
                passed: hasSeparateParameterBinding(code)
            },
            {
                label: 'Login bypass payload no longer changes query behavior',
                passed: !loginBypassStillWorks(code, config.attack_payloads || [])
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // XSS validation helpers.
    function usesUnsafeHtmlSink(code) {
        return /\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML\s*\(|document\.write\s*\(/i.test(code);
    }

    function usesSafeTextSink(code) {
        return /\.(textContent|innerText)\s*=|createTextNode\s*\(/i.test(code);
    }

    function encodesHtml(code) {
        return /escapeHTML|encodeHTML|sanitize|DOMPurify|replace\s*\(\s*\/\[&<>"'\]/i.test(code) ||
            /replace\s*\([^)]*&/i.test(code) && /replace\s*\([^)]*</i.test(code);
    }

    function xssPayloadStillExecutes(code, payloads = []) {
        const hasExecutablePayload = payloads.some(payload => /<script|onerror|onload|javascript:/i.test(payload));
        return hasExecutablePayload && usesUnsafeHtmlSink(code) && !encodesHtml(code);
    }

    function validateXssFix(code, config = {}) {
        const checks = [
            {
                label: 'Untrusted input is not written with innerHTML or document.write',
                passed: !usesUnsafeHtmlSink(code)
            },
            {
                label: 'Output uses a safe text sink or explicit HTML encoding',
                passed: usesSafeTextSink(code) || encodesHtml(code)
            },
            {
                label: 'Script payload is rendered as text instead of executing',
                passed: !xssPayloadStillExecutes(code, config.attack_payloads || [])
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
    }

    // CSRF validation helpers.
    function includesCsrfToken(code) {
        return /csrf[_-]?token/i.test(code);
    }

    function validatesCsrfToken(code) {
        return /(validate|verify|check|compare)[\s\S]{0,40}csrf[_-]?token|csrf[_-]?token[\s\S]{0,40}(validate|verify|check|compare)/i.test(code);
    }

    function usesSameSiteCookie(code) {
        return /SameSite\s*=\s*(Strict|Lax)/i.test(code) ||
            /sameSite\s*:\s*['"]?(strict|lax)['"]?/i.test(code);
    }

    function validateCsrfFix(code) {
        const checks = [
            {
                label: 'State-changing form includes a CSRF token',
                passed: includesCsrfToken(code)
            },
            {
                label: 'Server verifies the submitted CSRF token before updating data',
                passed: validatesCsrfToken(code)
            },
            {
                label: 'Session cookie is hardened with SameSite protection',
                passed: usesSameSiteCookie(code)
            }
        ];

        return {
            passed: checks.every(check => check.passed),
            checks
        };
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
            return JSON.parse(localStorage.getItem(storageKey) || '{}');
        } catch (_error) {
            return {};
        }
    }

    function getSimulationProgress(labId, taskIndex) {
        return getStoredSimulationProgress()[labId]?.[taskIndex] || null;
    }

    function setSimulationProgress(labId, taskIndex, value) {
        const storageKey = 'blt-lab-progress';
        const progress = getStoredSimulationProgress();
        const labProgress = progress[labId] || {};

        labProgress[taskIndex] = {
            ...(labProgress[taskIndex] || {}),
            ...value
        };

        progress[labId] = labProgress;
        localStorage.setItem(storageKey, JSON.stringify(progress));
    }

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
        element.className = `rounded-xl px-4 py-3 text-sm font-semibold ${
            type === 'success'
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
        return `<button type="button" data-stage-target="${stateName}" ${canVisit ? '' : 'disabled'} class="rounded-full px-4 py-1.5 text-xs font-bold transition ${
            isDone
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
            <div class="space-y-4">
                <div>
                    <h4 class="m-0 text-base font-bold text-gray-900 dark:text-white">Step 1: Identify Vulnerability</h4>
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(messages.identifyPrompt)}</p>
                </div>
            </div>
        `;
        stage.querySelector('.space-y-4').append(codeMount, feedback, validateButton);
    }

    function renderExplain(stage, config, state, rerender, messages, model) {
        const explain = config.explain || {};
        const feedback = document.createElement('p');
        feedback.className = 'hidden';

        const options = document.createElement('div');
        options.className = 'space-y-3';
        (explain.options || []).forEach(option => {
            const isSelected = model.selectedAnswer === option.id;
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
                model.selectedAnswer = option.id;
                rerender();
            });
            options.append(button);
        });

        const validateButton = document.createElement('button');
        validateButton.type = 'button';
        validateButton.className = buttonClasses();
        validateButton.textContent = 'Validate Explanation';
        validateButton.addEventListener('click', () => {
            if (validateExplainAnswer(model.selectedAnswer, explain.answer)) {
                model.explainDone = true;
                state.transition(SimulationStates.FIX);
                rerender();
            } else {
                renderFeedback(feedback, messages.explainError, 'error');
            }
        });

        stage.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="m-0 text-base font-bold text-gray-900 dark:text-white">Step 2: Explain</h4>
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(explain.question || 'Why is this vulnerable?')}</p>
                </div>
            </div>
        `;
        stage.querySelector('.space-y-4').append(options, feedback, validateButton);
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

    function renderFix(stage, config, context, state, rerender, options, hintController) {
        const editor = renderCodeEditor(config.fix_starter_code || '');
        const feedback = document.createElement('div');
        feedback.className = 'hidden';
        const checksList = document.createElement('div');
        checksList.className = 'space-y-2';
        const initialChecks = options.validateFix(config.fix_starter_code || '', config).checks;
        const { hintButton, hintBox } = createHintElements(hintController);

        const validateButton = document.createElement('button');
        validateButton.type = 'button';
        validateButton.className = buttonClasses();
        validateButton.innerHTML = '<i class="ph-bold ph-play"></i> Run Validation';
        validateButton.addEventListener('click', () => {
            const result = options.validateFix(editor.value, config);
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
                    engine: options.engine,
                    state: SimulationStates.COMPLETE,
                    score: 100
                });
                context.completeTask();
                rerender();
            } else {
                renderFeedback(feedback, options.messages.fixError, 'error');
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
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">${escapeHtml(options.messages.fixPrompt)}</p>
                </div>
                ${renderFixOverview(options.messages, initialChecks)}
                <div data-fix-editor class="space-y-4"></div>
                ${renderFixGuidance(options.messages, options.fixGuidance || config.fix_guidance || [])}
            </div>
        `;
        const actionRow = document.createElement('div');
        actionRow.className = 'flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center';
        actionRow.append(validateButton, resetButton, hintButton);
        stage.querySelector('[data-fix-editor]').append(renderEditorChrome(editor, options.language || 'JS'), actionRow, hintBox, checksList, feedback);
    }

    function renderCodeFixSimulation(container, config, context, options) {
        const savedProgress = getSimulationProgress(context.labId, context.taskIndex);
        const state = createSimulationState(savedProgress?.completed ? SimulationStates.COMPLETE : SimulationStates.IDENTIFY);
        const selectedLines = new Set();
        const hintController = createHintController(config.hints || []);
        const model = {
            selectedAnswer: null,
            explainDone: Boolean(savedProgress?.completed)
        };

        function rerender() {
            const identifyDone = validateLineSelection([...selectedLines], config.vulnerable_lines || []);
            const explainDone = identifyDone && (model.explainDone || [SimulationStates.FIX, SimulationStates.COMPLETE].includes(state.value));
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
                renderExplain(stage, config, state, rerender, options.messages, model);
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

            if (state.value !== SimulationStates.COMPLETE && state.value !== SimulationStates.FIX) {
                renderHints(stage, hintController);
            }
        }

        rerender();
    }

    function renderSqliLoginSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'sqli-login',
            title: 'SQL Injection Login Bypass',
            validateFix: validateSqliFix,
            fixGuidance: [
                {
                    title: 'Separate SQL from data',
                    body: 'Keep the SQL statement static and put untrusted values in a separate parameter list.',
                    code: "const query = 'SELECT * FROM users WHERE username = ? AND password = ?';\ndb.execute(query, [username, password]);"
                },
                {
                    title: 'Placeholder styles vary',
                    body: 'Many drivers use ? placeholders. PostgreSQL often uses $1, $2. Both are safe when values are bound separately.',
                    code: "db.query('SELECT * FROM users WHERE username = $1', [username]);"
                },
                {
                    title: 'What to avoid',
                    body: "String concatenation lets payloads like ' OR '1'='1 change the query structure.",
                    code: "query = \"... username = '\" + username + \"'\";"
                }
            ],
            messages: {
                identifyPrompt: 'Select the line where user input is joined into the SQL query.',
                identifyError: 'Not quite. Select the line where user input is joined into the SQL query.',
                explainError: 'Choose the answer that explains how the payload changes SQL logic.',
                fixPrompt: 'Rewrite the query using placeholders and pass user values separately.',
                fixGoal: 'Protect the login query from SQL injection.',
                fixError: 'The fix is close, but the validator still sees SQL injection risk.',
                complete: 'You identified the vulnerable line, explained the risk, and fixed the query.'
            }
        });
    }

    function renderSqliVariantSimulation(container, config, context, engine, title, messages) {
        renderCodeFixSimulation(container, config, context, {
            engine,
            title,
            validateFix: validateSqliFix,
            fixGuidance: [
                {
                    title: 'Keep the query shape fixed',
                    body: 'Build one static SQL statement and place every user-controlled value in a parameter list.',
                    code: "const query = 'SELECT id, name, price, description FROM products WHERE name LIKE ?';\ndb.execute(query, [`%${search}%`]);"
                },
                {
                    title: 'Bind inference inputs too',
                    body: 'Blind and time-based checks still need placeholders. The database should receive values, not SQL fragments.',
                    code: "db.query('SELECT id FROM profiles WHERE user_id = $1', [userId]);"
                },
                {
                    title: 'What to avoid',
                    body: 'Never concatenate search terms, IDs, ORDER BY values, or timing probes directly into SQL.',
                    code: "query = '... WHERE id = ' + userId;"
                }
            ],
            messages
        });
    }

    function renderSqliUnionSimulation(container, config, context) {
        renderSqliVariantSimulation(container, config, context, 'sqli-union', 'Union SQL Injection Defense', {
            identifyPrompt: 'Select the line where the search term is concatenated into a query that returns table columns.',
            identifyError: 'Not quite. Select the line where the search term changes the SELECT query.',
            explainError: 'Choose the answer that explains why UNION can append rows from another table.',
            fixPrompt: 'Parameterize the search term so UNION payloads are treated as data.',
            fixGoal: 'Stop UNION payloads from changing the product search query.',
            fixError: 'The fix still needs a static query, placeholders, and separate bound values.',
            complete: 'You identified the UNION injection point, explained the column-matching risk, and fixed the query.'
        });
    }

    function renderSqliBlindSimulation(container, config, context) {
        renderSqliVariantSimulation(container, config, context, 'sqli-blind', 'Blind SQL Injection Defense', {
            identifyPrompt: 'Select the line where the user ID can change a Boolean condition in SQL.',
            identifyError: 'Not quite. Select the query line that lets input alter SQL logic.',
            explainError: 'Choose the answer that explains how response differences leak data.',
            fixPrompt: 'Bind the user ID as a parameter so Boolean probes cannot alter the WHERE clause.',
            fixGoal: 'Stop Boolean probes from changing profile lookup behavior.',
            fixError: 'The fix still needs a parameterized query with the user ID bound separately.',
            complete: 'You identified the blind injection point, explained the inference channel, and fixed the lookup.'
        });
    }

    function renderSqliTimeSimulation(container, config, context) {
        renderSqliVariantSimulation(container, config, context, 'sqli-time', 'Time-Based SQL Injection Defense', {
            identifyPrompt: 'Select the line where the article ID can inject a time-delay expression.',
            identifyError: 'Not quite. Select the query line where user input reaches SQL.',
            explainError: 'Choose the answer that explains how response time becomes a data signal.',
            fixPrompt: 'Bind the article ID as a parameter so SLEEP payloads stay inert data.',
            fixGoal: 'Stop timing payloads from changing article lookup behavior.',
            fixError: 'The fix still needs a static query, placeholder, and separate parameter binding.',
            complete: 'You identified the timing injection point, explained the delay signal, and fixed the query.'
        });
    }

    function renderReflectedXssSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'xss-reflected',
            title: 'Reflected XSS Comment System',
            validateFix: validateXssFix,
            fixGuidance: [
                {
                    title: 'Prefer text sinks',
                    body: 'If the content should be text, use textContent so the browser does not parse tags or event handlers.',
                    code: 'preview.textContent = comment;'
                },
                {
                    title: 'Encode before HTML contexts',
                    body: 'If you must render into HTML, encode <, >, &, quotes, and apostrophes before insertion.',
                    code: 'preview.innerHTML = escapeHTML(comment);'
                },
                {
                    title: 'What to avoid',
                    body: 'innerHTML with raw user input turns payloads into executable markup.',
                    code: 'preview.innerHTML = comment;'
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that renders untrusted input as HTML.',
                identifyError: 'Not quite. Look for the line that writes user input into the page as HTML.',
                explainError: 'Choose the answer that explains why the script can execute in another user browser.',
                fixPrompt: 'Render the comment as text or encode HTML before displaying it.',
                fixGoal: 'Render untrusted comments without executing attacker-controlled markup.',
                fixError: 'The fix still allows untrusted HTML to reach an executable sink.',
                complete: 'You identified the unsafe HTML sink, explained the XSS risk, and rendered input safely.'
            }
        });
    }

    function renderXssVariantSimulation(container, config, context, engine, title, messages) {
        renderCodeFixSimulation(container, config, context, {
            engine,
            title,
            validateFix: validateXssFix,
            fixGuidance: [
                {
                    title: 'Prefer safe text sinks',
                    body: 'Use textContent or createTextNode when user content should be displayed as text.',
                    code: 'profileBio.textContent = bio;'
                },
                {
                    title: 'Encode before HTML contexts',
                    body: 'If markup is required, encode dangerous characters or use a trusted sanitizer.',
                    code: 'result.innerHTML = escapeHTML(searchTerm);'
                },
                {
                    title: 'What to avoid',
                    body: 'Filters that only block a few strings are bypassable. Do not write raw input into HTML.',
                    code: 'output.innerHTML = userInput;'
                }
            ],
            messages
        });
    }

    function renderStoredXssSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-stored', 'Stored XSS Profile Defense', {
            identifyPrompt: 'Select the line that renders stored profile data as executable HTML.',
            identifyError: 'Not quite. Select the line that writes the stored bio into the page as HTML.',
            explainError: 'Choose the answer that explains why every profile viewer is affected.',
            fixPrompt: 'Render stored profile content as text or sanitize it before display.',
            fixGoal: 'Prevent stored profile data from executing script for future viewers.',
            fixError: 'The fix still allows untrusted stored HTML to reach an executable sink.',
            complete: 'You identified stored XSS, explained persistence, and rendered profile content safely.'
        });
    }

    function renderXssFilterBypassSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-filter-bypass', 'XSS Filter Bypass Defense', {
            identifyPrompt: 'Select the line where filtered input is still inserted as HTML.',
            identifyError: 'Not quite. Select the line where the filtered search term reaches an HTML sink.',
            explainError: 'Choose the answer that explains why blocklists miss alternate payloads.',
            fixPrompt: 'Replace blocklist filtering with safe output encoding or a text sink.',
            fixGoal: 'Prevent bypass payloads from executing through the search result.',
            fixError: 'The fix still relies on unsafe HTML rendering or insufficient encoding.',
            complete: 'You identified the bypassable sink, explained blocklist weakness, and fixed rendering.'
        });
    }

    function renderDomXssSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-dom', 'DOM XSS Defense', {
            identifyPrompt: 'Select the client-side line that writes URL fragment data into HTML.',
            identifyError: 'Not quite. Select the DOM assignment that parses attacker-controlled markup.',
            explainError: 'Choose the answer that explains why this happens entirely in the browser.',
            fixPrompt: 'Treat fragment data as text or sanitize it before updating the DOM.',
            fixGoal: 'Stop URL fragment content from becoming executable DOM.',
            fixError: 'The fix still allows fragment data to reach an unsafe HTML sink.',
            complete: 'You identified DOM XSS, explained the client-side data flow, and fixed the sink.'
        });
    }

    function renderXssCookieTheftSimulation(container, config, context) {
        renderXssVariantSimulation(container, config, context, 'xss-cookie-theft', 'XSS Cookie Theft Defense', {
            identifyPrompt: 'Select the line that renders user messages as executable HTML.',
            identifyError: 'Not quite. Select the message rendering line that allows script execution.',
            explainError: 'Choose the answer that explains how script execution exposes browser data.',
            fixPrompt: 'Render messages safely and avoid exposing sensitive cookies to JavaScript.',
            fixGoal: 'Prevent message payloads from executing and reading cookie data.',
            fixError: 'The fix still allows untrusted HTML into the page.',
            complete: 'You identified the cookie-theft path, explained the impact, and fixed rendering.'
        });
    }

    function renderCsrfFormSimulation(container, config, context) {
        renderCodeFixSimulation(container, config, context, {
            engine: 'csrf-form',
            title: 'CSRF Email Change Defense',
            validateFix: validateCsrfFix,
            fixGuidance: [
                {
                    title: 'Add request intent',
                    body: 'State-changing forms should include a per-session CSRF token that attackers cannot guess.',
                    code: '<input type="hidden" name="csrf_token" value="{{ csrfToken }}">'
                },
                {
                    title: 'Verify on the server',
                    body: 'The server must compare the submitted token with the session token before changing data.',
                    code: 'verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);'
                },
                {
                    title: 'Harden cookies',
                    body: 'SameSite cookies reduce automatic cross-site cookie sending and complement token validation.',
                    code: "session({ cookie: { sameSite: 'Lax' } })"
                }
            ],
            messages: {
                identifyPrompt: 'Select the line that updates state without verifying request intent.',
                identifyError: 'Not quite. Select the state-changing line that runs without CSRF validation.',
                explainError: 'Choose the answer that explains why an attacker can force this request.',
                fixPrompt: 'Add a CSRF token to the form, verify it server-side, and harden the session cookie.',
                fixGoal: 'Protect this endpoint from CSRF.',
                fixError: 'The fix still needs token presence, server-side validation, and cookie hardening.',
                complete: 'You identified the missing request-intent check and added CSRF defenses.'
            }
        });
    }

    function renderCsrfVariantSimulation(container, config, context, engine, title, messages) {
        renderCodeFixSimulation(container, config, context, {
            engine,
            title,
            validateFix: validateCsrfFix,
            fixGuidance: [
                {
                    title: 'Require request intent',
                    body: 'State-changing requests should include an unpredictable CSRF token tied to the user session.',
                    code: '<input type="hidden" name="csrf_token" value="{{ csrfToken }}">'
                },
                {
                    title: 'Verify before action',
                    body: 'Reject the request before changing data if the submitted token does not match the session.',
                    code: 'verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);'
                },
                {
                    title: 'Harden cookies',
                    body: 'SameSite cookies reduce automatic cross-site cookie sending and complement token validation.',
                    code: "session({ cookie: { sameSite: 'Lax' } })"
                }
            ],
            messages
        });
    }

    function renderCsrfAutoSubmitSimulation(container, config, context) {
        renderCsrfVariantSimulation(container, config, context, 'csrf-auto-submit', 'Auto-Submit CSRF Defense', {
            identifyPrompt: 'Select the state-changing transfer line that runs without CSRF validation.',
            identifyError: 'Not quite. Select the line that transfers funds before verifying request intent.',
            explainError: 'Choose the answer that explains why auto-submit can trigger the request.',
            fixPrompt: 'Require and verify a CSRF token before transferring money, then harden cookies.',
            fixGoal: 'Protect the transfer endpoint from auto-submitted cross-site forms.',
            fixError: 'The fix still needs token presence, server validation, and SameSite cookie protection.',
            complete: 'You identified the auto-submit CSRF path and added request-intent defenses.'
        });
    }

    function renderCsrfImageSimulation(container, config, context) {
        renderCsrfVariantSimulation(container, config, context, 'csrf-image', 'Image CSRF Defense', {
            identifyPrompt: 'Select the GET route that deletes an account based only on a query string.',
            identifyError: 'Not quite. Select the destructive route that an image load can trigger.',
            explainError: 'Choose the answer that explains why GET endpoints should not change state.',
            fixPrompt: 'Move deletion behind a POST flow with CSRF validation and hardened cookies.',
            fixGoal: 'Prevent image loads from triggering account deletion.',
            fixError: 'The fix still needs token presence, server validation, and SameSite cookie protection.',
            complete: 'You identified the image-triggered CSRF path and protected the destructive action.'
        });
    }

    function renderCsrfAjaxSimulation(container, config, context) {
        renderCsrfVariantSimulation(container, config, context, 'csrf-ajax', 'AJAX CSRF Defense', {
            identifyPrompt: 'Select the password change line that trusts the request without token validation.',
            identifyError: 'Not quite. Select the line that changes the password before CSRF validation.',
            explainError: 'Choose the answer that explains why AJAX still needs request-intent checks.',
            fixPrompt: 'Validate a CSRF token from the request body or header before changing the password.',
            fixGoal: 'Protect the password endpoint from cross-site JavaScript requests.',
            fixError: 'The fix still needs token presence, server validation, and SameSite cookie protection.',
            complete: 'You identified the AJAX CSRF path and added token-based defenses.'
        });
    }

    function normalizeChallengeAnswer(value) {
        return String(value || '').trim().replace(/\s+/g, ' ').toLowerCase();
    }

    function renderLegacyPayloadSimulation(container, config, context) {
        const savedProgress = getSimulationProgress(context.labId, context.taskIndex);
        const completed = Boolean(savedProgress?.completed);
        const acceptedPayloads = Array.isArray(config.accepted_payloads)
            ? config.accepted_payloads
            : (config.accepted_payloads ? [config.accepted_payloads] : []);
        const expectedAnswers = [config.success_payload, ...acceptedPayloads]
            .map(normalizeChallengeAnswer)
            .filter(Boolean);
        const parameters = (config.vulnerable_parameters || []).map(escapeHtml).join(', ') || 'No parameter required';
        const hints = (config.hints || []).map(hint => `<li>${escapeHtml(hint)}</li>`).join('');

        container.innerHTML = `
            <section class="mt-6 overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900" aria-label="Safe payload simulation">
                <div class="border-b border-gray-200 bg-gray-50 p-5 dark:border-gray-700 dark:bg-gray-800/50">
                    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                            <p class="m-0 text-[10px] font-bold uppercase tracking-widest text-bltRed">Safe Mock Simulation</p>
                            <h3 class="m-0 mt-1 text-lg font-bold text-gray-900 dark:text-white">${escapeHtml(String(config.scenario || config.type || 'Payload challenge').replaceAll('_', ' '))}</h3>
                        </div>
                        <span class="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold capitalize text-gray-600 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300">${escapeHtml(config.difficulty || 'practice')}</span>
                    </div>
                </div>
                <div class="space-y-5 p-5">
                    <div class="grid gap-3 sm:grid-cols-2">
                        <div class="rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/40">
                            <p class="m-0 text-[10px] font-bold uppercase tracking-widest text-gray-400">Target</p>
                            <code class="mt-2 block break-all text-sm text-gray-800 dark:text-gray-200">${escapeHtml(config.target_url || '/safe-simulation')}</code>
                        </div>
                        <div class="rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/40">
                            <p class="m-0 text-[10px] font-bold uppercase tracking-widest text-gray-400">Parameters</p>
                            <p class="m-0 mt-2 text-sm font-semibold text-gray-800 dark:text-gray-200">${parameters}</p>
                        </div>
                    </div>
                    <div>
                        <h4 class="m-0 text-sm font-bold text-gray-900 dark:text-white">Objective</h4>
                        <p class="m-0 mt-1 text-sm leading-relaxed text-gray-600 dark:text-gray-300">${escapeHtml(config.success_criteria || 'Enter the payload that completes this safe simulation.')}</p>
                    </div>
                    ${completed ? `
                        <div class="rounded-xl border border-green-200 bg-green-50 p-4 text-green-700 dark:border-green-900/40 dark:bg-green-900/15 dark:text-green-300">
                            <p class="m-0 text-sm font-bold">Simulation complete</p>
                            <p class="m-0 mt-1 text-sm">The expected behavior was reproduced inside the mock environment. No real request or command was executed.</p>
                        </div>
                    ` : `
                        <div class="space-y-3">
                            <label class="block text-sm font-bold text-gray-900 dark:text-white" for="legacy-payload-${context.taskIndex}">Payload or action</label>
                            <textarea id="legacy-payload-${context.taskIndex}" data-legacy-payload rows="4" class="w-full rounded-xl border border-gray-200 bg-gray-950 p-4 font-mono text-sm text-gray-100 outline-none transition focus:border-bltRed focus:ring-2 focus:ring-red-100 dark:border-gray-700" placeholder="Enter your safe simulation input..."></textarea>
                            <div class="flex flex-wrap gap-3">
                                <button type="button" data-legacy-submit class="inline-flex items-center justify-center gap-2 rounded-xl bg-bltRed px-5 py-3 text-sm font-bold text-white transition hover:bg-bltRedHover"><i class="ph-bold ph-play"></i> Run Simulation</button>
                                <button type="button" data-legacy-reset class="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-3 text-sm font-semibold text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300"><i class="ph-bold ph-arrow-clockwise"></i> Reset</button>
                            </div>
                            <p data-legacy-feedback class="hidden" aria-live="polite"></p>
                        </div>
                        ${hints ? `
                            <details class="rounded-xl border border-red-100 bg-red-50/60 p-4 dark:border-red-900/30 dark:bg-red-900/10">
                                <summary class="cursor-pointer text-sm font-bold text-gray-900 dark:text-white">Show hints</summary>
                                <ul class="mb-0 mt-3 space-y-2 pl-5 text-sm text-gray-600 dark:text-gray-300">${hints}</ul>
                            </details>
                        ` : ''}
                    `}
                    <p class="m-0 text-xs leading-relaxed text-gray-500 dark:text-gray-400"><strong>Safety boundary:</strong> this challenge only compares input locally in your browser. It never sends the payload, contacts the target, uploads a file, or executes a command.</p>
                </div>
            </section>
        `;

        if (completed) {
            return;
        }

        const editor = container.querySelector('[data-legacy-payload]');
        const feedback = container.querySelector('[data-legacy-feedback]');
        container.querySelector('[data-legacy-submit]')?.addEventListener('click', () => {
            const answer = normalizeChallengeAnswer(editor?.value);
            if (answer && expectedAnswers.includes(answer)) {
                setSimulationProgress(context.labId, context.taskIndex, {
                    completed: true,
                    engine: 'legacy-payload',
                    state: SimulationStates.COMPLETE,
                    score: 100
                });
                context.completeTask();
                renderLegacyPayloadSimulation(container, config, context);
                return;
            }

            renderFeedback(feedback, 'That input does not reproduce the expected mock behavior yet. Review the objective and reveal a hint if needed.', 'error');
        });
        container.querySelector('[data-legacy-reset]')?.addEventListener('click', () => {
            if (editor) {
                editor.value = '';
                editor.focus();
            }
            if (feedback) {
                feedback.className = 'hidden';
                feedback.textContent = '';
            }
        });
    }

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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeLabSimulations);
    } else {
        initializeLabSimulations();
    }
}());
