import path from 'node:path';
import { fileURLToPath } from 'node:url';

const moduleParent = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const packageRoot = path.basename(moduleParent) === 'dist' ? path.dirname(moduleParent) : moduleParent;
