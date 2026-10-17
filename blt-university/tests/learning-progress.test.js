/** @jest-environment jsdom */

const fs = require('node:fs');
const path = require('node:path');

const SCRIPT_PATH = path.join(__dirname, '..', 'assets', 'js', 'learning-state.js');
const LEARNING_PROGRESS_KEY = 'blt-learning-progress';
const PROGRESS_KEY = 'blt-lab-progress';
const COURSE_PROGRESS_KEY = 'blt-course-progress';

function loadLearningProgress({ catalog = { labs: [] }, progress = {}, learningProgress } = {}) {
  document.body.innerHTML = `
    <script id="adaptive-recommendation-data" type="application/json"></script>
    <section data-learning-progress>
      <div data-learning-progress-stats></div>
      <div data-learning-progress-badges></div>
    </section>
  `;
  document.getElementById('adaptive-recommendation-data').textContent = JSON.stringify(catalog);
  localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
  if (learningProgress !== undefined) {
    localStorage.setItem(LEARNING_PROGRESS_KEY, learningProgress);
  }

  const runScript = new Function('window', 'document', 'localStorage', 'CustomEvent', fs.readFileSync(SCRIPT_PATH, 'utf8'));
  runScript(window, document, localStorage, CustomEvent);
  return window.BltLearningProgress;
}

describe('learning progress and achievements', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    localStorage.clear();
    delete window.BltLearningProgress;
  });

  it('calculates current and longest streaks without daylight-saving drift', () => {
    const learningProgress = loadLearningProgress();

    expect(learningProgress.calculateStreaks(
      ['2026-08-01', '2026-08-02', '2026-08-04', '2026-08-05', '2026-08-06'],
      new Date(2026, 7, 6, 12)
    )).toEqual({ current: 3, longest: 3 });

    expect(learningProgress.calculateStreaks(
      ['2026-08-01', '2026-08-02'],
      new Date(2026, 7, 6, 12)
    )).toEqual({ current: 0, longest: 2 });
  });

  it('records each completed task once and builds a streak across distinct task completions', () => {
    const learningProgress = loadLearningProgress();

    learningProgress.recordTaskCompletion('sql_injection', 0, new Date(2026, 7, 1, 10));
    learningProgress.recordTaskCompletion('sql-injection', 0, new Date(2026, 7, 2, 10));
    learningProgress.recordTaskCompletion('sql_injection', 1, new Date(2026, 7, 2, 10));
    const summary = learningProgress.recordTaskCompletion('sql_injection', 2, new Date(2026, 7, 3, 10));
    const stored = JSON.parse(localStorage.getItem(LEARNING_PROGRESS_KEY));

    expect(stored.activityDays).toEqual(['2026-08-01', '2026-08-02', '2026-08-03']);
    expect(Object.keys(stored.completedTaskEvents)).toHaveLength(3);
    expect(summary.currentStreak).toBe(3);
    expect(summary.longestStreak).toBe(3);
    expect(summary.earnedBadges['streak-3']).toBe('2026-08-03');
  });

  it('awards the first-lab badge from actual persisted progress', () => {
    const catalog = {
      labs: [{ id: 'idor-lab', title: 'IDOR', taskCount: 2 }]
    };
    const progress = {
      'idor-lab': {
        0: { completed: true },
        1: { completed: true }
      }
    };
    const learningProgress = loadLearningProgress({ catalog, progress });

    const summary = learningProgress.syncAchievements(new Date(2026, 7, 18, 12));

    expect(summary.completedLabs).toBe(1);
    expect(summary.badges.filter(badge => badge.earnedOn).map(badge => badge.id))
      .toEqual(['first-lab']);
  });

  it('awards course and challenge badges from completed course state', () => {
    const learningProgress = loadLearningProgress();
    localStorage.setItem(COURSE_PROGRESS_KEY, JSON.stringify({
      'web-security-intro': {
        lessons: { boundaries: true },
        challenges: { 'request-review': true },
        completedAt: '2026-08-19T10:00:00.000Z'
      }
    }));

    const summary = learningProgress.syncAchievements(new Date(2026, 7, 19, 12));
    const earnedIds = summary.badges.filter(badge => badge.earnedOn).map(badge => badge.id);

    expect(summary.completedCourses).toBe(1);
    expect(summary.completedChallenges).toBe(1);
    expect(earnedIds).toEqual(expect.arrayContaining([
      'first-course',
      'first-challenge',
      'web-security-path'
    ]));
  });

  it('recovers from corrupt learning-progress storage and renders achievement text safely', () => {
    const learningProgress = loadLearningProgress({ learningProgress: '{ broken json' });

    expect(() => learningProgress.renderLearningProgress(learningProgress.syncAchievements())).not.toThrow();
    expect(document.querySelector('[data-learning-progress-stats]').textContent).toContain('Current streak');
    expect(document.querySelector('[data-learning-progress-badges] script')).toBeNull();
  });

  it('refreshes when another tab changes progress storage', () => {
    loadLearningProgress({
      catalog: { labs: [{ id: 'idor-lab', title: 'IDOR', taskCount: 1 }] }
    });

    expect(document.querySelector('[data-learning-progress-stats]').textContent).toContain('0/1');

    localStorage.setItem(PROGRESS_KEY, JSON.stringify({
      'idor-lab': { 0: { completed: true } }
    }));
    window.dispatchEvent(new StorageEvent('storage', { key: PROGRESS_KEY }));

    expect(document.querySelector('[data-learning-progress-stats]').textContent).toContain('1/1');

    localStorage.clear();
    window.dispatchEvent(new StorageEvent('storage', { key: null }));
    expect(document.querySelector('[data-learning-progress-stats]').textContent).toContain('0/1');
  });
});
