(function () {
    'use strict';

    const dashboard = document.querySelector('[data-vulnerability-dashboard]');
    if (!dashboard) {
        return;
    }

    const numberFormatter = new Intl.NumberFormat(document.documentElement.lang || 'en');
    // Chart callbacks are registered before recommendations are initialized; this no-op is
    // replaced with the real updater below.
    let updateLearningRecommendation = () => {};
    dashboard.querySelectorAll('[data-format-number]').forEach(element => {
        const value = Number(element.textContent.trim());
        if (Number.isFinite(value)) {
            element.textContent = numberFormatter.format(value);
        }
    });

    // Split a comma-separated data attribute into non-empty entries.
    function splitList(value) {
        return (value || '').split(',').filter(entry => entry !== '');
    }

    dashboard.querySelectorAll('[data-mini-chart]').forEach(chart => {
        const counts = splitList(chart.dataset.miniChart)
            .map(value => Number(value))
            .filter(Number.isFinite);
        const months = splitList(chart.dataset.miniChartMonths);
        const complete = splitList(chart.dataset.miniChartComplete);
        const maximum = Math.max(...counts, 1);

        counts.forEach((count, index) => {
            const bar = document.createElement('span');
            const height = count === 0 ? 5 : Math.max(12, Math.round((count / maximum) * 100));
            // Partial months cover only part of the collection window, so their bars
            // are not comparable with the rest. Mute them and say so on hover.
            const isPartial = complete[index] === 'false';
            bar.className = isPartial
                ? 'min-w-0 flex-1 rounded-t bg-gray-200 transition-colors hover:bg-gray-400'
                : 'min-w-0 flex-1 rounded-t bg-red-100 transition-colors hover:bg-red-400';
            bar.style.height = `${height}%`;
            bar.title = `${months[index] || `Month ${index + 1}`}: ${numberFormatter.format(count)} CVEs`
                + (isPartial ? ' (partial month)' : '');
            chart.appendChild(bar);
        });
    });

    // Read the JSON payload embedded for the charts and recommendation.
    function getDashboardData() {
        const dataElement = document.querySelector('#dashboard-chart-data');
        try {
            const parsed = JSON.parse(dataElement?.textContent || '{}');
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    // Apply a chart click to the category filters and recommendation panel.
    function filterFromChart(categoryId, chartLabel) {
        if (!categoryId) {
            return;
        }

        const categorySelect = dashboard.querySelector('[data-category-filter]');
        const cveSelect = dashboard.querySelector('[data-cve-category]');
        // Use the document's Event constructor so browser and vm-based tests share the same API.
        const changeEvent = () => new document.defaultView.Event('change', { bubbles: true });
        if (categorySelect) {
            categorySelect.value = categoryId;
            categorySelect.dispatchEvent(changeEvent());
        }
        if (cveSelect) {
            cveSelect.value = categoryId;
            cveSelect.dispatchEvent(changeEvent());
        }

        const categoryName = categorySelect?.selectedOptions?.[0]?.textContent || categoryId;
        const status = dashboard.querySelector('[data-chart-selection-status]');
        if (status) {
            status.textContent = `${chartLabel} selected ${categoryName}. `
                + 'The learning map and CVE explorer are now filtered.';
            status.classList.remove('hidden');
        }

        updateLearningRecommendation(categoryId);

        const reducedMotion = document.defaultView?.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
        const recommendation = dashboard.querySelector('[data-learning-recommendation]');
        if (recommendation) {
            recommendation.scrollIntoView?.({
                behavior: reducedMotion ? 'auto' : 'smooth',
                block: 'center'
            });
        }
    }

    // Hide a chart canvas and reveal its static fallback.
    function showChartFallback(kind) {
        const canvas = dashboard.querySelector(`[data-dashboard-chart="${kind}"]`);
        const fallback = dashboard.querySelector(`[data-chart-fallback="${kind}"]`);
        canvas?.classList.add('hidden');
        fallback?.classList.remove('hidden');
    }

    // Render a YYYY-MM key as a localized short month and year.
    function formatMonth(month) {
        const match = /^(\d{4})-(\d{2})$/.exec(month || '');
        if (!match) {
            return month;
        }

        return new Intl.DateTimeFormat(document.documentElement.lang || 'en', {
            month: 'short',
            year: 'numeric',
            timeZone: 'UTC'
        }).format(new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1)));
    }

    // Draw the charts from the embedded payload and use static fallbacks when needed.
    function initializeCharts() {
        const categories = getDashboardData().categories;

        if (!Array.isArray(categories) || typeof Chart !== 'function') {
            ['bar', 'pie', 'line'].forEach(showChartFallback);
            return;
        }

        const ranked = categories
            .filter(category => Number.isFinite(Number(category.count)))
            .map(category => ({ ...category, count: Number(category.count) }))
            .sort((left, right) => right.count - left.count);
        const topFive = ranked.slice(0, 5);
        const topThree = ranked.slice(0, 3);
        const palette = [
            '#dc2626', '#f97316', '#f59e0b', '#0f766e', '#2563eb',
            '#7c3aed', '#db2777', '#64748b', '#84cc16', '#0891b2'
        ];
        const reducedMotion = document.defaultView?.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
        const sharedOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: reducedMotion ? 0 : 500 },
            plugins: {
                legend: {
                    labels: {
                        boxWidth: 10,
                        boxHeight: 10,
                        color: '#475569',
                        padding: 16,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: '#111827',
                    padding: 12,
                    titleFont: { weight: '600' }
                }
            }
        };

        const barCanvas = dashboard.querySelector('[data-dashboard-chart="bar"]');
        if (barCanvas && topFive.length) {
            new Chart(barCanvas, {
                type: 'bar',
                data: {
                    labels: topFive.map(category => `${category.id} · ${category.name}`),
                    datasets: [{
                        label: 'Mapped CVEs',
                        data: topFive.map(category => category.count),
                        backgroundColor: '#dc2626',
                        borderRadius: 7,
                        borderSkipped: false
                    }]
                },
                options: {
                    ...sharedOptions,
                    indexAxis: 'y',
                    onClick(_event, elements) {
                        filterFromChart(topFive[elements?.[0]?.index]?.id, 'Bar chart');
                    },
                    plugins: { ...sharedOptions.plugins, legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { color: '#64748b' } },
                        y: { grid: { display: false }, ticks: { color: '#334155', autoSkip: false } }
                    }
                }
            });
        } else {
            showChartFallback('bar');
        }

        const pieCanvas = dashboard.querySelector('[data-dashboard-chart="pie"]');
        if (pieCanvas && ranked.length) {
            const total = ranked.reduce((sum, category) => sum + category.count, 0);
            new Chart(pieCanvas, {
                type: 'pie',
                data: {
                    labels: ranked.map(category => category.id),
                    datasets: [{
                        data: ranked.map(category => category.count),
                        backgroundColor: ranked.map((_category, index) => palette[index % palette.length]),
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    ...sharedOptions,
                    onClick(_event, elements) {
                        filterFromChart(ranked[elements?.[0]?.index]?.id, 'Pie chart');
                    },
                    plugins: {
                        ...sharedOptions.plugins,
                        legend: { ...sharedOptions.plugins.legend, position: 'bottom' },
                        tooltip: {
                            ...sharedOptions.plugins.tooltip,
                            callbacks: {
                                label(context) {
                                    const percentage = total ? ((context.raw / total) * 100).toFixed(1) : '0.0';
                                    return `${context.label}: ${numberFormatter.format(context.raw)} `
                                        + `CVEs (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        } else {
            showChartFallback('pie');
        }

        const completeMonths = Array.from(new Set(topThree.flatMap(category =>
            (category.monthly_counts || [])
                .filter(entry => entry.complete === true)
                .map(entry => entry.month)
        ))).sort();
        const lineCanvas = dashboard.querySelector('[data-dashboard-chart="line"]');
        if (lineCanvas && topThree.length && completeMonths.length >= 2) {
            new Chart(lineCanvas, {
                type: 'line',
                data: {
                    labels: completeMonths.map(formatMonth),
                    datasets: topThree.map((category, index) => {
                        const countsByMonth = new Map(
                            (category.monthly_counts || []).map(entry => [entry.month, entry.count])
                        );
                        return {
                            label: `${category.id} · ${category.name}`,
                            data: completeMonths.map(month => Number(countsByMonth.get(month) || 0)),
                            borderColor: palette[index],
                            backgroundColor: palette[index],
                            borderWidth: 2.5,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            tension: 0.3
                        };
                    })
                },
                options: {
                    ...sharedOptions,
                    onClick(_event, elements) {
                        filterFromChart(topThree[elements?.[0]?.datasetIndex]?.id, 'Line chart');
                    },
                    interaction: { intersect: false, mode: 'index' },
                    plugins: {
                        ...sharedOptions.plugins,
                        legend: { ...sharedOptions.plugins.legend, position: 'bottom' }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#64748b' } },
                        y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', precision: 0 } }
                    }
                }
            });
        } else {
            showChartFallback('line');
        }
    }

    // Normalize the catalog and saved-progress key for a lab slug.
    function normalizeLabId(value) {
        return String(value || '').trim().toLowerCase().replace(/_/g, '-');
    }

    // Read progress saved on this device.
    function getSavedLabProgress() {
        try {
            const parsed = JSON.parse(document.defaultView?.localStorage?.getItem('blt-lab-progress') || '{}');
            return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    // Score labs once, then let chart selections choose from the candidates.
    function initializeLearningRecommendation() {
        const recommendation = dashboard.querySelector('[data-learning-recommendation]');
        const dashboardData = getDashboardData();
        const categories = Array.isArray(dashboardData.categories) ? dashboardData.categories : [];
        const labCatalog = Array.isArray(dashboardData.labs) ? dashboardData.labs : [];
        if (!recommendation || !categories.length) {
            return;
        }

        const catalogById = new Map(labCatalog.map(lab => [normalizeLabId(lab.slug), lab]));
        const progress = getSavedLabProgress();
        const maximumFrequency = Math.max(...categories.map(category => Number(category.count) || 0), 1);
        const maximumKev = Math.max(...categories.map(category => Number(category.known_exploited) || 0), 1);
        const candidatesByLab = new Map();

        categories.forEach(category => {
            const labs = Array.isArray(category.labs) ? category.labs : [];
            labs.forEach(lab => {
                const labId = normalizeLabId(lab.slug);
                const catalogEntry = catalogById.get(labId) || {};
                const taskCount = Math.max(0, Number(catalogEntry.task_count) || 0);
                const savedTasks = progress[labId];
                const completedTasks = savedTasks && typeof savedTasks === 'object' && !Array.isArray(savedTasks)
                    ? Object.values(savedTasks).filter(task => task?.completed === true).length
                    : 0;
                const hasTaskCount = taskCount > 0;
                const progressRatio = hasTaskCount ? Math.min(completedTasks, taskCount) / taskCount : 0;
                const frequencySignal = (Number(category.count) || 0) / maximumFrequency;
                const exploitationSignal = (Number(category.known_exploited) || 0) / maximumKev;
                // Without a known task count there is no progress evidence, so use a neutral
                // signal rather than claiming the lab is completely unstarted.
                const incompletenessSignal = hasTaskCount ? 1 - progressRatio : 0.5;
                // CVE volume and unfinished progress drive the score; KEV is a lighter tie-breaker.
                const score = (0.4 * frequencySignal)
                    + (0.4 * incompletenessSignal)
                    + (0.2 * exploitationSignal);
                const candidate = {
                    category,
                    lab,
                    url: catalogEntry.url || `/labs/${lab.slug}/`,
                    progressRatio,
                    score,
                    complete: taskCount > 0 && completedTasks >= taskCount
                };
                const existing = candidatesByLab.get(labId);
                if (!existing || candidate.score > existing.score) {
                    candidatesByLab.set(labId, candidate);
                }
            });
        });

        const setText = (selector, value) => {
            const element = recommendation.querySelector(selector);
            if (element) {
                element.textContent = value;
            }
        };
        const candidates = Array.from(candidatesByLab.values());
        updateLearningRecommendation = categoryId => {
            const categoryCandidates = categoryId
                ? candidates.filter(candidate => candidate.category.id === categoryId)
                : candidates;
            const relevantCandidates = categoryCandidates.length ? categoryCandidates : candidates;
            const incompleteCandidates = relevantCandidates.filter(candidate => !candidate.complete);
            const selected = (incompleteCandidates.length ? incompleteCandidates : relevantCandidates)
                .sort((left, right) => {
                    return right.score - left.score
                        || Number(right.category.count) - Number(left.category.count);
                })[0];
            if (!selected) {
                return;
            }

            setText('[data-recommendation-category]', `${selected.category.id} · ${selected.category.name}`);
            setText('[data-recommendation-title]', selected.lab.title);
            setText(
                '[data-recommendation-reason]',
                `${selected.lab.reason} Recommended from current vulnerability activity, `
                    + 'CISA exploitation evidence, and the lab progress saved on this device.'
            );
            setText('[data-recommendation-frequency]', `${numberFormatter.format(selected.category.count)} CVEs`);
            setText(
                '[data-recommendation-kev]',
                `${numberFormatter.format(selected.category.known_exploited)} CISA KEV`
            );
            setText('[data-recommendation-progress]', `${Math.round(selected.progressRatio * 100)}% complete`);
            setText('[data-recommendation-score]', `${Math.round(selected.score * 100)}% priority score`);
            const startLink = recommendation.querySelector('[data-start-learning]');
            if (startLink) {
                startLink.href = selected.url;
                // Update only the text node so the trailing arrow icon remains intact.
                if (startLink.firstChild) {
                    startLink.firstChild.textContent = selected.progressRatio > 0
                        ? 'Continue learning '
                        : 'Start learning ';
                }
            }
        };
        updateLearningRecommendation();
    }

    initializeCharts();
    initializeLearningRecommendation();

    const categoryFilter = dashboard.querySelector('[data-category-filter]');
    const categoryCards = Array.from(dashboard.querySelectorAll('[data-category-card]'));
    categoryFilter?.addEventListener('change', () => {
        const selected = categoryFilter.value;
        categoryCards.forEach(card => {
            card.classList.toggle('hidden', selected !== 'all' && card.dataset.categoryCard !== selected);
        });
    });

    const searchInput = dashboard.querySelector('[data-cve-search]');
    const cveCategory = dashboard.querySelector('[data-cve-category]');
    const cveSeverity = dashboard.querySelector('[data-cve-severity]');
    const kevOnly = dashboard.querySelector('[data-cve-kev]');
    const cveCards = Array.from(dashboard.querySelectorAll('[data-cve-card]'));
    const emptyState = dashboard.querySelector('[data-cve-empty]');
    const moreButton = dashboard.querySelector('[data-cve-more]');
    const pageSize = 8;
    let visibleLimit = pageSize;

    // Test one CVE card against the active search, category, severity, and KEV filters.
    function matchesFilters(card) {
        const query = (searchInput?.value || '').trim().toLowerCase();
        const category = cveCategory?.value || 'all';
        const severity = cveSeverity?.value || 'all';
        const requiresKev = Boolean(kevOnly?.checked);

        return (!query || (card.dataset.search || '').includes(query))
            && (category === 'all' || card.dataset.category === category)
            && (severity === 'all' || card.dataset.severity === severity)
            && (!requiresKev || card.dataset.kev === 'true');
    }

    // Re-apply filters and repaint the visible page of CVE cards.
    function updateCveList(resetLimit) {
        if (resetLimit) {
            visibleLimit = pageSize;
        }

        const matches = cveCards.filter(matchesFilters);
        cveCards.forEach(card => card.classList.add('hidden'));
        matches.slice(0, visibleLimit).forEach(card => card.classList.remove('hidden'));

        emptyState?.classList.toggle('hidden', matches.length !== 0);
        if (moreButton) {
            moreButton.parentElement?.classList.toggle('hidden', matches.length <= visibleLimit);
            const remaining = Math.max(0, matches.length - visibleLimit);
            const nextPage = Math.min(pageSize, remaining);
            moreButton.textContent = `Show ${nextPage} more ${nextPage === 1 ? 'CVE' : 'CVEs'}`;
        }
    }

    [searchInput, cveCategory, cveSeverity, kevOnly].forEach(control => {
        control?.addEventListener(control === searchInput ? 'input' : 'change', () => updateCveList(true));
    });
    moreButton?.addEventListener('click', () => {
        visibleLimit += pageSize;
        updateCveList(false);
    });

    updateCveList(true);
}());
