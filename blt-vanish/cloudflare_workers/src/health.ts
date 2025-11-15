/**
 * Broker health check endpoint
 * Checks if broker websites are accessible - NO PII involved
 */

export async function handleHealthCheck(
  request: Request,
  path: string
): Promise<Response> {
  const brokerId = path.split('/api/health/')[1];

  if (!brokerId) {
    return new Response(
      JSON.stringify({ error: 'Broker ID required' }),
      {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  // Perform health check
  const health = await checkBrokerHealth(brokerId);

  return new Response(JSON.stringify(health), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function checkBrokerHealth(brokerId: string): Promise<any> {
  // Map of broker IDs to their opt-out URLs
  const brokerUrls: Record<string, string> = {
    whitepages: 'https://www.whitepages.com/suppression-requests',
    spokeo: 'https://www.spokeo.com/optout',
    beenverified: 'https://www.beenverified.com/app/optout/search',
    truthfinder: 'https://www.truthfinder.com/opt-out/',
    intelius: 'https://www.intelius.com/opt-out/',
  };

  const url = brokerUrls[brokerId];

  if (!url) {
    return {
      brokerId,
      status: 'unknown',
      message: 'Broker not found',
      checkedAt: new Date().toISOString(),
    };
  }

  try {
    // Perform HEAD request to check availability
    const response = await fetch(url, {
      method: 'HEAD',
      headers: {
        'User-Agent': 'SelfErase-HealthCheck/1.0',
      },
      // Timeout after 5 seconds
      signal: AbortSignal.timeout(5000),
    });

    const isHealthy = response.status >= 200 && response.status < 400;

    return {
      brokerId,
      status: isHealthy ? 'healthy' : 'degraded',
      httpStatus: response.status,
      message: isHealthy
        ? 'Broker site is accessible'
        : 'Broker site may be experiencing issues',
      checkedAt: new Date().toISOString(),
      url,
    };
  } catch (error) {
    return {
      brokerId,
      status: 'error',
      message: 'Failed to check broker health',
      error: error instanceof Error ? error.message : 'Unknown error',
      checkedAt: new Date().toISOString(),
      url,
    };
  }
}
