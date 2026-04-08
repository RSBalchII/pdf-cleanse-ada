#!/usr/bin/env node
/**
 * Simple HTTP server for testing the HTML UI
 * Usage: node serve.js [port]
 */

import { createServer } from 'http';
import { createReadStream } from 'fs';
import { extname, join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PORT = process.argv[2] || 3000;

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = createServer((req, res) => {
  let filePath = join(__dirname, req.url === '/' ? 'index.html' : req.url);

  const ext = extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  createReadStream(filePath)
    .on('error', (err) => {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('File not found');
    })
    .pipe(res);
});

server.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════╗
║  PDF ADA Compliance Processor - Local Server             ║
╠═══════════════════════════════════════════════════════════╣
║  Server running at:                                       ║
║  → http://localhost:${PORT}                                ║
║                                                           ║
║  Press Ctrl+C to stop                                    ║
╚═══════════════════════════════════════════════════════════╝
  `);
});
