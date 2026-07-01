const {
  LAB_PROGRESS_STORAGE_KEY,
  SQLI_EXPLANATION_ANSWER,
  SQLI_LAB_ID,
  SQLI_LOGIN_ENGINE,
  SQLI_VULNERABLE_LINE,
  advanceSqliSimulationToFix,
  answerExplanation,
  cloneSerializableValue,
  findButton,
  findDescendant,
  getFixEditor,
  getRequiredButton,
  getStoredLabProgress,
  initializeSqliSimulation,
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
