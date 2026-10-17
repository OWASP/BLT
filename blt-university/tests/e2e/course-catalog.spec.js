const { test, expect } = require('./fixtures');

test.describe('course catalog', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('courses/', { waitUntil: 'domcontentloaded' });
  });

  test('lists the approved courses and filters them by search', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Choose your security track.' })).toBeVisible();

    const courses = page.locator('.course-card');
    await expect(courses).toHaveCount(5);
    await expect(courses.first().getByRole('link').first()).toHaveAttribute('href', /\/courses\/.+\//);

    await page.getByPlaceholder('Search courses, topics, or instructors...').fill('Cloud Security');
    await expect(page.locator('.course-card:not(.hidden)')).toHaveCount(1);
    await expect(page.locator('.course-card:not(.hidden)').getByRole('heading')).toHaveText('Cloud Security Essentials');
  });
});
