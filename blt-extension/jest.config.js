module.exports = {
  testEnvironment: 'jsdom',
  testMatch: ['**/tests/**/*.test.js'],
  collectCoverageFrom: [
    'popup.js',
    'background.js',
    'jobtracking.js',
    'linkedin-monitor.js',
    'wellfound-monitor.js',
    'trademark-scanner.js',
    'github-pr-button.js'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  moduleFileExtensions: ['js', 'json'],
  verbose: true
};
