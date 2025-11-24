/**
 * Durable Object for managing real-time tracking sessions
 * Provides WebSocket support for live activity tracking
 */

import { TimeTrackingSession, ActivityEvent } from '../types';

export class TrackerSession {
  private state: DurableObjectState;
  private session: TimeTrackingSession | null = null;
  private activities: ActivityEvent[] = [];
  private connections: Set<WebSocket> = new Set();

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Handle WebSocket upgrade
    if (request.headers.get('Upgrade') === 'websocket') {
      return this.handleWebSocket(request);
    }

    // Handle HTTP requests
    switch (url.pathname) {
      case '/start':
        return this.handleStart(request);
      case '/end':
        return this.handleEnd(request);
      case '/activity':
        return this.handleActivity(request);
      case '/status':
        return this.handleStatus(request);
      default:
        return new Response('Not found', { status: 404 });
    }
  }

  /**
   * Handle WebSocket connection for real-time updates
   */
  private async handleWebSocket(request: Request): Promise<Response> {
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    this.connections.add(server);

    server.accept();
    server.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data as string);
        this.handleWebSocketMessage(data);
      } catch (error) {
      }
    });

    server.addEventListener('close', () => {
      this.connections.delete(server);
    });

    return new Response(null, {
      status: 101,
      webSocket: client,
    });
  }

  /**
   * Handle WebSocket messages
   */
  private handleWebSocketMessage(data: any): void {
    if (data.type === 'ping') {
      this.broadcast({ type: 'pong', timestamp: Date.now() });
    }
  }

  /**
   * Broadcast message to all connected clients
   */
  private broadcast(message: any): void {
    const payload = JSON.stringify(message);
    this.connections.forEach((ws) => {
      try {
        ws.send(payload);
      } catch (error) {
      }
    });
  }

  /**
   * Start tracking session
   */
  private async handleStart(request: Request): Promise<Response> {
    try {
      const body = await request.json() as { userId: string; projectId: string };
      const { userId, projectId } = body;

      this.session = {
        id: crypto.randomUUID(),
        userId,
        projectId,
        startTime: Date.now(),
        status: 'active',
      };

      await this.state.storage.put('session', this.session);
      this.broadcast({ type: 'session-started', session: this.session });

      return new Response(JSON.stringify({ session: this.session }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      return new Response('Failed to start session', { status: 500 });
    }
  }

  /**
   * End tracking session
   */
  private async handleEnd(request: Request): Promise<Response> {
    try {
      if (!this.session) {
        return new Response('No active session', { status: 404 });
      }

      this.session.endTime = Date.now();
      this.session.duration = this.session.endTime - this.session.startTime;
      this.session.status = 'completed';

      await this.state.storage.put('session', this.session);
      this.broadcast({ type: 'session-ended', session: this.session });

      return new Response(JSON.stringify({ session: this.session }), {
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      return new Response('Failed to end session', { status: 500 });
    }
  }

  /**
   * Record activity
   */
  private async handleActivity(request: Request): Promise<Response> {
    try {
      const activity: ActivityEvent = await request.json();

      this.activities.push(activity);
      await this.state.storage.put('activities', this.activities);

      // Broadcast activity to connected clients
      this.broadcast({ type: 'activity', activity });

      return new Response(JSON.stringify({ activity }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      return new Response('Failed to record activity', { status: 500 });
    }
  }

  /**
   * Get session status
   */
  private async handleStatus(request: Request): Promise<Response> {
    try {
      return new Response(
        JSON.stringify({
          session: this.session,
          activityCount: this.activities.length,
          connections: this.connections.size,
        }),
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );
    } catch (error) {
      return new Response('Failed to get status', { status: 500 });
    }
  }
}
