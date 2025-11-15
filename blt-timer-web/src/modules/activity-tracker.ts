/**
 * Activity Tracker
 * Tracks keyboard and mouse activity (client-side component)
 */

import { ActivityEvent, KeyboardActivityData, MouseActivityData } from '../types';

export class ActivityTracker {
  private userId: string;
  private sessionId: string;
  private keyboardBuffer: { count: number; activeTime: number; idleTime: number };
  private mouseBuffer: { clicks: number; distance: number; activeTime: number };
  private lastActivityTime: number;

  constructor(userId: string, sessionId: string) {
    this.userId = userId;
    this.sessionId = sessionId;
    this.keyboardBuffer = { count: 0, activeTime: 0, idleTime: 0 };
    this.mouseBuffer = { clicks: 0, distance: 0, activeTime: 0 };
    this.lastActivityTime = Date.now();
  }

  /**
   * Record keyboard activity
   * Note: This would be implemented client-side for privacy
   */
  recordKeyboardActivity(keyCount: number, duration: number): ActivityEvent {
    this.keyboardBuffer.count += keyCount;
    this.keyboardBuffer.activeTime += duration;

    const event: ActivityEvent = {
      id: crypto.randomUUID(),
      sessionId: this.sessionId,
      userId: this.userId,
      type: 'keyboard',
      timestamp: Date.now(),
      data: {
        type: 'keyboard',
        keyCount,
        activeTime: duration,
        idleTime: 0,
      },
    };

    this.lastActivityTime = Date.now();
    return event;
  }

  /**
   * Record mouse activity
   * Note: This would be implemented client-side for privacy
   */
  recordMouseActivity(clicks: number, distance: number, duration: number): ActivityEvent {
    this.mouseBuffer.clicks += clicks;
    this.mouseBuffer.distance += distance;
    this.mouseBuffer.activeTime += duration;

    const event: ActivityEvent = {
      id: crypto.randomUUID(),
      sessionId: this.sessionId,
      userId: this.userId,
      type: 'mouse',
      timestamp: Date.now(),
      data: {
        type: 'mouse',
        clickCount: clicks,
        moveDistance: distance,
        activeTime: duration,
      },
    };

    this.lastActivityTime = Date.now();
    return event;
  }

  /**
   * Get aggregated activity data
   */
  getAggregatedActivity(): {
    keyboard: KeyboardActivityData;
    mouse: MouseActivityData;
  } {
    return {
      keyboard: {
        type: 'keyboard',
        keyCount: this.keyboardBuffer.count,
        activeTime: this.keyboardBuffer.activeTime,
        idleTime: this.keyboardBuffer.idleTime,
      },
      mouse: {
        type: 'mouse',
        clickCount: this.mouseBuffer.clicks,
        moveDistance: this.mouseBuffer.distance,
        activeTime: this.mouseBuffer.activeTime,
      },
    };
  }

  /**
   * Reset buffers (called after sync)
   */
  resetBuffers(): void {
    this.keyboardBuffer = { count: 0, activeTime: 0, idleTime: 0 };
    this.mouseBuffer = { clicks: 0, distance: 0, activeTime: 0 };
  }

  /**
   * Check if idle based on last activity
   */
  isIdle(idleThresholdMs: number = 300000): boolean {
    return Date.now() - this.lastActivityTime > idleThresholdMs;
  }
}
