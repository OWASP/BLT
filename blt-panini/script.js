
// State
let allApps = [];
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
const listView = document.getElementById('listView');
const mapView = document.getElementById('mapView');
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
    } catch (error) {
        console.error('Error loading banned apps data:', error);
        appsGrid.innerHTML = '<p class="text-red-500">Error loading data. Please check console.</p>';
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

    // Theme Toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Close Info Panel
    document.getElementById('closeInfoBtn').addEventListener('click', () => {
        countryInfo.classList.add('hidden');
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
            <div class="p-6 flex-grow">
                <div class="flex justify-between items-start mb-3">
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white">${app.app_name}</h3>
                    <span class="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                        ${app.country_name}
                    </span>
                </div>
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wide">${app.app_type}</p>
                <p class="text-gray-700 dark:text-gray-300 mb-4 line-clamp-3">${app.ban_reason}</p>
            </div>
            <div class="bg-gray-50 dark:bg-gray-700/50 px-6 py-4 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center text-sm">
                <span class="text-gray-500 dark:text-gray-400">Banned: ${new Date(app.ban_date).toLocaleDateString()}</span>
                ${app.source_url ? `<a href="${app.source_url}" target="_blank" class="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium hover:underline inline-flex items-center">Source <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>` : ''}
            </div>
        `;
        appsGrid.appendChild(card);
    });
}

function switchView(view) {
    currentView = view;
    if (view === 'list') {
        listView.classList.remove('hidden');
        mapView.classList.add('hidden');

        listViewBtn.classList.add('text-red-600', 'border-b-2', 'border-red-600');
        listViewBtn.classList.remove('text-gray-500', 'dark:text-gray-400');

        mapViewBtn.classList.remove('text-red-600', 'border-b-2', 'border-red-600');
        mapViewBtn.classList.add('text-gray-500', 'dark:text-gray-400');
    } else {
        listView.classList.add('hidden');
        mapView.classList.remove('hidden');

        mapViewBtn.classList.add('text-red-600', 'border-b-2', 'border-red-600');
        mapViewBtn.classList.remove('text-gray-500', 'dark:text-gray-400');

        listViewBtn.classList.remove('text-red-600', 'border-b-2', 'border-red-600');
        listViewBtn.classList.add('text-gray-500', 'dark:text-gray-400');

        if (!map) initMap();
        else setTimeout(() => map.invalidateSize(), 100); // Fix Leaflet render on tab switch
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
                <div class="relative w-10 h-10 group cursor-pointer transform hover:scale-110 transition-transform duration-200">
                    <div class="absolute inset-0 bg-red-600 rounded-full opacity-75 animate-ping group-hover:animate-none"></div>
                    <div class="absolute inset-0 bg-red-600 rounded-full flex items-center justify-center shadow-lg border-2 border-white dark:border-gray-800">
                        <span class="text-white font-bold text-sm">${count}</span>
                    </div>
                </div>`;

            const marker = L.marker(center, {
                icon: L.divIcon({
                    className: "",
                    html: markerHTML,
                    iconSize: [40, 40],
                    iconAnchor: [20, 20]
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
        <div class="p-3 rounded bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border border-gray-100 dark:border-gray-600">
            <h4 class="font-bold text-red-600 dark:text-red-400 text-sm">${app.app_name}</h4>
            <p class="text-xs text-gray-500 dark:text-gray-400 uppercase mt-0.5">${app.app_type}</p>
            <p class="text-xs text-gray-700 dark:text-gray-300 mt-1 line-clamp-2">${app.ban_reason}</p>
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
