import { agentForComputer } from '@midscene/computer';
import { createKeyboardTypeTextAction } from './keyboard-type-action.js';

export type ComputerAgent = Awaited<ReturnType<typeof agentForComputer>>;
export type ComputerAgentOptions = NonNullable<Parameters<typeof agentForComputer>[0]>;

export async function createKeyboardEnabledComputerAgent(
  options: ComputerAgentOptions,
): Promise<ComputerAgent> {
  const keyboardTypeText = createKeyboardTypeTextAction();
  const customActions = [...(options.customActions ?? []), keyboardTypeText.action];
  const agent = await agentForComputer({ ...options, customActions });
  const keyboard = agent.interface.inputPrimitives?.keyboard;
  if (!keyboard?.keyboardPress) {
    await agent.destroy();
    throw new Error('当前 Midscene computer interface 不支持底层 keyboardPress 输入');
  }
  keyboardTypeText.setPressKey(async (keyName, target) => {
    await keyboard.keyboardPress(keyName, { target });
  });
  return agent;
}
