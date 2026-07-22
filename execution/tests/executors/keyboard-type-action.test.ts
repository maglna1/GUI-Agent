import assert from 'node:assert/strict';
import test from 'node:test';
import { createKeyboardTypeTextAction, textToKeyboardSequence } from '../../executors/keyboard-type-action.js';

test('ASCII 文本映射为底层键盘序列', () => {
  assert.deepEqual(textToKeyboardSequence('47405'), ['4', '7', '4', '0', '5']);
  assert.deepEqual(textToKeyboardSequence('QATAR AIRWAYS'), [
    'Shift+Q', 'Shift+A', 'Shift+T', 'Shift+A', 'Shift+R', 'Space',
    'Shift+A', 'Shift+I', 'Shift+R', 'Shift+W', 'Shift+A', 'Shift+Y', 'Shift+S',
  ]);
  assert.deepEqual(textToKeyboardSequence('abc_123@example.com'), [
    'a', 'b', 'c', 'Shift+-', '1', '2', '3', 'Shift+2', 'e', 'x', 'a', 'm', 'p', 'l', 'e', '.', 'c', 'o', 'm',
  ]);
  assert.throws(() => textToKeyboardSequence('中文'), /ASCII/);
});

test('KeyboardTypeText replace 先清空再逐键输入', async () => {
  const keyboardTypeText = createKeyboardTypeTextAction();
  const target = { center: [10, 20], rect: { left: 1, top: 2, width: 30, height: 40 } };
  const pressedKeys: Array<{ keyName: string; hasTarget: boolean }> = [];
  keyboardTypeText.setPressKey(async (keyName, pressedTarget) => {
    pressedKeys.push({ keyName, hasTarget: pressedTarget === target });
  });
  await keyboardTypeText.action.call({ locate: target as never, value: 'A', mode: 'replace', keyDelayMs: 0 });
  assert.deepEqual(pressedKeys, [
    { keyName: 'Control+A', hasTarget: true },
    { keyName: 'Backspace', hasTarget: false },
    { keyName: 'Shift+A', hasTarget: false },
  ]);
});
