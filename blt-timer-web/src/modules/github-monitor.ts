/**
 * GitHub Activity Monitor
 * Tracks GitHub events for the user's repositories
 */

import { ActivityEvent, GitHubActivityData } from '../types';

export class GitHubMonitor {
  private userId: string;
  private sessionId: string;
  private githubToken?: string;

  constructor(userId: string, sessionId: string, githubToken?: string) {
    this.userId = userId;
    this.sessionId = sessionId;
    this.githubToken = githubToken;
  }

  /**
   * Track a GitHub event
   */
  async trackEvent(data: Omit<GitHubActivityData, 'type'>): Promise<ActivityEvent> {
    const event: ActivityEvent = {
      id: crypto.randomUUID(),
      sessionId: this.sessionId,
      userId: this.userId,
      type: 'github',
      timestamp: Date.now(),
      data: {
        type: 'github',
        ...data,
      },
    };

    return event;
  }

  /**
   * Fetch recent GitHub activity for the user
   * This would integrate with GitHub's API
   */
  async fetchRecentActivity(since?: number): Promise<ActivityEvent[]> {
    if (!this.githubToken) {
      return [];
    }

    // In a real implementation, this would call GitHub API
    // For now, we return a placeholder
    // Example: GET /users/{username}/events
    return [];
  }

  /**
   * Watch a repository for activity
   */
  async watchRepository(repositoryUrl: string): Promise<void> {
    // Implementation would set up webhooks or polling for the repository
    console.log(`Watching repository: ${repositoryUrl}`);
  }

  /**
   * Parse GitHub webhook payload
   */
  parseWebhook(payload: any): ActivityEvent | null {
    try {
      const eventType = this.mapWebhookEventType(payload);
      if (!eventType) return null;

      return {
        id: crypto.randomUUID(),
        sessionId: this.sessionId,
        userId: this.userId,
        type: 'github',
        timestamp: Date.now(),
        data: {
          type: 'github',
          action: eventType,
          repository: payload.repository?.full_name || 'unknown',
          branch: payload.ref || undefined,
          commitSha: payload.after || payload.head_commit?.id || undefined,
          url: payload.repository?.html_url || undefined,
        },
      };
    } catch (error) {
      console.error('Error parsing GitHub webhook:', error);
      return null;
    }
  }

  private mapWebhookEventType(payload: any): GitHubActivityData['action'] | null {
    // Map GitHub webhook events to our action types
    if (payload.commits) return 'push';
    if (payload.pull_request) return 'pull-request';
    if (payload.issue) return 'issue';
    if (payload.review) return 'review';
    if (payload.comment) return 'comment';
    return null;
  }
}
