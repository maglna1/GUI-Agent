import dotenv from 'dotenv';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { packageRoot } from '../cua/package-root.js';

const fileValues: Record<string, string> = {};
for (const filename of ['.env', '.env.local']) {
  try {
    Object.assign(fileValues, dotenv.parse(readFileSync(path.join(packageRoot, filename))));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
  }
}
for (const [key, value] of Object.entries(fileValues)) {
  if (key !== 'CUA_DATA_ROOT' && process.env[key] === undefined) process.env[key] = value;
}

export function warnIfNodeVersionIsOld(): void {
  const [major = 0, minor = 0] = process.versions.node.split('.').map(Number);
  if (major < 18 || (major === 18 && minor < 19)) {
    console.warn(
      `Warning: @midscene/computer declares Node >=18.19.0; current Node is ${process.versions.node}. Upgrade Node if model calls fail unexpectedly.`,
    );
  }
}

export const requiredModelEnv = [
  'MIDSCENE_MODEL_BASE_URL',
  'MIDSCENE_MODEL_NAME',
  'MIDSCENE_MODEL_API_KEY',
  'MIDSCENE_MODEL_FAMILY',
] as const;

export function checkRequiredModelEnv(): void {
  const missing = requiredModelEnv.filter((name) => !process.env[name]);
  if (missing.length > 0) {
    throw new Error(`Missing required env vars: ${missing.join(', ')}`);
  }
}
