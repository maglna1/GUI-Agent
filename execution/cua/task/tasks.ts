import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import type {
  JsonObject,
  ResolvedTaskResult,
  SceneManifest,
  TaskCatalogRoots,
  TaskManifest,
  TaskPaths,
} from '../contracts/types.js';
import { readSceneManifest, readTaskManifest } from '../contracts/validation.js';
import {
  readYamlDocument,
  resolveYamlInputs,
  validateRecordedTaskDocument,
} from './yaml-task.js';

async function isFile(sourcePath: string): Promise<boolean> {
  try {
    return (await stat(sourcePath)).isFile();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}

async function isDirectory(sourcePath: string): Promise<boolean> {
  try {
    return (await stat(sourcePath)).isDirectory();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}

export function requireIdentifier(value: string, label: string): string {
  if (!value || path.basename(value) !== value || value === '.' || value === '..' || /[\\/]/.test(value)) {
    throw new Error(`${label} 必须是单一目录标识：${value}`);
  }
  return value;
}

function candidateTaskPaths(
  scene: string,
  task: string,
  projectsRoot: string,
  origin: 'builtin' | 'user',
  writable: boolean,
): TaskPaths {
  const projects = path.resolve(projectsRoot);
  const taskRoot = path.resolve(projects, requireIdentifier(scene, 'scene'), requireIdentifier(task, 'task'));
  const relative = path.relative(projects, taskRoot);
  if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error(`任务路径越出 catalog：${taskRoot}`);
  const sceneRoot = path.dirname(taskRoot);
  return {
    origin,
    writable,
    sceneRoot,
    taskRoot,
    sceneManifestPath: path.join(sceneRoot, 'scene.json'),
    taskManifestPath: path.join(taskRoot, 'task.json'),
    taskYamlPath: path.join(taskRoot, 'task.yaml'),
  };
}

async function taskPaths(scene: string, task: string, catalog: TaskCatalogRoots): Promise<TaskPaths> {
  const candidates = [candidateTaskPaths(scene, task, catalog.builtinProjectsRoot, 'builtin', false)];
  if (catalog.userProjectsRoot) {
    candidates.push(candidateTaskPaths(scene, task, catalog.userProjectsRoot, 'user', true));
  }
  const existing: TaskPaths[] = [];
  for (const candidate of candidates) if (await isFile(candidate.taskManifestPath)) existing.push(candidate);
  if (existing.length > 1) {
    throw new Error(`任务 ${scene}/${task} 同时存在于内置与用户 catalog：${existing.map((item) => item.taskRoot).join(', ')}`);
  }
  if (!existing.length) {
    throw new Error(`任务不存在：${scene}/${task}\n已检查：${candidates.map((item) => item.taskRoot).join(', ')}`);
  }
  return existing[0];
}

function validateManifests(
  scene: SceneManifest,
  task: TaskManifest,
  requestedScene: string,
  requestedTask: string,
): void {
  if (scene.scene !== requestedScene) {
    throw new Error(`请求场景 ${requestedScene} 与 scene.json 标识 ${scene.scene} 不一致`);
  }
  if (task.scene !== requestedScene || task.task !== requestedTask) {
    throw new Error(`请求任务 ${requestedScene}/${requestedTask} 与 task.json 标识 ${task.scene}/${task.task} 不一致`);
  }
  for (const [field, value] of [
    ['scene.title', scene.title],
    ['task.title', task.title],
    ['task.goal', task.goal],
  ]) {
    if (!value.trim()) throw new Error(`${field} 必须是非空字符串`);
  }
  for (const [inputId, definition] of Object.entries(task.inputs)) {
    if (!inputId.trim()) throw new Error('input id 必须是非空字符串');
    if (!definition.label.trim()) throw new Error(`输入 ${inputId}.label 必须是非空字符串`);
  }
}

export async function resolveTask(options: {
  scene: string;
  task: string;
  catalog: TaskCatalogRoots;
  inputs?: Record<string, string>;
}): Promise<ResolvedTaskResult> {
  const paths = await taskPaths(options.scene, options.task, options.catalog);
  const [scene, manifest, document] = await Promise.all([
    readSceneManifest(paths.sceneManifestPath),
    readTaskManifest(paths.taskManifestPath),
    readYamlDocument(paths.taskYamlPath),
  ]);
  validateManifests(scene, manifest, options.scene, options.task);
  validateRecordedTaskDocument(document, manifest, paths.taskYamlPath);
  const resolved = resolveYamlInputs(document, manifest, options.inputs);
  return {
    document: resolved.document,
    manifest,
    sourcePath: paths.taskYamlPath,
    inputs: resolved.inputs,
    origin: paths.origin,
    writable: paths.writable,
  };
}

function catalogEntries(catalog: TaskCatalogRoots): Array<['builtin' | 'user', boolean, string]> {
  const entries: Array<['builtin' | 'user', boolean, string]> = [
    ['builtin', false, path.resolve(catalog.builtinProjectsRoot)],
  ];
  if (catalog.userProjectsRoot) entries.push(['user', true, path.resolve(catalog.userProjectsRoot)]);
  return entries;
}

export async function listScenes(catalog: TaskCatalogRoots): Promise<JsonObject[]> {
  const scenes = new Map<string, JsonObject>();
  for (const [origin, writable, root] of catalogEntries(catalog)) {
    if (!(await isDirectory(root))) {
      if (origin === 'user') continue;
      throw new Error(`读取${origin} 场景目录失败：${root}\n目录不存在`);
    }
    const entries = (await readdir(root, { withFileTypes: true })).filter((item) => item.isDirectory()).sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      const sceneRoot = path.join(root, entry.name);
      const manifest = await readSceneManifest(path.join(sceneRoot, 'scene.json'));
      if (manifest.scene !== entry.name) throw new Error(`场景目录 ${entry.name} 与 scene.json 标识 ${manifest.scene} 不一致`);
      const current = scenes.get(manifest.scene) ?? { ...manifest, origins: [], writable: false, sceneRoots: [] };
      (current.origins as string[]).push(origin);
      current.writable = Boolean(current.writable) || writable;
      (current.sceneRoots as string[]).push(sceneRoot);
      scenes.set(manifest.scene, current);
    }
  }
  return [...scenes.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([, value]) => value);
}

export async function describeTask(scene: string, task: string, catalog: TaskCatalogRoots): Promise<JsonObject> {
  const paths = await taskPaths(scene, task, catalog);
  const [manifest, document] = await Promise.all([
    readTaskManifest(paths.taskManifestPath),
    readYamlDocument(paths.taskYamlPath),
  ]);
  await resolveTask({ scene, task, catalog });
  const tasks = document.tasks as JsonObject[];
  return {
    ...manifest,
    origin: paths.origin,
    writable: paths.writable,
    taskRoot: paths.taskRoot,
    taskYamlPath: paths.taskYamlPath,
    taskCount: tasks.length,
    actionCount: tasks.reduce((count, item) => count + (item.flow as unknown[]).length, 0),
  };
}

export async function listTasks(scene: string, catalog: TaskCatalogRoots): Promise<JsonObject[]> {
  const discovered = new Map<string, TaskPaths[]>();
  for (const [origin, writable, root] of catalogEntries(catalog)) {
    const sceneRoot = path.join(root, scene);
    if (!(await isDirectory(sceneRoot))) continue;
    const manifest = await readSceneManifest(path.join(sceneRoot, 'scene.json'));
    if (manifest.scene !== scene) throw new Error(`请求场景 ${scene} 与 scene.json 标识 ${manifest.scene} 不一致`);
    const entries = (await readdir(sceneRoot, { withFileTypes: true })).filter((item) => item.isDirectory()).sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      const candidate = candidateTaskPaths(scene, entry.name, root, origin, writable);
      if (!(await isFile(candidate.taskManifestPath))) continue;
      discovered.set(entry.name, [...(discovered.get(entry.name) ?? []), candidate]);
    }
  }
  const result: JsonObject[] = [];
  for (const task of [...discovered.keys()].sort()) {
    const locations = discovered.get(task)!;
    if (locations.length > 1) {
      throw new Error(`任务 ${scene}/${task} 同时存在于内置与用户 catalog：${locations.map((item) => item.taskRoot).join(', ')}`);
    }
    result.push(await describeTask(scene, task, catalog));
  }
  return result;
}
