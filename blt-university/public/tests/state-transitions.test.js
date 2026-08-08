const {
  findButton,
  getFixEditor,
  loadLabHelpers,
  renderLabFixture
} = require('./helpers');

describe('simulation state machine', () => {
  describe.each([
    {
      name: 'unknown initial state',
      initialState: 'definitely-not-a-stage',
      transitionTo: null,
      expectedState: 'identify'
    },
    {
      name: 'invalid transition',
      initialState: 'identify',
      transitionTo: 'sideways',
      expectedState: 'identify'
    },
    {
      name: 'skipping from identify to complete',
      initialState: 'identify',
      transitionTo: 'complete',
      expectedState: 'identify'
    },
    {
      name: 'moving backwards from fix to explain',
      initialState: 'fix',
      transitionTo: 'explain',
      expectedState: 'fix'
    }
  ])('$name', ({ initialState, transitionTo, expectedState }) => {
    it(`keeps the stage at ${expectedState}`, () => {
      const { createSimulationState } = loadLabHelpers().helpers;
      const simulationState = createSimulationState(initialState);

      if (transitionTo) {
        simulationState.transition(transitionTo);
      }

      expect(simulationState.value).toBe(expectedState);
    });
  });

  it('allows one-stage forward transitions in order', () => {
    const { SimulationStates, createSimulationState } = loadLabHelpers().helpers;
    const simulationState = createSimulationState();

    expect(simulationState.transition(SimulationStates.EXPLAIN)).toBe(SimulationStates.EXPLAIN);
    expect(simulationState.transition(SimulationStates.FIX)).toBe(SimulationStates.FIX);
    expect(simulationState.transition(SimulationStates.COMPLETE)).toBe(SimulationStates.COMPLETE);
  });
});

describe('lab simulation initialization', () => {
  it('renders a safe placeholder when a simulation engine is unknown', () => {
    const labDocument = renderLabFixture({
      labDataText: JSON.stringify([{ simulation: { engine: 'missing-engine' } }]),
      simulationEngine: 'missing-engine'
    });
    const { helpers } = loadLabHelpers({ document: labDocument });

    helpers.initializeLabSimulations();

    expect(labDocument.simulationRoot.textContent).toContain(
      'Simulation engine "missing-engine" is not implemented yet'
    );
  });

  describe.each([
    { name: 'malformed JSON', labDataText: '{ no valid json' },
    { name: 'empty array', labDataText: JSON.stringify([]) },
    { name: 'null', labDataText: JSON.stringify(null) },
    { name: 'string', labDataText: JSON.stringify('hello') },
    { name: 'number', labDataText: JSON.stringify(123) }
  ])('fallback lab data: $name', ({ labDataText }) => {
    it('still renders a usable simulation shell', () => {
      const labDocument = renderLabFixture({
        labDataText,
        simulationEngine: 'sqli-login'
      });
      const { helpers } = loadLabHelpers({ document: labDocument });

      expect(() => helpers.initializeLabSimulations()).not.toThrow();
      expect(findButton(labDocument.simulationRoot, 'Validate Selection')).toBeTruthy();
      expect(getFixEditor(labDocument.simulationRoot)).toBeNull();
    });
  });
});
