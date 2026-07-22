import { checkComputerEnvironment, version } from '@midscene/computer';
import { checkRequiredModelEnv, warnIfNodeVersionIsOld } from './env.js';

async function main(): Promise<void> {
  warnIfNodeVersionIsOld();
  checkRequiredModelEnv();

  const env = await checkComputerEnvironment();
  if (!env.available) {
    throw new Error(env.error ?? 'Midscene computer environment is unavailable.');
  }

  console.log(`@midscene/computer ${version()} ready on ${env.platform}; displays=${env.displays}`);
  console.log(`model=${process.env.MIDSCENE_MODEL_NAME}; family=${process.env.MIDSCENE_MODEL_FAMILY}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
