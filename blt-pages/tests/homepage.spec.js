// @ts-check
const { test, expect } = require('@playwright/test');

test('homepage loads without JavaScript errors', async ({ page }) => {
  const jsErrors = [];

  // Capture uncaught JavaScript exceptions (excludes failed network requests)
  page.on('pageerror', (err) => {
    jsErrors.push(err.message);
  });

  await page.goto('/');

  // Wait for the page to load, then wait until the leaderboard-rows tbody
  // has been populated — this indicates async initialization (JSON fetch +
  // render, or the API-fallback + error-row path) has fully settled.
  await page.waitForLoadState('load');
  await page.waitForFunction(
    () => document.getElementById('leaderboard-rows')?.childElementCount > 0,
    { timeout: 15000 }
  );

  expect(
    jsErrors,
    `Homepage has JavaScript errors:\n${jsErrors.join('\n')}`
  ).toHaveLength(0);
});

test('homepage has expected title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/BLT/i);
});

test('homepage renders the main heading', async ({ page }) => {
  await page.goto('/');
  // The H1 hero heading should be visible
  const h1 = page.locator('h1');
  await expect(h1).toBeVisible();
});
