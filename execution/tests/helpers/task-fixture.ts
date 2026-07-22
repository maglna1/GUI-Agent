import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import type { JsonObject, SceneManifest, TaskManifest } from '../../cua/contracts/types.js';
import { writeJsonFile } from '../../cua/contracts/validation.js';
import { writeYamlDocument } from '../../cua/task/yaml-task.js';

export async function createTaskFixture(
  projectsRoot: string,
  options: { scene?: string; task?: string } = {},
): Promise<string> {
  const scene = options.scene ?? 'browser-demo';
  const task = options.task ?? 'search-demo';
  const sceneRoot = path.join(projectsRoot, scene);
  const taskRoot = path.join(sceneRoot, task);
  await mkdir(taskRoot, { recursive: true });
  const sceneManifest: SceneManifest = {
    schemaVersion: '0.1',
    scene,
    title: '浏览器示例',
    description: '测试场景',
  };
  const taskManifest: TaskManifest = {
    schemaVersion: '0.2',
    scene,
    task,
    title: '搜索示例',
    description: '测试任务',
    goal: '测试搜索',
    source: {
      tracePath: 'source/showui-trace.json',
      processedLogPath: 'source/processed-log-sc.json',
      conversionCommand: 'npm run cua -- task init-from-trace',
    },
    inputs: {
      'step-001-input': {
        type: 'string',
        label: '搜索词',
        description: '搜索内容',
        default: '默认关键词',
      },
    },
  };
  const document: JsonObject = {
    computer: {},
    agent: { groupName: task, groupDescription: '测试搜索', generateReport: true },
    tasks: [
      {
        name: 'step-001 | input',
        flow: [
          {
            KeyboardTypeText: {
              locate: '页面顶部搜索框',
              value: '{{step-001-input}}',
              mode: 'replace',
            },
          },
        ],
      },
      {
        name: 'step-002 | click',
        flow: [{ aiTap: '点击与 {{step-001-input}} 对应的候选项' }],
      },
    ],
  };
  await writeJsonFile(path.join(sceneRoot, 'scene.json'), sceneManifest);
  await writeJsonFile(path.join(taskRoot, 'task.json'), taskManifest);
  await writeYamlDocument(path.join(taskRoot, 'task.yaml'), document);
  await writeFile(path.join(sceneRoot, 'SKILL.md'), '# 测试场景\n', 'utf8');
  return taskRoot;
}
