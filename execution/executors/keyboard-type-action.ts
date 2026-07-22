import {
  getMidsceneLocationSchema,
  z,
  type DeviceAction,
  type LocateResultElement,
} from '@midscene/core';

export type KeyboardTypeMode = 'replace' | 'append' | 'typeOnly' | 'clear';

export interface KeyboardTypeTextParam {
  value: string;
  locate?: LocateResultElement;
  mode?: KeyboardTypeMode;
  keyDelayMs?: number;
}

type PressKey = (keyName: string, target?: LocateResultElement) => Promise<void>;

export interface KeyboardTypeTextActionBundle {
  action: DeviceAction<KeyboardTypeTextParam, void>;
  setPressKey: (pressKey: PressKey) => void;
}

const DEFAULT_KEY_DELAY_MS = 50;

const keyboardTypeTextParamSchema = z.object({
  value: z
    .union([z.string(), z.number()])
    .transform((value) => String(value))
    .describe('The ASCII text to input without using clipboard paste.'),
  locate: getMidsceneLocationSchema()
    .describe('The position of the target input field. If there is no content, locate the center of the input field.')
    .optional(),
  mode: z.enum(['replace', 'clear', 'typeOnly', 'append']).default('replace'),
  keyDelayMs: z.number().optional(),
});

const shiftedSymbols: Record<string, string> = {
  '~': '`',
  '!': '1',
  '@': '2',
  '#': '3',
  $: '4',
  '%': '5',
  '^': '6',
  '&': '7',
  '*': '8',
  '(': '9',
  ')': '0',
  _: '-',
  '+': '=',
  '{': '[',
  '}': ']',
  '|': '\\',
  ':': ';',
  '"': "'",
  '<': ',',
  '>': '.',
  '?': '/',
};

const plainSymbols = new Set(['`', '-', '=', '[', ']', '\\', ';', "'", ',', '.', '/']);

function charCodePoint(char: string): string {
  return `U+${char.codePointAt(0)?.toString(16).toUpperCase().padStart(4, '0') ?? 'UNKNOWN'}`;
}

export function textToKeyboardSequence(value: string): string[] {
  const keys: string[] = [];

  for (const char of value) {
    if (/^[a-z0-9]$/.test(char)) {
      keys.push(char);
      continue;
    }

    if (/^[A-Z]$/.test(char)) {
      keys.push(`Shift+${char}`);
      continue;
    }

    if (char === ' ') {
      keys.push('Space');
      continue;
    }

    if (plainSymbols.has(char)) {
      keys.push(char);
      continue;
    }

    const shiftedBase = shiftedSymbols[char];
    if (shiftedBase) {
      keys.push(`Shift+${shiftedBase}`);
      continue;
    }

    throw new Error(`KeyboardTypeText 不支持字符 "${char}" (${charCodePoint(char)})，当前仅支持 ASCII 键盘输入`);
  }

  return keys;
}

async function delay(ms: number): Promise<void> {
  if (ms <= 0) return;
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function pressWithDelay(
  pressKey: PressKey,
  keyName: string,
  keyDelayMs: number,
  target?: LocateResultElement,
): Promise<void> {
  await pressKey(keyName, target);
  await delay(keyDelayMs);
}

export function createKeyboardTypeTextAction(): KeyboardTypeTextActionBundle {
  let pressKey: PressKey = async () => {
    throw new Error('KeyboardTypeText 尚未绑定 KeyboardPress 动作');
  };

  const action: DeviceAction<KeyboardTypeTextParam, void> = {
    name: 'KeyboardTypeText',
    description:
      'Type ASCII text through physical keyboard events without clipboard paste. Use this when clipboard-based input is unavailable.',
    sample: {
      value: '47405',
      mode: 'replace',
    },
    call: async (param) => {
      if (!param || typeof param.value !== 'string') {
        throw new Error('KeyboardTypeText 参数 value 必须是字符串');
      }

      const mode = param.mode === 'append' ? 'typeOnly' : (param.mode ?? 'replace');
      const keyDelayMs = param.keyDelayMs ?? DEFAULT_KEY_DELAY_MS;
      let shouldFocusTarget = Boolean(param.locate);

      if (mode === 'replace') {
        await pressWithDelay(pressKey, 'Control+A', keyDelayMs, param.locate);
        shouldFocusTarget = false;
        await pressWithDelay(pressKey, 'Backspace', keyDelayMs);
      }

      if (mode === 'clear') {
        await pressWithDelay(pressKey, 'Control+A', keyDelayMs, param.locate);
        await pressWithDelay(pressKey, 'Backspace', keyDelayMs);
        return;
      }

      for (const keyName of textToKeyboardSequence(param.value)) {
        await pressWithDelay(pressKey, keyName, keyDelayMs, shouldFocusTarget ? param.locate : undefined);
        shouldFocusTarget = false;
      }
    },
    paramSchema: keyboardTypeTextParamSchema as unknown as DeviceAction<KeyboardTypeTextParam, void>['paramSchema'],
  };

  return {
    action,
    setPressKey: (nextPressKey) => {
      pressKey = nextPressKey;
    },
  };
}
