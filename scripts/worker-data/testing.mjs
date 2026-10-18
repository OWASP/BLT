// Test doubles for Workers that use kv-data.js: an in-memory KV namespace, a static ASSETS
// binding and a fetch stub. Used by the node --test suites of each project.

export class MemoryKV {
  constructor(entries = {}) {
    this.store = new Map();
    this.puts = [];
    for (const [key, value] of Object.entries(entries)) this.store.set(key, { value, metadata: null });
  }

  #decode(entry, options) {
    if (!entry) return null;
    const type = typeof options === "string" ? options : options && options.type;
    if (type === "json") return JSON.parse(entry.value);
    if (type === "stream") return new Response(entry.value).body;
    return entry.value;
  }

  async get(key, options) {
    return this.#decode(this.store.get(key), options);
  }

  async getWithMetadata(key, options) {
    const entry = this.store.get(key);
    return { value: this.#decode(entry, options), metadata: entry ? entry.metadata : null };
  }

  async put(key, value, options = {}) {
    this.puts.push(key);
    this.store.set(key, { value: String(value), metadata: options.metadata || null });
  }

  text(key) {
    const entry = this.store.get(key);
    return entry ? entry.value : null;
  }
}

// files: {"/path": string | object}
export function staticAssets(files = {}) {
  return {
    requests: [],
    async fetch(request) {
      const url = new URL(typeof request === "string" ? request : request.url);
      this.requests.push(url.pathname);
      if (!(url.pathname in files)) return new Response("Not found", { status: 404 });
      const body = files[url.pathname];
      return new Response(typeof body === "string" ? body : JSON.stringify(body), {
        headers: { "content-type": "application/octet-stream", "x-static": "1" },
      });
    },
  };
}

// Replace globalThis.fetch with `handler(url, init)` (returning a Response or a plain object that
// becomes a JSON response). Returns {calls, restore}.
export function stubFetch(handler) {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (input, init = {}) => {
    const url = typeof input === "string" ? input : input.url;
    calls.push({ url, init });
    const result = await handler(url, init);
    if (result instanceof Response) return result;
    return Response.json(result);
  };
  return { calls, restore: () => { globalThis.fetch = original; } };
}

export function cronRequest(body = {}, secret = "s3cret") {
  return new Request("https://worker.test/__scheduled", {
    method: "POST",
    headers: { "content-type": "application/json", "x-blt-cron-secret": secret },
    body: JSON.stringify(body),
  });
}
