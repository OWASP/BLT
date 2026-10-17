const {
  LAB_PROGRESS_STORAGE_KEY,
  SQLI_LAB_ID,
  SQLI_LOGIN_ENGINE,
  cloneSerializableValue,
  getStoredLabProgress,
  loadLabHelpers,
  renderLabFixture
} = require('./helpers');

describe('simulation progress storage', () => {
  it('stores progress under lab id and task index without changing unrelated tasks', () => {
    const { helpers } = loadLabHelpers();

    helpers.setSimulationProgress(SQLI_LAB_ID, 2, {
      completed: true,
      engine: SQLI_LOGIN_ENGINE,
      state: helpers.SimulationStates.COMPLETE,
      score: 100
    });
    helpers.setSimulationProgress(SQLI_LAB_ID, 3, {
      completed: false,
      engine: 'sqli-union'
    });

    expect(cloneSerializableValue(helpers.getSimulationProgress(SQLI_LAB_ID, 2))).toEqual({
      completed: true,
      engine: SQLI_LOGIN_ENGINE,
      state: helpers.SimulationStates.COMPLETE,
      score: 100
    });
    expect(cloneSerializableValue(helpers.getSimulationProgress(SQLI_LAB_ID, 3))).toEqual({
      completed: false,
      engine: 'sqli-union'
    });
    expect(helpers.getSimulationProgress(SQLI_LAB_ID, 99)).toBeNull();
  });

  it('updates one task while preserving existing metadata for that task', () => {
    const { helpers } = loadLabHelpers();

    helpers.setSimulationProgress(SQLI_LAB_ID, 2, {
      completed: false,
      engine: SQLI_LOGIN_ENGINE,
      score: 20
    });
    helpers.setSimulationProgress(SQLI_LAB_ID, 2, {
      completed: true,
      score: 100
    });

    expect(cloneSerializableValue(helpers.getSimulationProgress(SQLI_LAB_ID, 2))).toEqual({
      completed: true,
      engine: SQLI_LOGIN_ENGINE,
      score: 100
    });
  });

  it('recovers with an empty object when localStorage contains corrupt JSON', () => {
    const { helpers, storage } = loadLabHelpers();

    storage.set(LAB_PROGRESS_STORAGE_KEY, '{ this is not json');

    expect(cloneSerializableValue(helpers.getStoredSimulationProgress())).toEqual({});
  });

  describe.each([
    { name: 'null', storedValue: 'null' },
    { name: 'array', storedValue: '[]' },
    { name: 'string', storedValue: '"progress"' },
    { name: 'number', storedValue: '42' }
  ])('shape-safe storage recovery: $name', ({ storedValue }) => {
    it('recovers with an empty object', () => {
      const { helpers, storage } = loadLabHelpers();

      storage.set(LAB_PROGRESS_STORAGE_KEY, storedValue);

      expect(cloneSerializableValue(helpers.getStoredSimulationProgress())).toEqual({});
      expect(helpers.getSimulationProgress(SQLI_LAB_ID, 0)).toBeNull();
    });
  });

  it('treats storage writes as best effort', () => {
    const { helpers } = loadLabHelpers();
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });

    try {
      let result;
      expect(() => {
        result = helpers.setSimulationProgress(SQLI_LAB_ID, 2, {
          completed: true
        });
      }).not.toThrow();
      expect(result).toBe(false);
    } finally {
      setItem.mockRestore();
    }
  });

  it('restores a completed simulation without dropping other labs from storage', () => {
    const taskIndex = 0;
    const labDocument = renderLabFixture({
      taskIndex,
      labDataText: JSON.stringify([
        {
          simulation: {
            engine: SQLI_LOGIN_ENGINE,
            vulnerable_code: 'const query = "SELECT * FROM users WHERE id = " + id;',
            vulnerable_lines: [1],
            explain: {
              options: [{ id: 'direct_sql_input', label: 'Input changes SQL.' }],
              answer: 'direct_sql_input'
            },
            fix_starter_code: 'const query = "SELECT * FROM users WHERE id = " + id;'
          }
        }
      ])
    });
    const { helpers, storage } = loadLabHelpers({ document: labDocument });
    storage.set(LAB_PROGRESS_STORAGE_KEY, JSON.stringify({
      [SQLI_LAB_ID]: {
        [taskIndex]: {
          completed: true,
          engine: SQLI_LOGIN_ENGINE,
          state: helpers.SimulationStates.COMPLETE,
          score: 100
        }
      },
      'xss-lab': {
        2: {
          completed: true,
          engine: 'xss-reflected'
        }
      }
    }));

    helpers.initializeLabSimulations();

    expect(labDocument.simulationRoot.textContent).toContain('Simulation Complete');
    expect(getStoredLabProgress(storage)['xss-lab']).toEqual({
      2: {
        completed: true,
        engine: 'xss-reflected'
      }
    });
  });
});
