/**
 * SelfErase Cloudflare Workers
 * 
 * Stateless edge functions that serve PUBLIC data only.
 * NO USER PII IS EVER PROCESSED OR STORED.
 * 
 * Endpoints:
 * - GET /api/brokers - List all data brokers
 * - GET /api/brokers/:id - Get specific broker details
 * - GET /api/health/:id - Check broker site health
 * - GET /api/templates/:id - Get opt-out template
 * - GET /api/categories - Get broker categories
 */

import { handleBrokersRequest } from './brokers';
import { handleHealthCheck } from './health';
import { handleTemplatesRequest } from './templates';

// CORS headers for security
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

// Security headers
const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
};

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: corsHeaders,
      });
    }

    // Route requests
    try {
      let response: Response;

      if (path === '/api/brokers' || path.startsWith('/api/brokers/')) {
        response = await handleBrokersRequest(request, path);
      } else if (path.startsWith('/api/health/')) {
        response = await handleHealthCheck(request, path);
      } else if (path.startsWith('/api/templates/')) {
        response = await handleTemplatesRequest(request, path);
      } else if (path === '/api/categories') {
        response = await handleCategoriesRequest();
      } else if (path === '/' || path === '/api') {
        response = handleRootRequest();
      } else {
        response = new Response('Not Found', { status: 404 });
      }

      // Add security and CORS headers
      const headers = new Headers(response.headers);
      Object.entries({ ...corsHeaders, ...securityHeaders }).forEach(
        ([key, value]) => headers.set(key, value)
      );

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    } catch (error) {
      console.error('Worker error:', error);
      return new Response(
        JSON.stringify({ error: 'Internal server error' }),
        {
          status: 500,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders,
            ...securityHeaders,
          },
        }
      );
    }
  },
};

function handleRootRequest(): Response {
  const info = {
    name: 'SelfErase Workers API',
    version: '1.0.0',
    description: 'Stateless edge functions for public broker data',
    privacy: 'NO USER PII IS PROCESSED OR STORED',
    endpoints: {
      brokers: '/api/brokers',
      broker_detail: '/api/brokers/:id',
      health_check: '/api/health/:id',
      template: '/api/templates/:id',
      categories: '/api/categories',
    },
    documentation: 'https://github.com/OWASP-BLT/SelfErase',
  };

  return new Response(JSON.stringify(info, null, 2), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function handleCategoriesRequest(): Promise<Response> {
  // This would typically fetch from a KV store or external source
  // For now, return default categories
  const categories = [
    'People Search',
    'Data Broker',
    'Background Check',
    'Public Records',
    'Social Media',
    'Marketing',
  ];

  return new Response(JSON.stringify(categories), {
    headers: { 'Content-Type': 'application/json' },
  });
}
