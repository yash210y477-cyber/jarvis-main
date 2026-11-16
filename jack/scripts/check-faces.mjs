#!/usr/bin/env node
// Which Jack face frames are in place, and which reactions they unlock.
//
// The portrait engine asks for one picture per expression; a missing file is
// simply skipped, so nothing tells you what is still absent. This reads the
// engine's own key list (never a hand copy) and reports:
//
//   node scripts/check-faces.mjs
//
// Green = the engine will show that face.

import { readFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const engine = join(root, 'public', 'living-portrait.js');
const folder = join(root, 'public', 'jack-faces');

const source = readFileSync(engine, 'utf8');
const idsLine = source.match(/const IDS = Object\.fromEntries\(\[([^\]]+)\]/);
if (!idsLine) {
  console.error('Could not read the face keys from public/living-portrait.js');
  process.exit(1);
}
const KEYS = [...idsLine[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);

// What each group of frames is for, in the engine's own words.
const GROUPS = {
  Base: ['rest'],
  'Blink + wake': ['closed', 'half'],
  'Eyes follow the cursor': [
    'right', 'left', 'up', 'down', 'ene', 'nne', 'nnw', 'wnw',
    'wsw', 'ssw', 'sse', 'ese', 'upright', 'downleft', 'downright',
  ],
  'Eye roll / shifty / side-eye': ['deadpan'],
  Expressions: [
    'shock', 'tongue', 'cross', 'angry', 'scrunch', 'winkr', 'winkl', 'raised',
    'puff', 'laugh', 'yawn', 'grin', 'kiss', 'cry', 'smug', 'scared', 'fish',
    'dizzy', 'ouch',
  ],
  'Hair colours': ['pink', 'blue', 'blonde'],
  'Idle acts': [
    'yawn1', 'yawn2', 'yawn4', 'whistle1', 'whistle2', 'sneeze1', 'sneeze2',
    'gum1', 'gum2', 'gum3', 'gumpop', 'hearts', 'stars', 'snore', 'shy',
    'sick', 'wind',
  ],
};

function pngSize(path) {
  const head = readFileSync(path).subarray(0, 33);
  if (head.toString('ascii', 1, 4) !== 'PNG') return null;
  return {
    width: head.readUInt32BE(16),
    height: head.readUInt32BE(20),
    channels: head[25] === 6 ? 4 : head[25] === 4 ? 2 : 3,
  };
}

const present = new Map();
let restSize = null;

for (const key of KEYS) {
  const path = join(folder, `${key}.png`);
  if (!existsSync(path)) continue;
  const size = pngSize(path);
  present.set(key, size);
  if (key === 'rest' && size) restSize = size;
}

const problems = [];
for (const [key, size] of present) {
  if (!size) {
    problems.push(`${key}.png is not a PNG file`);
    continue;
  }
  if (size.channels !== 4) problems.push(`${key}.png has no transparency`);
  if (restSize && key !== 'rest' && (size.width !== restSize.width || size.height !== restSize.height)) {
    problems.push(`${key}.png is ${size.width}x${size.height}, rest.png is ${restSize.width}x${restSize.height} (frames must line up)`);
  }
}

let ready = 0;
for (const [group, keys] of Object.entries(GROUPS)) {
  const have = keys.filter((k) => present.has(k));
  ready += have.length;
  const mark = have.length === keys.length ? '✔' : have.length ? '·' : '✗';
  console.log(`${mark} ${group}: ${have.length}/${keys.length}`);
  const missing = keys.filter((k) => !present.has(k));
  if (missing.length) console.log(`    missing: ${missing.join(', ')}`);
}

console.log(`\n${present.size}/${KEYS.length} pictures in public/jack-faces, ${ready} of the reaction groups complete`);
if (!present.has('rest')) {
  console.log('Without rest.png the portrait stays a still image.');
} else if (!present.has('closed') || !present.has('half')) {
  console.log('Without closed.png and half.png there is no blinking.');
}
if (problems.length) {
  console.log('\nFix these:');
  for (const line of problems) console.log(' - ' + line);
} else if (present.size > 1) {
  console.log('All present frames are PNGs with transparency and the same size as rest.png.');
}
