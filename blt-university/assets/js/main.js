// BLT University JavaScript
// Load saved theme
if (localStorage.getItem("theme") === "dark") {
    document.documentElement.classList.add("dark");
}

document.addEventListener('DOMContentLoaded', function() {
    
    // DARK MODE TOGGLE
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
        toggle.addEventListener("click", () => {

            document.documentElement.classList.toggle("dark");

            if (document.documentElement.classList.contains("dark")) {
                localStorage.setItem("theme", "dark");

            } else {
                localStorage.setItem("theme", "light");
            }

        });
    }

    // Course Filtering
    const categoryFilter = document.getElementById('category-filter');
    const levelFilter = document.getElementById('level-filter');
    const searchFilter = document.getElementById('search-filter');
    const coursesGrid = document.getElementById('courses-grid');
    const noResults = document.getElementById('no-results');

    if (categoryFilter && levelFilter && searchFilter && coursesGrid) {
        function filterCourses() {
            const categoryValue = (categoryFilter.value || '').toLowerCase();
            const levelValue = (levelFilter.value || '').toLowerCase();
            const searchValue = (searchFilter.value || '').toLowerCase().trim();

            const courses = coursesGrid.getElementsByClassName('course-card');
            let visibleCount = 0;

            Array.from(courses).forEach(course => {
                const courseCategory = course.getAttribute('data-category') || '';
                const courseLevel = course.getAttribute('data-level') || '';
                const courseSearch = course.getAttribute('data-search') || '';

                const categoryMatch = !categoryValue || courseCategory === categoryValue;
                const levelMatch = !levelValue || courseLevel === levelValue;
                const searchMatch = !searchValue || courseSearch.includes(searchValue);

                if (categoryMatch && levelMatch && searchMatch) {
                    course.classList.remove('hidden');
                    visibleCount++;
                } else {
                    course.classList.add('hidden');
                }
            });

            if (noResults) {
                if (visibleCount === 0) {
                    noResults.classList.remove('hidden');
                    coursesGrid.classList.add('hidden');
                } else {
                    noResults.classList.add('hidden');
                    coursesGrid.classList.remove('hidden');
                }
            }
        }

        categoryFilter.addEventListener('change', filterCourses);
        levelFilter.addEventListener('change', filterCourses);
        searchFilter.addEventListener('input', filterCourses);

        // Initial filter
        filterCourses();
    }

    // Lab task navigation and MCQ feedback
    document.querySelectorAll('[data-lab-root]').forEach(labRoot => {
        const tasks = Array.from(labRoot.querySelectorAll('[data-lab-task]'));
        const jumps = Array.from(labRoot.querySelectorAll('[data-lab-jump]'));
        const prevButton = labRoot.querySelector('[data-lab-prev]');
        const nextButton = labRoot.querySelector('[data-lab-next]');
        const progressBar = labRoot.querySelector('[data-lab-progress]');
        const percentLabel = labRoot.querySelector('[data-lab-percent]');
        let currentIndex = 0;
        let highestUnlocked = 0;
        const completedTasks = new Set();

        if (!tasks.length) {
            return;
        }

        function taskRequiresCorrectAnswer(index) {
            return Boolean(tasks[index]?.querySelector('[data-mcq]'));
        }

        function isTaskComplete(index) {
            return completedTasks.has(index);
        }

        function completeTask(index) {
            completedTasks.add(index);
            highestUnlocked = Math.max(highestUnlocked, Math.min(index + 1, tasks.length - 1));
        }

        function lockAfter(index) {
            highestUnlocked = Math.min(highestUnlocked, index);
            completedTasks.forEach(taskIndex => {
                if (taskIndex >= index) {
                    completedTasks.delete(taskIndex);
                }
            });
        }

        function updateProgress() {
            const progress = Math.round((completedTasks.size / tasks.length) * 100);
            if (progressBar) {
                progressBar.style.width = progress + '%';
            }
            if (percentLabel) {
                percentLabel.textContent = progress + '%';
            }
        }

        function showTask(index) {
            currentIndex = Math.max(0, Math.min(index, tasks.length - 1));

            tasks.forEach((task, taskIndex) => {
                task.classList.toggle('hidden', taskIndex !== currentIndex);
            });

            jumps.forEach((jump, jumpIndex) => {
                const isCurrent = jumpIndex === currentIndex;
                const isUnlocked = jumpIndex <= highestUnlocked;
                const badge = jump.querySelector('[data-step-badge]');
                const state = jump.querySelector('[data-step-state]');

                jump.disabled = !isUnlocked;
                jump.classList.toggle('opacity-50', !isUnlocked);
                jump.classList.toggle('cursor-not-allowed', !isUnlocked);

                if (badge) {
                    badge.className = 'w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 ' +
                        (isCurrent
                            ? 'bg-bltRed text-white'
                            : isUnlocked
                                ? 'bg-red-50 dark:bg-red-900/30 text-bltRed'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400');
                }

                if (state) {
                    state.textContent = isCurrent ? 'Current' : isTaskComplete(jumpIndex) ? 'Complete' : isUnlocked ? 'Available' : 'Locked';
                    state.className = 'block text-xs ' + (isCurrent || isTaskComplete(jumpIndex) ? 'text-bltRed' : 'text-gray-400');
                }
            });

            updateProgress();

            if (prevButton) {
                prevButton.disabled = currentIndex === 0;
            }
            if (nextButton) {
                const needsAnswer = taskRequiresCorrectAnswer(currentIndex) && !isTaskComplete(currentIndex);
                nextButton.disabled = needsAnswer || (currentIndex === tasks.length - 1 && isTaskComplete(currentIndex));
                nextButton.title = needsAnswer ? 'Answer the knowledge check correctly to continue.' : '';
                nextButton.innerHTML = currentIndex === tasks.length - 1
                    ? 'Complete <i class="ph-bold ph-check"></i>'
                    : 'Next <i class="ph-bold ph-arrow-right"></i>';
            }
        }

        prevButton?.addEventListener('click', () => showTask(currentIndex - 1));
        nextButton?.addEventListener('click', () => {
            if (taskRequiresCorrectAnswer(currentIndex) && !isTaskComplete(currentIndex)) {
                return;
            }

            if (!taskRequiresCorrectAnswer(currentIndex)) {
                completeTask(currentIndex);
            }

            if (currentIndex < tasks.length - 1) {
                showTask(currentIndex + 1);
            } else {
                showTask(currentIndex);
            }
        });

        jumps.forEach(jump => {
            jump.addEventListener('click', () => {
                const requestedIndex = Number(jump.getAttribute('data-task-index'));
                if (requestedIndex <= highestUnlocked) {
                    showTask(requestedIndex);
                }
            });
        });

        labRoot.querySelectorAll('[data-mcq]').forEach(mcq => {
            const feedback = mcq.querySelector('[data-mcq-feedback]');
            const options = Array.from(mcq.querySelectorAll('[data-mcq-option]'));

            options.forEach(option => {
                option.addEventListener('click', () => {
                    const correctAnswer = option.getAttribute('data-correct-answer');
                    const selectedAnswer = option.getAttribute('data-option-letter');
                    const isCorrect = selectedAnswer === correctAnswer;

                    options.forEach(item => {
                        const itemAnswer = item.getAttribute('data-option-letter');
                        const marker = item.querySelector('[data-option-marker]');

                        item.classList.remove('border-bltRed', 'bg-red-50', 'dark:bg-red-900/10', 'border-green-500', 'bg-green-50', 'dark:bg-green-900/10');

                        if (itemAnswer === correctAnswer) {
                            item.classList.add('border-green-500', 'bg-green-50', 'dark:bg-green-900/10');
                            if (marker) {
                                marker.textContent = '✓';
                                marker.classList.add('text-green-600', 'font-bold');
                            }
                        } else if (item === option && !isCorrect) {
                            item.classList.add('border-bltRed', 'bg-red-50', 'dark:bg-red-900/10');
                            if (marker) {
                                marker.textContent = '×';
                                marker.classList.add('text-bltRed', 'font-bold');
                            }
                        } else if (marker) {
                            marker.textContent = '';
                            marker.classList.remove('text-green-600', 'text-bltRed', 'font-bold');
                        }
                    });

                    if (isCorrect) {
                        completeTask(currentIndex);
                    } else {
                        lockAfter(currentIndex);
                    }

                    if (feedback) {
                        feedback.classList.remove('hidden', 'text-green-600', 'text-bltRed');
                        feedback.classList.add(isCorrect ? 'text-green-600' : 'text-bltRed');
                        feedback.textContent = isCorrect ? 'Correct. You can continue.' : 'Not quite. Choose the correct answer before moving on.';
                    }

                    showTask(currentIndex);
                });
            });
        });

        showTask(0);
    });

    // Lab catalog filtering
    const labCategoryFilter = document.getElementById('lab-category-filter');
    const labLevelFilter = document.getElementById('lab-level-filter');
    const labSearchFilter = document.getElementById('lab-search-filter');
    const labsGrid = document.getElementById('labs-grid');
    const labNoResults = document.getElementById('lab-no-results');

    if (labCategoryFilter && labLevelFilter && labSearchFilter && labsGrid) {
        function filterLabs() {
            const categoryValue = (labCategoryFilter.value || '').toLowerCase();
            const levelValue = (labLevelFilter.value || '').toLowerCase();
            const searchValue = (labSearchFilter.value || '').toLowerCase().trim();
            const labs = labsGrid.getElementsByClassName('lab-card');
            let visibleCount = 0;

            Array.from(labs).forEach(lab => {
                const labCategory = lab.getAttribute('data-category') || '';
                const labLevel = lab.getAttribute('data-level') || '';
                const labSearch = lab.getAttribute('data-search') || '';
                const categoryMatch = !categoryValue || labCategory === categoryValue;
                const levelMatch = !levelValue || labLevel === levelValue;
                const searchMatch = !searchValue || labSearch.includes(searchValue);

                if (categoryMatch && levelMatch && searchMatch) {
                    lab.classList.remove('hidden');
                    visibleCount++;
                } else {
                    lab.classList.add('hidden');
                }
            });

            if (labNoResults) {
                labNoResults.classList.toggle('hidden', visibleCount !== 0);
                labsGrid.classList.toggle('hidden', visibleCount === 0);
            }
        }

        labCategoryFilter.addEventListener('change', filterLabs);
        labLevelFilter.addEventListener('change', filterLabs);
        labSearchFilter.addEventListener('input', filterLabs);
        filterLabs();
    }

    // Parse URL parameters for enrollment
    const urlParams = new URLSearchParams(window.location.search);
    const courseParam = urlParams.get('course');
    const titleParam = urlParams.get('title');

    if (courseParam && window.location.pathname.includes('/enroll/')) {
        console.log('Enrolling in course:', courseParam, titleParam);

        // Update the enrollment button to prefill the title if available
        if (titleParam) {
            const enrollButton = document.querySelector('[data-enrollment-button]');
            if (enrollButton) {
                const currentHref = enrollButton.getAttribute('href');
                const separator = currentHref.includes('?') ? '&' : '?';
                const prefilledTitle = `[ENROLLMENT] ${titleParam} - `;
                enrollButton.setAttribute('href', currentHref + separator + `title=${encodeURIComponent(prefilledTitle)}`);
            }
        }
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add active class to current navigation item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.site-navigation a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});
