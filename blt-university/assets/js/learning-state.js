(function () {
    'use strict';

    const LEARNING_PROGRESS_STORAGE_KEY = 'blt-learning-progress';
    const PROGRESS_STORAGE_KEY = 'blt-lab-progress';
    const COURSE_PROGRESS_STORAGE_KEY = 'blt-course-progress';
    const MAX_ACTIVITY_DAYS = 370;
    const PROGRESS_STORAGE_KEYS = [
        LEARNING_PROGRESS_STORAGE_KEY,
        PROGRESS_STORAGE_KEY,
        COURSE_PROGRESS_STORAGE_KEY
    ];
    const milestoneBadges = [
        {
            id: 'first-lab',
            title: 'First Lab',
            description: 'Complete your first BLT University lab.',
            icon: 'fa-flag-checkered',
            isUnlocked: summary => summary.completedLabs >= 1
        },
        {
            id: 'lab-explorer',
            title: 'Lab Explorer',
            description: 'Complete five hands-on security labs.',
            icon: 'fa-compass',
            isUnlocked: summary => summary.completedLabs >= 5
        },
        {
            id: 'lab-specialist',
            title: 'Lab Specialist',
            description: 'Complete ten hands-on security labs.',
            icon: 'fa-flask-vial',
            isUnlocked: summary => summary.completedLabs >= 10
        },
        {
            id: 'first-course',
            title: 'Path Starter',
            description: 'Complete your first BLT University course.',
            icon: 'fa-book-open-reader',
            isUnlocked: summary => summary.completedCourses >= 1
        },
        {
            id: 'course-explorer',
            title: 'Course Explorer',
            description: 'Complete three different learning paths.',
            icon: 'fa-route',
            isUnlocked: summary => summary.completedCourses >= 3
        },
        {
            id: 'first-challenge',
            title: 'Evidence Hunter',
            description: 'Solve your first interactive course challenge.',
            icon: 'fa-magnifying-glass',
            isUnlocked: summary => summary.completedChallenges >= 1
        },
        {
            id: 'web-security-path',
            title: 'Web Security Path',
            description: 'Complete the Introduction to Web Application Security course.',
            icon: 'fa-shield-halved',
            isUnlocked: summary => summary.completedCourseIds.includes('web-security-intro')
        },
        {
            id: 'streak-3',
            title: 'Steady Learner',
            description: 'Build a three-day learning streak.',
            icon: 'fa-fire',
            isUnlocked: summary => summary.longestStreak >= 3
        },
        {
            id: 'streak-7',
            title: 'Security Habit',
            description: 'Keep learning for seven consecutive days.',
            icon: 'fa-bolt',
            isUnlocked: summary => summary.longestStreak >= 7
        }
    ];

    function isPlainObject(value) {
        return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
    }

    function readJsonStorage(key) {
        try {
            const value = JSON.parse(localStorage.getItem(key) || '{}');
            return isPlainObject(value) ? value : {};
        } catch (_error) {
            return {};
        }
    }

    function writeJsonStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (_error) {
            return false;
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function dateKey(value = new Date()) {
        const date = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(date.getTime())) {
            return '';
        }

        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function dayNumber(key) {
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key || '');
        if (!match) {
            return null;
        }

        return Math.floor(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) / 86400000);
    }

    function uniqueSortedDays(activityDays) {
        return [...new Set(Array.isArray(activityDays) ? activityDays : [])]
            .filter(key => dayNumber(key) !== null)
            .sort((left, right) => dayNumber(left) - dayNumber(right));
    }

    function calculateStreaks(activityDays, today = new Date()) {
        const days = uniqueSortedDays(activityDays);
        if (!days.length) {
            return { current: 0, longest: 0 };
        }

        let longest = 1;
        let run = 1;
        for (let index = 1; index < days.length; index += 1) {
            if (dayNumber(days[index]) - dayNumber(days[index - 1]) === 1) {
                run += 1;
                longest = Math.max(longest, run);
            } else {
                run = 1;
            }
        }

        const todayNumber = dayNumber(dateKey(today));
        const latestNumber = dayNumber(days[days.length - 1]);
        if (todayNumber === null || latestNumber === null || todayNumber - latestNumber > 1) {
            return { current: 0, longest };
        }

        let current = 1;
        for (let index = days.length - 1; index > 0; index -= 1) {
            if (dayNumber(days[index]) - dayNumber(days[index - 1]) !== 1) {
                break;
            }
            current += 1;
        }

        return { current, longest };
    }

    function slugKey(value) {
        return String(value || '').replace(/[-_]/g, '').toLowerCase();
    }

    function readCatalog() {
        const element = document.getElementById('adaptive-recommendation-data');
        if (!element) {
            return [];
        }

        try {
            const parsed = JSON.parse(element.textContent || '{}');
            return Array.isArray(parsed.labs) ? parsed.labs.filter(isPlainObject) : [];
        } catch (_error) {
            return [];
        }
    }

    function completedLabCount(labs, progress) {
        return labs.filter(lab => {
            const taskCount = Number(lab.taskCount || 0);
            const labProgress = isPlainObject(progress[lab.id]) ? progress[lab.id] : {};
            const completedTasks = Object.values(labProgress)
                .filter(task => isPlainObject(task) && task.completed === true).length;
            return taskCount > 0 && completedTasks >= taskCount;
        }).length;
    }

    function getStoredLearningProgress() {
        const stored = readJsonStorage(LEARNING_PROGRESS_STORAGE_KEY);
        return {
            activityDays: uniqueSortedDays(stored.activityDays).slice(-MAX_ACTIVITY_DAYS),
            completedTaskEvents: isPlainObject(stored.completedTaskEvents) ? stored.completedTaskEvents : {},
            earnedBadges: isPlainObject(stored.earnedBadges) ? stored.earnedBadges : {}
        };
    }

    function courseMilestones() {
        const progress = readJsonStorage(COURSE_PROGRESS_STORAGE_KEY);
        const completedCourseIds = [];
        let completedChallenges = 0;

        Object.entries(progress).forEach(([courseId, course]) => {
            if (!isPlainObject(course)) {
                return;
            }
            if (typeof course.completedAt === 'string' && course.completedAt) {
                completedCourseIds.push(courseId);
            }
            if (isPlainObject(course.challenges)) {
                completedChallenges += Object.values(course.challenges).filter(Boolean).length;
            }
        });

        return { completedCourseIds, completedChallenges };
    }

    function buildSummary(today = new Date()) {
        const labs = readCatalog();
        const progress = readJsonStorage(PROGRESS_STORAGE_KEY);
        const learningProgress = getStoredLearningProgress();
        const streaks = calculateStreaks(learningProgress.activityDays, today);
        const courses = courseMilestones();

        return {
            activityDays: learningProgress.activityDays,
            currentStreak: streaks.current,
            longestStreak: streaks.longest,
            completedLabs: completedLabCount(labs, progress),
            totalLabs: labs.length,
            completedCourses: courses.completedCourseIds.length,
            completedCourseIds: courses.completedCourseIds,
            completedChallenges: courses.completedChallenges,
            earnedBadges: learningProgress.earnedBadges
        };
    }

    function syncAchievements(today = new Date()) {
        const learningProgress = getStoredLearningProgress();
        const summary = buildSummary(today);
        const candidates = milestoneBadges.filter(badge => badge.isUnlocked(summary));
        const earnedOn = dateKey(today);
        let changed = false;

        candidates.forEach(badge => {
            if (!learningProgress.earnedBadges[badge.id]) {
                learningProgress.earnedBadges[badge.id] = earnedOn;
                changed = true;
            }
        });

        if (changed) {
            writeJsonStorage(LEARNING_PROGRESS_STORAGE_KEY, learningProgress);
        }

        return {
            ...buildSummary(today),
            badges: milestoneBadges.map(badge => ({
                ...badge,
                earnedOn: learningProgress.earnedBadges[badge.id] || null
            }))
        };
    }

    function recordActivity(eventId, completedAt = new Date()) {
        if (!eventId) {
            return syncAchievements(completedAt);
        }

        const learningProgress = getStoredLearningProgress();
        const eventKey = String(eventId).slice(0, 240);
        if (!learningProgress.completedTaskEvents[eventKey]) {
            const completedOn = dateKey(completedAt);
            learningProgress.completedTaskEvents[eventKey] = completedOn;
            learningProgress.activityDays = uniqueSortedDays([
                ...learningProgress.activityDays,
                completedOn
            ]).slice(-MAX_ACTIVITY_DAYS);
            writeJsonStorage(LEARNING_PROGRESS_STORAGE_KEY, learningProgress);
        }

        const summary = syncAchievements(completedAt);
        document.dispatchEvent(new CustomEvent('blt:learning-progress-updated', { detail: summary }));
        return summary;
    }

    function recordTaskCompletion(labId, taskIndex, completedAt = new Date()) {
        if (!labId || !Number.isInteger(Number(taskIndex))) {
            return syncAchievements(completedAt);
        }

        return recordActivity(`lab:${slugKey(labId)}:${Number(taskIndex)}`, completedAt);
    }

    function statMarkup(label, value) {
        return `
            <div class="min-w-0 rounded-2xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50">
                <p class="break-words text-xl font-bold text-gray-900 dark:text-white sm:text-2xl">${escapeHtml(value)}</p>
                <p class="mt-1 break-words text-[10px] font-bold uppercase tracking-wider text-gray-400 sm:tracking-widest">${escapeHtml(label)}</p>
            </div>
        `;
    }

    function renderBadges(container, badges) {
        const visibleBadges = badges.length ? badges : milestoneBadges.map(badge => ({ ...badge, earnedOn: null }));
        container.innerHTML = visibleBadges.map(badge => `
            <article class="min-w-0 rounded-2xl border p-4 ${badge.earnedOn
                ? 'border-red-200 bg-red-50/70 dark:border-red-900/40 dark:bg-red-900/10'
                : 'border-gray-200 bg-gray-50 opacity-65 dark:border-gray-700 dark:bg-gray-800/40'}">
                <div class="flex items-center gap-3">
                    <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${badge.earnedOn
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-300'}">
                        <i class="fa-solid ${badge.earnedOn ? escapeHtml(badge.icon) : 'fa-lock'} text-sm" aria-hidden="true"></i>
                    </span>
                    <div>
                        <h3 class="break-words text-sm font-bold text-gray-900 dark:text-white">${escapeHtml(badge.title)}</h3>
                        <p class="mt-0.5 text-[10px] font-semibold uppercase tracking-wider ${badge.earnedOn ? 'text-red-600' : 'text-gray-400'}">${badge.earnedOn ? `Earned ${escapeHtml(badge.earnedOn)}` : 'Locked'}</p>
                    </div>
                </div>
                <p class="mt-3 break-words text-xs leading-5 text-gray-600 dark:text-gray-400">${escapeHtml(badge.description)}</p>
            </article>
        `).join('');
    }

    function renderLearningProgress(summary = syncAchievements()) {
        document.querySelectorAll('[data-learning-progress]').forEach(container => {
            const stats = container.querySelector('[data-learning-progress-stats]');
            if (stats) {
                stats.innerHTML = [
                    statMarkup('Current streak', `${summary.currentStreak} day${summary.currentStreak === 1 ? '' : 's'}`),
                    statMarkup('Longest streak', `${summary.longestStreak} day${summary.longestStreak === 1 ? '' : 's'}`),
                    statMarkup('Labs completed', `${summary.completedLabs}/${summary.totalLabs}`),
                    statMarkup('Courses completed', String(summary.completedCourses)),
                    statMarkup('Challenges solved', String(summary.completedChallenges)),
                    statMarkup('Badges earned', String(Object.keys(summary.earnedBadges).length))
                ].join('');
            }

            const badgeContainer = container.querySelector('[data-learning-progress-badges]');
            if (badgeContainer) {
                renderBadges(badgeContainer, summary.badges || []);
            }
        });
    }

    window.BltLearningProgress = {
        LEARNING_PROGRESS_STORAGE_KEY,
        buildSummary,
        calculateStreaks,
        courseMilestones,
        dateKey,
        recordActivity,
        recordTaskCompletion,
        renderLearningProgress,
        syncAchievements
    };

    function initialize() {
        renderLearningProgress();
        document.addEventListener('blt:learning-progress-updated', event => renderLearningProgress(event.detail));
        window.addEventListener('storage', event => {
            if (event.key === null || PROGRESS_STORAGE_KEYS.includes(event.key)) {
                renderLearningProgress();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
}());
