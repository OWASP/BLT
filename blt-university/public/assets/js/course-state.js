(function () {
    'use strict';

    const COURSE_PROGRESS_STORAGE_KEY = 'blt-course-progress';
    const LAB_PROGRESS_STORAGE_KEY = 'blt-lab-progress';

    function isPlainObject(value) {
        return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
    }

    function readStorage(key) {
        try {
            const value = JSON.parse(localStorage.getItem(key) || '{}');
            return isPlainObject(value) ? value : {};
        } catch (_error) {
            return {};
        }
    }

    function writeStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (_error) {
            return false;
        }
    }

    function normalizedAnswer(value) {
        return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
    }

    function courseState(courseId) {
        const progress = readStorage(COURSE_PROGRESS_STORAGE_KEY);
        const saved = isPlainObject(progress[courseId]) ? progress[courseId] : {};
        return {
            lessons: isPlainObject(saved.lessons) ? saved.lessons : {},
            challenges: isPlainObject(saved.challenges) ? saved.challenges : {},
            completedAt: typeof saved.completedAt === 'string' ? saved.completedAt : null
        };
    }

    function saveCourseState(courseId, state, options = {}) {
        const progress = readStorage(COURSE_PROGRESS_STORAGE_KEY);
        const saved = isPlainObject(progress[courseId]) ? progress[courseId] : {};
        const merged = {
            lessons: {
                ...(isPlainObject(saved.lessons) ? saved.lessons : {}),
                ...(isPlainObject(state.lessons) ? state.lessons : {})
            },
            challenges: {
                ...(isPlainObject(saved.challenges) ? saved.challenges : {}),
                ...(isPlainObject(state.challenges) ? state.challenges : {})
            },
            completedAt: typeof saved.completedAt === 'string' ? saved.completedAt : null
        };

        if (options.completion === true) {
            merged.completedAt = typeof state.completedAt === 'string'
                ? state.completedAt
                : new Date().toISOString();
        } else if (options.completion === false) {
            merged.completedAt = null;
        }

        progress[courseId] = merged;
        writeStorage(COURSE_PROGRESS_STORAGE_KEY, progress);
        return merged;
    }

    function labIsComplete(labElement, labProgress) {
        const labId = labElement.dataset.labId;
        const taskCount = Number(labElement.dataset.taskCount || 0);
        const storedTasks = isPlainObject(labProgress[labId]) ? labProgress[labId] : {};
        const completedTasks = Object.values(storedTasks)
            .filter(task => isPlainObject(task) && task.completed === true).length;
        return taskCount > 0 && completedTasks >= taskCount;
    }

    function setFeedback(element, message, success) {
        if (!element) {
            return;
        }
        element.textContent = message;
        element.className = `mt-3 text-sm font-semibold ${success
            ? 'text-green-600 dark:text-green-300'
            : 'text-red-600 dark:text-red-300'}`;
    }

    function recordActivity(eventId) {
        window.BltLearningProgress?.recordActivity(eventId);
    }

    function initializeCourse(root) {
        const courseId = root.dataset.courseId;
        if (!courseId) {
            return null;
        }

        const lessons = Array.from(root.querySelectorAll('[data-course-lesson]'));
        const challenges = Array.from(root.querySelectorAll('[data-course-challenge]'));
        const labs = Array.from(root.querySelectorAll('[data-course-lab]'));
        let state = courseState(courseId);

        function completeChallenge(challenge, feedback, message) {
            const challengeId = challenge.dataset.challengeId;
            const lesson = challenge.closest('[data-course-lesson]');
            const lessonId = lesson?.dataset.lessonId;
            if (!state.challenges[challengeId]) {
                state.challenges[challengeId] = true;
                if (lessonId) {
                    state.lessons[lessonId] = true;
                }
                state = saveCourseState(courseId, state);
                recordActivity(`challenge:${courseId}:${challengeId}`);
            }
            challenge.dataset.completed = 'true';
            setFeedback(feedback, message || challenge.dataset.challengeSuccess || 'Challenge complete. This lesson is now complete.', true);
            updateProgress();
        }

        challenges.forEach(challenge => {
            const challengeId = challenge.dataset.challengeId;
            const feedback = challenge.querySelector('[data-challenge-feedback]');
            if (state.challenges[challengeId]) {
                challenge.dataset.completed = 'true';
                setFeedback(feedback, 'Challenge completed.', true);
            }

            challenge.querySelector('[data-challenge-reveal]')?.addEventListener('click', () => {
                console.info(`[BLT University course clue] ${challenge.dataset.challengeClue || ''}`);
                setFeedback(feedback, 'Clue sent. Open DevTools and check the browser console.', true);
            });

            challenge.querySelector('[data-challenge-submit]')?.addEventListener('click', () => {
                const input = challenge.querySelector('[data-challenge-input]');
                const correct = normalizedAnswer(input?.value) === normalizedAnswer(challenge.dataset.challengeAnswer);
                if (correct) {
                    completeChallenge(challenge, feedback);
                } else {
                    setFeedback(feedback, 'Not quite. Look at the evidence again and enter the exact value.', false);
                }
            });

            challenge.querySelectorAll('[data-challenge-option]').forEach(option => {
                option.addEventListener('click', () => {
                    const correct = normalizedAnswer(option.dataset.challengeOption)
                        === normalizedAnswer(challenge.dataset.challengeAnswer);
                    challenge.querySelectorAll('[data-challenge-option]').forEach(candidate => {
                        candidate.setAttribute('aria-pressed', String(candidate === option));
                        candidate.classList.toggle('border-bltRed', candidate === option);
                        candidate.classList.toggle('bg-red-50', candidate === option);
                    });
                    if (correct) {
                        completeChallenge(challenge, feedback);
                    } else {
                        setFeedback(feedback, 'That action misses the strongest signal. Review the evidence before choosing again.', false);
                    }
                });
            });

            const sequenceOptions = Array.from(challenge.querySelectorAll('[data-sequence-option]'));
            const sequenceReset = challenge.querySelector('[data-sequence-reset]');
            const sequenceSummary = challenge.querySelector('[data-sequence-summary]');
            let sequence = [];

            function renderSequence() {
                sequenceOptions.forEach((option, originalIndex) => {
                    const position = sequence.indexOf(option.dataset.sequenceOption);
                    const positionLabel = option.querySelector('[data-sequence-position]');
                    if (positionLabel) {
                        positionLabel.textContent = position >= 0 ? `${position + 1}.` : '';
                    }
                    option.disabled = position >= 0;
                    option.style.order = position >= 0 ? position : sequenceOptions.length + originalIndex;
                    option.classList.toggle('border-bltRed', position >= 0);
                    option.classList.toggle('bg-red-50', position >= 0);
                });
                if (sequenceSummary) {
                    sequenceSummary.textContent = sequence.length
                        ? `${sequence.length} of ${sequenceOptions.length} steps selected.`
                        : 'Select the steps in the order they should happen.';
                }
            }

            sequenceOptions.forEach(option => {
                option.addEventListener('click', () => {
                    sequence.push(option.dataset.sequenceOption);
                    renderSequence();
                    if (sequence.length === sequenceOptions.length) {
                        const correct = normalizedAnswer(sequence.join('|'))
                            === normalizedAnswer(challenge.dataset.challengeAnswer);
                        if (correct) {
                            completeChallenge(challenge, feedback);
                        } else {
                            setFeedback(feedback, 'That order uses data before every trust check is complete. Reset it and trace the boundary again.', false);
                        }
                    }
                });
            });

            sequenceReset?.addEventListener('click', () => {
                sequence = [];
                renderSequence();
                feedback?.classList.add('hidden');
            });
            renderSequence();
        });

        lessons.forEach(lesson => {
            const lessonId = lesson.dataset.lessonId;
            const button = lesson.querySelector('[data-complete-lesson]');
            button?.addEventListener('click', () => {
                if (!state.lessons[lessonId]) {
                    state.lessons[lessonId] = true;
                    state = saveCourseState(courseId, state);
                    recordActivity(`lesson:${courseId}:${lessonId}`);
                }
                updateProgress();
            });
        });

        function updateProgress() {
            state = courseState(courseId);
            const labProgress = readStorage(LAB_PROGRESS_STORAGE_KEY);
            const completedLabs = labs.filter(lab => labIsComplete(lab, labProgress));
            const completedLessons = lessons.filter(lesson => state.lessons[lesson.dataset.lessonId]);
            const completedCount = completedLessons.length + completedLabs.length;
            const totalCount = lessons.length + labs.length;
            const percent = totalCount ? Math.round((completedCount / totalCount) * 100) : 0;

            lessons.forEach(lesson => {
                const complete = Boolean(state.lessons[lesson.dataset.lessonId]);
                const status = lesson.querySelector('[data-lesson-status]');
                const button = lesson.querySelector('[data-complete-lesson]');
                if (status) {
                    status.textContent = complete ? 'Completed' : 'Not started';
                    status.className = `rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider ${complete
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}`;
                }
                if (button) {
                    button.disabled = complete;
                    button.classList.toggle('opacity-60', complete);
                    const label = button.querySelector('span');
                    if (label) {
                        label.textContent = complete ? 'Lesson completed' : 'Mark lesson complete';
                    }
                }
            });

            labs.forEach(lab => {
                const complete = completedLabs.includes(lab);
                const status = lab.querySelector('[data-course-lab-status]');
                if (status) {
                    status.textContent = complete ? 'Completed' : 'Not completed';
                    status.className = complete ? 'font-semibold text-green-600 dark:text-green-300' : '';
                }
            });

            const progressBar = root.querySelector('[data-course-progress-bar]');
            const percentLabel = root.querySelector('[data-course-progress-percent]');
            const countLabel = root.querySelector('[data-course-progress-count]');
            if (progressBar) {
                progressBar.style.width = `${percent}%`;
            }
            if (percentLabel) {
                percentLabel.textContent = `${percent}%`;
            }
            if (countLabel) {
                countLabel.textContent = `${completedCount} of ${totalCount} steps completed`;
            }

            const completed = totalCount > 0 && completedCount === totalCount;
            root.querySelector('[data-course-complete]')?.classList.toggle('hidden', !completed);
            if (completed && !state.completedAt) {
                state.completedAt = new Date().toISOString();
                state = saveCourseState(courseId, state, { completion: true });
                recordActivity(`course:${courseId}`);
            } else if (!completed && state.completedAt) {
                state.completedAt = null;
                state = saveCourseState(courseId, state, { completion: false });
            }

            const detail = { courseId, completed, completedCount, totalCount, percent };
            document.dispatchEvent(new CustomEvent('blt:course-progress-updated', { detail }));
            return detail;
        }

        updateProgress();
        window.addEventListener('pageshow', updateProgress);
        window.addEventListener('storage', event => {
            if (event.key === COURSE_PROGRESS_STORAGE_KEY || event.key === LAB_PROGRESS_STORAGE_KEY) {
                updateProgress();
            }
        });
        return { updateProgress };
    }

    window.BltCourseProgress = {
        COURSE_PROGRESS_STORAGE_KEY,
        LAB_PROGRESS_STORAGE_KEY,
        courseState,
        initializeCourse,
        labIsComplete,
        normalizedAnswer
    };

    function initialize() {
        document.querySelectorAll('[data-course-root]').forEach(initializeCourse);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
}());
