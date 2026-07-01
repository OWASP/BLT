const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const LAB_PROGRESS_STORAGE_KEY = 'blt-lab-progress';
const SQLI_LAB_ID = 'sql-injection';
const SQLI_EXPLANATION_ANSWER = 'direct_sql_input';
const SQLI_LOGIN_ENGINE = 'sqli-login';
const SQLI_VULNERABLE_LINE = 3;

function findDescendant(rootElement, predicate) {
  const walker = document.createTreeWalker(rootElement, NodeFilter.SHOW_ELEMENT);
  let current = rootElement;

  while (current) {
    if (predicate(current)) {
      return current;
    }
    current = walker.nextNode();
  }

  return null;
}

function findButton(rootElement, label) {
  return [...rootElement.querySelectorAll('button')].find((element) =>
    element.textContent.includes(label)
  ) || null;
}

function getRequiredButton(rootElement, label) {
  const button = findButton(rootElement, label);
  expect(button).toBeTruthy();
  return button;
}

function getRequiredElement(rootElement, selector) {
  const element = rootElement.querySelector(selector);
  expect(element).toBeTruthy();
  return element;
}

function getFixEditor(rootElement) {
  return findDescendant(rootElement, (element) => element.tagName === 'TEXTAREA');
}

function getStoredLabProgress(storage) {
  return JSON.parse(storage.get(LAB_PROGRESS_STORAGE_KEY));
}

function createMockDocument({
  labDataText = '[]',
  labId = SQLI_LAB_ID,
  simulationEngine = SQLI_LOGIN_ENGINE,
  taskIndex = 0
} = {}) {
  document.body.replaceChildren();

  const labData = document.createElement('script');
  labData.id = 'lab-data';
  labData.type = 'application/json';
  labData.textContent = labDataText;

  const labRoot = document.createElement('main');
  labRoot.dataset.labRoot = '';
  labRoot.dataset.labId = labId;

  const simulationRoot = document.createElement('div');
  simulationRoot.dataset.simulationRoot = '';
  simulationRoot.dataset.simulationEngine = simulationEngine;
  simulationRoot.dataset.taskIndex = String(taskIndex);

  labRoot.append(simulationRoot);
  document.body.append(labData, labRoot);

  document.labRoot = labRoot;
  document.simulationRoot = simulationRoot;

  return document;
}

function loadLabHelpers(overrides = {}) {
  window.localStorage.clear();
  delete window.__BLT_LAB_TESTING__;
  delete window.BltLabs;
  window.__BLT_LAB_TEST_MODE__ = true;

  if (overrides.pathname) {
    window.history.pushState({}, '', overrides.pathname);
  } else {
    window.history.pushState({}, '', '/labs/sql-injection/');
  }

  if (!overrides.document) {
    createMockDocument();
  }

  Object.defineProperty(document, 'readyState', {
    configurable: true,
    value: 'loading'
  });

  const browserSandbox = {
    CustomEvent: window.CustomEvent,
    document,
    localStorage: window.localStorage,
    window
  };

  const modularScriptNames = [
    'core.js',
    'validators.js',
    'ui.js',
    'flow.js',
    'simulations.js',
    'main.js'
  ];
  const scriptNames = fs.existsSync(path.join(__dirname, '..', 'assets/js/labs/core.js'))
    ? modularScriptNames
    : ['main.js'];

  scriptNames.forEach((scriptName) => {
    const scriptPath = path.join(__dirname, '..', 'assets/js/labs', scriptName);
    const labEngineSource = fs.readFileSync(scriptPath, 'utf8');
    vm.runInNewContext(labEngineSource, browserSandbox, { filename: `assets/js/labs/${scriptName}` });
  });
  delete window.__BLT_LAB_TEST_MODE__;

  expect(window.__BLT_LAB_TESTING__).toBeTruthy();

  return {
    helpers: window.__BLT_LAB_TESTING__,
    storage: {
      get(key) {
        return window.localStorage.getItem(key) ?? undefined;
      },
      set(key, value) {
        window.localStorage.setItem(key, String(value));
      }
    }
  };
}

function cloneSerializableValue(value) {
  return JSON.parse(JSON.stringify(value));
}

function createSqliLoginTask(overrides = {}) {
  return {
    simulation: {
      engine: SQLI_LOGIN_ENGINE,
      vulnerable_code: [
        'const username = request.body.username;',
        'const password = request.body.password;',
        'const query = "SELECT * FROM users WHERE username = \'" + username + "\' AND password = \'" + password + "\'";',
        'db.query(query);'
      ].join('\n'),
      vulnerable_lines: [SQLI_VULNERABLE_LINE],
      explain: {
        question: 'Why can the login be bypassed?',
        options: [
          { id: SQLI_EXPLANATION_ANSWER, label: 'User input is concatenated directly into the SQL query.' },
          { id: 'missing_https', label: 'The request is not using HTTPS.' }
        ],
        answer: SQLI_EXPLANATION_ANSWER
      },
      attack_payloads: ["' OR '1'='1"],
      fix_starter_code: [
        'const username = request.body.username;',
        'const password = request.body.password;',
        'const query = "SELECT * FROM users WHERE username = \'" + username + "\' AND password = \'" + password + "\'";',
        'db.query(query);'
      ].join('\n'),
      hints: [
        'Look for the line that builds SQL with user input.',
        'Bind username and password separately from the query.'
      ],
      ...overrides
    }
  };
}

function createSqliSimulationDocument(taskIndex = 0, taskOverrides = {}) {
  return createMockDocument({
    taskIndex,
    labDataText: JSON.stringify([
      createSqliLoginTask(taskOverrides)
    ])
  });
}

function initializeSqliSimulation(taskIndex = 0, taskOverrides = {}) {
  const labDocument = createSqliSimulationDocument(taskIndex, taskOverrides);
  const loaded = loadLabHelpers({ document: labDocument });

  loaded.helpers.initializeLabSimulations();

  return {
    ...loaded,
    labDocument
  };
}

function selectCodeLine(labDocument, lineNumber) {
  getRequiredElement(labDocument.simulationRoot, `[data-line-number="${lineNumber}"]`).click();
}

function validateSelection(labDocument) {
  getRequiredButton(labDocument.simulationRoot, 'Validate Selection').click();
}

function answerExplanation(labDocument, answerId = SQLI_EXPLANATION_ANSWER) {
  getRequiredElement(labDocument.simulationRoot, `[data-answer="${answerId}"]`).click();
}

function validateExplanation(labDocument) {
  getRequiredButton(labDocument.simulationRoot, 'Validate Explanation').click();
}

function submitFix(labDocument, code) {
  const editor = getFixEditor(labDocument.simulationRoot);
  expect(editor).toBeTruthy();
  editor.value = code;
  getRequiredButton(labDocument.simulationRoot, 'Run Validation').click();
}

function advanceSqliSimulationToFix(labDocument) {
  selectCodeLine(labDocument, SQLI_VULNERABLE_LINE);
  validateSelection(labDocument);
  answerExplanation(labDocument);
  validateExplanation(labDocument);
}

module.exports = {
  LAB_PROGRESS_STORAGE_KEY,
  SQLI_EXPLANATION_ANSWER,
  SQLI_LAB_ID,
  SQLI_LOGIN_ENGINE,
  SQLI_VULNERABLE_LINE,
  advanceSqliSimulationToFix,
  answerExplanation,
  cloneSerializableValue,
  createMockDocument,
  createSqliLoginTask,
  createSqliSimulationDocument,
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
};
