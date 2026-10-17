const { test: base, expect } = require('@playwright/test');
const { CoursePage } = require('./pages/course-page');

const test = base.extend({
  coursePage: async ({ page }, use) => {
    await use(new CoursePage(page));
  },
  page: async ({ page }, use) => {
    const runtimeErrors = [];

    page.on('console', (message) => {
      if (message.type() === 'error') {
        runtimeErrors.push(`console: ${message.text()}`);
      }
    });
    page.on('pageerror', (error) => {
      runtimeErrors.push(`page: ${error.message}`);
    });
    page.on('requestfailed', (request) => {
      runtimeErrors.push(`request: ${request.url()} (${request.failure()?.errorText || 'failed'})`);
    });

    await use(page);

    expect(runtimeErrors, 'The page emitted unexpected runtime errors').toEqual([]);
  }
});

module.exports = { test, expect };
