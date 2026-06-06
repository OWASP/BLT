// AI-Powered GitHub Sportscaster
// Sound Effects Manager using Web Audio API
class SoundEffects {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
        this.volume = parseFloat(localStorage.getItem('sound_volume') ?? '0.5');
        this.isUnlocked = false;
        this.isIOS = this.detectIOS();
        this.initAudioContext();
        this.setupVisibilityHandler();
    }

    /**
     * Detects if the current device is running iOS (Safari, DuckDuckGo, etc.)
     * @returns {boolean} True if running on iOS
     */
    detectIOS() {
        const userAgent = navigator.userAgent || navigator.vendor || '';
        // Check for iOS devices including iPad on iOS 13+
        return /iPad|iPhone|iPod/.test(userAgent) || 
               (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    initAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('Web Audio API not supported');
            this.enabled = false;
        }
    }

    /**
     * Sets up visibility change handler to re-unlock audio after tab switch on iOS
     */
    setupVisibilityHandler() {
        if (typeof document !== 'undefined') {
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible' && this.isIOS) {
                    // Audio may be suspended after tab switch on iOS
                    // Mark as needing unlock on next user interaction
                    this.isUnlocked = false;
                }
            });
        }
    }

    /**
     * Resumes the audio context and unlocks it for iOS
     * Must be called from a user gesture (click/tap) for iOS compatibility
     * @returns {Promise<void>}
     */
    async resumeContext() {
        if (!this.audioContext) return;
        
        if (this.audioContext.state === 'suspended') {
            try {
                await this.audioContext.resume();
            } catch (e) {
                console.warn('Failed to resume AudioContext:', e);
            }
        }
        
        // iOS/WebKit workaround: Play a silent buffer to unlock audio
        if (!this.isUnlocked) {
            this.playWarmUpBuffer();
            this.isUnlocked = true;
        }
    }

    /**
     * Plays a silent buffer to unlock/warm up the audio context on iOS
     * This trick ensures the audio context stays primed for future sounds
     */
    playWarmUpBuffer() {
        if (!this.audioContext) return;
        
        try {
            // Create a short silent buffer
            const buffer = this.audioContext.createBuffer(1, 1, 22050);
            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.audioContext.destination);
            source.start(0);
        } catch (e) {
            console.warn('Failed to play warm-up buffer:', e);
        }
    }

    /**
     * Toggles sound effects on/off and unlocks audio on iOS
     * Must be called from a user gesture (click/tap) for iOS compatibility
     * @returns {boolean} New enabled state
     */
    toggle() {
        this.enabled = !this.enabled;
        
        // Unlock audio context on user interaction (required for iOS)
        if (this.enabled) {
            this.resumeContext();
        }
        
        return this.enabled;
    }

    playNote(frequency, duration, type = 'sine', volume = 0.3) {
        if (!this.enabled || !this.audioContext) return;
        
        this.resumeContext();
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.type = type;
        oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
        
        const scaledVolume = volume * this.volume;
        gainNode.gain.setValueAtTime(scaledVolume, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }

    /**
     * Sets the master volume and persists it to localStorage
     * @param {number} value - Volume level between 0 and 1
     */
    setVolume(value) {
        this.volume = Math.max(0, Math.min(1, value));
        localStorage.setItem('sound_volume', String(this.volume));
    }

    playPushEvent() {
        this.playNote(392, 0.1, 'square', 0.2);
        setTimeout(() => this.playNote(523, 0.1, 'square', 0.2), 50);
        setTimeout(() => this.playNote(659, 0.15, 'square', 0.2), 100);
    }

    playPullRequestEvent() {
        this.playNote(523, 0.2, 'sine', 0.3);
        setTimeout(() => this.playNote(659, 0.3, 'sine', 0.3), 150);
    }

    playIssuesEvent() {
        this.playNote(880, 0.1, 'triangle', 0.25);
        setTimeout(() => this.playNote(880, 0.1, 'triangle', 0.25), 150);
    }

    playWatchEvent() {
        this.playNote(1047, 0.15, 'sine', 0.2);
    }

    playForkEvent() {
        this.playNote(440, 0.15, 'sawtooth', 0.15);
        setTimeout(() => {
            this.playNote(554, 0.2, 'sawtooth', 0.12);
            this.playNote(330, 0.2, 'sawtooth', 0.12);
        }, 100);
    }

    playCreateEvent() {
        this.playNote(523, 0.08, 'sine', 0.2);
        setTimeout(() => this.playNote(659, 0.08, 'sine', 0.2), 60);
        setTimeout(() => this.playNote(784, 0.08, 'sine', 0.2), 120);
        setTimeout(() => this.playNote(1047, 0.15, 'sine', 0.25), 180);
    }

    playDeleteEvent() {
        this.playNote(587, 0.1, 'triangle', 0.2);
        setTimeout(() => this.playNote(440, 0.1, 'triangle', 0.2), 80);
        setTimeout(() => this.playNote(330, 0.15, 'triangle', 0.2), 160);
    }

    playReleaseEvent() {
        this.playNote(523, 0.1, 'square', 0.2);
        setTimeout(() => this.playNote(659, 0.1, 'square', 0.2), 100);
        setTimeout(() => this.playNote(784, 0.1, 'square', 0.2), 200);
        setTimeout(() => this.playNote(1047, 0.3, 'square', 0.25), 300);
    }

    playCommentEvent() {
        this.playNote(698, 0.08, 'sine', 0.2);
        setTimeout(() => this.playNote(880, 0.12, 'sine', 0.2), 60);
    }

    playDefaultEvent() {
        this.playNote(600, 0.1, 'sine', 0.15);
    }

    playEventSound(eventType) {
        switch (eventType) {
            case 'PushEvent': this.playPushEvent(); break;
            case 'PullRequestEvent': this.playPullRequestEvent(); break;
            case 'IssuesEvent': this.playIssuesEvent(); break;
            case 'WatchEvent': this.playWatchEvent(); break;
            case 'ForkEvent': this.playForkEvent(); break;
            case 'CreateEvent': this.playCreateEvent(); break;
            case 'DeleteEvent': this.playDeleteEvent(); break;
            case 'ReleaseEvent': this.playReleaseEvent(); break;
            case 'IssueCommentEvent':
            case 'CommitCommentEvent':
            case 'PullRequestReviewCommentEvent':
                this.playCommentEvent(); break;
            default: this.playDefaultEvent();
        }
    }
}

// Text-to-Speech Manager
class TextToSpeech {
    // Delay in ms after cancel before speaking (Chrome bug workaround)
    static SPEAK_DELAY_MS = 50;
    // Maximum retries for loading voices on iOS
    static MAX_VOICE_RETRIES = 50;
    // Delay between voice loading retries in ms
    static VOICE_RETRY_DELAY_MS = 100;

    constructor() {
        this.enabled = false;
        this.synth = window.speechSynthesis;
        this.voice = null;
        this.rate = 1.1;
        this.pitch = 1.0;
        this.voicesLoaded = false;
        this.isUnlocked = false;
        this.pendingText = null;
        this.isIOS = this.detectIOS();
        this.initVoice();
    }

    /**
     * Detects if the current device is running iOS (Safari, DuckDuckGo, etc.)
     * @returns {boolean} True if running on iOS
     */
    detectIOS() {
        const userAgent = navigator.userAgent || navigator.vendor || '';
        // Check for iOS devices including iPad on iOS 13+
        return /iPad|iPhone|iPod/.test(userAgent) || 
               (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    initVoice() {
        if (!this.synth) {
            console.warn('Speech synthesis not supported');
            return;
        }
        
        const loadVoices = () => {
            const voices = this.synth.getVoices();
            if (voices.length > 0) {
                this.voice = voices.find(v => v.lang.startsWith('en') && v.name.includes('Google')) ||
                             voices.find(v => v.lang.startsWith('en')) ||
                             voices[0];
                this.voicesLoaded = true;
                
                // If we have pending text and TTS is enabled and unlocked, speak it now
                if (this.pendingText && this.enabled && this.isUnlocked) {
                    const text = this.pendingText;
                    this.pendingText = null;
                    this.speakInternal(text);
                }
            }
        };
        
        loadVoices();
        if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = loadVoices;
        }
        
        // iOS/WebKit workaround: voices might not load immediately
        // Poll for voices if not loaded yet
        if (!this.voicesLoaded && this.isIOS) {
            this.pollForVoices(loadVoices);
        }
    }

    /**
     * Polls for voices until they become available (iOS workaround)
     * @param {Function} loadVoices - Callback to load voices
     * @param {number} retries - Current retry count
     */
    pollForVoices(loadVoices, retries = 0) {
        if (this.voicesLoaded || retries >= TextToSpeech.MAX_VOICE_RETRIES) {
            return;
        }
        setTimeout(() => {
            loadVoices();
            if (!this.voicesLoaded) {
                this.pollForVoices(loadVoices, retries + 1);
            }
        }, TextToSpeech.VOICE_RETRY_DELAY_MS);
    }

    /**
     * Toggles TTS on/off and unlocks speech synthesis on iOS
     * Must be called from a user gesture (click/tap) for iOS compatibility
     * @returns {boolean} New enabled state
     */
    toggle() {
        this.enabled = !this.enabled;
        
        if (this.enabled && this.synth) {
            // iOS/WebKit workaround: "unlock" speech synthesis on first user interaction
            // Speaking an empty utterance initializes the audio context
            if (!this.isUnlocked) {
                this.unlockSynthesis();
            }
        } else if (!this.enabled && this.synth) {
            this.synth.cancel();
            this.pendingText = null;
        }
        return this.enabled;
    }

    /**
     * Unlocks speech synthesis by speaking a silent utterance
     * Required on iOS to enable TTS from user gesture
     */
    unlockSynthesis() {
        if (!this.synth || this.isUnlocked) return;
        
        try {
            // Cancel any pending speech
            this.synth.cancel();
            
            // Create a silent utterance to unlock the audio context
            const silentUtterance = new SpeechSynthesisUtterance('');
            silentUtterance.volume = 0;
            silentUtterance.rate = 1;
            
            silentUtterance.onend = () => {
                this.isUnlocked = true;
            };
            
            silentUtterance.onerror = () => {
                // Even on error, consider it unlocked - we tried from user gesture
                this.isUnlocked = true;
            };
            
            this.synth.speak(silentUtterance);
            this.isUnlocked = true; // Optimistically set to unlocked
        } catch (e) {
            console.warn('Failed to unlock speech synthesis:', e);
            this.isUnlocked = true; // Don't block further attempts
        }
    }

    /**
     * Resumes speech synthesis if it's in a paused state
     * This fixes issues in some browsers where synthesis gets stuck
     */
    resumeSynthesis() {
        if (this.synth && this.synth.paused) {
            this.synth.resume();
        }
    }

    /**
     * Internal method to actually speak the text
     * @param {string} text - Text to speak
     */
    speakInternal(text) {
        if (!this.synth || !text) return;
        
        // Cancel any pending speech
        this.synth.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        if (this.voice) utterance.voice = this.voice;
        utterance.rate = this.rate;
        utterance.pitch = this.pitch;
        
        // Chrome bug workaround: synthesis can get stuck if not resumed
        // Adding a small delay after cancel helps ensure the queue is clear
        setTimeout(() => {
            if (this.synth) {
                this.resumeSynthesis();
                this.synth.speak(utterance);
            }
        }, TextToSpeech.SPEAK_DELAY_MS);
    }

    speak(text) {
        if (!this.enabled || !this.synth || !text) return;
        
        // On iOS, if voices aren't loaded yet, queue the text for later
        if (!this.voicesLoaded && this.isIOS) {
            this.pendingText = text;
            return;
        }
        
        this.speakInternal(text);
    }
}

// AI Commentary Generator
class AICommentary {
    // Maximum length for error messages displayed in the UI
    static MAX_ERROR_DISPLAY_LENGTH = 30;
    
    constructor() {
        this.enabled = false;
        this.apiUrl = localStorage.getItem('ai_api_url') || 'https://api.openai.com/v1/chat/completions';
        this.apiKey = localStorage.getItem('ai_api_key') || '';
        this.model = localStorage.getItem('ai_model') || 'gpt-4o-mini';
        this.lastCommentary = '';
        this.isGenerating = false;
    }

    toggle() {
        this.enabled = !this.enabled;
        const commentarySection = document.getElementById('ai-commentary');
        if (commentarySection) {
            commentarySection.style.display = this.enabled ? 'block' : 'none';
        }
        return this.enabled;
    }

    updateConfig(apiUrl, apiKey, model) {
        // Sanitize inputs before storing
        this.apiUrl = (apiUrl || '').trim();
        this.apiKey = (apiKey || '').trim();
        this.model = (model || 'gpt-4o-mini').trim();
        
        // Only store in localStorage if values are provided
        if (this.apiUrl) localStorage.setItem('ai_api_url', this.apiUrl);
        if (this.apiKey) localStorage.setItem('ai_api_key', this.apiKey);
        if (this.model) localStorage.setItem('ai_model', this.model);
    }

    /**
     * Updates the connection status indicator in the UI
     * @param {string} status - The status to display: 'checking', 'connected', 'error', or 'not-configured'
     * @param {string} message - The message to display
     */
    updateConnectionStatus(status, message) {
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        
        if (!indicator || !text) return;
        
        // Remove all status classes
        indicator.classList.remove('checking', 'connected', 'error', 'ready');
        text.classList.remove('checking', 'connected', 'error', 'ready');
        
        // Add the new status class (not-configured uses default gray styling)
        if (status !== 'not-configured') {
            indicator.classList.add(status);
            text.classList.add(status);
        }
        
        text.textContent = message;
    }

    /**
     * Tests the connection to the OpenAI API
     * @returns {Promise<{success: boolean, message: string}>}
     */
    async testConnection() {
        const testBtn = document.getElementById('test-connection-btn');
        
        // Update UI to show checking status
        this.updateConnectionStatus('checking', 'Checking connection...');
        if (testBtn) testBtn.disabled = true;
        
        // Get current values from inputs (not stored values)
        const apiUrlEl = document.getElementById('ai-api-url');
        const apiKeyEl = document.getElementById('ai-api-key');
        const modelEl = document.getElementById('ai-model');
        
        const apiUrl = apiUrlEl ? apiUrlEl.value.trim() : '';
        const apiKey = apiKeyEl ? apiKeyEl.value.trim() : '';
        const model = modelEl ? modelEl.value.trim() : 'gpt-4o-mini';
        
        // Validate inputs
        if (!apiUrl || !apiKey) {
            this.updateConnectionStatus('not-configured', 'Not configured');
            if (testBtn) testBtn.disabled = false;
            return { success: false, message: 'API URL and Key are required' };
        }
        
        if (!this.isValidApiUrl(apiUrl)) {
            this.updateConnectionStatus('error', 'Invalid API URL');
            if (testBtn) testBtn.disabled = false;
            return { success: false, message: 'Invalid API URL format' };
        }
        
        if (!this.isValidApiKey(apiKey)) {
            this.updateConnectionStatus('error', 'Invalid API Key format');
            if (testBtn) testBtn.disabled = false;
            return { success: false, message: 'Invalid API key format' };
        }
        
        try {
            const response = await this.fetchWithTimeout(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify({
                    model: model,
                    messages: [
                        { role: 'user', content: 'Say "OK" to confirm connection.' }
                    ],
                    max_tokens: 5
                })
            }, 15000); // 15 second timeout for connection test
            
            if (response.ok) {
                this.updateConnectionStatus('connected', 'Connected ✓');
                if (testBtn) testBtn.disabled = false;
                return { success: true, message: 'Connection successful' };
            } else {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.error?.message || `HTTP ${response.status}`;
                this.updateConnectionStatus('error', `Error: ${errorMessage.substring(0, AICommentary.MAX_ERROR_DISPLAY_LENGTH)}`);
                if (testBtn) testBtn.disabled = false;
                return { success: false, message: errorMessage };
            }
        } catch (error) {
            let errorMessage = 'Connection failed';
            if (error.name === 'AbortError') {
                errorMessage = 'Connection timeout';
            } else if (error.message) {
                errorMessage = error.message.substring(0, AICommentary.MAX_ERROR_DISPLAY_LENGTH);
            }
            this.updateConnectionStatus('error', errorMessage);
            if (testBtn) testBtn.disabled = false;
            return { success: false, message: error.message };
        }
    }

    /**
     * Initializes the connection status based on stored configuration
     */
    initConnectionStatus() {
        if (this.apiUrl && this.apiKey) {
            if (this.isValidApiUrl(this.apiUrl) && this.isValidApiKey(this.apiKey)) {
                this.updateConnectionStatus('ready', 'Ready to test');
            } else {
                this.updateConnectionStatus('error', 'Invalid configuration');
            }
        } else {
            this.updateConnectionStatus('not-configured', 'Not configured');
        }
    }

    getPrompt(event, leaderboard) {
        const topRepos = leaderboard.slice(0, 5).map((r, i) => 
            `${i + 1}. ${r.name} (${r.activityScore} points, ${r.totalEvents} events)`
        ).join('\n');

        return `You are an enthusiastic sports announcer providing live play-by-play commentary for GitHub activity. 
Keep your response to 1-2 exciting sentences, using sports metaphors and energy.

Latest Event:
- Repository: ${event.repoName}
- Event Type: ${event.eventType}
- Actor: ${event.actor}
- Time: Just now

Current Leaderboard:
${topRepos}

Generate exciting sports-style commentary for this GitHub event. Be energetic, use sports metaphors, and make it fun!`;
    }

    /**
     * Validates the API key format
     * @param {string} key - The API key to validate
     * @returns {boolean} - True if the key appears valid
     */
    isValidApiKey(key) {
        if (!key || typeof key !== 'string') return false;
        const trimmed = key.trim();
        // Minimum length check for security
        if (trimmed.length < 10 || trimmed.length > 500) return false;
        // Allow alphanumeric, dashes, underscores, dots, and slashes (common in API keys)
        // Also ensure no control characters or obvious injection attempts
        const validPattern = /^[a-zA-Z0-9_\-./]+$/;
        return validPattern.test(trimmed);
    }

    /**
     * Validates the API URL format
     * @param {string} url - The URL to validate
     * @returns {boolean} - True if the URL appears valid
     */
    isValidApiUrl(url) {
        if (!url || typeof url !== 'string') return false;
        try {
            const parsed = new URL(url);
            return parsed.protocol === 'https:' || parsed.protocol === 'http:';
        } catch {
            return false;
        }
    }

    /**
     * Creates a fetch request with timeout
     * @param {string} url - The URL to fetch
     * @param {Object} options - Fetch options
     * @param {number} timeout - Timeout in milliseconds
     * @returns {Promise<Response>}
     */
    async fetchWithTimeout(url, options, timeout = 10000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            return response;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    async generateCommentary(event, leaderboard) {
        // Check if AI commentary is enabled
        if (!this.enabled) {
            return this.generateFallbackCommentary(event, leaderboard);
        }

        // Check if already generating (prevent concurrent requests)
        if (this.isGenerating) {
            return this.generateFallbackCommentary(event, leaderboard);
        }

        // Validate API configuration
        if (!this.isValidApiUrl(this.apiUrl)) {
            console.warn('AI Commentary: Invalid or missing API URL');
            return this.generateFallbackCommentary(event, leaderboard);
        }

        if (!this.isValidApiKey(this.apiKey)) {
            console.warn('AI Commentary: Invalid or missing API key');
            return this.generateFallbackCommentary(event, leaderboard);
        }

        this.isGenerating = true;
        this.showTypingIndicator();

        try {
            const response = await this.fetchWithTimeout(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey.trim()}`
                },
                body: JSON.stringify({
                    model: this.model,
                    messages: [
                        { role: 'system', content: 'You are an enthusiastic sports announcer for GitHub activity.' },
                        { role: 'user', content: this.getPrompt(event, leaderboard) }
                    ],
                    max_tokens: 100,
                    temperature: 0.8
                })
            }, 10000); // 10 second timeout

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            const commentary = data.choices?.[0]?.message?.content || this.generateFallbackCommentary(event, leaderboard);
            
            this.lastCommentary = commentary;
            this.displayCommentary(commentary);
            return commentary;

        } catch (error) {
            console.warn('AI Commentary error:', error);
            const fallback = this.generateFallbackCommentary(event, leaderboard);
            this.displayCommentary(fallback);
            return fallback;
        } finally {
            this.isGenerating = false;
        }
    }

    generateFallbackCommentary(event, leaderboard) {
        const templates = {
            PushEvent: [
                `🚀 And ${event.actor} pushes the code forward for ${event.repoName}! The crowd goes wild!`,
                `💪 What a play! ${event.actor} drives it home with a push to ${event.repoName}!`,
                `⚡ ${event.repoName} is on fire! ${event.actor} just landed another push!`
            ],
            PullRequestEvent: [
                `🔀 Breaking news! ${event.actor} opens up the field with a PR for ${event.repoName}!`,
                `🎯 ${event.actor} goes for the merge! ${event.repoName} in the spotlight!`,
                `🤝 Teamwork makes the dream work! ${event.actor} submits a PR to ${event.repoName}!`
            ],
            WatchEvent: [
                `⭐ The fans are loving it! ${event.repoName} gains another star from ${event.actor}!`,
                `🌟 Star power! ${event.actor} shows love for ${event.repoName}!`,
                `✨ ${event.repoName} is trending! ${event.actor} drops a star!`
            ],
            ForkEvent: [
                `🍴 ${event.actor} forks ${event.repoName}! A new challenger approaches!`,
                `🔱 Split play! ${event.actor} branches off from ${event.repoName}!`,
                `📋 ${event.repoName} gets copied! ${event.actor} enters the game!`
            ],
            IssuesEvent: [
                `🐛 Bug spotted! ${event.actor} raises an issue on ${event.repoName}!`,
                `📋 ${event.actor} files a ticket for ${event.repoName}! The debug begins!`,
                `🔍 ${event.repoName} gets a new issue from ${event.actor}!`
            ],
            ReleaseEvent: [
                `🎉 TOUCHDOWN! ${event.repoName} just dropped a new release!`,
                `🚀 It's official! ${event.repoName} ships a new version! What a moment!`,
                `🏆 Release day for ${event.repoName}! The crowd is on their feet!`
            ],
            CreateEvent: [
                `✨ Something new is born! ${event.actor} creates in ${event.repoName}!`,
                `🎨 Fresh start! ${event.actor} kicks things off in ${event.repoName}!`,
                `🌱 Growth alert! ${event.repoName} sees new creation from ${event.actor}!`
            ]
        };

        const eventTemplates = templates[event.eventType] || [
            `🎬 Action in ${event.repoName}! ${event.actor} makes a move!`,
            `📢 ${event.repoName} stays active! ${event.actor} in the game!`,
            `⚡ Activity detected! ${event.actor} works on ${event.repoName}!`
        ];

        return eventTemplates[Math.floor(Math.random() * eventTemplates.length)];
    }

    showTypingIndicator() {
        const textEl = document.getElementById('ai-commentary-text');
        if (textEl) {
            textEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
            textEl.classList.add('generating');
        }
    }

    displayCommentary(text) {
        const textEl = document.getElementById('ai-commentary-text');
        if (textEl) {
            textEl.textContent = text;
            textEl.classList.remove('generating');
        }
    }
}

// Main Sportscaster Class
class GitHubSportscaster {
    static EVENT_WEIGHTS = {
        PushEvent: 3,
        PullRequestEvent: 5,
        IssuesEvent: 2,
        ReleaseEvent: 10,
        ForkEvent: 4,
        WatchEvent: 1,
        CreateEvent: 2,
        DeleteEvent: 1,
        IssueCommentEvent: 1,
        CommitCommentEvent: 1
    };

    static CHANNEL_FILTERS = {
        all: () => true,
        hot: (e) => ['PushEvent', 'PullRequestEvent', 'ReleaseEvent'].includes(e.eventType),
        code: (e) => ['PushEvent', 'PullRequestEvent', 'CreateEvent', 'DeleteEvent'].includes(e.eventType),
        social: (e) => ['WatchEvent', 'ForkEvent', 'IssuesEvent', 'IssueCommentEvent'].includes(e.eventType)
    };

    static PRESET_CHANNELS = {
        trending: { orgs: [], repos: [], topics: ['javascript', 'python', 'rust'] },
        web: { orgs: ['facebook', 'vercel', 'vuejs'], repos: [], topics: [] },
        ai: { orgs: ['openai', 'huggingface', 'tensorflow'], repos: [], topics: [] },
        devops: { orgs: ['kubernetes', 'docker', 'hashicorp'], repos: [], topics: [] }
    };

    static RATE_LIMIT_WARNING = 30;
    static RATE_LIMIT_DANGER = 10;
    static THROTTLE_INTERVAL = 30000;

    constructor() {
        this.events = [];
        this.repositories = new Map();
        this.maxEvents = 50;
        this.totalEvents = 0;
        this.baseUpdateInterval = 10000;
        this.updateInterval = 10000;
        this.demoMode = false;
        this.failedAttempts = 0;
        this.seenEventIds = new Set();
        this.latestEvent = null;
        this.previousRanks = new Map();
        this.soundEffects = new SoundEffects();
        this.tts = new TextToSpeech();
        this.aiCommentary = new AICommentary();
        this.etag = null;
        this.lastModified = null;
        this.rateLimit = { remaining: null, limit: null, reset: null };
        this.countdownInterval = null;
        this.fetchInterval = null;
        this.secondsUntilRefresh = 0;
        this.autoProtect = true;
        this.isThrottled = false;
        this.currentChannel = 'all';
        this.eventTypeFilter = 'all';
        this.scopeType = 'global';
        this.scopeValue = '';
        
        this.loadConfig();
        this.init();
    }

    loadConfig() {
        this.scopeType = localStorage.getItem('scope_type') || 'global';
        this.scopeValue = localStorage.getItem('scope_value') || '';
        this.eventTypeFilter = localStorage.getItem('event_type_filter') || 'all';
        this.githubToken = localStorage.getItem('github_token') || '';
        
        const scopeTypeEl = document.getElementById('scope-type');
        const scopeValueEl = document.getElementById('scope-value');
        const scopeValueGroup = document.getElementById('scope-value-group');
        
        if (scopeTypeEl) scopeTypeEl.value = this.scopeType;
        if (scopeValueEl) scopeValueEl.value = this.scopeValue;
        if (scopeValueGroup) {
            scopeValueGroup.style.display = this.scopeType !== 'global' ? 'block' : 'none';
        }
    }

    saveConfig() {
        localStorage.setItem('scope_type', this.scopeType);
        localStorage.setItem('scope_value', this.scopeValue);
        localStorage.setItem('event_type_filter', this.eventTypeFilter);
        if (this.githubToken) {
            localStorage.setItem('github_token', this.githubToken);
        } else {
            localStorage.removeItem('github_token');
        }
    }

    async init() {
        this.setupGlobalAudioUnlock();
        this.setupSoundToggle();
        this.setupTTSToggle();
        this.setupAIToggle();
        this.setupConfigPanel();
        this.setupChannelFilters();
        this.setupSpeedControl();
        this.setupVolumeControl();
        this.startCountdown();
        await this.fetchActivity();
        this.startFetchInterval();
    }

    /**
     * Sets up a global handler to unlock audio on first user interaction
     * Required for iOS (Safari, DuckDuckGo, etc.) to allow audio playback
     */
    setupGlobalAudioUnlock() {
        // Listen for various user interaction events to unlock audio
        const events = ['touchstart', 'touchend', 'mousedown', 'keydown'];
        
        const unlockHandler = () => {
            // Unlock sound effects on first interaction
            this.soundEffects.resumeContext();
            // Note: TTS is unlocked when toggled, not here
        };
        
        events.forEach(event => {
            document.addEventListener(event, unlockHandler, { once: true, passive: true });
        });
    }

    setupSoundToggle() {
        const toggleBtn = document.getElementById('sound-toggle');
        if (!toggleBtn) return;

        const renderSoundIcon = (enabled) => {
            const iconEl = document.getElementById('sound-icon');
            if (iconEl) {
                iconEl.className = enabled
                    ? 'fa-solid fa-volume-high'
                    : 'fa-solid fa-volume-xmark';
            }
            toggleBtn.setAttribute('aria-label', enabled ? 'Disable sound effects' : 'Enable sound effects');
            toggleBtn.classList.toggle('muted', !enabled);
        };

        renderSoundIcon(this.soundEffects.enabled);

        toggleBtn.addEventListener('click', () => {
            const enabled = this.soundEffects.toggle();
            renderSoundIcon(enabled);
        });
    }

    setupTTSToggle() {
        const toggleBtn = document.getElementById('tts-toggle');
        if (!toggleBtn) return;
        toggleBtn.addEventListener('click', () => {
            const enabled = this.tts.toggle();
            toggleBtn.setAttribute('aria-pressed', String(enabled));
            toggleBtn.classList.toggle('active', enabled);
            toggleBtn.classList.toggle('disabled', !enabled);
        });
    }

    setupAIToggle() {
        const toggleBtn = document.getElementById('ai-toggle');
        if (!toggleBtn) return;
        toggleBtn.addEventListener('click', () => {
            const enabled = this.aiCommentary.toggle();
            toggleBtn.setAttribute('aria-pressed', String(enabled));
            toggleBtn.classList.toggle('active', enabled);
        });
    }

    setupConfigPanel() {
        const configToggle = document.getElementById('config-toggle');
        const configPanel = document.getElementById('config-panel');
        const applyBtn = document.getElementById('apply-config');
        const resetBtn = document.getElementById('reset-config');
        const scopeType = document.getElementById('scope-type');
        const scopeValueGroup = document.getElementById('scope-value-group');

        if (!configToggle || !configPanel) return;

        configToggle.addEventListener('click', () => {
            configPanel.classList.toggle('visible');
            configToggle.classList.toggle('active');
        });

        if (scopeType) {
            scopeType.addEventListener('change', () => {
                if (scopeValueGroup) {
                    scopeValueGroup.style.display = scopeType.value !== 'global' ? 'block' : 'none';
                }
            });
        }

        document.querySelectorAll('#event-type-filters .preset-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('#event-type-filters .preset-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this.eventTypeFilter = chip.dataset.type;
            });
        });

        document.querySelectorAll('.preset-chips [data-preset]').forEach(chip => {
            chip.addEventListener('click', () => {
                const preset = chip.dataset.preset;
                const presetData = GitHubSportscaster.PRESET_CHANNELS[preset];
                if (presetData && presetData.orgs.length > 0 && scopeType && scopeValueGroup) {
                    scopeType.value = 'org';
                    scopeValueGroup.style.display = 'block';
                    const scopeValueEl = document.getElementById('scope-value');
                    if (scopeValueEl) scopeValueEl.value = presetData.orgs[0];
                }
            });
        });

        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                this.scopeType = scopeType ? scopeType.value : 'global';
                const scopeValueEl = document.getElementById('scope-value');
                this.scopeValue = scopeValueEl ? scopeValueEl.value : '';
                
                const githubTokenEl = document.getElementById('github-token');
                if (githubTokenEl) {
                    const tokenVal = githubTokenEl.value.trim();
                    // Accept blank (no token) or common GitHub token formats: ghp_, gho_, github_pat_, or 40-char classic tokens
                    if (tokenVal === '' || /^(ghp_|gho_|github_pat_)[a-zA-Z0-9_]+$/.test(tokenVal) || /^[a-fA-F0-9]{40}$/.test(tokenVal)) {
                        this.githubToken = tokenVal;
                    } else {
                        this.githubToken = '';
                        githubTokenEl.value = '';
                    }
                }
                
                const apiUrlEl = document.getElementById('ai-api-url');
                const apiKeyEl = document.getElementById('ai-api-key');
                const modelEl = document.getElementById('ai-model');
                
                if (apiUrlEl && apiKeyEl && modelEl) {
                    this.aiCommentary.updateConfig(apiUrlEl.value, apiKeyEl.value, modelEl.value);
                }
                
                this.saveConfig();
                this.resetData();
                this.fetchActivity();
                configPanel.classList.remove('visible');
                if (configToggle) configToggle.classList.remove('active');
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.scopeType = 'global';
                this.scopeValue = '';
                this.eventTypeFilter = 'all';
                this.githubToken = '';
                if (scopeType) scopeType.value = 'global';
                const scopeValueEl = document.getElementById('scope-value');
                if (scopeValueEl) scopeValueEl.value = '';
                if (scopeValueGroup) scopeValueGroup.style.display = 'none';
                const githubTokenEl = document.getElementById('github-token');
                if (githubTokenEl) githubTokenEl.value = '';
                document.querySelectorAll('#event-type-filters .preset-chip').forEach(c => c.classList.remove('active'));
                const allChip = document.querySelector('#event-type-filters .preset-chip[data-type="all"]');
                if (allChip) allChip.classList.add('active');
                this.saveConfig();
                this.resetData();
                this.fetchActivity();
            });
        }
        
        // Test connection button handler
        const testConnectionBtn = document.getElementById('test-connection-btn');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', () => {
                this.aiCommentary.testConnection();
            });
        }
        
        const apiUrlEl = document.getElementById('ai-api-url');
        const apiKeyEl = document.getElementById('ai-api-key');
        const modelEl = document.getElementById('ai-model');
        const githubTokenEl = document.getElementById('github-token');
        if (apiUrlEl) apiUrlEl.value = this.aiCommentary.apiUrl;
        if (apiKeyEl) apiKeyEl.value = this.aiCommentary.apiKey;
        if (modelEl) modelEl.value = this.aiCommentary.model;
        if (githubTokenEl) githubTokenEl.value = this.githubToken;
        
        // Initialize connection status display
        this.aiCommentary.initConnectionStatus();
    }

    setupChannelFilters() {
        document.querySelectorAll('.channel-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.channel-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                this.currentChannel = pill.dataset.channel;
                this.render();
            });
        });
    }

    setupSpeedControl() {
        const slider = document.getElementById('speed-slider');
        const valueDisplay = document.getElementById('speed-value');
        const autoProtectCheckbox = document.getElementById('auto-protect');

        if (slider) {
            slider.addEventListener('input', () => {
                const seconds = parseInt(slider.value, 10);
                if (valueDisplay) valueDisplay.textContent = `${seconds}s`;
                this.baseUpdateInterval = seconds * 1000;
                
                if (!this.isThrottled) {
                    this.updateInterval = this.baseUpdateInterval;
                    this.startFetchInterval();
                    this.startCountdown();
                }
            });
        }

        if (autoProtectCheckbox) {
            autoProtectCheckbox.addEventListener('change', () => {
                this.autoProtect = autoProtectCheckbox.checked;
                if (!this.autoProtect) {
                    this.isThrottled = false;
                    const rateProtectedEl = document.getElementById('rate-protected');
                    if (rateProtectedEl) rateProtectedEl.style.display = 'none';
                    this.updateInterval = this.baseUpdateInterval;
                    this.startFetchInterval();
                    this.startCountdown();
                }
            });
        }
    }

    setupVolumeControl() {
        const slider = document.getElementById('volume-slider');
        const display = document.getElementById('volume-display');
        
        if (!slider) return;
        
        // Sync slider to current volume
        const pct = Math.round(this.soundEffects.volume * 100);
        slider.value = pct;
        if (display) display.textContent = `${pct}%`;
        
        slider.addEventListener('input', () => {
            const val = parseInt(slider.value, 10) / 100;
            this.soundEffects.setVolume(val);
            if (display) display.textContent = `${slider.value}%`;
        });
    }

    resetData() {
        this.events = [];
        this.repositories.clear();
        this.seenEventIds.clear();
        this.totalEvents = 0;
        this.latestEvent = null;
        this.previousRanks.clear();
        this.etag = null;
        this.lastModified = null;
    }

    startFetchInterval() {
        if (this.fetchInterval) clearInterval(this.fetchInterval);
        this.fetchInterval = setInterval(() => this.fetchActivity(), this.updateInterval);
    }

    startCountdown() {
        this.secondsUntilRefresh = this.updateInterval / 1000;
        this.updateCountdownDisplay();
        
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        
        this.countdownInterval = setInterval(() => {
            this.secondsUntilRefresh--;
            if (this.secondsUntilRefresh < 0) this.secondsUntilRefresh = 0;
            this.updateCountdownDisplay();
        }, 1000);
    }

    updateCountdownDisplay() {
        const countdownEl = document.getElementById('countdown');
        const progressBar = document.getElementById('progress-bar');
        
        if (countdownEl) countdownEl.textContent = this.secondsUntilRefresh;
        if (progressBar) {
            const progress = (this.secondsUntilRefresh / (this.updateInterval / 1000)) * 100;
            progressBar.style.width = `${progress}%`;
            progressBar.classList.remove('loading');
        }
    }

    updateRateLimitDisplay() {
        const remainingEl = document.getElementById('rate-remaining');
        const limitEl = document.getElementById('rate-limit');
        const resetEl = document.getElementById('rate-reset');
        
        if (this.rateLimit.remaining !== null && remainingEl && limitEl) {
            remainingEl.textContent = this.rateLimit.remaining;
            limitEl.textContent = this.rateLimit.limit;
            
            remainingEl.classList.remove('warning', 'danger');
            if (this.rateLimit.remaining <= GitHubSportscaster.RATE_LIMIT_DANGER) {
                remainingEl.classList.add('danger');
            } else if (this.rateLimit.remaining <= GitHubSportscaster.RATE_LIMIT_WARNING) {
                remainingEl.classList.add('warning');
            }

            this.checkRateLimitProtection();
        }
        
        if (this.rateLimit.reset !== null && resetEl) {
            const now = Math.floor(Date.now() / 1000);
            const secondsUntilReset = Math.max(0, this.rateLimit.reset - now);
            const minutes = Math.floor(secondsUntilReset / 60);
            const seconds = secondsUntilReset % 60;
            resetEl.textContent = `${minutes}m ${seconds}s`;
        }
    }

    checkRateLimitProtection() {
        if (!this.autoProtect || this.rateLimit.remaining === null) return;

        const rateProtectedEl = document.getElementById('rate-protected');

        if (this.rateLimit.remaining <= GitHubSportscaster.RATE_LIMIT_DANGER) {
            if (!this.isThrottled) {
                this.isThrottled = true;
                this.updateInterval = GitHubSportscaster.THROTTLE_INTERVAL;
                if (rateProtectedEl) {
                    rateProtectedEl.style.display = 'inline';
                    rateProtectedEl.textContent = '⚠️ Throttled (low rate limit)';
                }
                this.startFetchInterval();
                this.startCountdown();
            }
        } else if (this.isThrottled && this.rateLimit.remaining > GitHubSportscaster.RATE_LIMIT_WARNING) {
            this.isThrottled = false;
            this.updateInterval = this.baseUpdateInterval;
            if (rateProtectedEl) rateProtectedEl.style.display = 'none';
            this.startFetchInterval();
            this.startCountdown();
        }
    }

    getApiUrl() {
        let url = 'https://api.github.com';
        
        switch (this.scopeType) {
            case 'org':
                if (this.scopeValue) url += `/orgs/${encodeURIComponent(this.scopeValue)}/events`;
                else url += '/events';
                break;
            case 'repo':
                if (this.scopeValue && this.scopeValue.includes('/')) {
                    url += `/repos/${this.scopeValue}/events`;
                } else url += '/events';
                break;
            case 'user':
                if (this.scopeValue) url += `/users/${encodeURIComponent(this.scopeValue)}/events`;
                else url += '/events';
                break;
            default:
                url += '/events';
        }
        
        return url + '?per_page=100';
    }

    generateMockEvent(repoName, eventType) {
        const id = Math.floor(Math.random() * 1000000000) + Date.now();
        const actorNum = Math.floor(Math.random() * 100);
        const actor = { login: 'demo-user-' + actorNum, avatar_url: `https://avatars.githubusercontent.com/u/${actorNum + 1000}?v=4` };

        let payload = {};
        if (eventType === 'PushEvent') {
            const mockMessages = [
                'Fix typo in README', 'Add unit tests', 'Update dependencies',
                'Refactor authentication logic', 'Improve performance', 'Handle edge case in parser'
            ];
            const mockAuthors = ['Alice Smith', 'Bob Jones', 'Carol White', 'Dave Brown'];
            const commitCount = Math.floor(Math.random() * 3) + 1;
            const commits = [];
            for (let c = 0; c < commitCount; c++) {
                const sha = Array.from({ length: 5 }, () => Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, '0')).join('');
                commits.push({
                    sha,
                    message: mockMessages[Math.floor(Math.random() * mockMessages.length)],
                    author: { name: mockAuthors[Math.floor(Math.random() * mockAuthors.length)], email: 'demo@example.com' },
                    url: `https://api.github.com/repos/${repoName}/git/commits/${sha}`
                });
            }
            const branches = ['main', 'develop', 'feature/new-ui', 'fix/bug-123'];
            payload = {
                ref: `refs/heads/${branches[Math.floor(Math.random() * branches.length)]}`,
                size: commitCount,
                before: Array.from({ length: 5 }, () => Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, '0')).join(''),
                head: commits[commits.length - 1].sha,
                commits
            };
        }

        return {
            id: id.toString(),
            repo: { id: Math.floor(Math.random() * 1000000), name: repoName },
            type: eventType,
            created_at: new Date().toISOString(),
            actor,
            payload
        };
    }

    getMockEvents() {
        const repos = [
            'facebook/react', 'microsoft/vscode', 'vercel/next.js', 
            'nodejs/node', 'tensorflow/tensorflow', 'kubernetes/kubernetes',
            'rust-lang/rust', 'golang/go', 'python/cpython', 
            'microsoft/TypeScript', 'angular/angular', 'vuejs/vue'
        ];
        const eventTypes = [
            'PushEvent', 'PullRequestEvent', 'IssuesEvent', 
            'WatchEvent', 'ForkEvent', 'CreateEvent', 'ReleaseEvent'
        ];
        
        const events = [];
        const count = Math.floor(Math.random() * 5) + 3;
        for (let i = 0; i < count; i++) {
            events.push(this.generateMockEvent(
                repos[Math.floor(Math.random() * repos.length)],
                eventTypes[Math.floor(Math.random() * eventTypes.length)]
            ));
        }
        
        this.rateLimit = {
            remaining: Math.floor(Math.random() * 30) + 30,
            limit: 60,
            reset: Math.floor(Date.now() / 1000) + 3600
        };
        this.updateRateLimitDisplay();
        
        return events;
    }

    async fetchActivity() {
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) progressBar.classList.add('loading');
        
        try {
            let events;
            
            if (this.demoMode) {
                events = this.getMockEvents();
            } else {
                const headers = {};
                if (this.etag) headers['If-None-Match'] = this.etag;
                if (this.lastModified) headers['If-Modified-Since'] = this.lastModified;
                if (this.githubToken) headers['Authorization'] = `Bearer ${this.githubToken}`;
                
                const response = await fetch(this.getApiUrl(), { headers });
                
                const remaining = response.headers.get('X-RateLimit-Remaining');
                const limit = response.headers.get('X-RateLimit-Limit');
                const reset = response.headers.get('X-RateLimit-Reset');
                
                if (remaining !== null) {
                    this.rateLimit.remaining = parseInt(remaining, 10);
                    this.rateLimit.limit = parseInt(limit, 10);
                    this.rateLimit.reset = parseInt(reset, 10);
                    this.updateRateLimitDisplay();
                }
                
                const newEtag = response.headers.get('ETag');
                const newLastModified = response.headers.get('Last-Modified');
                if (newEtag) this.etag = newEtag;
                if (newLastModified) this.lastModified = newLastModified;
                
                if (response.status === 304) {
                    console.log('No new events (304 Not Modified)');
                    this.startCountdown();
                    const loadingEl = document.getElementById('loading');
                    if (loadingEl) loadingEl.style.display = 'none';
                    return;
                }
                
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

                events = await response.json();
                this.failedAttempts = 0;
            }

            this.processEvents(events);
            this.render();
            
            const loadingEl = document.getElementById('loading');
            const errorEl = document.getElementById('error');
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) errorEl.style.display = 'none';
            
        } catch (error) {
            console.error('Error fetching GitHub events:', error);
            this.failedAttempts++;
            
            if (this.failedAttempts >= 2 && !this.demoMode) {
                this.demoMode = true;
                console.log('Switching to demo mode with mock data');
                const errorDiv = document.getElementById('error');
                if (errorDiv) {
                    errorDiv.textContent = 'Running in demo mode with simulated data';
                    errorDiv.style.display = 'block';
                    setTimeout(() => errorDiv.style.display = 'none', 3000);
                }
                return this.fetchActivity();
            }
            
            const errorDiv = document.getElementById('error');
            if (errorDiv) {
                errorDiv.textContent = `Error loading data: ${error.message}. Retrying...`;
                errorDiv.style.display = 'block';
            }
        }
        
        this.startCountdown();
    }

    processEvents(events) {
        const newEvents = [];

        events.forEach(event => {
            if (!event || !event.id || !event.repo || !event.repo.name || !event.type || !event.created_at) return;
            if (this.seenEventIds.has(event.id)) return;

            if (this.eventTypeFilter !== 'all' && event.type !== this.eventTypeFilter) return;

            this.seenEventIds.add(event.id);
            
            const processedEvent = {
                id: event.id,
                repoName: event.repo.name,
                repoUrl: `https://github.com/${event.repo.name}`,
                eventType: event.type,
                createdAt: new Date(event.created_at),
                isNew: true,
                actor: event.actor ? event.actor.login : 'unknown',
                actorAvatarUrl: event.actor ? (event.actor.avatar_url || '') : '',
                payload: event.payload || {}
            };

            newEvents.push(processedEvent);
            this.totalEvents++;
            this.updateRepositoryStats(processedEvent);
            this.soundEffects.playEventSound(event.type);
        });

        newEvents.sort((a, b) => b.createdAt - a.createdAt);

        const allEvents = [...newEvents, ...this.events];
        allEvents.sort((a, b) => b.createdAt - a.createdAt);
        this.events = allEvents.slice(0, this.maxEvents);

        if (newEvents.length > 0) {
            const newestEvent = newEvents.reduce((a, b) => a.createdAt > b.createdAt ? a : b);
            this.latestEvent = newestEvent;
            
            const leaderboard = this.getLeaderboard();
            this.aiCommentary.generateCommentary(newestEvent, leaderboard).then(commentary => {
                if (commentary) {
                    this.tts.speak(commentary);
                }
            });
        }

        this.newEventIds = new Set(newEvents.map(e => e.id));

        const eventCountEl = document.getElementById('event-count');
        const repoCountEl = document.getElementById('repo-count');
        const lastUpdateEl = document.getElementById('last-update');
        
        if (eventCountEl) eventCountEl.textContent = this.totalEvents;
        if (repoCountEl) repoCountEl.textContent = this.repositories.size;
        if (lastUpdateEl) lastUpdateEl.textContent = new Date().toLocaleTimeString();
        
        this.updateChannelCounts();
    }

    updateRepositoryStats(event) {
        const repoName = event.repoName;
        
        if (!this.repositories.has(repoName)) {
            this.repositories.set(repoName, {
                name: repoName,
                url: event.repoUrl,
                totalEvents: 0,
                eventCounts: {},
                recentEvents: [],
                firstSeen: event.createdAt,
                lastActivity: event.createdAt,
                contributors: new Set(),
                activityScore: 0
            });
        }

        const repo = this.repositories.get(repoName);
        repo.totalEvents++;
        repo.lastActivity = event.createdAt;
        
        if (!repo.eventCounts[event.eventType]) repo.eventCounts[event.eventType] = 0;
        repo.eventCounts[event.eventType]++;

        repo.recentEvents.unshift({ type: event.eventType, time: event.createdAt, actor: event.actor });
        if (repo.recentEvents.length > 5) repo.recentEvents.pop();

        if (event.actor) repo.contributors.add(event.actor);

        this.calculateActivityScore(repo);
    }

    calculateActivityScore(repo) {
        const now = new Date();
        let score = 0;

        Object.entries(repo.eventCounts).forEach(([type, count]) => {
            const weight = GitHubSportscaster.EVENT_WEIGHTS[type] || 1;
            score += count * weight;
        });

        const hoursSinceLastActivity = (now - repo.lastActivity) / (1000 * 60 * 60);
        if (hoursSinceLastActivity < 1) score *= 1.5;
        else if (hoursSinceLastActivity < 24) score *= 1.2;

        score += repo.contributors.size * 2;
        repo.activityScore = Math.round(score);
    }

    getLeaderboard() {
        return Array.from(this.repositories.values())
            .sort((a, b) => b.activityScore - a.activityScore)
            .slice(0, 10);
    }

    updateChannelCounts() {
        const allCount = this.events.length;
        const hotCount = this.events.filter(GitHubSportscaster.CHANNEL_FILTERS.hot).length;
        const codeCount = this.events.filter(GitHubSportscaster.CHANNEL_FILTERS.code).length;
        const socialCount = this.events.filter(GitHubSportscaster.CHANNEL_FILTERS.social).length;
        
        const allCountEl = document.getElementById('all-count');
        const hotCountEl = document.getElementById('hot-count');
        const codeCountEl = document.getElementById('code-count');
        const socialCountEl = document.getElementById('social-count');
        
        if (allCountEl) allCountEl.textContent = allCount;
        if (hotCountEl) hotCountEl.textContent = hotCount;
        if (codeCountEl) codeCountEl.textContent = codeCount;
        if (socialCountEl) socialCountEl.textContent = socialCount;
    }

    getEventIcon(eventType) {
        const icons = {
            PushEvent: 'fa-upload',
            PullRequestEvent: 'fa-code-pull-request',
            IssuesEvent: 'fa-bug',
            WatchEvent: 'fa-star',
            ForkEvent: 'fa-code-fork',
            CreateEvent: 'fa-wand-magic-sparkles',
            DeleteEvent: 'fa-trash',
            ReleaseEvent: 'fa-rocket',
            IssueCommentEvent: 'fa-comment',
            CommitCommentEvent: 'fa-comment-dots',
            PullRequestReviewEvent: 'fa-eye',
            PullRequestReviewCommentEvent: 'fa-comments',
            GollumEvent: 'fa-file-lines',
            MemberEvent: 'fa-users',
            PublicEvent: 'fa-globe'
        };
        const iconClass = icons[eventType] || 'fa-location-pin';
        return `<i class="fa-solid ${iconClass} event-icon" aria-hidden="true"></i>`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatEventType(type) {
        return type.replace('Event', '').replace(/([A-Z])/g, ' $1').trim();
    }

    formatTime(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    formatCommitInfo(event) {
        if (event.eventType !== 'PushEvent' || !event.payload || !event.payload.commits) {
            return '';
        }

        const commits = event.payload.commits || [];
        const commitCount = event.payload.size || commits.length;
        
        if (commitCount === 0) {
            return '';
        }

        let html = '<div class="commit-info">';
        html += `<div class="commit-count"><i class="fa-solid fa-code-commit event-icon" aria-hidden="true"></i> ${commitCount} commit${commitCount > 1 ? 's' : ''}</div>`;
        
        // Show up to 3 commit messages
        const displayCommits = commits.slice(0, 3);
        if (displayCommits.length > 0) {
            html += '<div class="commit-list">';
            displayCommits.forEach(commit => {
                const shortSha = commit.sha ? commit.sha.substring(0, 7) : '';
                const message = commit.message ? commit.message.split('\n')[0] : 'No message';
                const commitUrl = commit.url || `${event.repoUrl}/commit/${commit.sha}`;
                
                html += '<div class="commit-item">';
                if (shortSha) {
                    html += `<a href="${this.escapeHtml(commitUrl)}" target="_blank" rel="noopener noreferrer" class="commit-sha">${this.escapeHtml(shortSha)}</a>`;
                }
                html += `<span class="commit-message">${this.escapeHtml(message)}</span>`;
                html += '</div>';
            });
            html += '</div>';
            
            if (commits.length > 3) {
                html += `<div class="commit-more">+ ${commits.length - 3} more commit${commits.length - 3 > 1 ? 's' : ''}</div>`;
            }
        }
        
        html += '</div>';
        return html;
    }

    getEventUrl(event) {
        const baseUrl = event.repoUrl;
        switch (event.eventType) {
            case 'PushEvent': return `${baseUrl}/commits`;
            case 'PullRequestEvent': return `${baseUrl}/pulls`;
            case 'IssuesEvent': return `${baseUrl}/issues`;
            case 'ReleaseEvent': return `${baseUrl}/releases`;
            case 'ForkEvent': return `${baseUrl}/forks`;
            case 'WatchEvent': return `${baseUrl}/stargazers`;
            default: return baseUrl;
        }
    }

    /**
     * Returns HTML showing rich event details — PR title, issue title, release name,
     * branch/ref for creates, commit messages for pushes, etc.
     * @param {Object} event - Processed event object
     * @returns {string} HTML string
     */
    formatEventDetails(event) {
        const payload = event.payload || {};
        let html = '';

        switch (event.eventType) {
            case 'PushEvent': {
                const commits = payload.commits || [];
                const commitCount = payload.size || commits.length;
                if (commitCount === 0) break;

                const branch = payload.ref ? payload.ref.replace('refs/heads/', '') : '';
                html = '<div class="event-detail-info commit-info">';
                if (branch) {
                    html += `<div class="commit-count"><i class="fa-solid fa-code-branch event-icon" aria-hidden="true"></i> <span class="event-detail-ref">${this.escapeHtml(branch)}</span> — ${commitCount} commit${commitCount !== 1 ? 's' : ''}</div>`;
                } else {
                    html += `<div class="commit-count"><i class="fa-solid fa-code-commit event-icon" aria-hidden="true"></i> ${commitCount} commit${commitCount !== 1 ? 's' : ''}</div>`;
                }
                const displayCommits = commits.slice(0, 3);
                if (displayCommits.length > 0) {
                    html += '<div class="commit-list">';
                    displayCommits.forEach(commit => {
                        const shortSha = commit.sha ? commit.sha.substring(0, 7) : '';
                        const message = commit.message ? commit.message.split('\n')[0] : 'No message';
                        const commitUrl = `${event.repoUrl}/commit/${commit.sha}`;
                        const authorName = commit.author ? commit.author.name : '';
                        html += '<div class="commit-item">';
                        if (shortSha) {
                            html += `<a href="${this.escapeHtml(commitUrl)}" target="_blank" rel="noopener noreferrer" class="commit-sha">${this.escapeHtml(shortSha)}</a>`;
                        }
                        html += `<span class="commit-message">${this.escapeHtml(message)}</span>`;
                        if (authorName) {
                            html += `<span class="commit-author">${this.escapeHtml(authorName)}</span>`;
                        }
                        html += '</div>';
                    });
                    html += '</div>';
                    if (commits.length > 3) {
                        html += `<div class="commit-more">+ ${commits.length - 3} more commit${commits.length - 3 !== 1 ? 's' : ''}</div>`;
                    }
                }
                if (event.filesChanged && event.filesChanged.length > 0) {
                    html += this.formatFilesChanged(event.filesChanged);
                }
                html += '</div>';
                break;
            }
            case 'PullRequestEvent': {
                const pr = payload.pull_request;
                if (!pr) break;
                const action = payload.action || 'updated';
                const prUrl = pr.html_url || `${event.repoUrl}/pull/${pr.number}`;
                const bodySnippet = pr.body ? pr.body.trim().substring(0, 120) : '';
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">${this.escapeHtml(action)}</span>
                    <a href="${this.escapeHtml(prUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">#${pr.number} ${this.escapeHtml(pr.title || '')}</a>
                    ${bodySnippet ? `<div class="event-detail-body">${this.escapeHtml(bodySnippet)}${pr.body.trim().length > 120 ? '…' : ''}</div>` : ''}
                </div>`;
                break;
            }
            case 'IssuesEvent': {
                const issue = payload.issue;
                if (!issue) break;
                const action = payload.action || 'updated';
                const issueUrl = issue.html_url || `${event.repoUrl}/issues/${issue.number}`;
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">${this.escapeHtml(action)}</span>
                    <a href="${this.escapeHtml(issueUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">#${issue.number} ${this.escapeHtml(issue.title || '')}</a>
                </div>`;
                break;
            }
            case 'IssueCommentEvent': {
                const issue = payload.issue;
                const comment = payload.comment;
                if (!issue) break;
                const issueUrl = issue.html_url || `${event.repoUrl}/issues/${issue.number}`;
                const commentSnippet = comment && comment.body ? comment.body.trim().substring(0, 120) : '';
                html = `<div class="event-detail-info">
                    <a href="${this.escapeHtml(issueUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">#${issue.number} ${this.escapeHtml(issue.title || '')}</a>
                    ${commentSnippet ? `<div class="event-detail-body">${this.escapeHtml(commentSnippet)}${comment.body.trim().length > 120 ? '…' : ''}</div>` : ''}
                </div>`;
                break;
            }
            case 'PullRequestReviewEvent':
            case 'PullRequestReviewCommentEvent': {
                const pr = payload.pull_request;
                const comment = payload.comment || payload.review;
                if (!pr) break;
                const prUrl = pr.html_url || `${event.repoUrl}/pull/${pr.number}`;
                const commentSnippet = comment && comment.body ? comment.body.trim().substring(0, 120) : '';
                html = `<div class="event-detail-info">
                    <a href="${this.escapeHtml(prUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">#${pr.number} ${this.escapeHtml(pr.title || '')}</a>
                    ${commentSnippet ? `<div class="event-detail-body">${this.escapeHtml(commentSnippet)}${comment.body.trim().length > 120 ? '…' : ''}</div>` : ''}
                </div>`;
                break;
            }
            case 'CommitCommentEvent': {
                const comment = payload.comment;
                if (!comment) break;
                const commentSnippet = comment.body ? comment.body.trim().substring(0, 120) : '';
                const commentUrl = comment.html_url || event.repoUrl;
                html = `<div class="event-detail-info">
                    <a href="${this.escapeHtml(commentUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">
                        <i class="fa-solid fa-comment-dots" aria-hidden="true"></i> Commit comment
                    </a>
                    ${commentSnippet ? `<div class="event-detail-body">${this.escapeHtml(commentSnippet)}${comment.body.trim().length > 120 ? '…' : ''}</div>` : ''}
                </div>`;
                break;
            }
            case 'ReleaseEvent': {
                const release = payload.release;
                if (!release) break;
                const releaseName = release.name || release.tag_name || '';
                const releaseUrl = release.html_url || `${event.repoUrl}/releases`;
                const releaseSnippet = release.body ? release.body.trim().substring(0, 120) : '';
                html = `<div class="event-detail-info">
                    <a href="${this.escapeHtml(releaseUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">🚀 ${this.escapeHtml(releaseName)}</a>
                    ${releaseSnippet ? `<div class="event-detail-body">${this.escapeHtml(releaseSnippet)}${release.body.trim().length > 120 ? '…' : ''}</div>` : ''}
                </div>`;
                break;
            }
            case 'CreateEvent': {
                const refType = payload.ref_type || 'repository';
                const ref = payload.ref || '';
                const description = payload.description || '';
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">Created ${this.escapeHtml(refType)}</span>
                    ${ref ? `<span class="event-detail-ref">${this.escapeHtml(ref)}</span>` : ''}
                    ${description ? `<div class="event-detail-body">${this.escapeHtml(description.substring(0, 120))}${description.length > 120 ? '…' : ''}</div>` : ''}
                </div>`;
                break;
            }
            case 'DeleteEvent': {
                const refType = payload.ref_type || '';
                const ref = payload.ref || '';
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">Deleted ${this.escapeHtml(refType)}</span>
                    ${ref ? `<span class="event-detail-ref">${this.escapeHtml(ref)}</span>` : ''}
                </div>`;
                break;
            }
            case 'ForkEvent': {
                const forkee = payload.forkee;
                if (!forkee) break;
                const forkUrl = forkee.html_url || `https://github.com/${forkee.full_name}`;
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">Forked to</span>
                    <a href="${this.escapeHtml(forkUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">${this.escapeHtml(forkee.full_name || '')}</a>
                </div>`;
                break;
            }
            case 'WatchEvent': {
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">⭐ starred this repository</span>
                </div>`;
                break;
            }
            case 'MemberEvent': {
                const member = payload.member;
                const action = payload.action || '';
                if (!member) break;
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">${this.escapeHtml(action)} collaborator</span>
                    <span class="event-detail-title">${this.escapeHtml(member.login || '')}</span>
                </div>`;
                break;
            }
            case 'GollumEvent': {
                const pages = payload.pages || [];
                if (pages.length === 0) break;
                html = `<div class="event-detail-info">
                    <span class="event-detail-action">Wiki:</span>
                    ${pages.slice(0, 2).map(p =>
                        `<a href="${this.escapeHtml(p.html_url || event.repoUrl)}" target="_blank" rel="noopener noreferrer" class="event-detail-title">${this.escapeHtml(p.page_name || '')} (${this.escapeHtml(p.action || '')})</a>`
                    ).join(' · ')}
                </div>`;
                break;
            }
            default:
                break;
        }

        return html;
    }

    getTrendingIndicator(repoName, currentRank) {
        const previousRank = this.previousRanks.get(repoName);
        
        if (previousRank === undefined) {
            return { class: 'new', icon: '<i class="fa-solid fa-sparkles trend-icon" aria-hidden="true"></i>', text: 'New' };
        }
        
        if (currentRank < previousRank) {
            return { class: 'up', icon: '<i class="fa-solid fa-arrow-trend-up trend-icon" aria-hidden="true"></i>', text: `+${previousRank - currentRank}` };
        } else if (currentRank > previousRank) {
            return { class: 'down', icon: '<i class="fa-solid fa-arrow-trend-down trend-icon" aria-hidden="true"></i>', text: `-${currentRank - previousRank}` };
        }
        
        return { class: '', icon: '<i class="fa-solid fa-arrow-right trend-icon" aria-hidden="true"></i>', text: '—' };
    }

    updateAnnouncement() {
        const announcementDiv = document.getElementById('announcement');
        if (!announcementDiv) return;
        
        if (!this.latestEvent) {
            announcementDiv.innerHTML = '<div class="no-announcement">Waiting for activity...</div>';
            return;
        }

        const event = this.latestEvent;
        const icon = this.getEventIcon(event.eventType);
        const eventUrl = this.getEventUrl(event);
        const eventDetailsHtml = this.formatEventDetails(event);
        
        announcementDiv.innerHTML = `
            <div class="announcement-event-type">${icon} ${this.escapeHtml(this.formatEventType(event.eventType))}</div>
            <div class="announcement-repo">
                <a href="${this.escapeHtml(event.repoUrl)}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(event.repoName)}</a>
            </div>
            <div class="announcement-time">
                <span>${event.actorAvatarUrl ? `<img src="${this.escapeHtml(event.actorAvatarUrl)}" alt="" class="actor-avatar actor-avatar-lg" loading="lazy">` : ''}<a href="https://github.com/${this.escapeHtml(event.actor)}" target="_blank" rel="noopener noreferrer" class="actor-link">${this.escapeHtml(event.actor)}</a> • ${this.escapeHtml(this.formatTime(event.createdAt))}</span>
                <a href="${this.escapeHtml(eventUrl)}" target="_blank" rel="noopener noreferrer" class="view-link"><i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i> View</a>
            </div>
            ${eventDetailsHtml}
        `;
    }

    renderLeaderboard() {
        const container = document.getElementById('leaderboard-list');
        if (!container) return;
        
        const leaderboard = this.getLeaderboard();
        
        container.innerHTML = '';
        
        leaderboard.forEach((repo, index) => {
            const rank = index + 1;
            const trending = this.getTrendingIndicator(repo.name, rank);
            
            const rankClass = rank === 1 ? 'rank-1' : rank === 2 ? 'rank-2' : rank === 3 ? 'rank-3' : '';
            const rankIcon = rank === 1
                ? '<i class="fa-solid fa-crown leader-icon" aria-hidden="true"></i>'
                : rank === 2
                    ? '<i class="fa-solid fa-medal leader-icon" aria-hidden="true"></i>'
                    : rank === 3
                        ? '<i class="fa-solid fa-award leader-icon" aria-hidden="true"></i>'
                        : `<span>${rank}</span>`;
            const colorClass = rank <= 3 ? 'top-rank' : '';
            
            const item = document.createElement('div');
            item.className = `leaderboard-item ${rankClass}`;
            
            item.innerHTML = `
                <div class="leaderboard-rank ${colorClass}">${rankIcon}</div>
                <div class="leaderboard-repo">
                    <div class="leaderboard-repo-name">
                        <a href="${this.escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(repo.name)}</a>
                    </div>
                </div>
                <div class="leaderboard-stats">
                    <div class="leaderboard-stat"><i class="fa-solid fa-bolt stat-pill-icon" aria-hidden="true"></i> ${repo.activityScore}</div>
                    <div class="leaderboard-stat"><i class="fa-solid fa-chart-line stat-pill-icon" aria-hidden="true"></i> ${repo.totalEvents}</div>
                    <div class="leaderboard-stat"><i class="fa-solid fa-users stat-pill-icon" aria-hidden="true"></i> ${repo.contributors.size}</div>
                </div>
                ${trending.text !== '—' ? `<div class="leaderboard-change ${trending.class}">${trending.icon} ${trending.text}</div>` : ''}
            `;
            
            container.appendChild(item);
            
            this.previousRanks.set(repo.name, rank);
        });
    }

    render() {
        const listContainer = document.getElementById('event-list');
        if (!listContainer) return;
        
        this.updateAnnouncement();
        this.renderLeaderboard();
        
        listContainer.innerHTML = '';

        const channelFilter = GitHubSportscaster.CHANNEL_FILTERS[this.currentChannel] || (() => true);
        const filteredEvents = this.events.filter(channelFilter);
        const sortedEvents = [...filteredEvents].sort((a, b) => b.createdAt - a.createdAt);

        const repoScores = Array.from(this.repositories.values()).map(r => r.activityScore);
        const highestActivityScore = repoScores.length > 0 ? Math.max(...repoScores) : 1;

        sortedEvents.forEach((event, index) => {
            const isNew = this.newEventIds && this.newEventIds.has(event.id);
            const icon = this.getEventIcon(event.eventType);
            const repo = this.repositories.get(event.repoName);

            const item = document.createElement('div');
            item.className = 'event-item';
            item.id = `event-${String(event.id).replace(/[^a-zA-Z0-9-_]/g, '-')}`;

            if (isNew) {
                item.classList.add('new-event', 'stagger-in');
                item.style.animationDelay = `${Math.random() * 500}ms`;
            }

            let statsHtml = '';
            if (repo && highestActivityScore > 0) {
                const activityPercent = Math.round((repo.activityScore / highestActivityScore) * 100);
                
                statsHtml = `
                    <div class="event-stats">
                        <span class="stat-pill" title="Total Events">
                            <span class="stat-pill-icon"><i class="fa-solid fa-chart-line" aria-hidden="true"></i></span>
                            <span class="stat-pill-value">${repo.totalEvents}</span>
                        </span>
                        <span class="stat-pill" title="Contributors">
                            <span class="stat-pill-icon"><i class="fa-solid fa-users" aria-hidden="true"></i></span>
                            <span class="stat-pill-value">${repo.contributors.size}</span>
                        </span>
                        <span class="stat-pill" title="Activity Score">
                            <span class="stat-pill-icon"><i class="fa-solid fa-bolt" aria-hidden="true"></i></span>
                            <span class="stat-pill-value">${repo.activityScore}</span>
                        </span>
                        <div class="mini-activity-bar" title="Activity Level ${activityPercent}%">
                            <div class="mini-activity-fill" style="width: ${activityPercent}%"></div>
                        </div>
                    </div>
                `;
            }

            const eventDetailsHtml = this.formatEventDetails(event);
            
            item.innerHTML = `
                <div class="event-item-row">
                    <div class="event-number">${index + 1}</div>
                    <div class="event-details">
                        <div class="event-repo-name">
                            <a href="${this.escapeHtml(event.repoUrl)}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(event.repoName)}</a>
                        </div>
                        <div class="event-meta">
                            <span class="event-type">${icon} ${this.escapeHtml(this.formatEventType(event.eventType))}</span>
                            <span class="event-time">${event.actorAvatarUrl ? `<img src="${this.escapeHtml(event.actorAvatarUrl)}" alt="" class="actor-avatar" loading="lazy">` : ''}<a href="https://github.com/${this.escapeHtml(event.actor)}" target="_blank" rel="noopener noreferrer" class="actor-link">${this.escapeHtml(event.actor)}</a> • ${this.escapeHtml(this.formatTime(event.createdAt))}</span>
                        </div>
                        ${eventDetailsHtml}
                    </div>
                    ${statsHtml}
                </div>
            `;

            listContainer.appendChild(item);

            if (event.eventType === 'PushEvent' && event.filesChanged === undefined) {
                this.fetchAndRenderFilesChanged(event, item.id);
            }
        });

        this.newEventIds = new Set();
        this.events.forEach(e => e.isNew = false);
    }

    async fetchAndRenderFilesChanged(event, cardId) {
        const payload = event.payload || {};
        const before = payload.before;
        const head = payload.head;
        if (!before || !head || /^0{40}$/.test(before)) {
            event.filesChanged = null;
            return;
        }

        const url = `https://api.github.com/repos/${event.repoName}/compare/${before}...${head}`;
        try {
            const headers = { 'Accept': 'application/vnd.github+json' };
            if (this.githubToken) headers['Authorization'] = `Bearer ${this.githubToken}`;
            const response = await fetch(url, { headers });
            if (!response.ok) {
                event.filesChanged = null;
                return;
            }
            const data = await response.json();
            event.filesChanged = data.files || [];
        } catch (e) {
            event.filesChanged = null;
            return;
        }

        if (!event.filesChanged || event.filesChanged.length === 0) return;

        const cardEl = document.getElementById(cardId);
        if (!cardEl) return;

        const commitInfoEl = cardEl.querySelector('.event-detail-info.commit-info');
        if (commitInfoEl) {
            commitInfoEl.insertAdjacentHTML('beforeend', this.formatFilesChanged(event.filesChanged));
        }
    }

    formatFilesChanged(files) {
        if (!files || files.length === 0) return '';

        const totalAdditions = files.reduce((sum, f) => sum + (f.additions || 0), 0);
        const totalDeletions = files.reduce((sum, f) => sum + (f.deletions || 0), 0);
        const displayFiles = files.slice(0, 5);

        let html = '<div class="files-changed">';
        html += '<div class="files-changed-summary">';
        html += `<i class="fa-solid fa-file-lines event-icon" aria-hidden="true"></i>`;
        html += ` ${files.length} file${files.length !== 1 ? 's' : ''} changed`;
        if (totalAdditions > 0) html += ` <span class="files-additions">+${totalAdditions}</span>`;
        if (totalDeletions > 0) html += ` <span class="files-deletions">-${totalDeletions}</span>`;
        html += '</div>';

        html += '<div class="files-list">';
        displayFiles.forEach(file => {
            const fileStatus = file.status || 'modified';
            const statusIcon = this.getFileStatusIcon(fileStatus);
            const statusClass = `files-status-${this.escapeHtml(fileStatus)}`;
            html += '<div class="files-item">';
            html += `<span class="files-status ${statusClass}">${statusIcon}</span>`;
            html += `<span class="files-name">${this.escapeHtml(file.filename || '')}</span>`;
            if (file.additions !== undefined || file.deletions !== undefined) {
                html += `<span class="files-diff"><span class="files-additions">+${file.additions || 0}</span> <span class="files-deletions">-${file.deletions || 0}</span></span>`;
            }
            html += '</div>';
        });
        if (files.length > 5) {
            html += `<div class="files-more">+ ${files.length - 5} more file${files.length - 5 !== 1 ? 's' : ''}</div>`;
        }
        html += '</div>';
        html += '</div>';
        return html;
    }

    getFileStatusIcon(status) {
        const icons = { added: 'A', removed: 'D', renamed: 'R', copied: 'C' };
        return icons[status] || 'M';
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    new GitHubSportscaster();
});