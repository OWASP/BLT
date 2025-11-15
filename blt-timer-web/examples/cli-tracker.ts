#!/usr/bin/env node

/**
 * CLI Time Tracker
 * Command-line interface for tracking development time
 */

import { spawn } from 'child_process';
import * as readline from 'readline';

interface TrackerConfig {
  apiUrl: string;
  userId: string;
  projectId: string;
}

class CLITracker {
  private config: TrackerConfig;
  private sessionId: string | null = null;
  private gitWatcher: any = null;

  constructor(config: TrackerConfig) {
    this.config = config;
  }

  async start(): Promise<void> {
    console.log('🚀 Starting time tracking session...');

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

      console.log(`✅ Session started: ${this.sessionId}`);
      console.log('📊 Tracking: Git activity, Agent prompts');
      console.log('⏸️  Press Ctrl+C to stop tracking\n');

      // Start monitoring Git
      this.startGitMonitoring();

      // Handle graceful shutdown
      process.on('SIGINT', () => this.stop());
    } catch (error) {
      console.error('❌ Failed to start session:', error);
      process.exit(1);
    }
  }

  async stop(): Promise<void> {
    if (!this.sessionId) {
      process.exit(0);
      return;
    }

    console.log('\n⏹️  Stopping time tracking session...');

    try {
      const response = await fetch(
        `${this.config.apiUrl}/api/sessions/${this.sessionId}/end`,
        {
          method: 'POST',
          headers: {
            'X-User-ID': this.config.userId,
          },
        }
      );

      const data = await response.json();
      const duration = Math.floor((data.session.duration || 0) / 1000 / 60);

      console.log(`✅ Session ended`);
      console.log(`⏱️  Total time: ${duration} minutes`);

      // Get summary
      await this.printSummary();

      process.exit(0);
    } catch (error) {
      console.error('❌ Failed to stop session:', error);
      process.exit(1);
    }
  }

  private startGitMonitoring(): void {
    // Watch for git commits
    const gitLog = spawn('git', ['log', '--follow', '--oneline', '-1']);
    
    gitLog.stdout.on('data', (data) => {
      const commit = data.toString().trim();
      if (commit) {
        this.trackGitCommit(commit);
      }
    });

    // Poll for new commits every 30 seconds
    setInterval(() => {
      const gitLog = spawn('git', ['log', '--follow', '--oneline', '-1']);
      gitLog.stdout.on('data', (data) => {
        const commit = data.toString().trim();
        if (commit) {
          this.trackGitCommit(commit);
        }
      });
    }, 30000);
  }

  private async trackGitCommit(commit: string): Promise<void> {
    if (!this.sessionId) return;

    try {
      const [sha, ...messageParts] = commit.split(' ');
      const message = messageParts.join(' ');

      await fetch(`${this.config.apiUrl}/api/activity`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': this.config.userId,
        },
        body: JSON.stringify({
          sessionId: this.sessionId,
          type: 'github',
          data: {
            type: 'github',
            action: 'commit',
            repository: await this.getRepoName(),
            commitSha: sha,
          },
        }),
      });

      console.log(`📝 Tracked commit: ${sha.substring(0, 7)} - ${message}`);
    } catch (error) {
      console.error('Failed to track commit:', error);
    }
  }

  private async getRepoName(): Promise<string> {
    return new Promise((resolve) => {
      const git = spawn('git', ['remote', 'get-url', 'origin']);
      let output = '';

      git.stdout.on('data', (data) => {
        output += data.toString();
      });

      git.on('close', () => {
        const match = output.match(/github\.com[:/](.+?)\.git/);
        resolve(match ? match[1] : 'unknown');
      });
    });
  }

  private async printSummary(): Promise<void> {
    if (!this.sessionId) return;

    try {
      const response = await fetch(
        `${this.config.apiUrl}/api/sessions/${this.sessionId}/summary`,
        {
          headers: {
            'X-User-ID': this.config.userId,
          },
        }
      );

      const { summary } = await response.json();

      console.log('\n📊 Session Summary:');
      console.log(`   GitHub Events: ${summary.githubEvents}`);
      console.log(`   Agent Prompts: ${summary.agentPrompts}`);
      console.log(`   Productivity: ${summary.productivity.toUpperCase()}`);
      console.log('');
    } catch (error) {
      console.error('Failed to get summary:', error);
    }
  }
}

// CLI Interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function prompt(question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

async function main() {
  console.log('🕐 Fresh Time Tracker CLI\n');

  const apiUrl = await prompt('API URL (default: http://localhost:8787): ') || 'http://localhost:8787';
  const userId = await prompt('User ID: ');
  const projectId = await prompt('Project ID: ');

  if (!userId || !projectId) {
    console.error('❌ User ID and Project ID are required');
    process.exit(1);
  }

  rl.close();

  const tracker = new CLITracker({
    apiUrl,
    userId,
    projectId,
  });

  await tracker.start();
}

if (require.main === module) {
  main();
}

export default CLITracker;
