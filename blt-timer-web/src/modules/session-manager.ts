/**
 * Session Manager
 * Manages time tracking sessions with Durable Objects
 */

import {
  TimeTrackingSession,
  ActivityEvent,
  ActivitySummary,
  Env,
} from '../types';

export class SessionManager {
  private userId: string;
  private env: Env;

  constructor(userId: string, env: Env) {
    this.userId = userId;
    this.env = env;
  }

  /**
   * Start a new tracking session
   */
  async startSession(projectId: string): Promise<TimeTrackingSession> {
    const session: TimeTrackingSession = {
      id: crypto.randomUUID(),
      userId: this.userId,
      projectId,
      startTime: Date.now(),
      status: 'active',
    };

    await this.env.TIME_TRACKING_DATA.put(
      `session:${session.id}`,
      JSON.stringify(session)
    );

    return session;
  }

  /**
   * End a tracking session
   */
  async endSession(sessionId: string): Promise<TimeTrackingSession | null> {
    const sessionData = await this.env.TIME_TRACKING_DATA.get(`session:${sessionId}`);
    if (!sessionData) return null;

    const session: TimeTrackingSession = JSON.parse(sessionData);
    session.endTime = Date.now();
    session.duration = session.endTime - session.startTime;
    session.status = 'completed';

    await this.env.TIME_TRACKING_DATA.put(
      `session:${sessionId}`,
      JSON.stringify(session)
    );

    return session;
  }

  /**
   * Pause a tracking session
   */
  async pauseSession(sessionId: string): Promise<TimeTrackingSession | null> {
    const sessionData = await this.env.TIME_TRACKING_DATA.get(`session:${sessionId}`);
    if (!sessionData) return null;

    const session: TimeTrackingSession = JSON.parse(sessionData);
    session.status = 'paused';

    await this.env.TIME_TRACKING_DATA.put(
      `session:${sessionId}`,
      JSON.stringify(session)
    );

    return session;
  }

  /**
   * Resume a paused session
   */
  async resumeSession(sessionId: string): Promise<TimeTrackingSession | null> {
    const sessionData = await this.env.TIME_TRACKING_DATA.get(`session:${sessionId}`);
    if (!sessionData) return null;

    const session: TimeTrackingSession = JSON.parse(sessionData);
    session.status = 'active';

    await this.env.TIME_TRACKING_DATA.put(
      `session:${sessionId}`,
      JSON.stringify(session)
    );

    return session;
  }

  /**
   * Get session details
   */
  async getSession(sessionId: string): Promise<TimeTrackingSession | null> {
    const sessionData = await this.env.TIME_TRACKING_DATA.get(`session:${sessionId}`);
    if (!sessionData) return null;

    return JSON.parse(sessionData);
  }

  /**
   * Store activity event
   */
  async storeActivity(event: ActivityEvent): Promise<void> {
    await this.env.ACTIVITY_DATA.put(
      `activity:${event.id}`,
      JSON.stringify(event)
    );

    // Also add to session index
    const sessionKey = `session:${event.sessionId}:activities`;
    const activities = await this.env.ACTIVITY_DATA.get(sessionKey);
    const activityList = activities ? JSON.parse(activities) : [];
    activityList.push(event.id);
    await this.env.ACTIVITY_DATA.put(sessionKey, JSON.stringify(activityList));
  }

  /**
   * Get activities for a session
   */
  async getSessionActivities(sessionId: string): Promise<ActivityEvent[]> {
    const sessionKey = `session:${sessionId}:activities`;
    const activities = await this.env.ACTIVITY_DATA.get(sessionKey);
    if (!activities) return [];

    const activityIds: string[] = JSON.parse(activities);
    const events: ActivityEvent[] = [];

    for (const id of activityIds) {
      const eventData = await this.env.ACTIVITY_DATA.get(`activity:${id}`);
      if (eventData) {
        events.push(JSON.parse(eventData));
      }
    }

    return events;
  }

  /**
   * Generate activity summary for a session
   */
  async generateSummary(sessionId: string): Promise<ActivitySummary | null> {
    const session = await this.getSession(sessionId);
    if (!session) return null;

    const activities = await this.getSessionActivities(sessionId);

    const summary: ActivitySummary = {
      sessionId,
      totalDuration: session.duration || 0,
      activeTime: 0,
      idleTime: 0,
      githubEvents: 0,
      keyboardActivity: 0,
      mouseActivity: 0,
      agentPrompts: 0,
      screenshots: 0,
      productivity: 'medium',
    };

    activities.forEach((event) => {
      switch (event.type) {
        case 'github':
          summary.githubEvents++;
          break;
        case 'keyboard':
          summary.keyboardActivity++;
          summary.activeTime += (event.data as any).activeTime || 0;
          break;
        case 'mouse':
          summary.mouseActivity++;
          summary.activeTime += (event.data as any).activeTime || 0;
          break;
        case 'agent-prompt':
          summary.agentPrompts++;
          break;
        case 'screenshot':
          summary.screenshots++;
          break;
      }
    });

    // Calculate productivity based on activity
    const activityScore =
      summary.githubEvents * 3 +
      summary.keyboardActivity * 2 +
      summary.mouseActivity +
      summary.agentPrompts * 2;

    if (activityScore > 50) {
      summary.productivity = 'high';
    } else if (activityScore < 20) {
      summary.productivity = 'low';
    }

    return summary;
  }

  /**
   * List user's sessions
   */
  async listSessions(limit: number = 50): Promise<TimeTrackingSession[]> {
    // In production, you'd want to use a more efficient indexing strategy
    const sessions: TimeTrackingSession[] = [];
    const list = await this.env.TIME_TRACKING_DATA.list({ prefix: 'session:' });

    for (const key of list.keys) {
      const data = await this.env.TIME_TRACKING_DATA.get(key.name);
      if (data) {
        const session: TimeTrackingSession = JSON.parse(data);
        if (session.userId === this.userId) {
          sessions.push(session);
        }
      }
      if (sessions.length >= limit) break;
    }

    return sessions.sort((a, b) => b.startTime - a.startTime);
  }
}
