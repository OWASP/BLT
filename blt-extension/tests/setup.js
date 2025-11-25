// Mock Chrome API for testing
global.chrome = {
  runtime: {
    sendMessage: jest.fn((message, callback) => {
      if (callback) callback();
    }),
    onMessage: {
      addListener: jest.fn(),
      removeListener: jest.fn()
    },
    getURL: jest.fn((path) => `chrome-extension://test-id/${path}`),
    getManifest: jest.fn(() => ({
      version: '1.5.0'
    }))
  },
  tabs: {
    query: jest.fn((options, callback) => {
      callback([{ id: 1, url: 'https://example.com' }]);
    }),
    create: jest.fn((options, callback) => {
      if (callback) callback({ id: 2 });
    }),
    captureVisibleTab: jest.fn((windowId, options, callback) => {
      callback('data:image/png;base64,mock-screenshot-data');
    }),
    sendMessage: jest.fn()
  },
  storage: {
    local: {
      get: jest.fn((keys, callback) => {
        const mockData = {
          jobApplications: []
        };
        if (typeof keys === 'string') {
          callback({ [keys]: mockData[keys] });
        } else if (Array.isArray(keys)) {
          const result = {};
          keys.forEach(key => {
            result[key] = mockData[key];
          });
          callback(result);
        } else {
          callback(mockData);
        }
      }),
      set: jest.fn((data, callback) => {
        if (callback) callback();
      }),
      remove: jest.fn((keys, callback) => {
        if (callback) callback();
      })
    }
  },
  downloads: {
    download: jest.fn((options, callback) => {
      if (callback) callback(1);
    })
  },
  windows: {
    WINDOW_ID_CURRENT: -2
  }
};

// Mock window.close
global.window.close = jest.fn();

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: jest.fn((key) => localStorageMock.store[key] || null),
  setItem: jest.fn((key, value) => {
    localStorageMock.store[key] = value;
  }),
  removeItem: jest.fn((key) => {
    delete localStorageMock.store[key];
  }),
  clear: jest.fn(() => {
    localStorageMock.store = {};
  })
};
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ available: true, trademarks: [] })
  })
);

// Reset all mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
  localStorageMock.clear();
  document.body.innerHTML = '';
});
