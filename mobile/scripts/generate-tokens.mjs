// Generates src/theme/generated/tokens.ts from the design tokens in 00-docs (single source of truth).
// Run via `pnpm gen` / `make gen`. Output is committed and checked for drift in CI.
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(
  here,
  '../../00-docs/15-design/design/design-tokens.json',
);
const target = resolve(here, '../src/theme/generated/tokens.ts');

/** Replaces `{"$value": x}` leaves by `x`, recursively. */
function flatten(node) {
  if (node && typeof node === 'object' && '$value' in node) return node.$value;
  if (node && typeof node === 'object') {
    return Object.fromEntries(
      Object.entries(node)
        .filter(([key]) => !key.startsWith('$'))
        .map(([key, value]) => [key, flatten(value)]),
    );
  }
  return node;
}

const tokens = JSON.parse(readFileSync(source, 'utf8'));
const {meta, ...rest} = tokens;
const output = `// Generated from 00-docs/15-design/design/design-tokens.json by \`make gen\` - DO NOT EDIT.
// Design tokens version ${meta.version}.

export const designTokens = ${JSON.stringify(flatten(rest), null, 2)} as const;
`;

mkdirSync(dirname(target), {recursive: true});
writeFileSync(target, output);
console.log(`Wrote ${target}`);
