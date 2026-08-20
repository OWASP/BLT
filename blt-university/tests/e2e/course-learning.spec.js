const { test, expect } = require('./fixtures');

test.describe('advanced course learning path', () => {
  test('completes five cloud activities, restores progress, and opens the next course', async ({ page, coursePage }) => {
    await coursePage.open('cloud-security-essentials');
    await coursePage.expectCourseFrame(5);

    await coursePage.submitAnswer('trace-runtime-role', 'finance-read-role');

    const inspection = coursePage.challenge('inspect-assumed-role');
    const evidence = await inspection.locator('[data-course-artifact]').getAttribute('data-evidence');
    await inspection.locator('[data-challenge-input]').fill(evidence);
    await inspection.getByRole('button', { name: 'Check answer' }).click();

    await coursePage.chooseSequence('containment-order', [
      'Block the exposed access path.',
      'Preserve logs and configuration history.',
      'Rotate the affected credential.',
      'Trace access and data movement.'
    ]);
    await coursePage.submitAnswer('stale-credential', 'key-201/unknown-workload');
    await coursePage.chooseOption(
      'preventive-guardrail',
      'Apply an organization-level policy that denies public bucket access.'
    );

    await coursePage.expectComplete(5);

    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('blt-course-progress')));
    expect(stored['cloud-security-essentials'].completedAt).toEqual(expect.any(String));
    expect(Object.keys(stored['cloud-security-essentials'].challenges)).toHaveLength(5);

    await page.reload();
    await expect(coursePage.progressCount).toHaveText('5 of 5 steps completed');

    await expect(coursePage.nextCourse.getByRole('heading')).toHaveText('Up next: Cryptography for Developers');
    await coursePage.nextCourse.getByRole('link', { name: 'Continue course' }).click();
    await expect(page).toHaveURL(/\/courses\/crypto-for-devs\/$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Cryptography for Developers');
  });
});
