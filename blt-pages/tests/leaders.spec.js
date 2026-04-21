// @ts-check
const { test, expect } = require('@playwright/test');

test('leaders page loads without JavaScript errors', async ({ page }) => {
  const jsErrors = [];
  page.on('pageerror', err => jsErrors.push(err.message));

  await page.goto('/leaders.html');
  await page.waitForLoadState('load');

  expect(
    jsErrors,
    `Leaders page has JavaScript errors:\n${jsErrors.join('\n')}`
  ).toHaveLength(0);
});

test('leaders page has expected title', async ({ page }) => {
  await page.goto('/leaders.html');
  await expect(page).toHaveTitle(/Leaders.*BLT/i);
});

test('leaders page renders tabs', async ({ page }) => {
  await page.goto('/leaders.html');
  await expect(page.locator('[data-tab="elections"]')).toBeVisible();
  await expect(page.locator('[data-tab="projects"]')).toBeVisible();
  await expect(page.locator('[data-tab="winners"]')).toBeVisible();
});

test('leaders page tab switching works', async ({ page }) => {
  await page.goto('/leaders.html');

  // Projects tab should be hidden initially
  await expect(page.locator('[data-panel="projects"]')).toBeHidden();

  // Click Projects tab
  await page.locator('[data-tab="projects"]').click();
  await expect(page.locator('[data-panel="projects"]')).toBeVisible();
  await expect(page.locator('[data-panel="elections"]')).toBeHidden();
});
