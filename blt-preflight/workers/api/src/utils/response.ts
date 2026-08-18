/**
 * Shared response helpers
 */

export function json(data: unknown, status = 200, headers: Record<string, string> = {}): Response {
    return new Response(JSON.stringify(data, null, 2), {
      status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        ...headers,
      },
    });
  }
  
  export function error(message: string, status = 400, extra: Record<string, unknown> = {}): Response {
    return json(
      {
        error: true,
        message,
        ...extra,
      },
      status
    );
  }