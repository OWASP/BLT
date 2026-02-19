// SelfErase Web App - Privacy Profile Manager
// All operations happen in the browser - no data is sent to servers

// State management
let currentProfile = null;
let brokers = [];

// Initialize the app
document.addEventListener('DOMContentLoaded', async () => {
    setupNavigation();
    setupEventListeners();
    await loadBrokers();
});

// Navigation
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (link.getAttribute('href').startsWith('#')) {
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            }
        });
    });
}

// Event Listeners
function setupEventListeners() {
    document.getElementById('fileUpload').addEventListener('change', handleFileUpload);
    document.getElementById('createProfile').addEventListener('click', createNewProfile);
    document.getElementById('downloadProfile').addEventListener('click', downloadProfile);
    document.getElementById('profileForm').addEventListener('submit', handleProfileSave);
    document.getElementById('encryptProfile').addEventListener('click', encryptAndDownload);
    
    // Modal
    const modal = document.getElementById('brokerModal');
    const closeBtn = document.querySelector('.close');
    closeBtn.onclick = () => modal.style.display = 'none';
    window.onclick = (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    };
}

// Load brokers data from GitHub
async function loadBrokers() {
    try {
        const response = await fetch('https://raw.githubusercontent.com/OWASP-BLT/SelfErase/main/data/brokers/brokers.json');
        brokers = await response.json();
        console.log(`Loaded ${brokers.length} brokers`);
    } catch (error) {
        console.error('Error loading brokers:', error);
        showAlert('Unable to load broker data. Using offline mode.', 'error');
        // Fallback to embedded data
        brokers = getFallbackBrokers();
    }
}

// Fallback brokers data
function getFallbackBrokers() {
    return [
        {
            id: "whitepages",
            name: "Whitepages",
            description: "Online directory providing contact information and background data",
            website: "https://www.whitepages.com",
            optOutUrl: "https://www.whitepages.com/suppression-requests",
            category: "People Search",
            dataTypes: ["name", "address", "phone", "age", "relatives"],
            optOutMethod: {
                type: "online_form",
                instructions: "Fill out the opt-out form on their suppression page",
                steps: [
                    "Visit the opt-out page",
                    "Search for your listing",
                    "Click 'Remove this listing'",
                    "Enter your email for confirmation",
                    "Verify via email link"
                ]
            },
            requiredFields: ["firstName", "lastName", "state"],
            estimatedResponseDays: 7,
            isActive: true
        },
        {
            id: "spokeo",
            name: "Spokeo",
            description: "People search engine aggregating public records and social media",
            website: "https://www.spokeo.com",
            optOutUrl: "https://www.spokeo.com/optout",
            category: "People Search",
            dataTypes: ["name", "address", "phone", "email", "social_media", "photos"],
            optOutMethod: {
                type: "online_form",
                instructions: "Submit opt-out request through their form",
                steps: [
                    "Go to opt-out page",
                    "Search for your profile",
                    "Select listings to remove",
                    "Enter email address",
                    "Confirm via email"
                ]
            },
            requiredFields: ["firstName", "lastName", "state", "email"],
            estimatedResponseDays: 5,
            isActive: true
        }
    ];
}

// File Upload Handler
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const content = e.target.result;
            
            // Check if file is encrypted
            if (file.name.endsWith('.enc')) {
                const password = prompt('Enter the password to decrypt your profile:');
                if (!password) {
                    showAlert('Decryption cancelled', 'info');
                    return;
                }
                
                try {
                    const decrypted = await decryptData(content, password);
                    currentProfile = JSON.parse(decrypted);
                    showAlert('Profile decrypted and loaded successfully!', 'success');
                } catch (error) {
                    showAlert('Failed to decrypt. Wrong password or corrupted file.', 'error');
                    return;
                }
            } else {
                currentProfile = JSON.parse(content);
                showAlert('Profile loaded successfully!', 'success');
            }
            
            updateProfileUI();
        } catch (error) {
            showAlert('Error reading file. Make sure it\'s a valid SelfErase profile.', 'error');
            console.error('File upload error:', error);
        }
    };
    reader.readAsText(file);
}

// Create New Profile
function createNewProfile() {
    currentProfile = {
        version: '1.0',
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
        personalInfo: {
            firstName: '',
            lastName: '',
            email: '',
            phone: '',
            address: '',
            city: '',
            state: '',
            age: null
        },
        brokerRequests: []
    };
    
    showAlert('New profile created. Fill in your information below.', 'success');
    updateProfileUI();
}

// Update UI with current profile
function updateProfileUI() {
    if (!currentProfile) return;

    // Update status
    const statusDiv = document.getElementById('profileStatus');
    statusDiv.innerHTML = `
        <p>✅ Profile loaded: ${currentProfile.personalInfo.firstName || 'New Profile'} ${currentProfile.personalInfo.lastName || ''}</p>
        <p class="info-text">Created: ${new Date(currentProfile.created).toLocaleDateString()}</p>
    `;

    // Enable download button
    document.getElementById('downloadProfile').disabled = false;

    // Show profile form
    document.getElementById('profileInfo').style.display = 'block';
    
    // Populate form
    const info = currentProfile.personalInfo;
    document.getElementById('firstName').value = info.firstName || '';
    document.getElementById('lastName').value = info.lastName || '';
    document.getElementById('email').value = info.email || '';
    document.getElementById('phone').value = info.phone || '';
    document.getElementById('address').value = info.address || '';
    document.getElementById('city').value = info.city || '';
    document.getElementById('state').value = info.state || '';
    document.getElementById('age').value = info.age || '';

    // Show brokers section
    document.getElementById('brokersSection').style.display = 'block';
    displayBrokers();
}

// Handle Profile Save
function handleProfileSave(event) {
    event.preventDefault();
    
    if (!currentProfile) {
        showAlert('No profile loaded', 'error');
        return;
    }

    // Update profile with form data
    currentProfile.personalInfo = {
        firstName: document.getElementById('firstName').value,
        lastName: document.getElementById('lastName').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        address: document.getElementById('address').value,
        city: document.getElementById('city').value,
        state: document.getElementById('state').value,
        age: document.getElementById('age').value ? parseInt(document.getElementById('age').value) : null
    };
    
    currentProfile.updated = new Date().toISOString();
    
    showAlert('Profile saved successfully!', 'success');
    updateProfileUI();
}

// Display Brokers
function displayBrokers() {
    const brokersList = document.getElementById('brokersList');
    brokersList.innerHTML = '';

    brokers.forEach(broker => {
        const brokerItem = document.createElement('div');
        brokerItem.className = 'broker-item';
        brokerItem.innerHTML = `
            <h4>${broker.name}</h4>
            <p>${broker.description}</p>
            <div class="broker-tags">
                <span class="broker-tag">${broker.category}</span>
                <span class="broker-tag">~${broker.estimatedResponseDays} days</span>
            </div>
        `;
        brokerItem.addEventListener('click', () => showBrokerDetails(broker));
        brokersList.appendChild(brokerItem);
    });
}

// Show Broker Details in Modal
function showBrokerDetails(broker) {
    const modal = document.getElementById('brokerModal');
    const detailsDiv = document.getElementById('brokerDetails');
    
    detailsDiv.innerHTML = `
        <h3>${broker.name}</h3>
        <div class="detail-section">
            <p>${broker.description}</p>
            <p><strong>Category:</strong> ${broker.category}</p>
            <p><strong>Website:</strong> <a href="${broker.website}" target="_blank">${broker.website}</a></p>
            <p><strong>Estimated Response Time:</strong> ${broker.estimatedResponseDays} days</p>
        </div>

        <div class="detail-section">
            <h4>📋 Data Types They May Have:</h4>
            <div class="broker-tags">
                ${broker.dataTypes.map(type => `<span class="broker-tag">${type}</span>`).join('')}
            </div>
        </div>

        <div class="detail-section">
            <h4>🚫 How to Opt Out:</h4>
            <p><strong>Method:</strong> ${broker.optOutMethod.type.replace('_', ' ')}</p>
            <p><strong>Instructions:</strong> ${broker.optOutMethod.instructions}</p>
        </div>

        <div class="detail-section">
            <h4>📝 Steps:</h4>
            <ol>
                ${broker.optOutMethod.steps.map(step => `<li>${step}</li>`).join('')}
            </ol>
        </div>

        <div class="detail-section">
            <h4>✅ Required Information:</h4>
            <ul>
                ${broker.requiredFields.map(field => `<li>${formatFieldName(field)}</li>`).join('')}
            </ul>
        </div>

        <div class="detail-section">
            <a href="${broker.optOutUrl}" target="_blank" class="btn btn-primary">🔗 Go to Opt-Out Page</a>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Format field names for display
function formatFieldName(field) {
    return field.replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

// Download Profile (unencrypted)
function downloadProfile() {
    if (!currentProfile) {
        showAlert('No profile to download', 'error');
        return;
    }

    // Show encryption option
    document.getElementById('passwordSection').style.display = 'block';
}

// Encrypt and Download
async function encryptAndDownload() {
    const password = document.getElementById('password').value;
    
    if (!password) {
        showAlert('Please enter a password', 'error');
        return;
    }

    if (password.length < 8) {
        showAlert('Password must be at least 8 characters', 'error');
        return;
    }

    try {
        const profileJson = JSON.stringify(currentProfile, null, 2);
        const encrypted = await encryptData(profileJson, password);
        
        downloadFile(encrypted, 'selferase-profile.enc', 'text/plain');
        showAlert('Profile encrypted and downloaded successfully!', 'success');
        
        // Clear password field
        document.getElementById('password').value = '';
        document.getElementById('passwordSection').style.display = 'none';
    } catch (error) {
        showAlert('Encryption failed: ' + error.message, 'error');
        console.error('Encryption error:', error);
    }
}

// Simple encryption using Web Crypto API
async function encryptData(data, password) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    
    // Derive key from password
    const passwordBuffer = encoder.encode(password);
    const passwordKey = await crypto.subtle.importKey(
        'raw',
        passwordBuffer,
        { name: 'PBKDF2' },
        false,
        ['deriveBits', 'deriveKey']
    );
    
    // Generate salt
    const salt = crypto.getRandomValues(new Uint8Array(16));
    
    // Derive encryption key
    const key = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: salt,
            iterations: 100000,
            hash: 'SHA-256'
        },
        passwordKey,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt']
    );
    
    // Generate IV
    const iv = crypto.getRandomValues(new Uint8Array(12));
    
    // Encrypt
    const encryptedBuffer = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        dataBuffer
    );
    
    // Combine salt + iv + encrypted data
    const result = new Uint8Array(salt.length + iv.length + encryptedBuffer.byteLength);
    result.set(salt, 0);
    result.set(iv, salt.length);
    result.set(new Uint8Array(encryptedBuffer), salt.length + iv.length);
    
    // Convert to base64
    return btoa(String.fromCharCode(...result));
}

// Decryption using Web Crypto API
async function decryptData(encryptedBase64, password) {
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    
    // Decode base64
    const encryptedData = Uint8Array.from(atob(encryptedBase64), c => c.charCodeAt(0));
    
    // Extract salt, iv, and encrypted content
    const salt = encryptedData.slice(0, 16);
    const iv = encryptedData.slice(16, 28);
    const data = encryptedData.slice(28);
    
    // Derive key from password
    const passwordBuffer = encoder.encode(password);
    const passwordKey = await crypto.subtle.importKey(
        'raw',
        passwordBuffer,
        { name: 'PBKDF2' },
        false,
        ['deriveBits', 'deriveKey']
    );
    
    // Derive decryption key
    const key = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: salt,
            iterations: 100000,
            hash: 'SHA-256'
        },
        passwordKey,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
    );
    
    // Decrypt
    const decryptedBuffer = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        data
    );
    
    return decoder.decode(decryptedBuffer);
}

// Download file helper
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Show alert messages
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.app-container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}
