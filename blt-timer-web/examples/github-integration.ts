/**
 * GitHub Integration Example
 * Shows how to integrate with GitHub webhooks and API
 */

interface GitHubConfig {
  apiUrl: string;
  userId: string;
  sessionId: string;
  githubToken?: string;
}

class GitHubIntegration {
  private config: GitHubConfig;

  constructor(config: GitHubConfig) {
    this.config = config;
  }

  /**
   * Set up webhook handler for GitHub events
   * This would typically run on your server
   */
  async handleWebhook(payload: any, event: string): Promise<void> {
    try {
      const response = await fetch(`${this.config.apiUrl}/api/webhooks/github`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
          'X-Session-ID': this.config.sessionId,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        console.log(`✅ GitHub ${event} event tracked`);
      }
    } catch (error) {
      console.error('Failed to track GitHub webhook:', error);
    }
  }

  /**
   * Manually track a commit
   */
  async trackCommit(repository: string, sha: string, branch: string): Promise<void> {
    try {
      await fetch(`${this.config.apiUrl}/api/activity`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
        },
        body: JSON.stringify({
          sessionId: this.config.sessionId,
          type: 'github',
          data: {
            type: 'github',
            action: 'commit',
            repository,
            branch,
            commitSha: sha,
          },
        }),
      });

      console.log(`✅ Commit tracked: ${sha}`);
    } catch (error) {
      console.error('Failed to track commit:', error);
    }
  }

  /**
   * Track a pull request
   */
  async trackPullRequest(
    repository: string,
    prNumber: number,
    action: 'opened' | 'closed' | 'merged'
  ): Promise<void> {
    try {
      await fetch(`${this.config.apiUrl}/api/activity`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
        },
        body: JSON.stringify({
          sessionId: this.config.sessionId,
          type: 'github',
          data: {
            type: 'github',
            action: 'pull-request',
            repository,
            url: `https://github.com/${repository}/pull/${prNumber}`,
          },
        }),
      });

      console.log(`✅ PR #${prNumber} ${action} tracked`);
    } catch (error) {
      console.error('Failed to track PR:', error);
    }
  }

  /**
   * Fetch recent GitHub activity from GitHub API
   */
  async fetchRecentActivity(): Promise<any[]> {
    if (!this.config.githubToken) {
      console.warn('GitHub token not provided, skipping fetch');
      return [];
    }

    try {
      const username = await this.getUsername();
      const response = await fetch(
        `https://api.github.com/users/${username}/events/public`,
        {
          headers: {
            Authorization: `Bearer ${this.config.githubToken}`,
            Accept: 'application/vnd.github.v3+json',
          },
        }
      );

      const events = await response.json();
      return events;
    } catch (error) {
      console.error('Failed to fetch GitHub activity:', error);
      return [];
    }
  }

  /**
   * Get authenticated user's username
   */
  private async getUsername(): Promise<string> {
    if (!this.config.githubToken) {
      throw new Error('GitHub token required');
    }

    const response = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `Bearer ${this.config.githubToken}`,
        Accept: 'application/vnd.github.v3+json',
      },
    });

    const user = await response.json();
    return user.login;
  }
}

// Example usage
async function example() {
  const integration = new GitHubIntegration({
    apiUrl: 'https://your-worker.workers.dev',
    userId: 'user-123',
    sessionId: 'session-456',
    githubToken: process.env.GITHUB_TOKEN,
  });

  // Track a commit
  await integration.trackCommit(
    'OWASP-BLT/Fresh',
    'abc123def456',
    'main'
  );

  // Track a PR
  await integration.trackPullRequest(
    'OWASP-BLT/Fresh',
    42,
    'opened'
  );

  // Fetch recent activity
  const activities = await integration.fetchRecentActivity();
  console.log(`Found ${activities.length} recent GitHub events`);
}

export default GitHubIntegration;
