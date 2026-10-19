// Streamable HTTP entry: `node dist/http.js` -> http://127.0.0.1:8770/mcp
// createMcpHandler serves 2026-07-28 per request and (default legacy: 'stateless') 2025-era clients too.
import { createServer as createHttpServer } from 'node:http';
import { createMcpHandler } from '@modelcontextprotocol/server';
import { toNodeHandler } from '@modelcontextprotocol/node';
import { createServer } from './textkit.js';

const PORT = Number(process.env.PORT ?? 8770);
const mcp = toNodeHandler(createMcpHandler(createServer));

createHttpServer((req, res) => {
    const host = req.headers.host ?? '';
    // Minimal DNS-rebinding guard: only answer to localhost Host headers.
    if (!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host)) {
        res.writeHead(421).end('Invalid Host header');
        return;
    }
    if (req.url === '/mcp') return mcp(req, res);
    res.writeHead(404).end();
}).listen(PORT, '127.0.0.1', () => console.error(`textkit-ts listening on http://127.0.0.1:${PORT}/mcp`));
