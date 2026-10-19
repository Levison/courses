// stdio entry: `node dist/server.js`
import { serveStdio } from '@modelcontextprotocol/server/stdio';
import { createServer } from './textkit.js';

serveStdio(createServer);
