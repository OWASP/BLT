/**
 * API Routes for the time tracking system
 */

import { Hono } from 'hono';
import { Env } from '../types';
import { SessionManager } from '../modules/session-manager';
import { GitHubMonitor } from '../modules/github-monitor';

const app = new Hono<{ Bindings: Env }>();

/**
 * Health check endpoint
 */
app.get('/health', (c) => {
  return c.json({ status: 'healthy', timestamp: Date.now() });
});

/**
 * Start a new tracking session
 */
app.post('/api/sessions/start', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const { projectId } = await c.req.json();
    if (!projectId) {
      return c.json({ error: 'Project ID required' }, 400);
    }

    const manager = new SessionManager(userId, c.env);
    const session = await manager.startSession(projectId);

    return c.json({ session }, 201);
  } catch (error) {
    return c.json({ error: 'Failed to start session' }, 500);
  }
});

/**
 * End a tracking session
 */
app.post('/api/sessions/:sessionId/end', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const sessionId = c.req.param('sessionId');
    const manager = new SessionManager(userId, c.env);
    const session = await manager.endSession(sessionId);

    if (!session) {
      return c.json({ error: 'Session not found' }, 404);
    }

    return c.json({ session });
  } catch (error) {
    return c.json({ error: 'Failed to end session' }, 500);
  }
});

/**
 * Pause a tracking session
 */
app.post('/api/sessions/:sessionId/pause', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const sessionId = c.req.param('sessionId');
    const manager = new SessionManager(userId, c.env);
    const session = await manager.pauseSession(sessionId);

    if (!session) {
      return c.json({ error: 'Session not found' }, 404);
    }

    return c.json({ session });
  } catch (error) {
    return c.json({ error: 'Failed to pause session' }, 500);
  }
});

/**
 * Resume a tracking session
 */
app.post('/api/sessions/:sessionId/resume', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const sessionId = c.req.param('sessionId');
    const manager = new SessionManager(userId, c.env);
    const session = await manager.resumeSession(sessionId);

    if (!session) {
      return c.json({ error: 'Session not found' }, 404);
    }

    return c.json({ session });
  } catch (error) {
    return c.json({ error: 'Failed to resume session' }, 500);
  }
});

/**
 * Get session details
 */
app.get('/api/sessions/:sessionId', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const sessionId = c.req.param('sessionId');
    const manager = new SessionManager(userId, c.env);
    const session = await manager.getSession(sessionId);

    if (!session) {
      return c.json({ error: 'Session not found' }, 404);
    }

    return c.json({ session });
  } catch (error) {
    return c.json({ error: 'Failed to get session' }, 500);
  }
});

/**
 * List user sessions
 */
app.get('/api/sessions', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const limit = parseInt(c.req.query('limit') || '50');
    const manager = new SessionManager(userId, c.env);
    const sessions = await manager.listSessions(limit);

    return c.json({ sessions });
  } catch (error) {
    return c.json({ error: 'Failed to list sessions' }, 500);
  }
});

/**
 * Track activity event
 */
app.post('/api/activity', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const { sessionId, type, data } = await c.req.json();
    if (!sessionId || !type || !data) {
      return c.json({ error: 'Missing required fields' }, 400);
    }

    const manager = new SessionManager(userId, c.env);
    const event = {
      id: crypto.randomUUID(),
      sessionId,
      userId,
      type,
      timestamp: Date.now(),
      data,
    };

    await manager.storeActivity(event);
    return c.json({ event }, 201);
  } catch (error) {
    return c.json({ error: 'Failed to track activity' }, 500);
  }
});

/**
 * Get session activities
 */
app.get('/api/sessions/:sessionId/activities', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const sessionId = c.req.param('sessionId');
    const manager = new SessionManager(userId, c.env);
    const activities = await manager.getSessionActivities(sessionId);

    return c.json({ activities });
  } catch (error) {
    return c.json({ error: 'Failed to get activities' }, 500);
  }
});

/**
 * Get session summary
 */
app.get('/api/sessions/:sessionId/summary', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    if (!userId) {
      return c.json({ error: 'User ID required' }, 401);
    }

    const sessionId = c.req.param('sessionId');
    const manager = new SessionManager(userId, c.env);
    const summary = await manager.generateSummary(sessionId);

    if (!summary) {
      return c.json({ error: 'Session not found' }, 404);
    }

    return c.json({ summary });
  } catch (error) {
    return c.json({ error: 'Failed to generate summary' }, 500);
  }
});

/**
 * GitHub webhook endpoint
 */
app.post('/api/webhooks/github', async (c) => {
  try {
    const userId = c.req.header('X-User-ID');
    const sessionId = c.req.header('X-Session-ID');

    if (!userId || !sessionId) {
      return c.json({ error: 'User ID and Session ID required' }, 401);
    }

    const payload = await c.req.json();
    const monitor = new GitHubMonitor(userId, sessionId);
    const event = monitor.parseWebhook(payload);

    if (event) {
      const manager = new SessionManager(userId, c.env);
      await manager.storeActivity(event);
      return c.json({ event }, 201);
    }

    return c.json({ message: 'Event ignored' }, 200);
  } catch (error) {
    return c.json({ error: 'Failed to process webhook' }, 500);
  }
});

export default app;
