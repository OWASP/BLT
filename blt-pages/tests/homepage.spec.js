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

test('pricing section and nav links are hidden when SHOW_PRICING is false', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('load');

  // Pricing section should not be visible (SHOW_PRICING defaults to false for OWASP instance)
  const pricingSection = page.locator('#pricing');
  await expect(pricingSection).toBeHidden();

  // Pricing nav links (desktop and mobile) should not be visible
  const pricingNavLink = page.locator('#pricing-nav-link');
  await expect(pricingNavLink).toBeHidden();

  const pricingNavLinkMobile = page.locator('#pricing-nav-link-mobile');
  await expect(pricingNavLinkMobile).toBeHidden();
});

