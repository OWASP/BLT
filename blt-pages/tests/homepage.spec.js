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

test('dynamic sections are pre-rendered in HTML without waiting for JS', async ({ page }) => {
  // Intercept JS files to ensure content is already in the HTML, not added by JS
  await page.route('**/js/app.js', route => route.abort());

  await page.goto('/', { waitUntil: 'domcontentloaded' });

  // Leaderboard rows should already be present in HTML (pre-rendered by workflow)
  const leaderboardRows = page.locator('#leaderboard-rows[data-pre-rendered="true"]');
  await expect(leaderboardRows).toBeAttached();
  const leaderboardChildren = await page.evaluate(() => document.getElementById('leaderboard-rows')?.childElementCount ?? 0);
  expect(leaderboardChildren, 'leaderboard rows should be pre-rendered').toBeGreaterThan(0);

  // Recent bugs grid should already be present
  const recentBugsGrid = page.locator('#recent-bugs-grid[data-pre-rendered="true"]');
  await expect(recentBugsGrid).toBeAttached();
  const recentBugsChildren = await page.evaluate(() => document.getElementById('recent-bugs-grid')?.childElementCount ?? 0);
  expect(recentBugsChildren, 'recent bugs should be pre-rendered').toBeGreaterThan(0);

  // Stat numbers should not show placeholder '-'
  const statBugs = await page.evaluate(() => document.getElementById('stat-total-bugs')?.textContent?.trim());
  expect(statBugs, 'stat-total-bugs should be pre-rendered (not "-")').not.toBe('-');
  expect(statBugs, 'stat-total-bugs should not be empty').not.toBe('');
});
