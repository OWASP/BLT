/**
 * Client-side Time Tracker
 * This runs locally on the user's machine to track activity
 * All sensitive data processing happens locally
 */

interface TrackerClientConfig {
  apiUrl: string;
  userId: string;
  projectId: string;
  enableKeyboard?: boolean;
  enableMouse?: boolean;
  enableScreenshots?: boolean;
  screenshotInterval?: number; // minutes
}

class TimeTrackerClient {
  private config: TrackerClientConfig;
  private sessionId: string | null = null;
  private keyboardCount: number = 0;
  private mouseClicks: number = 0;
  private mouseDistance: number = 0;
  private lastMouseX: number = 0;
  private lastMouseY: number = 0;
  private syncInterval: number = 60000; // 1 minute

  constructor(config: TrackerClientConfig) {
    this.config = config;
  }

  /**
   * Start tracking session
   */
  async startSession(): Promise<void> {
    try {
      const response = await fetch(`${this.config.apiUrl}/api/sessions/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
        },
        body: JSON.stringify({
          projectId: this.config.projectId,
        }),
      });

      const data = await response.json();
      this.sessionId = data.session.id;

      // Start monitoring
      this.startMonitoring();

      console.log('Tracking session started:', this.sessionId);
    } catch (error) {
      console.error('Failed to start session:', error);
      throw error;
    }
  }

  /**
   * End tracking session
   */
  async endSession(): Promise<void> {
    if (!this.sessionId) return;

    try {
      await this.syncActivity();

      await fetch(`${this.config.apiUrl}/api/sessions/${this.sessionId}/end`, {
        method: 'POST',
        headers: {
          'X-User-ID': this.config.userId,
        },
      });

      this.stopMonitoring();
      this.sessionId = null;

      console.log('Tracking session ended');
    } catch (error) {
      console.error('Failed to end session:', error);
      throw error;
    }
  }

  /**
   * Start monitoring activity
   */
  private startMonitoring(): void {
    if (this.config.enableKeyboard) {
      document.addEventListener('keydown', this.handleKeyboard);
    }

    if (this.config.enableMouse) {
      document.addEventListener('click', this.handleMouseClick);
      document.addEventListener('mousemove', this.handleMouseMove);
    }

    // Periodic sync
    setInterval(() => this.syncActivity(), this.syncInterval);

    // Screenshot capture (if enabled)
    if (this.config.enableScreenshots && this.config.screenshotInterval) {
      setInterval(
        () => this.captureAndAnalyzeScreenshot(),
        this.config.screenshotInterval * 60 * 1000
      );
    }
  }

  /**
   * Stop monitoring activity
   */
  private stopMonitoring(): void {
    document.removeEventListener('keydown', this.handleKeyboard);
    document.removeEventListener('click', this.handleMouseClick);
    document.removeEventListener('mousemove', this.handleMouseMove);
  }

  /**
   * Handle keyboard events
   */
  private handleKeyboard = (): void => {
    this.keyboardCount++;
  };

  /**
   * Handle mouse clicks
   */
  private handleMouseClick = (): void => {
    this.mouseClicks++;
  };

  /**
   * Handle mouse movement
   */
  private handleMouseMove = (event: MouseEvent): void => {
    if (this.lastMouseX > 0 && this.lastMouseY > 0) {
      const dx = event.clientX - this.lastMouseX;
      const dy = event.clientY - this.lastMouseY;
      this.mouseDistance += Math.sqrt(dx * dx + dy * dy);
    }
    this.lastMouseX = event.clientX;
    this.lastMouseY = event.clientY;
  };

  /**
   * Sync activity to server
   */
  private async syncActivity(): Promise<void> {
    if (!this.sessionId) return;

    const activities = [];

    if (this.keyboardCount > 0) {
      activities.push({
        sessionId: this.sessionId,
        type: 'keyboard',
        data: {
          type: 'keyboard',
          keyCount: this.keyboardCount,
          activeTime: this.syncInterval,
          idleTime: 0,
        },
      });
      this.keyboardCount = 0;
    }

    if (this.mouseClicks > 0 || this.mouseDistance > 0) {
      activities.push({
        sessionId: this.sessionId,
        type: 'mouse',
        data: {
          type: 'mouse',
          clickCount: this.mouseClicks,
          moveDistance: Math.round(this.mouseDistance),
          activeTime: this.syncInterval,
        },
      });
      this.mouseClicks = 0;
      this.mouseDistance = 0;
    }

    for (const activity of activities) {
      try {
        await fetch(`${this.config.apiUrl}/api/activity`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-ID': this.config.userId,
          },
          body: JSON.stringify(activity),
        });
      } catch (error) {
        console.error('Failed to sync activity:', error);
      }
    }
  }

  /**
   * Capture and analyze screenshot locally
   * IMPORTANT: Screenshot is never uploaded, only analyzed locally
   */
  private async captureAndAnalyzeScreenshot(): Promise<void> {
    if (!this.sessionId) return;

    try {
      // This would use a local screenshot API or browser extension
      // For security, this requires explicit user permission
      
      // Simulated local analysis
      const screenshotId = crypto.randomUUID();
      
      // In production, this would:
      // 1. Capture screenshot to local storage
      // 2. Run local LLM analysis
      // 3. Delete screenshot
      // 4. Send only the analysis result

      const analysisResult = {
        activity: 'coding',
        confidence: 0.85,
        processedLocally: true,
        summary: 'User is coding',
      };

      await fetch(`${this.config.apiUrl}/api/activity`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
        },
        body: JSON.stringify({
          sessionId: this.sessionId,
          type: 'screenshot',
          data: {
            type: 'screenshot',
            localAnalysisId: screenshotId,
            analysisResult,
            timestamp: Date.now(),
          },
        }),
      });

      console.log('Screenshot analyzed locally');
    } catch (error) {
      console.error('Failed to capture/analyze screenshot:', error);
    }
  }

  /**
   * Track agent prompt
   */
  async trackAgentPrompt(
    agentName: string,
    promptLength: number,
    responseLength?: number
  ): Promise<void> {
    if (!this.sessionId) return;

    try {
      await fetch(`${this.config.apiUrl}/api/activity`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
        },
        body: JSON.stringify({
          sessionId: this.sessionId,
          type: 'agent-prompt',
          data: {
            type: 'agent-prompt',
            agentName,
            promptLength,
            responseLength,
          },
        }),
      });
    } catch (error) {
      console.error('Failed to track agent prompt:', error);
    }
  }
}

// Export for use in browser or Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TimeTrackerClient;
}
