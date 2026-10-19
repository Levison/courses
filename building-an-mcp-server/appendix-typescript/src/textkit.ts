// Shared server definition: the same factory backs stdio and HTTP, and both protocol eras.
import { McpServer } from '@modelcontextprotocol/server';
import * as z from 'zod/v4';

export function createServer(): McpServer {
    const server = new McpServer(
        { name: 'textkit-ts', version: '0.1.0' },
        { capabilities: { tools: {}, resources: {} }, instructions: 'Small text utilities (TypeScript twin of module 1).' }
    );

    server.registerTool(
        'word_stats',
        {
            description: 'Count words, unique words and sentences, and return the most frequent words.',
            inputSchema: z.object({
                text: z.string().min(1).max(100_000).describe('Text to analyse'),
                top_n: z.number().int().min(1).max(50).default(5)
            }),
            outputSchema: z.object({
                words: z.number().int(),
                unique_words: z.number().int(),
                sentences: z.number().int(),
                // Not z.tuple(): it emits `items: false`, which `inspector --strict` flags as unportable.
                top_words: z.array(z.object({ word: z.string(), count: z.number().int() }))
            }),
            annotations: { readOnlyHint: true, idempotentHint: true }
        },
        async ({ text, top_n }) => {
            const words = text.toLowerCase().match(/[a-z']+/g) ?? [];
            const counts = new Map<string, number>();
            for (const w of words) counts.set(w, (counts.get(w) ?? 0) + 1);
            const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, top_n);
            const result = {
                words: words.length,
                unique_words: counts.size,
                sentences: text.split(/[.!?]+/).filter(s => s.trim()).length,
                top_words: top.map(([word, count]) => ({ word, count }))
            };
            return { content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result };
        }
    );

    server.registerTool(
        'slugify',
        {
            description: 'Turn a title into a URL slug.',
            inputSchema: z.object({ title: z.string().max(500) })
        },
        async ({ title }) => {
            const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
            if (!slug) {
                // Tool-level failure the model can read and recover from.
                return { isError: true, content: [{ type: 'text', text: `Title ${JSON.stringify(title)} has no slug-able characters.` }] };
            }
            return { content: [{ type: 'text', text: slug }] };
        }
    );

    server.registerResource(
        'about',
        'textkit://about',
        { title: 'About textkit', mimeType: 'text/plain' },
        async uri => ({ contents: [{ uri: uri.href, text: 'textkit-ts: a TypeScript MCP server on SDK v2.' }] })
    );

    return server;
}
