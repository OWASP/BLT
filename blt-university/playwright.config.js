const { defineConfig, devices } = require('@playwright/test');

const configuredBaseURL = process.env.PLAYWRIGHT_BASE_URL;
const baseURL = configuredBaseURL || 'http://127.0.0.1:4173';

module.exports = defineConfig({
  expect: {
    timeout: 15_000
  },
  testDir: './tests/e2e',
  timeout: 30_000,
  outputDir: 'test-results',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [['list', { printSteps: true }], ['html', { open: 'never' }]]
    : [['list', { printSteps: true }]],
  use: {
    baseURL,
    headless: true,
    navigationTimeout: 15_000,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['iPhone 13'] }
    }
  ],
  webServer: configuredBaseURL ? undefined : {
    command: 'node tests/e2e/helpers/static-server.js',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000
  }
});
