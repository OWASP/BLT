/** @jest-environment jsdom */

const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'assets', 'js', 'course-state.js');
const COURSE_PROGRESS_KEY = 'blt-course-progress';
const LAB_PROGRESS_KEY = 'blt-lab-progress';

function renderCourseFixture() {
  document.body.innerHTML = `
    <article data-course-root data-course-id="sample-course">
      <section data-course-lesson data-lesson-id="lesson-one">
        <span data-lesson-status></span>
        <button data-complete-lesson><span>Mark lesson complete</span></button>
        <section data-course-challenge data-challenge-id="decision" data-challenge-type="choice" data-challenge-answer="reject">
          <button data-challenge-option="accept">Accept</button>
          <button data-challenge-option="reject">Reject</button>
          <p data-challenge-feedback class="hidden"></p>
        </section>
      </section>
      <a data-course-lab data-lab-id="sample-lab" data-task-count="2">
        <span data-course-lab-status></span>
      </a>
      <span data-course-progress-percent></span>
      <span data-course-progress-count></span>
      <div data-course-progress-bar></div>
      <div data-course-complete class="hidden"></div>
    </article>
  `;
}

function loadCourseProgress() {
  window.BltLearningProgress = { recordActivity: jest.fn() };
  const runScript = new Function(
    'window',
    'document',
    'localStorage',
    'CustomEvent',
    fs.readFileSync(SCRIPT_PATH, 'utf8')
  );
  runScript(window, document, localStorage, CustomEvent);
  document.dispatchEvent(new Event('DOMContentLoaded'));
  return window.BltCourseProgress;
}

describe('course lesson, challenge, and lab progress', () => {
  beforeEach(() => {
    renderCourseFixture();
    localStorage.setItem(LAB_PROGRESS_KEY, JSON.stringify({
      'sample-lab': {
        0: { completed: true },
        1: { completed: true }
      }
    }));
  });

  afterEach(() => {
    document.body.innerHTML = '';
    localStorage.clear();
    delete window.BltCourseProgress;
    delete window.BltLearningProgress;
  });

  it('completes a course only after its lesson, challenge, and lab are complete', () => {
    loadCourseProgress();

    document.querySelector('[data-challenge-option="reject"]').click();

    const saved = JSON.parse(localStorage.getItem(COURSE_PROGRESS_KEY))['sample-course'];
    expect(saved.lessons['lesson-one']).toBe(true);
    expect(saved.challenges.decision).toBe(true);
    expect(saved.completedAt).toEqual(expect.any(String));
    expect(document.querySelector('[data-course-progress-percent]').textContent).toBe('100%');
    expect(document.querySelector('[data-course-complete]').classList.contains('hidden')).toBe(false);
  });

  it('does not award challenge progress for an incorrect decision', () => {
    loadCourseProgress();

    document.querySelector('[data-challenge-option="accept"]').click();

    const state = window.BltCourseProgress.courseState('sample-course');
    expect(state.challenges.decision).toBeUndefined();
    expect(document.querySelector('[data-challenge-feedback]').textContent).toContain('strongest signal');
  });

  it('marks the containing lesson complete when its challenge is solved', () => {
    loadCourseProgress();

    document.querySelector('[data-challenge-option="reject"]').click();

    const state = window.BltCourseProgress.courseState('sample-course');
    expect(state.lessons['lesson-one']).toBe(true);
    expect(document.querySelector('[data-lesson-status]').textContent).toBe('Completed');
  });

  it('merges progress written after the page loaded instead of replacing it', () => {
    loadCourseProgress();
    localStorage.setItem(COURSE_PROGRESS_KEY, JSON.stringify({
      'sample-course': {
        lessons: { 'remote-lesson': true },
        challenges: { 'remote-challenge': true },
        completedAt: null
      }
    }));

    document.querySelector('[data-challenge-option="reject"]').click();

    const saved = window.BltCourseProgress.courseState('sample-course');
    expect(saved.lessons).toMatchObject({
      'remote-lesson': true,
      'lesson-one': true
    });
    expect(saved.challenges).toMatchObject({
      'remote-challenge': true,
      decision: true
    });
  });

  it('clears an old completion date when the current course has unfinished steps', () => {
    localStorage.setItem(COURSE_PROGRESS_KEY, JSON.stringify({
      'sample-course': {
        lessons: {},
        challenges: {},
        completedAt: '2026-08-19T10:00:00.000Z'
      }
    }));

    loadCourseProgress();

    expect(window.BltCourseProgress.courseState('sample-course').completedAt).toBeNull();
  });

  it('completes an ordering activity only when every step is in the right order', () => {
    document.body.innerHTML = `
      <article data-course-root data-course-id="sequence-course">
        <section data-course-lesson data-lesson-id="trust-boundary">
          <span data-lesson-status></span>
          <section data-course-challenge data-challenge-id="verification-order" data-challenge-type="sequence" data-challenge-answer="verify|validate|authorize">
            <button data-sequence-option="authorize"><span data-sequence-position></span>Authorize</button>
            <button data-sequence-option="validate"><span data-sequence-position></span>Validate</button>
            <button data-sequence-option="verify"><span data-sequence-position></span>Verify</button>
            <button data-sequence-reset>Reset order</button>
            <p data-sequence-summary></p>
            <p data-challenge-feedback class="hidden"></p>
          </section>
        </section>
        <span data-course-progress-percent></span>
        <span data-course-progress-count></span>
        <div data-course-progress-bar></div>
        <div data-course-complete class="hidden"></div>
      </article>
    `;
    loadCourseProgress();

    document.querySelector('[data-sequence-option="authorize"]').click();
    document.querySelector('[data-sequence-option="verify"]').click();
    document.querySelector('[data-sequence-option="validate"]').click();
    expect(document.querySelector('[data-challenge-feedback]').textContent).toContain('uses data before');

    document.querySelector('[data-sequence-reset]').click();
    document.querySelector('[data-sequence-option="verify"]').click();
    document.querySelector('[data-sequence-option="validate"]').click();
    document.querySelector('[data-sequence-option="authorize"]').click();

    const state = window.BltCourseProgress.courseState('sequence-course');
    expect(state.challenges['verification-order']).toBe(true);
    expect(state.lessons['trust-boundary']).toBe(true);
    expect(document.querySelector('[data-course-progress-percent]').textContent).toBe('100%');
  });

  it('normalizes typed evidence answers before completing the lesson', () => {
    document.body.innerHTML = `
      <article data-course-root data-course-id="evidence-course">
        <section data-course-lesson data-lesson-id="identity-path">
          <span data-lesson-status></span>
          <section data-course-challenge data-challenge-id="runtime-role" data-challenge-type="artifact" data-challenge-answer="finance-read-role">
            <input data-challenge-input>
            <button data-challenge-submit>Check answer</button>
            <p data-challenge-feedback class="hidden"></p>
          </section>
        </section>
        <span data-course-progress-percent></span>
        <span data-course-progress-count></span>
        <div data-course-progress-bar></div>
        <div data-course-complete class="hidden"></div>
      </article>
    `;
    loadCourseProgress();

    const input = document.querySelector('[data-challenge-input]');
    input.value = 'wrong-role';
    document.querySelector('[data-challenge-submit]').click();
    expect(window.BltCourseProgress.courseState('evidence-course').lessons['identity-path']).toBeUndefined();

    input.value = '  FINANCE-READ-ROLE  ';
    document.querySelector('[data-challenge-submit]').click();
    expect(window.BltCourseProgress.courseState('evidence-course').lessons['identity-path']).toBe(true);
    expect(document.querySelector('[data-course-progress-percent]').textContent).toBe('100%');
  });

  it('recovers from malformed course storage without breaking the page', () => {
    localStorage.setItem(COURSE_PROGRESS_KEY, '{broken');

    expect(() => loadCourseProgress()).not.toThrow();
    expect(document.querySelector('[data-course-progress-percent]').textContent).toBe('50%');
  });
});
