/**
 * Screenshot Analyzer
 * LOCAL ONLY - No screenshots or data are ever uploaded to 3rd party services
 * All analysis happens locally with a secure local LLM
 */

import { ActivityEvent, ScreenshotData, LocalAnalysisResult } from '../types';

export class ScreenshotAnalyzer {
  private userId: string;
  private sessionId: string;
  private enabled: boolean;

  constructor(userId: string, sessionId: string, enabled: boolean = false) {
    this.userId = userId;
    this.sessionId = sessionId;
    this.enabled = enabled;
  }

  /**
   * Analyze screenshot locally
   * IMPORTANT: This runs ONLY on the user's local machine
   * No screenshot data is ever transmitted or stored on servers
   */
  async analyzeScreenshotLocally(screenshotId: string): Promise<ActivityEvent> {
    if (!this.enabled) {
      throw new Error('Screenshot analysis is disabled');
    }

    // Simulate local LLM analysis
    // In production, this would use a local model like:
    // - LLaMA running locally
    // - Ollama
    // - LocalAI
    // - Private transformers.js model
    const analysisResult = await this.performLocalAnalysis(screenshotId);

    const event: ActivityEvent = {
      id: crypto.randomUUID(),
      sessionId: this.sessionId,
      userId: this.userId,
      type: 'screenshot',
      timestamp: Date.now(),
      data: {
        type: 'screenshot',
        localAnalysisId: screenshotId,
        analysisResult,
        timestamp: Date.now(),
      },
    };

    return event;
  }

  /**
   * Perform local analysis
   * This is a placeholder for actual local LLM integration
   */
  private async performLocalAnalysis(screenshotId: string): Promise<LocalAnalysisResult> {
    // In production, this would:
    // 1. Load the screenshot from local storage
    // 2. Process it with a local vision LLM
    // 3. Extract activity type (coding, debugging, etc.)
    // 4. Delete the screenshot after analysis
    // 5. Only store the generic activity classification

    // Simulated analysis
    const activities: LocalAnalysisResult['activity'][] = [
      'coding',
      'debugging',
      'research',
      'communication',
    ];
    const randomActivity = activities[Math.floor(Math.random() * activities.length)];

    return {
      activity: randomActivity,
      confidence: 0.85,
      processedLocally: true,
      summary: `User appears to be ${randomActivity}`,
    };
  }

  /**
   * Get privacy-safe summary of screenshot analysis
   * Returns only high-level activity patterns, no sensitive data
   */
  async getActivitySummary(events: ActivityEvent[]): Promise<{
    totalScreenshots: number;
    activityBreakdown: Record<string, number>;
    avgConfidence: number;
  }> {
    const screenshotEvents = events.filter((e) => e.type === 'screenshot');
    const activityBreakdown: Record<string, number> = {};
    let totalConfidence = 0;

    screenshotEvents.forEach((event) => {
      const data = event.data as ScreenshotData;
      if (data.analysisResult) {
        const activity = data.analysisResult.activity;
        activityBreakdown[activity] = (activityBreakdown[activity] || 0) + 1;
        totalConfidence += data.analysisResult.confidence;
      }
    });

    return {
      totalScreenshots: screenshotEvents.length,
      activityBreakdown,
      avgConfidence: screenshotEvents.length > 0 ? totalConfidence / screenshotEvents.length : 0,
    };
  }

  /**
   * Configure screenshot settings
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  isEnabled(): boolean {
    return this.enabled;
  }
}
