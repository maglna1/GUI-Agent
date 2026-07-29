"""sync_to_execution.py — 把 record 端的 trace + sc.json 同步到 execution 端的 source/。

Midscene 执行器 `task init-from-trace` 期望源码布局：
    <data_root>/projects/<scene>/<task>/source/
        ├── showui-trace.json        ← _trace.json 的拷贝
        └── processed-log-sc.json    ← _processed_log_sc.json 的拷贝

`<data_root>` 默认从 `execution/.env.local` 的 `CUA_DATA_ROOT` 读出来。run 一次之前必跑。

CLI:
    python Aloha_Learn/scripts/sync_to_execution.py <project> <scene> <task>
        [--data-root <path>]
        [--force]              # 允许覆盖已存在的 source/ 中同名文件

示例：
    python Aloha_Learn/scripts/sync_to_execution.py \\
        record_icon_click record-icon-demo record_icon_click
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _read_data_root_from_execution_env(execution_root: Path) -> str | None:
    """从 execution/.env.local / .env 读 CUA_DATA_ROOT。"""
    for filename in (".env.local", ".env"):
        env_path = execution_root / filename
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "CUA_DATA_ROOT":
                value = v.strip().strip('"').strip("'")
                if value:
                    return value
    return None


def _resolve_record_project(record_root: Path, name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.is_dir():
        return p.resolve()
    candidate = record_root / "Aloha_Learn" / "projects" / name_or_path
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(
        f"record project 找不到: {name_or_path}（已查 {p} 和 {candidate}）"
    )


def _resolve_data_root(repo_root: Path, override: str | None) -> Path:
    """Resolve `<data_root>` for the execution-side project layout.

    Override (from `--data-root`) is strict: if the path doesn't exist we
    surface the bad path instead of silently falling back. The non-override
    branch tries execution env first, then `<repo_root>/cua-data` as a last
    resort, only if either exists.
    """
    if override:
        override_path = Path(override)
        if not override_path.is_dir():
            raise FileNotFoundError(
                f"--data-root 指定的路径不存在或不是目录：{override_path}"
            )
        return override_path.resolve()

    candidates: list[Path] = []
    env_value = _read_data_root_from_execution_env(repo_root / "execution")
    if env_value:
        candidates.append(Path(env_value))
    candidates.append(repo_root / "cua-data")
    for c in candidates:
        if c and c.is_dir():
            return c.resolve()
    raise FileNotFoundError(
        "找不到 data_root。请在 execution/.env.local 里设置 CUA_DATA_ROOT，"
        "或者传 --data-root <path>"
    )


def _required_files(project: Path) -> dict[str, Path]:
    """返回源文件名 + 完整路径，缺则抛错。"""
    out: dict[str, Path] = {}
    for src_name in ("_trace.json", "_processed_log_sc.json"):
        p = project / f"{project.name}{src_name}"
        if not p.is_file():
            raise FileNotFoundError(f"缺少 record 端产物：{p}，先跑 parser.py")
        out[src_name] = p
    return out


def sync(
    project: str,
    scene: str,
    task: str,
    *,
    data_root: str | None = None,
    force: bool = False,
) -> int:
    script_dir = Path(__file__).resolve().parent
    record_root = script_dir.parent.parent  # record/
    repo_root = record_root.parent  # GUI-Agent-Github-Maglna1/

    project_dir = _resolve_record_project(record_root, project)
    data_root_resolved = _resolve_data_root(repo_root, data_root)
    source_dir = data_root_resolved / "projects" / scene / task / "source"

    sources = _required_files(project_dir)
    mapping = {
        "_trace.json": "showui-trace.json",
        "_processed_log_sc.json": "processed-log-sc.json",
    }

    existing = [
        source_dir / mapping[k] for k in mapping
        if (source_dir / mapping[k]).exists()
    ]
    if existing and not force:
        print(
            f"ERROR: 目标 source/ 已存在文件 {existing}。"
            f"再加 --force 才会覆盖。",
            file=sys.stderr,
        )
        return 2

    source_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    print(f"project  : {project_dir}")
    print(f"data_root: {data_root_resolved}")
    print(f"target   : {source_dir}")
    for src_key, dst_name in mapping.items():
        src_path = sources[src_key]
        dst_path = source_dir / dst_name
        shutil.copy2(src_path, dst_path)
        size = dst_path.stat().st_size
        total += size
        print(f"  cp {src_path.name} -> {dst_name}  ({size:,} bytes)")
    print(f"已同步 {len(mapping)} 个文件，共 {total:,} bytes")
    print()
    print("下一步（执行端，cd execution）:")
    print(f"  npm run cua -- task init-from-trace "
          f"--scene {scene} --task {task} --goal \"<填这里>\"")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(__doc__, file=sys.stderr)
        print("ERROR: 需要 3 个位置参数 <project> <scene> <task>", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="record 端 project 名或路径")
    parser.add_argument("scene", help="execution 端 scene 名")
    parser.add_argument("task", help="execution 端 task 名")
    parser.add_argument(
        "--data-root",
        help="Midscene data_root 覆盖（默认从 execution/.env.local 读 CUA_DATA_ROOT）",
    )
    parser.add_argument(
        "--force", action="store_true", help="覆盖 source/ 中已存在的同名文件",
    )
    args = parser.parse_args(argv[1:])
    return sync(
        args.project,
        args.scene,
        args.task,
        data_root=args.data_root,
        force=args.force,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
