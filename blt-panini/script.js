
// State
let allApps = [];
let allSlackApps = [];
let slackSortField = 'app_name';
let slackSortDir = 'asc';
let map;
let countriesLayer;
let markersLayer;
let allCountriesData = {};
let geoJSONLoaded = false;
let currentView = 'list';

// DOM Elements
const searchInput = document.getElementById('countrySearch');
const listViewBtn = document.getElementById('listViewBtn');
const mapViewBtn = document.getElementById('mapViewBtn');
const slackViewBtn = document.getElementById('slackViewBtn');
const listView = document.getElementById('listView');
const mapView = document.getElementById('mapView');
const slackView = document.getElementById('slackView');
const searchBarWrapper = document.getElementById('searchBarWrapper');
const resultsSection = document.getElementById('resultsSection');
const appsGrid = document.getElementById('appsGrid');
const noResults = document.getElementById('noResults');
const countryInfo = document.getElementById('countryInfo');
const themeToggle = document.getElementById('themeToggle');
const sunIcon = document.getElementById('sunIcon');
const moonIcon = document.getElementById('moonIcon');

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Check system preference for dark mode
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.classList.add('dark');
        updateThemeIcon(true);
    }

    try {
        const response = await fetch('banned_apps.json');
        const data = await response.json();
        // Parse Django fixture format
        allApps = data.map(item => ({
            ...item.fields,
            id: item.pk // keeping pk if needed though not used extensively
        }));

        // Initial render
        renderApps(allApps);
        updateStats();
    } catch (error) {
        console.error('Error loading banned apps data:', error);
        appsGrid.innerHTML = '<p class="text-red-500">Error loading data. Please check console.</p>';
    }

    try {
        const slackResponse = await fetch('slack_apps.json');
        allSlackApps = await slackResponse.json();
        updateStats();
    } catch (error) {
        console.error('Error loading slack apps data:', error);
    }

    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Search
    searchInput.addEventListener('input', debounce((e) => {
        const query = e.target.value.trim().toLowerCase();
        handleSearch(query);
    }, 300));

    // View Toggles
    listViewBtn.addEventListener('click', () => switchView('list'));
    mapViewBtn.addEventListener('click', () => switchView('map'));
    slackViewBtn.addEventListener('click', () => switchView('slack'));

    // Theme Toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Close Info Panel
    document.getElementById('closeInfoBtn').addEventListener('click', () => {
        countryInfo.classList.add('hidden');
    });

    // Slack filters
    document.getElementById('slackSearch').addEventListener('input', debounce(renderSlackApps, 300));
    document.getElementById('slackRatingFilter').addEventListener('change', renderSlackApps);
    document.getElementById('slackDataAccessFilter').addEventListener('change', renderSlackApps);
    document.getElementById('slackCategoryFilter').addEventListener('change', renderSlackApps);

    // Slack table column sort
    document.querySelectorAll('#slackView th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (slackSortField === field) {
                slackSortDir = slackSortDir === 'asc' ? 'desc' : 'asc';
            } else {
                slackSortField = field;
                slackSortDir = 'asc';
            }
            renderSlackApps();
        });
    });
}

function handleSearch(query) {
    // Always reset map visuals/highlights first when searching
    resetMapHighlights();

    if (!query) {
        renderApps(allApps);
        if (currentView === 'map') resetMapVisuals();
        return;
    }

    const filteredApps = allApps.filter(app =>
        app.country_name.toLowerCase().includes(query) ||
        app.app_name.toLowerCase().includes(query)
    );

    if (currentView === 'list') {
        renderApps(filteredApps);
    } else {
        // Map view: Update markers? For now, we keep markers for all apps but highlight the searched country.
        // If the query matches a country name, highlight it.
        const matchedCountry = Object.keys(allCountriesData).find(c => c.includes(query));
        if (matchedCountry) {
            highlightCountry(matchedCountry, true);
        }
    }
}

function renderApps(apps) {
    if (apps.length === 0) {
        resultsSection.classList.add('hidden');
        noResults.classList.remove('hidden');
        return;
    }

    resultsSection.classList.remove('hidden');
    noResults.classList.add('hidden');
    appsGrid.innerHTML = '';

    apps.forEach(app => {
        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-300 overflow-hidden border border-gray-100 dark:border-gray-700 flex flex-col';

        card.innerHTML = `
            <div class="bg-gray-50 dark:bg-gray-700/30 px-6 py-4 border-b border-gray-100 dark:border-gray-700/50 flex justify-between items-center">
                <h3 class="text-xl font-bold text-red-600 truncate mr-2">${app.app_name}</h3>
                <span class="px-2 py-1 text-[10px] uppercase tracking-wider font-bold rounded bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 whitespace-nowrap">
                    ${app.country_name}
                </span>
            </div>
            <div class="p-6 flex-grow">
                <p class="text-[11px] font-bold text-gray-400 dark:text-gray-500 mb-2 uppercase tracking-widest">${app.app_type}</p>
                <p class="text-gray-700 dark:text-gray-300 text-sm leading-relaxed line-clamp-3">${app.ban_reason}</p>
            </div>
            <div class="bg-gray-50/50 dark:bg-gray-800 px-6 py-4 border-t border-gray-100 dark:border-gray-700/50 flex justify-between items-center text-xs">
                <span class="text-gray-500 dark:text-gray-400 font-medium">${new Date(app.ban_date).toLocaleDateString()}</span>
                ${app.source_url ? `<a href="${app.source_url}" target="_blank" class="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-bold hover:underline inline-flex items-center">Details <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>` : ''}
            </div>
        `;
        appsGrid.appendChild(card);
    });
}

// ── Stats ─────────────────────────────────────────────────────────────────────

function updateStats() {
    const totalBanned = allApps.length;
    const totalCountries = new Set(allApps.map(app => app.country_name)).size;
    const totalSlack = allSlackApps?.length ?? 0;

    document.getElementById('statTotalBannedApps').textContent = totalBanned || '—';
    document.getElementById('statTotalCountries').textContent = totalCountries || '—';
    document.getElementById('statTotalSlackApps').textContent = totalSlack || '—';
}

// ── Slack Apps ────────────────────────────────────────────────────────────────

const RATING_ORDER = { A: 0, B: 1, C: 2, D: 3, F: 4 };
const DATA_ACCESS_ORDER = { Low: 0, Medium: 1, High: 2 };
const UNKNOWN_SORT_VALUE = 99;

const RATING_CLASSES = {
    A: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    B: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    D: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    F: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const DATA_ACCESS_CLASSES = {
    Low: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    Medium: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    High: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

function populateSlackCategoryFilter() {
    const select = document.getElementById('slackCategoryFilter');
    const categories = [...new Set(allSlackApps.map(a => a.category))].sort();
    categories.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        select.appendChild(opt);
    });
}

function renderSlackApps() {
    const tbody = document.getElementById('slackAppsTableBody');
    const noResultsEl = document.getElementById('slackNoResults');
    const searchVal = document.getElementById('slackSearch').value.trim().toLowerCase();
    const ratingVal = document.getElementById('slackRatingFilter').value;
    const categoryVal = document.getElementById('slackCategoryFilter').value;
    const dataAccessVal = document.getElementById('slackDataAccessFilter').value;

    let filtered = allSlackApps.filter(app => {
        if (searchVal && !app.app_name.toLowerCase().includes(searchVal) &&
            !app.developer.toLowerCase().includes(searchVal) &&
            !app.category.toLowerCase().includes(searchVal)) return false;
        if (ratingVal && app.security_rating !== ratingVal) return false;
        if (categoryVal && app.category !== categoryVal) return false;
        if (dataAccessVal && app.data_access !== dataAccessVal) return false;
        return true;
    });

    // Sort
    filtered.sort((a, b) => {
        let aVal = a[slackSortField];
        let bVal = b[slackSortField];
        if (slackSortField === 'security_rating') {
            aVal = RATING_ORDER[aVal] ?? UNKNOWN_SORT_VALUE;
            bVal = RATING_ORDER[bVal] ?? UNKNOWN_SORT_VALUE;
        } else if (slackSortField === 'data_access') {
            aVal = DATA_ACCESS_ORDER[aVal] ?? UNKNOWN_SORT_VALUE;
            bVal = DATA_ACCESS_ORDER[bVal] ?? UNKNOWN_SORT_VALUE;
        } else {
            aVal = (aVal || '').toString().toLowerCase();
            bVal = (bVal || '').toString().toLowerCase();
        }
        if (aVal < bVal) return slackSortDir === 'asc' ? -1 : 1;
        if (aVal > bVal) return slackSortDir === 'asc' ? 1 : -1;
        return 0;
    });

    // Update sort indicators
    document.querySelectorAll('#slackView th[data-sort]').forEach(th => {
        const indicator = th.querySelector('.sort-indicator');
        if (th.dataset.sort === slackSortField) {
            indicator.textContent = slackSortDir === 'asc' ? '↑' : '↓';
            indicator.classList.remove('text-gray-400');
            indicator.classList.add('text-red-500');
        } else {
            indicator.textContent = '↕';
            indicator.classList.add('text-gray-400');
            indicator.classList.remove('text-red-500');
        }
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        noResultsEl.classList.remove('hidden');
        return;
    }
    noResultsEl.classList.add('hidden');

    tbody.innerHTML = filtered.map(app => {
        const ratingClass = RATING_CLASSES[app.security_rating] || 'bg-gray-100 text-gray-700';
        const dataClass = DATA_ACCESS_CLASSES[app.data_access] || 'bg-gray-100 text-gray-700';
        const permissions = app.permissions.map(p =>
            `<span class="inline-block px-1.5 py-0.5 rounded text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 mr-1 mb-1">${p}</span>`
        ).join('');
        const verifiedBadge = app.verified
            ? `<span class="inline-flex items-center gap-0.5 text-green-600 dark:text-green-400 font-medium" title="Verified"><svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg> Yes</span>`
            : `<span class="text-gray-400 dark:text-gray-500">—</span>`;
        const link = app.source_url
            ? `<a href="${app.source_url}" target="_blank" rel="noopener noreferrer" class="text-red-600 hover:underline font-medium text-xs inline-flex items-center gap-0.5">View<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>`
            : '';
        const privacyLink = app.privacy_policy_url
            ? `<a href="${app.privacy_policy_url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline font-medium text-xs inline-flex items-center gap-0.5">Privacy<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>`
            : '<span class="text-gray-400 dark:text-gray-500 text-xs">—</span>';
        return `<tr class="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors">
            <td class="px-4 py-3 font-semibold text-gray-900 dark:text-white whitespace-nowrap">${app.app_name}<div class="text-xs font-normal text-gray-400 dark:text-gray-500">${app.developer}</div></td>
            <td class="px-4 py-3 text-gray-600 dark:text-gray-300 whitespace-nowrap">${app.category}</td>
            <td class="px-4 py-3"><span class="inline-block w-7 h-7 rounded font-black text-center leading-7 text-sm ${ratingClass}">${app.security_rating}</span></td>
            <td class="px-4 py-3"><span class="px-2 py-0.5 rounded-full text-xs font-medium ${dataClass}">${app.data_access}</span></td>
            <td class="px-4 py-3 min-w-[180px]"><div class="flex flex-wrap">${permissions}</div></td>
            <td class="px-4 py-3 text-xs text-gray-600 dark:text-gray-300 max-w-xs">${app.security_notes}</td>
            <td class="px-4 py-3 text-center">${verifiedBadge}</td>
            <td class="px-4 py-3">${link}</td>
            <td class="px-4 py-3">${privacyLink}</td>
        </tr>`;
    }).join('');
}

// ── View switching ────────────────────────────────────────────────────────────

function switchView(view) {
    currentView = view;

    // Reset all tab styles
    [listViewBtn, mapViewBtn, slackViewBtn].forEach(btn => {
        btn.classList.remove('text-red-600', 'border-b-2', 'border-red-600');
        btn.classList.add('text-gray-500', 'dark:text-gray-400');
    });

    // Hide all views
    listView.classList.add('hidden');
    mapView.classList.add('hidden');
    slackView.classList.add('hidden');

    if (view === 'list') {
        listView.classList.remove('hidden');
        searchBarWrapper.classList.remove('hidden');
        listViewBtn.classList.add('text-red-600', 'border-b-2', 'border-red-600');
        listViewBtn.classList.remove('text-gray-500', 'dark:text-gray-400');
    } else if (view === 'map') {
        mapView.classList.remove('hidden');
        searchBarWrapper.classList.remove('hidden');
        mapViewBtn.classList.add('text-red-600', 'border-b-2', 'border-red-600');
        mapViewBtn.classList.remove('text-gray-500', 'dark:text-gray-400');
        if (!map) initMap();
        else setTimeout(() => map.invalidateSize(), 100); // Fix Leaflet render on tab switch
    } else if (view === 'slack') {
        slackView.classList.remove('hidden');
        searchBarWrapper.classList.add('hidden');
        slackViewBtn.classList.add('text-red-600', 'border-b-2', 'border-red-600');
        slackViewBtn.classList.remove('text-gray-500', 'dark:text-gray-400');
        // Populate category filter and render on first visit
        const categorySelect = document.getElementById('slackCategoryFilter');
        if (categorySelect.options.length === 1) {
            populateSlackCategoryFilter();
        }
        renderSlackApps();
    }
}

// Map Functions
function initMap() {
    map = L.map('map').setView([20, 0], 2);

    // Check for dark mode to set initial tile layer
    const isDark = document.documentElement.classList.contains('dark');
    const tileUrl = isDark
        ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

    const attribution = isDark
        ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

    const tileLayer = L.tileLayer(tileUrl, { attribution }).addTo(map);

    // Save tileLayer reference to update on theme toggle if needed (advanced)

    markersLayer = L.layerGroup().addTo(map);

    fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
        .then(response => response.json())
        .then(data => {
            const features = data.features || [];
            countriesLayer = L.geoJSON(features, {
                style: getCountryStyle,
                onEachFeature: onEachFeature
            }).addTo(map);
            geoJSONLoaded = true;

            // Populate markers initially
            placeMarkersForApps(allApps);
        })
        .catch(err => {
            console.error("Error loading GeoJSON:", err);
            geoJSONLoaded = true;
        });
}

function getCountryStyle(feature) {
    const isDark = document.documentElement.classList.contains('dark');
    return {
        fillColor: isDark ? "#374151" : "#f3f4f6",
        weight: 1,
        opacity: 1,
        color: isDark ? "#4b5563" : "#d1d5db",
        fillOpacity: 0.7
    };
}

function onEachFeature(feature, layer) {
    const countryName = (feature.properties.name || feature.properties.ADMIN || "").toLowerCase();
    if (!countryName) return;

    allCountriesData[countryName] = {
        layer: layer,
        feature: feature,
        center: layer.getBounds().getCenter() // Approximation
    };

    layer.on({
        mouseover: function (e) {
            const layer = e.target;
            const isDark = document.documentElement.classList.contains('dark');
            layer.setStyle({
                weight: 2,
                color: isDark ? "#9ca3af" : "#6b7280",
                fillOpacity: 0.9
            });
            layer.bringToFront();
        },
        mouseout: function (e) {
            countriesLayer.resetStyle(e.target);
            // Re-apply highlight if active? (Simplification: just reset)
        },
        click: function (e) {
            // Maybe filter list by this country?
            const clickedCountry = countryName;
            // For now, just zoom
            map.fitBounds(e.target.getBounds());

            // Show info if apps exist
            const apps = allApps.filter(app => app.country_name.toLowerCase() === clickedCountry);
            if (apps.length > 0) {
                showCountryInfo(clickedCountry, apps);
            }
        }
    });
}

function placeMarkersForApps(apps) {
    if (!markersLayer) return;
    markersLayer.clearLayers();

    // Group apps by country
    const appsByCountry = {};
    apps.forEach(app => {
        const cLower = app.country_name.toLowerCase();
        if (!appsByCountry[cLower]) appsByCountry[cLower] = [];
        appsByCountry[cLower].push(app);
    });

    Object.entries(appsByCountry).forEach(([countryName, countryApps]) => {
        const countryData = allCountriesData[countryName];
        if (countryData) {
            const center = countryData.layer.getBounds().getCenter();
            const count = countryApps.length;

            const markerHTML = `
                <div style="position: relative; width: 42px; height: 42px;">
                    <div style="width: 42px; height: 42px; border-radius: 50% 50% 50% 0; background: #dc2626; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; font-weight: 700; box-shadow: 0 0 10px rgba(0,0,0,0.25); ">
                        <div style="transform: rotate(45deg);">
                            ${count}
                        </div>
                    </div>
                </div>`;

            const marker = L.marker(center, {
                icon: L.divIcon({
                    className: "map-pin-marker",
                    html: markerHTML,
                    iconSize: [42, 42],
                    iconAnchor: [21, 42]
                })
            });

            marker.bindTooltip(`${countryApps[0].country_name}: ${count} banned apps`, {
                direction: "top",
                offset: [0, -20],
                className: "bg-gray-800 text-white px-2 py-1 rounded text-xs"
            });

            marker.on('click', () => {
                showCountryInfo(countryName, countryApps);
                map.setView(center, 4);
            });

            markersLayer.addLayer(marker);
        }
    });
}

function showCountryInfo(countryName, apps) {
    const titleName = countryName.charAt(0).toUpperCase() + countryName.slice(1);
    document.getElementById('countryName').textContent = titleName;
    document.getElementById('bannedAppsCount').textContent = `${apps.length} Banned Apps`;

    const listDiv = document.getElementById('bannedAppsList');
    listDiv.innerHTML = apps.map(app => `
        <div class="rounded-lg overflow-hidden border border-gray-100 dark:border-gray-700 shadow-sm transition-all hover:shadow-md">
            <div class="bg-gray-50 dark:bg-gray-700/50 px-3 py-2 border-b border-gray-100 dark:border-gray-700/50 flex justify-between items-center">
                <h4 class="font-bold text-red-600 text-sm truncate mr-2">${app.app_name}</h4>
                <span class="text-[9px] font-bold text-gray-400 uppercase tracking-tighter">${app.app_type}</span>
            </div>
            <div class="p-3 bg-white dark:bg-gray-800">
                <p class="text-[13px] text-gray-700 dark:text-gray-300 leading-snug line-clamp-2">${app.ban_reason}</p>
                <div class="mt-2 flex justify-between items-center">
                    <span class="text-[10px] text-gray-400 font-medium italic">${new Date(app.ban_date).toLocaleDateString()}</span>
                    ${app.source_url ? `<a href="${app.source_url}" target="_blank" class="text-[10px] text-red-600 hover:underline font-bold">Source</a>` : ''}
                </div>
            </div>
        </div>
    `).join('');

    countryInfo.classList.remove('hidden');
}

function highlightCountry(countryName, isActive) {
    if (!map || !countriesLayer) return;

    const lower = countryName.toLowerCase();
    const countryData = allCountriesData[lower];

    if (countryData) {
        if (isActive) {
            const layer = countryData.layer;
            const isDark = document.documentElement.classList.contains('dark');

            layer.setStyle({
                fillColor: '#ef4444',
                weight: 2,
                color: isDark ? '#fca5a5' : '#b91c1c',
                fillOpacity: 0.6
            });

            layer.bringToFront();
            map.fitBounds(layer.getBounds(), { padding: [50, 50] });

            const popup = L.popup()
                .setLatLng(layer.getBounds().getCenter())
                .setContent(`<div class="text-center font-bold px-2 py-1">${countryName.toUpperCase()}</div>`)
                .openOn(map);
        }
    }
}

function resetMapHighlights() {
    if (countriesLayer) {
        countriesLayer.eachLayer(layer => {
            countriesLayer.resetStyle(layer);
        });
    }
    if (map) {
        map.closePopup();
    }
}

function resetMapVisuals() {
    resetMapHighlights();
    if (countryInfo) countryInfo.classList.add('hidden');
    if (map) map.setView([20, 0], 2);
}

// Utility
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

// Theme
function toggleTheme() {
    const html = document.documentElement;
    if (html.classList.contains('dark')) {
        html.classList.remove('dark');
        updateThemeIcon(false);
    } else {
        html.classList.add('dark');
        updateThemeIcon(true);
    }

    // Re-initialize map tiles if necessary (simple reload or layer swap)
    if (map) {
        map.remove();
        initMap(); // Simplest way to swap tile styles properly
    }
}

function updateThemeIcon(isDark) {
    if (isDark) {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    }
}
