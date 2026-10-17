(function () {
    'use strict';

    const STORAGE_KEY = 'blt-lab-progress';
    const SCORE_WEIGHTS = { frequency: 0.4, incomplete: 0.4, owasp: 0.2 };

    function isPlainObject(value) {
        return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
    }

    function readData() {
        const element = document.getElementById('adaptive-recommendation-data');
        if (!element) {
            return null;
        }

        try {
            const data = JSON.parse(element.textContent);
            return isPlainObject(data) && Array.isArray(data.categories) && Array.isArray(data.labs)
                ? data
                : null;
        } catch (_error) {
            return null;
        }
    }

    function readProgress() {
        try {
            const progress = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            return isPlainObject(progress) ? progress : {};
        } catch (_error) {
            return {};
        }
    }

    function completionRate(lab, progress) {
        if (!lab.taskCount) {
            return 0;
        }

        const labProgress = isPlainObject(progress[lab.id]) ? progress[lab.id] : {};
        const completed = Object.values(labProgress).filter(step => isPlainObject(step) && step.completed).length;
        return Math.min(completed / lab.taskCount, 1);
    }

    function slugKey(value) {
        return String(value || '').replace(/[-_]/g, '').toLowerCase();
    }

    function getRecommendations({ currentLabId, limit = 3 } = {}) {
        const data = readData();
        if (!data) {
            return [];
        }

        const progress = readProgress();
        const categories = data.categories.filter(isPlainObject);
        const maxCount = Math.max(...categories.map(category => category.count || 0), 1);
        const weights = isPlainObject(data.weights) ? data.weights : {};
        const currentLabKey = slugKey(currentLabId);

        return data.labs.filter(lab => {
            return isPlainObject(lab) && lab.id && lab.title && lab.url && slugKey(lab.id) !== currentLabKey;
        }).map(lab => ({
            lab,
            completion: completionRate(lab, progress)
        })).filter(({ completion }) => completion < 1).map(({ lab, completion }) => {
            const related = categories.filter(category => {
                const mappedLabs = Array.isArray(category.labs) ? category.labs : [];
                return mappedLabs.some(mapped => {
                    return isPlainObject(mapped) && slugKey(mapped.slug) === slugKey(lab.id);
                });
            });
            const category = related.reduce((best, candidate) => {
                const candidateScore = (candidate.count / maxCount) * SCORE_WEIGHTS.frequency +
                    (weights[candidate.id] || 0) * SCORE_WEIGHTS.owasp;
                const bestScore = best
                    ? (best.count / maxCount) * SCORE_WEIGHTS.frequency +
                        (weights[best.id] || 0) * SCORE_WEIGHTS.owasp
                    : -1;
                return candidateScore > bestScore ? candidate : best;
            }, null);
            const incomplete = 1 - completion;
            const frequency = category ? category.count / maxCount : 0;
            const owasp = category ? (weights[category.id] || 0) : 0;

            return {
                ...lab,
                category,
                score: SCORE_WEIGHTS.frequency * frequency +
                    SCORE_WEIGHTS.incomplete * incomplete +
                    SCORE_WEIGHTS.owasp * owasp
            };
        }).sort((a, b) => b.score - a.score || a.title.localeCompare(b.title)).slice(0, limit);
    }

    function escapeHtml(value) {
        const element = document.createElement('span');
        element.textContent = value;
        return element.innerHTML;
    }

    function render(container, { force = false } = {}) {
        if (container.dataset.renderOnCompletion === 'true' && !force) {
            return;
        }

        const recommendations = getRecommendations({
            currentLabId: container.dataset.currentLab || undefined,
            limit: Number(container.dataset.limit || 3)
        });
        if (!recommendations.length) {
            container.hidden = true;
            return;
        }

        container.hidden = false;
        const list = container.querySelector('[data-adaptive-recommendation-list]') || container;
        list.innerHTML = recommendations.map((lab, index) => {
            const categoryBadge = lab.category
                ? `<span class="mt-2 inline-flex rounded-full bg-white px-2 py-1 text-[10px] font-bold text-gray-600 ring-1 ring-gray-200">OWASP ${escapeHtml(lab.category.id)} · ${escapeHtml(lab.category.name)}</span>`
                : '';

            return `
            <a href="${escapeHtml(lab.url)}" class="group block rounded-2xl border border-red-100 bg-red-50/50 p-4 transition hover:border-red-300 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-200">
                <span class="flex items-start gap-3">
                    <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white">${index + 1}</span>
                    <span class="min-w-0">
                        <span class="block text-[10px] font-bold uppercase tracking-widest text-red-600">Recommended lab</span>
                        <span class="mt-1 block text-sm font-bold text-gray-900 group-hover:text-red-700">${escapeHtml(lab.title)}</span>
                        <span class="mt-1 block text-xs leading-5 text-gray-600">${escapeHtml(lab.description || 'Build practical security skills through a focused lab.')}</span>
                        ${categoryBadge}
                    </span>
                </span>
            </a>`;
        }).join('');
    }

    function renderAll(options) {
        document.querySelectorAll('[data-adaptive-recommendations]').forEach(container => {
            render(container, options);
        });
    }

    window.BltRecommendations = { getRecommendations, renderAll };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderAll);
    } else {
        renderAll();
    }
}());
