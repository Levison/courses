# Notes: Appendix A (reference answers)

Code: [`files/src/textkit.ts`](files/src/textkit.ts).

## Exercise 1: `count_tokens_estimate` in TypeScript

`registerTool` with a zod `inputSchema`, an `outputSchema` of `z.object({ tokens: z.number().int() })`, and
`annotations: { readOnlyHint: true }`. Unlike the Python SDK, the TS SDK does not wrap primitives in `{ result }` for
you: `structuredContent` must be an object that matches `outputSchema`, so you choose the wrapper name yourself. Return
the text form in `content` too, for clients that ignore structured output.

## Exercise 2: Schema portability

`z.tuple([z.string(), z.number()])` compiles to JSON Schema 2020-12 `prefixItems` plus `items: false` (no extra items).
A bare boolean schema is valid JSON Schema, but some shipping MCP clients and LLM tool-schema converters only accept
object schemas, so `inspector --strict` flags it (exit 6). Other zod v4 outputs worth knowing (checked with
`z.toJSONSchema` on 2026-10-19): `z.never()` becomes `{"not": {}}` and `z.any()` becomes `{}` (both accept or reject
everything, which tells the model nothing); `z.union([z.string(), z.number()])` becomes `"type": ["string", "number"]`
(type arrays are rejected by some strict provider modes); and `.transform()` is invisible in the schema (input type only),
so the model is never told about the conversion. Prefer arrays of objects with named fields: they are portable and
easier for the model to fill in. Run `--strict` and a conformance harness in CI.
