// BLT-Vanish Web App — Privacy Profile Manager
// All operations happen in the browser. No data is ever sent to a server.

'use strict';

// ─── State ────────────────────────────────────────────────────────────────────
let currentProfile = null;
let brokers = [];

// ─── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    setupNavigation();
    setupEventListeners();
    await loadBrokers();
});

// ─── Navigation ───────────────────────────────────────────────────────────────
// Highlights the active nav-link as the user clicks through anchored sections.
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (link.getAttribute('href').startsWith('#')) {
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            }
        });
    });
}

// ─── Event Listeners ──────────────────────────────────────────────────────────
function setupEventListeners() {
    const fileUpload  = document.getElementById('fileUpload');
    const createBtn   = document.getElementById('createProfile');
    const downloadBtn = document.getElementById('downloadProfile');
    const profileForm = document.getElementById('profileForm');
    const encryptBtn  = document.getElementById('encryptProfile');

    if (fileUpload)  fileUpload.addEventListener('change', handleFileUpload);
    if (createBtn)   createBtn.addEventListener('click', createNewProfile);
    if (downloadBtn) downloadBtn.addEventListener('click', revealPasswordSection);
    if (profileForm) profileForm.addEventListener('submit', handleProfileSave);
    if (encryptBtn)  encryptBtn.addEventListener('click', encryptAndDownload);

    // Broker modal: close button, backdrop click, ESC key
    const modal    = document.getElementById('brokerModal');
    const closeBtn = document.querySelector('#brokerModal .close');

    if (closeBtn) closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });
    window.addEventListener('click', e => { if (modal && e.target === modal) modal.style.display = 'none'; });
    window.addEventListener('keydown', e => { if (e.key === 'Escape' && modal) modal.style.display = 'none'; });
}

// ─── Load Brokers ─────────────────────────────────────────────────────────────
async function loadBrokers() {
    try {
        // Root-relative path seamlessly bridges localhost and production domains via edge routing
        const res = await fetch('/api/brokers');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        brokers = await res.json();
        console.info('[BLT Vanish] Loaded ' + brokers.length + ' brokers');
    } catch (err) {
        console.warn('[BLT Vanish] Edge broker endpoint fetch failed; using built-in list:', err.message);
        brokers = getFallbackBrokers();
        showAlert('Unable to load latest broker data — using built-in offline list.', 'info');
    }
}

// Built-in fallback used when the network request fails.
function getFallbackBrokers() {
    return [
        {
            id: 'whitepages',
            name: 'Whitepages',
            description: 'Online directory providing contact information and background data.',
            website: 'https://www.whitepages.com',
            optOutUrl: 'https://www.whitepages.com/suppression-requests',
            category: 'People Search',
            dataTypes: ['name', 'address', 'phone', 'age', 'relatives'],
            optOutMethod: {
                type: 'online_form',
                instructions: 'Fill out the opt-out form on their suppression page.',
                steps: [
                    'Visit the opt-out page',
                    'Search for your listing',
                    "Click 'Remove this listing'",
                    'Enter your email for confirmation',
                    'Verify via email link',
                ],
            },
            requiredFields: ['firstName', 'lastName', 'state'],
            estimatedResponseDays: 7,
            isActive: true,
        },
        {
            id: 'spokeo',
            name: 'Spokeo',
            description: 'People search engine aggregating public records and social media.',
            website: 'https://www.spokeo.com',
            optOutUrl: 'https://www.spokeo.com/optout',
            category: 'People Search',
            dataTypes: ['name', 'address', 'phone', 'email', 'social_media', 'photos'],
            optOutMethod: {
                type: 'online_form',
                instructions: 'Submit opt-out request through their form.',
                steps: [
                    'Go to opt-out page',
                    'Search for your profile',
                    'Select listings to remove',
                    'Enter email address',
                    'Confirm via email',
                ],
            },
            requiredFields: ['firstName', 'lastName', 'state', 'email'],
            estimatedResponseDays: 5,
            isActive: true,
        },
        {
            id: 'intelius',
            name: 'Intelius',
            description: 'Background check and people search service.',
            website: 'https://www.intelius.com',
            optOutUrl: 'https://suppression.peopleconnect.us/login',
            category: 'Background Checks',
            dataTypes: ['name', 'address', 'phone', 'relatives', 'criminal_records'],
            optOutMethod: {
                type: 'account_required',
                instructions: 'Create a PeopleConnect suppression account to remove your records.',
                steps: [
                    'Go to the PeopleConnect suppression portal',
                    'Create a free suppression account',
                    'Verify your identity',
                    'Submit opt-out request',
                    'Await confirmation email',
                ],
            },
            requiredFields: ['firstName', 'lastName', 'state', 'email'],
            estimatedResponseDays: 30,
            isActive: true,
        },
        {
            id: 'beenverified',
            name: 'BeenVerified',
            description: 'Public records search for contact and background information.',
            website: 'https://www.beenverified.com',
            optOutUrl: 'https://www.beenverified.com/app/optout/search',
            category: 'Background Checks',
            dataTypes: ['name', 'address', 'phone', 'email', 'social_media'],
            optOutMethod: {
                type: 'online_form',
                instructions: 'Search for your record and submit the opt-out form.',
                steps: [
                    'Visit the opt-out page',
                    'Enter your name and state',
                    'Locate your record',
                    'Click Opt Out',
                    'Verify via email',
                ],
            },
            requiredFields: ['firstName', 'lastName', 'state', 'email'],
            estimatedResponseDays: 7,
            isActive: true,
        },
    ];
}

// ─── File Upload ──────────────────────────────────────────────────────────────
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const content = e.target.result;

            if (file.name.endsWith('.enc')) {
                const password = prompt('Enter the password to decrypt your profile:');
                if (!password) { showAlert('Decryption cancelled.', 'info'); return; }
                try {
                    const decrypted = await decryptData(content, password);
                    currentProfile  = JSON.parse(decrypted);
                    showAlert('Profile decrypted and loaded successfully!', 'success');
                } catch (_) {
                    showAlert('Failed to decrypt — wrong password or corrupted file.', 'error');
                    return;
                }
            } else {
                currentProfile = JSON.parse(content);
                showAlert('Profile loaded successfully!', 'success');
            }

            updateProfileUI();
        } catch (_) {
            showAlert("Error reading file. Make sure it's a valid BLT Vanish profile (.json or .enc).", 'error');
        }
    };
    reader.readAsText(file);
    event.target.value = ''; // allow re-selecting the same file
}

// ─── Create New Profile ───────────────────────────────────────────────────────
function createNewProfile() {
    currentProfile = {
        version: '1.0',
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
        personalInfo: {
            firstName: '', lastName: '', email: '', phone: '',
            address: '', city: '', state: '', age: null,
        },
        brokerRequests: [],
    };
    showAlert('New profile created. Fill in your information and hit Save Profile.', 'success');
    updateProfileUI();
}

// ─── Update UI from currentProfile ────────────────────────────────────────────
function updateProfileUI() {
    if (!currentProfile) return;

    // Status banner
    const statusDiv = document.getElementById('profileStatus');
    if (statusDiv) {
        var name = [currentProfile.personalInfo.firstName, currentProfile.personalInfo.lastName]
            .filter(Boolean).join(' ') || 'New Profile';
        statusDiv.innerHTML =
            '<p class="font-medium text-gray-800">\u2705 Profile loaded: ' + escapeHtml(name) + '</p>' +
            '<p class="info-text mt-0.5">Created: ' + new Date(currentProfile.created).toLocaleDateString() + '</p>';
    }

    // Enable download button: remove disabled state and Tailwind opacity/cursor classes
    var downloadBtn = document.getElementById('downloadProfile');
    if (downloadBtn) {
        downloadBtn.disabled = false;
        downloadBtn.classList.remove('cursor-not-allowed', 'opacity-50', 'text-gray-400');
        downloadBtn.classList.add('text-gray-700', 'hover:border-gray-300', 'hover:bg-gray-50', 'cursor-pointer');
    }

    // Show profile form card
    var profileInfo = document.getElementById('profileInfo');
    if (profileInfo) profileInfo.classList.remove('hidden');

    // Populate form
    var info = currentProfile.personalInfo;
    setValue('firstName', info.firstName);
    setValue('lastName',  info.lastName);
    setValue('email',     info.email);
    setValue('phone',     info.phone);
    setValue('address',   info.address);
    setValue('city',      info.city);
    setValue('state',     info.state);
    setValue('age',       info.age !== null ? info.age : '');

    // Show brokers section
    var brokersSection = document.getElementById('brokersSection');
    if (brokersSection) brokersSection.classList.remove('hidden');
    displayBrokers();
}

function setValue(id, value) {
    var el = document.getElementById(id);
    if (el) el.value = (value !== null && value !== undefined) ? value : '';
}

// ─── Save Profile ─────────────────────────────────────────────────────────────
function handleProfileSave(event) {
    event.preventDefault();
    if (!currentProfile) { showAlert('No profile loaded.', 'error'); return; }

    currentProfile.personalInfo = {
        firstName: getVal('firstName'),
        lastName:  getVal('lastName'),
        email:     getVal('email'),
        phone:     getVal('phone'),
        address:   getVal('address'),
        city:      getVal('city'),
        state:     getVal('state'),
        age:       getVal('age') ? parseInt(getVal('age'), 10) : null,
    };
    currentProfile.updated = new Date().toISOString();
    showAlert('Profile saved. Download it to keep a local backup.', 'success');
    updateProfileUI();
}

function getVal(id) {
    var el = document.getElementById(id);
    return el ? el.value.trim() : '';
}

// ─── Reveal Password / Download Section ───────────────────────────────────────
function revealPasswordSection() {
    if (!currentProfile) { showAlert('No profile to download.', 'error'); return; }
    var section = document.getElementById('passwordSection');
    if (section) section.classList.remove('hidden');
}

// ─── Encrypt & Download ───────────────────────────────────────────────────────
async function encryptAndDownload() {
    var passwordEl = document.getElementById('password');
    var password   = passwordEl ? passwordEl.value : '';

    if (!password) { showAlert('Please enter a password.', 'error'); return; }
    if (password.length < 8) { showAlert('Password must be at least 8 characters.', 'error'); return; }

    try {
        var profileJson = JSON.stringify(currentProfile, null, 2);
        var encrypted   = await encryptData(profileJson, password);
        downloadFile(encrypted, 'blt-vanish-profile.enc', 'text/plain');
        showAlert('Profile encrypted and downloaded successfully!', 'success');
        if (passwordEl) passwordEl.value = '';
        var section = document.getElementById('passwordSection');
        if (section) section.classList.add('hidden');
    } catch (err) {
        showAlert('Encryption failed: ' + err.message, 'error');
        console.error('[BLT Vanish] Encryption error:', err);
    }
}

// ─── Display Brokers ──────────────────────────────────────────────────────────
function displayBrokers() {
    var list = document.getElementById('brokersList');
    if (!list) return;
    list.innerHTML = '';

    brokers.forEach(function(broker) {
        var item = document.createElement('div');
        item.className = 'broker-item';
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
        item.setAttribute('aria-label', 'View opt-out details for ' + broker.name);
        item.innerHTML =
            '<h4>' + escapeHtml(broker.name) + '</h4>' +
            '<p>' + escapeHtml(broker.description) + '</p>' +
            '<div class="broker-tags">' +
                '<span class="broker-tag">' + escapeHtml(broker.category) + '</span>' +
                '<span class="broker-tag">~' + broker.estimatedResponseDays + ' days</span>' +
            '</div>';

        var open = function() { showBrokerDetails(broker); };
        item.addEventListener('click', open);
        item.addEventListener('keydown', function(e) { if (e.key === 'Enter' || e.key === ' ') open(); });
        list.appendChild(item);
    });
}

// ─── Broker Details Modal ─────────────────────────────────────────────────────
function showBrokerDetails(broker) {
    var modal      = document.getElementById('brokerModal');
    var detailsDiv = document.getElementById('brokerDetails');
    if (!modal || !detailsDiv) return;

    var dataTypeTags = broker.dataTypes
        .map(function(t) { return '<span class="broker-tag">' + escapeHtml(t) + '</span>'; })
        .join('');

    var requiredItems = broker.requiredFields
        .map(function(f) { return '<li>' + escapeHtml(formatFieldName(f)) + '</li>'; })
        .join('');

    var stepItems = broker.optOutMethod.steps
        .map(function(s) { return '<li>' + escapeHtml(s) + '</li>'; })
        .join('');

    detailsDiv.innerHTML =
        '<h3>' + escapeHtml(broker.name) + '</h3>' +

        '<div class="detail-section">' +
            '<p>' + escapeHtml(broker.description) + '</p>' +
            '<p><strong>Category:</strong> ' + escapeHtml(broker.category) + '</p>' +
            '<p><strong>Website:</strong> <a href="' + broker.website + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(broker.website) + '</a></p>' +
            '<p><strong>Estimated response time:</strong> ' + broker.estimatedResponseDays + ' days</p>' +
        '</div>' +

        '<div class="detail-section">' +
            '<h4>\uD83D\uDCCB Data types they may have</h4>' +
            '<div class="broker-tags">' + dataTypeTags + '</div>' +
        '</div>' +

        '<div class="detail-section">' +
            '<h4>\uD83D\uDEAB How to opt out</h4>' +
            '<p><strong>Method:</strong> ' + escapeHtml(broker.optOutMethod.type.replace(/_/g, ' ')) + '</p>' +
            '<p><strong>Instructions:</strong> ' + escapeHtml(broker.optOutMethod.instructions) + '</p>' +
        '</div>' +

        '<div class="detail-section">' +
            '<h4>\uD83D\uDCDD Steps</h4>' +
            '<ol>' + stepItems + '</ol>' +
        '</div>' +

        '<div class="detail-section">' +
            '<h4>\u2705 Required information</h4>' +
            '<ul>' + requiredItems + '</ul>' +
        '</div>' +

        '<div class="detail-section">' +
            '<a href="' + broker.optOutUrl + '" target="_blank" rel="noopener noreferrer" class="btn btn-primary">' +
                '\uD83D\uDD17 Go to opt-out page' +
            '</a>' +
        '</div>';

    modal.style.display = 'block';
}

// ─── Crypto: AES-256-GCM Encrypt ─────────────────────────────────────────────
async function encryptData(data, password) {
    var encoder    = new TextEncoder();
    var dataBuffer = encoder.encode(data);

    var passwordKey = await crypto.subtle.importKey(
        'raw', encoder.encode(password), { name: 'PBKDF2' }, false, ['deriveKey']
    );

    var salt = crypto.getRandomValues(new Uint8Array(16));
    var iv   = crypto.getRandomValues(new Uint8Array(12));

    var key = await crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' },
        passwordKey,
        { name: 'AES-GCM', length: 256 }, false, ['encrypt']
    );

    var encryptedBuffer = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, dataBuffer);

    // Layout: [16 bytes salt][12 bytes IV][ciphertext]
    var result = new Uint8Array(salt.length + iv.length + encryptedBuffer.byteLength);
    result.set(salt, 0);
    result.set(iv, salt.length);
    result.set(new Uint8Array(encryptedBuffer), salt.length + iv.length);

    return btoa(String.fromCharCode.apply(null, result));
}

// ─── Crypto: AES-256-GCM Decrypt ─────────────────────────────────────────────
async function decryptData(encryptedBase64, password) {
    var encoder = new TextEncoder();
    var decoder = new TextDecoder();

    var encryptedData = Uint8Array.from(atob(encryptedBase64), function(c) { return c.charCodeAt(0); });
    var salt          = encryptedData.slice(0, 16);
    var iv            = encryptedData.slice(16, 28);
    var data          = encryptedData.slice(28);

    var passwordKey = await crypto.subtle.importKey(
        'raw', encoder.encode(password), { name: 'PBKDF2' }, false, ['deriveKey']
    );

    var key = await crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' },
        passwordKey,
        { name: 'AES-GCM', length: 256 }, false, ['decrypt']
    );

    var decryptedBuffer = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: iv }, key, data);
    return decoder.decode(decryptedBuffer);
}

// ─── File Download Helper ─────────────────────────────────────────────────────
function downloadFile(content, filename, contentType) {
    var blob = new Blob([content], { type: contentType });
    var url  = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href     = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function() { URL.revokeObjectURL(url); }, 60000);
}

// ─── Alert Messages ───────────────────────────────────────────────────────────
// Targets #app-alerts . Falls back to first <main> element.
function showAlert(message, type) {
    var target = document.getElementById('app-alerts')
              || document.querySelector('.app-container')
              || document.querySelector('main');
    if (!target) return;

    var alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-' + type;
    alertDiv.setAttribute('role', type === 'error' ? 'alert' : 'status');
    alertDiv.innerHTML =
        '<span>' + escapeHtml(message) + '</span>' +
        '<button type="button" onclick="this.parentElement.remove()" ' +
            'style="float:right;background:none;border:none;cursor:pointer;font-size:1.1rem;line-height:1;opacity:.6;" ' +
            'aria-label="Dismiss">&times;</button>';

    target.insertBefore(alertDiv, target.firstChild);

    setTimeout(function() {
        if (alertDiv.parentElement) alertDiv.remove();
    }, 5000);
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function formatFieldName(field) {
    return field.replace(/([A-Z])/g, ' $1').replace(/^./, function(s) { return s.toUpperCase(); }).trim();
}

function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
