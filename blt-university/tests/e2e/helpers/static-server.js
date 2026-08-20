const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');

const root = path.resolve(process.env.PLAYWRIGHT_SITE_DIR || 'public');
const host = '127.0.0.1';
const port = 4173;
const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2'
};

const server = http.createServer(async (request, response) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end('Method not allowed');
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(request.url, `http://${host}`).pathname);
  } catch (_error) {
    response.writeHead(400).end('Invalid URL');
    return;
  }

  const requestedFile = pathname.endsWith('/') ? `${pathname}index.html` : pathname;
  const filePath = path.resolve(root, `.${requestedFile}`);

  if (filePath !== root && !filePath.startsWith(`${root}${path.sep}`)) {
    response.writeHead(403).end('Forbidden');
    return;
  }

  try {
    const body = await fs.readFile(filePath);
    const headers = { 'Content-Type': contentTypes[path.extname(filePath)] || 'application/octet-stream' };
    response.writeHead(200, headers).end(request.method === 'HEAD' ? undefined : body);
  } catch (error) {
    const status = error.code === 'ENOENT' ? 404 : 500;
    response.writeHead(status).end(status === 404 ? 'Not found' : 'Server error');
  }
});

server.listen(port, host);
