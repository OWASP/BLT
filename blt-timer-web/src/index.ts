/**
 * Fresh Time Tracker - Main Entry Point
 * Privacy-focused time tracking system with local LLM analysis
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { Env } from './types';
import routes from './api/routes';

// Export Durable Object
export { TrackerSession } from './durable-objects/tracker-session';

const app = new Hono<{ Bindings: Env }>();

// Enable CORS for client applications
app.use('/*', cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'X-User-ID', 'X-Session-ID'],
}));

// Mount API routes
app.route('/', routes);

// Root endpoint
app.get('/', (c) => {
  return c.json({
    name: 'Fresh Time Tracker',
    version: '1.0.0',
    description: 'Privacy-focused time tracking system',
    endpoints: {
      health: '/health',
      sessions: {
        start: 'POST /api/sessions/start',
        end: 'POST /api/sessions/:sessionId/end',
        pause: 'POST /api/sessions/:sessionId/pause',
        resume: 'POST /api/sessions/:sessionId/resume',
        get: 'GET /api/sessions/:sessionId',
        list: 'GET /api/sessions',
        activities: 'GET /api/sessions/:sessionId/activities',
        summary: 'GET /api/sessions/:sessionId/summary',
      },
      activity: {
        track: 'POST /api/activity',
      },
      webhooks: {
        github: 'POST /api/webhooks/github',
      },
    },
    features: {
      githubIntegration: true,
      keyboardTracking: true,
      mouseTracking: true,
      agentPromptTracking: true,
      screenshotAnalysis: true,
      localLLMOnly: true,
      cloudflareWorker: true,
    },
    privacy: {
      dataStorage: 'Cloudflare KV (encrypted)',
      screenshotProcessing: 'Local only - never uploaded',
      llmAnalysis: 'Local models only - no 3rd party',
      dataSecurity: 'End-to-end encryption',
    },
  });
});

export default app;
