const { expect } = require('@playwright/test');

class CoursePage {
  constructor(page) {
    this.page = page;
    this.lessons = page.locator('[data-course-lesson]');
    this.progressCount = page.locator('[data-course-progress-count]');
    this.progressPercent = page.locator('[data-course-progress-percent]');
    this.completionNotice = page.locator('[data-course-complete]');
    this.nextCourse = page.locator('[data-next-course]');
  }

  async open(courseSlug) {
    await this.page.goto(`courses/${courseSlug}/`, { waitUntil: 'domcontentloaded' });
  }

  challenge(challengeId) {
    return this.page.locator(`[data-challenge-id="${challengeId}"]`);
  }

  async submitAnswer(challengeId, answer) {
    const challenge = this.challenge(challengeId);
    await challenge.locator('[data-challenge-input]').fill(answer);
    await challenge.getByRole('button', { name: 'Check answer' }).click();
  }

  async chooseOption(challengeId, label) {
    await this.challenge(challengeId).getByRole('button', { name: label, exact: true }).click();
  }

  async chooseSequence(challengeId, labels) {
    const challenge = this.challenge(challengeId);
    for (const label of labels) {
      await challenge.getByRole('button', { name: label, exact: true }).click();
    }
  }

  async expectCourseFrame(lessonCount) {
    await expect(this.lessons).toHaveCount(lessonCount);
    await expect(this.page.getByRole('heading', { name: 'Course lessons' })).toBeVisible();
    await expect(this.page.getByRole('heading', { name: 'By the end of this course, you can' })).toBeVisible();
    await expect(this.progressCount).toHaveText(`0 of ${lessonCount} steps completed`);
  }

  async expectComplete(lessonCount) {
    await expect(this.lessons.locator('[data-lesson-status]')).toHaveText(
      Array.from({ length: lessonCount }, () => 'Completed')
    );
    await expect(this.progressCount).toHaveText(`${lessonCount} of ${lessonCount} steps completed`);
    await expect(this.progressPercent).toHaveText('100%');
    await expect(this.completionNotice).toBeVisible();
  }
}

module.exports = { CoursePage };
