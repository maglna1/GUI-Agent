export type JsonObject = Record<string, unknown>;

export interface SceneManifest {
  schemaVersion: '0.1';
  scene: string;
  title: string;
  description: string;
}

export interface TaskInputDefinition {
  type: 'string';
  label: string;
  description?: string | null;
  default: string;
}

export interface TaskSource {
  tracePath: string;
  processedLogPath: string;
  conversionCommand: string;
  recordingPreparationCommand?: string | null;
  traceGenerationCommand?: string | null;
}

export interface TaskManifest {
  schemaVersion: '0.2';
  scene: string;
  task: string;
  title: string;
  description: string;
  goal: string;
  source: TaskSource;
  inputs: Record<string, TaskInputDefinition>;
}

export interface ExecutorResult {
  schemaVersion: '0.2';
  status: 'succeeded' | 'failed';
  sourceYamlPath: string;
  dryRun: boolean;
  taskCount?: number | null;
  midsceneResult?: Record<string, unknown> | null;
  finishedAt: string;
  error?: string | null;
}

export type TraceOperationType = 'click' | 'doubleClick' | 'input' | 'keyboard' | 'wait';

export interface ShowuiTraceOperation {
  type: TraceOperationType;
  prompt?: string | null;
  locatePrompt?: string | null;
  value?: string | null;
  key?: string | null;
  condition?: string | null;
}

export interface ShowuiTraceStep {
  step_idx: number;
  caption: {
    operation: ShowuiTraceOperation;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface ShowuiTrace {
  trajectory: ShowuiTraceStep[];
  [key: string]: unknown;
}

export interface ProcessedLogStep {
  timestamp: number;
  [key: string]: unknown;
}

export interface TaskCatalogRoots {
  builtinProjectsRoot: string;
  userProjectsRoot?: string;
}

export interface DataPaths {
  root: string;
  projectsRoot: string;
  runsRoot: string;
  cacheRoot: string;
}

export interface RuntimeLayout {
  catalog: TaskCatalogRoots;
  data?: DataPaths;
}

export interface TaskPaths {
  origin: 'builtin' | 'user';
  writable: boolean;
  sceneRoot: string;
  taskRoot: string;
  sceneManifestPath: string;
  taskManifestPath: string;
  taskYamlPath: string;
}

export interface ResolvedTaskResult {
  document: JsonObject;
  manifest: TaskManifest;
  sourcePath: string;
  inputs: Record<string, string>;
  origin: 'builtin' | 'user';
  writable: boolean;
}
