const {
  LAB_PROGRESS_STORAGE_KEY,
  SQLI_EXPLANATION_ANSWER,
  SQLI_LAB_ID,
  SQLI_LOGIN_ENGINE,
  SQLI_VULNERABLE_LINE,
  advanceSqliSimulationToFix,
  answerExplanation,
  cloneSerializableValue,
  createMockDocument,
  findButton,
  findDescendant,
  getFixEditor,
  getRequiredButton,
  getRequiredElement,
  getStoredLabProgress,
  initializeSqliSimulation,
  loadLabHelpers,
  selectCodeLine,
  submitFix,
  validateExplanation,
  validateSelection
} = require('./helpers');

const SECURE_SQLI_FIX = `
  const username = request.body.username;
  const password = request.body.password;
  const query = 'SELECT * FROM users WHERE username = ? AND password = ?';
  db.execute(query, [username, password]);
`;

describe('SQLi simulation user flow', () => {
  it('completes identify, explain, fix, progress, and task-complete dispatch', () => {
    const taskIndex = 0;
    const { labDocument, storage } = initializeSqliSimulation(taskIndex);
    const completionEvents = [];
    labDocument.labRoot.addEventListener('lab:task-complete', (event) => {
      completionEvents.push(event.detail);
    });

    selectCodeLine(labDocument, SQLI_VULNERABLE_LINE);
    validateSelection(labDocument);
    answerExplanation(labDocument);
    validateExplanation(labDocument);
    submitFix(labDocument, SECURE_SQLI_FIX);

    expect(cloneSerializableValue(completionEvents)).toEqual([
      expect.objectContaining({ taskIndex })
    ]);
    expect(cloneSerializableValue(getStoredLabProgress(storage))).toMatchObject({
      [SQLI_LAB_ID]: {
        [taskIndex]: {
          completed: true,
          engine: SQLI_LOGIN_ENGINE,
          state: 'complete',
          score: 100
        }
      }
    });
    expect(labDocument.simulationRoot.textContent).toContain('Simulation Complete');
  });

  it('keeps the learner on identify after an incorrect line selection', () => {
    const { labDocument, storage } = initializeSqliSimulation();

    selectCodeLine(labDocument, SQLI_VULNERABLE_LINE - 1);
    validateSelection(labDocument);

    expect(findButton(labDocument.simulationRoot, 'Validate Selection')).toBeTruthy();
    expect(labDocument.simulationRoot.querySelector(`[data-answer="${SQLI_EXPLANATION_ANSWER}"]`)).toBeNull();
    expect(storage.get(LAB_PROGRESS_STORAGE_KEY)).toBeUndefined();
  });

  it('keeps the learner on explain after an incorrect answer', () => {
    const { labDocument, storage } = initializeSqliSimulation();

    selectCodeLine(labDocument, SQLI_VULNERABLE_LINE);
    validateSelection(labDocument);
    answerExplanation(labDocument, 'missing_https');
    validateExplanation(labDocument);

    expect(findButton(labDocument.simulationRoot, 'Validate Explanation')).toBeTruthy();
    expect(getFixEditor(labDocument.simulationRoot)).toBeNull();
    expect(storage.get(LAB_PROGRESS_STORAGE_KEY)).toBeUndefined();
  });

  it('keeps the learner on fix after an invalid submission', () => {
    const { labDocument, storage } = initializeSqliSimulation();
    const completionEvents = [];
    labDocument.labRoot.addEventListener('lab:task-complete', (event) => {
      completionEvents.push(event.detail);
    });

    advanceSqliSimulationToFix(labDocument);
    getRequiredButton(labDocument.simulationRoot, 'Run Validation').click();

    expect(completionEvents).toEqual([]);
    expect(storage.get(LAB_PROGRESS_STORAGE_KEY)).toBeUndefined();
    expect(getFixEditor(labDocument.simulationRoot)).toBeTruthy();
    expect(labDocument.simulationRoot.textContent).toContain(
      'The fix is close, but the validator still sees SQL injection risk.'
    );
  });

  it('does not allow locked stages to be opened before prerequisites pass', () => {
    const { labDocument } = initializeSqliSimulation();

    labDocument.simulationRoot.querySelector('[data-stage-target="fix"]').click();

    expect(findButton(labDocument.simulationRoot, 'Validate Selection')).toBeTruthy();
    expect(getFixEditor(labDocument.simulationRoot)).toBeNull();
  });

  it('moves back to earlier completed stages through stage navigation', () => {
    const { labDocument } = initializeSqliSimulation();

    advanceSqliSimulationToFix(labDocument);
    expect(getFixEditor(labDocument.simulationRoot)).toBeTruthy();

    labDocument.simulationRoot.querySelector('[data-stage-target="identify"]').click();

    expect(findButton(labDocument.simulationRoot, 'Validate Selection')).toBeTruthy();
    expect(getFixEditor(labDocument.simulationRoot)).toBeNull();
  });

  it('shows progressive hints and repeats the final hint', () => {
    const { labDocument } = initializeSqliSimulation();
    const hintButton = getRequiredButton(labDocument.simulationRoot, 'Show Hint');

    hintButton.click();
    expect(findDescendant(
      labDocument.simulationRoot,
      (element) => element.textContent === 'Look for the line that builds SQL with user input.'
    )).toBeTruthy();

    hintButton.click();
    expect(findDescendant(
      labDocument.simulationRoot,
      (element) => element.textContent === 'Bind username and password separately from the query.'
    )).toBeTruthy();

    hintButton.click();
    expect(findDescendant(
      labDocument.simulationRoot,
      (element) => element.textContent === 'Bind username and password separately from the query.'
    )).toBeTruthy();
  });
});

describe('open redirect identify-explain-fix simulation', () => {
  it('completes and stores progress without legacy payload simulation', () => {
    const taskIndex = 0;
    const labDocument = createMockDocument({
      labId: 'open-redirect',
      simulationEngine: 'redirect-basic',
      taskIndex,
      labDataText: JSON.stringify([
        {
          simulation: {
            engine: 'redirect-basic',
            vulnerable_code: [
              "app.get('/redirect', (req, res) => {",
              "  const next = req.query.next || '/dashboard';",
              '  res.redirect(next);',
              '});'
            ].join('\n'),
            vulnerable_lines: [3],
            explain: {
              question: 'Why can this redirect be abused?',
              options: [
                { id: 'raw_redirect', label: 'The app redirects to raw user input.' },
                { id: 'missing_template', label: 'The app lacks a template.' }
              ],
              answer: 'raw_redirect'
            },
            fix_starter_code: "res.redirect(req.query.next);",
            hints: ['Find the redirect call.']
          }
        }
      ])
    });
    const loaded = loadLabHelpers({ document: labDocument, pathname: '/labs/open-redirect/' });

    loaded.helpers.initializeLabSimulations();
    selectCodeLine(labDocument, 3);
    validateSelection(labDocument);
    getRequiredElement(labDocument.simulationRoot, '[data-answer="raw_redirect"]').click();
    validateExplanation(labDocument);
    expect(getFixEditor(labDocument.simulationRoot)).toBeTruthy();

    submitFix(labDocument, `
      const allowedPaths = ['/dashboard'];
      const parsed = new URL(req.query.next || '/dashboard', 'https://app.example');
      if (parsed.protocol === 'javascript:' || parsed.protocol === 'data:' || req.query.next.startsWith('//')) reject();
      const next = allowedPaths.includes(parsed.pathname) ? parsed.pathname : '/dashboard';
      res.redirect(next);
    `);

    expect(getStoredLabProgress(loaded.storage)).toMatchObject({
      'open-redirect': {
        [taskIndex]: {
          completed: true,
          engine: 'redirect-basic',
          state: 'complete',
          score: 100
        }
      }
    });
    expect(labDocument.simulationRoot.textContent).toContain('Simulation Complete');
  });
});
