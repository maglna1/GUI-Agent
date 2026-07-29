import os, json, base64, re, time, requests, urllib3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} 必须是 true/false、1/0、yes/no 或 on/off")

class TraceGenerator:
    """Generate step-by-step traces from GUI actions with crop+full screenshots."""

    def __init__(self, default_prompt_path: str = "default_prompt.json",
                 api_provider: str = "openai",
                 openai_model: str = "gpt-4o",
                 claude_model: str = "claude-sonnet-4-20250514",
                 api_keys_path: str = "config/api_keys.json"):
        """Load default prompt and API settings from config file or env vars."""
        project_env = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(project_env, override=True)
        with open(default_prompt_path, "r", encoding="utf-8") as f:
            self.default_prompt = json.load(f)

        self.api_provider = api_provider.lower()
        self.openai_model = (
            os.environ.get("OPENAI_MODEL")
            or os.environ.get("MIDSCENE_MODEL_NAME")
            or openai_model
        )
        self.openai_base_url = (
            os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("MIDSCENE_MODEL_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.openai_temperature = float(os.environ.get("ALOHA_TRACE_TEMPERATURE", "0.2"))
        # Network timeouts. The OpenAI HTTP call below uses `timeout` (connect+read),
        # but Claude passes connect/read separately.
        raw_timeout = os.environ.get("ALOHA_TRACE_TIMEOUT")
        self.openai_timeout = float(raw_timeout) if raw_timeout else 300.0  # was hardcoded 120s; too short for some Ark / Volcengine models on huge prompts.
        self.claude_connect_timeout = float(os.environ.get("ALOHA_TRACE_CLAUDE_CONNECT_TIMEOUT", "10"))
        self.claude_read_timeout = float(os.environ.get("ALOHA_TRACE_CLAUDE_READ_TIMEOUT", "300"))
        self.openai_verify_ssl = env_bool("OPENAI_VERIFY_SSL", True)
        if not self.openai_verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.claude_model = claude_model

        self.openai_key = ""
        self.claude_key = ""

        try:
            with open(api_keys_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.openai_key = (
                cfg.get("OPENAI_API_KEY", "")
                or os.environ.get("OPENAI_API_KEY", "")
                or os.environ.get("MIDSCENE_MODEL_API_KEY", "")
            )
            self.claude_key = cfg.get("CLAUDE_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        except FileNotFoundError:
            self.openai_key = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("MIDSCENE_MODEL_API_KEY", "")
            self.claude_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not self.openai_key and not self.claude_key:
            raise RuntimeError("No API keys found. Please fill config/api_keys.json or set env vars.")

    def _val(self, d: Dict[str, Any], *keys, default=""):
        """Get dictionary value by key (case-insensitive)."""
        for k in keys:
            if k in d: return d[k]
            for dk in d.keys():
                if dk.lower() == k.lower():
                    return d[dk]
        return default

    def _encode_image(self, path: str) -> Optional[str]:
        """Read image file and return base64 data URI."""
        if not path or not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract first valid JSON object from a string."""
        if not text:
            return {}
        blocks = re.findall(r"\{.*\}", text, flags=re.S)
        for b in blocks:
            try:
                return json.loads(b)
            except json.JSONDecodeError:
                continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _sanitize_operation(self, operation: Any) -> Dict[str, Any]:
        """Keep the minimal structured operation used by downstream runners."""
        if not isinstance(operation, dict):
            return {}

        raw_type = str(operation.get("type") or "").strip().lower()
        operation_types = {
            "click": "click",
            "doubleclick": "doubleClick",
            "input": "input",
            "keyboard": "keyboard",
            "wait": "wait",
        }
        op_type = operation_types.get(raw_type)
        if op_type is None:
            return {}

        sanitized: Dict[str, Any] = {"type": op_type}
        for key in ("prompt", "locatePrompt", "value", "key", "condition"):
            value = operation.get(key)
            if isinstance(value, str) and value.strip():
                sanitized[key] = value.strip()

        # Preserve icon-click image references injected by the icon-review
        # workflow (see apply_icon_decisions). Each entry: {name, url}.
        images = operation.get("images")
        if isinstance(images, list) and images:
            clean_images: list[dict] = []
            for entry in images:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                url = entry.get("url")
                if isinstance(name, str) and name and isinstance(url, str) and url.startswith("data:image/"):
                    clean_images.append({"name": name, "url": url})
            if clean_images:
                sanitized["images"] = clean_images

        return sanitized

    def _recorded_operation_type(self, action: str) -> str | None:
        """Return the operation type mandated by an explicit recorder event."""
        event_name = re.split(r"\s+|:", action.strip(), maxsplit=1)[0].lower()
        if event_name in {"ldoubleclick", "ldblclick", "doubleclick", "dblclick"}:
            return "doubleClick"
        return None

    def _operation_error(
        self,
        operation: Any,
        expected_type: str | None = None,
    ) -> str | None:
        if not isinstance(operation, dict):
            return "Operation 必须是对象"
        operation_type = operation.get("type")
        required_fields = {
            "click": ("prompt",),
            "doubleClick": ("prompt",),
            "input": ("prompt", "locatePrompt", "value"),
            "keyboard": ("key",),
            "wait": ("condition",),
        }
        if operation_type not in required_fields:
            return "Operation.type 必须是 click、doubleClick、input、keyboard 或 wait"
        if expected_type is not None and operation_type != expected_type:
            return (
                f"录制事件要求 Operation.type 为 {expected_type}，"
                f"模型输出为 {operation_type}"
            )
        missing = [field for field in required_fields[operation_type] if not operation.get(field)]
        if missing:
            return f"Operation 缺少非空字段：{', '.join(missing)}"
        return None

    def _sanitize_caption(self, cap: Dict[str, Any]) -> Dict[str, Any]:
        """Clean LLM output: strip coordinates, enforce crop-first observation."""
        patterns = [
            r"\bcoordinates?\b.*?\[[^\]]*\]",
            r"\bcoordinates?\b",
            r"\b(x\s*[:=]?\s*\d+|y\s*[:=]?\s*\d+)"
        ]

        def scrub(s: str) -> str:
            if not isinstance(s, str): return s
            for p in patterns:
                s = re.sub(p, "", s, flags=re.I)
            s = re.sub(r"\[\s*\d+\s*,\s*\d+\s*\]", "", s)
            return re.sub(r"\s{2,}", " ", s).strip()

        for k in ("observation", "think", "action", "expectation"):
            cap[k] = scrub(cap.get(k, ""))

        cap["operation"] = self._sanitize_operation(cap.get("operation"))

        if not cap.get("observation", "").lower().startswith("cropped image shows"):
            cap["observation"] = ("Cropped image shows " + cap.get("observation", "")).strip()

        return cap

    def _caption_needs_retry(
        self,
        cap: Dict[str, Any],
        expected_operation_type: str | None = None,
    ) -> bool:
        return (
            not cap.get("action")
            or self._operation_error(
                cap.get("operation"),
                expected_operation_type,
            )
            is not None
        )

    def _prompt(self, action: Dict[str, Any], overall_task: str, step_idx: int, recent_steps: List[Dict[str, Any]]) -> str:
        """Build the step prompt. Core rules live in default_prompt.json; add small action-type deltas conditionally."""
        base = self.default_prompt.get("Base Prompt", "")
        deltas_cfg = self.default_prompt.get("Deltas", {})
        modifier_guide = self.default_prompt.get("Modifier_Guide", "")
        sw = action.get("current_software") or ""
        ts = action.get("timestamp")
        act = (action.get("action") or "").strip()
        recent_json = json.dumps(recent_steps, ensure_ascii=False, indent=2)

        delta = self._action_delta(act, action, deltas_cfg, modifier_guide)

        return f"""{base}

Recent Steps (most recent first, up to 3):
{recent_json}

Step Index: {step_idx}
Action: {act}
Software: {sw}
Timestamp: {ts}s
Overall Task: {overall_task}

{delta}

只输出 JSON。JSON 字段名必须保持为 Observation、Think、Action、Expectation、Operation。
前四个字段的字段值必须使用中文；Operation.prompt 也应使用中文，只有界面原文、品牌名、按钮名、机场名、URL、快捷键和专有名词可以保留英文。
如果第一次输出不是有效 JSON，请立即重新输出修正后的 JSON。"""

    def _action_delta(self, act_str: str, action: Dict[str, Any], deltas_cfg: Dict[str, str], modifier_guide: str) -> str:
        a = (act_str or "").lower()
        key = None
        if "dragstart" in a or a.startswith("drag"):
            key = "Drag"
        elif "rclick" in a or "right click" in a:
            key = "RClick"
        elif "dbl" in a or "double" in a:
            key = "DblClick"
        elif "wheel" in a or "scroll" in a:
            key = "MouseWheel"
        elif "type" in a or "input" in a or "key" in a:
            key = "Type"
        elif "click" in a:
            key = "Click"
        elif "scroll" in a:
            key = "Scroll"
        if not key:
            return ""
        text = deltas_cfg.get(key, "")
        mod_txt = self._modifiers_text(action, modifier_guide)
        return text.replace("<MODIFIER_GUIDE>", mod_txt)

    def _modifiers_text(self, action: Dict[str, Any], modifier_guide: str) -> str:
        """Build a compact modifier summary only when modifiers are actually present.
       Expecting action.get('modifiers') as a list like ['Shift', 'Ctrl'] (case-insensitive)."""
        mods = action.get("modifiers") or action.get("modifier") or []
        if isinstance(mods, str):
            mods = [mods]
        mods = [m.capitalize() for m in mods if isinstance(m, str)]
        present = [m for m in ["Shift", "Ctrl", "Alt"] if m in mods]
        if not present:
            return ""  # remove placeholder cleanly
        # Keep guidance short by scoping to present modifiers only
        guide_map = {
            "Shift": "Shift—add to selection / constrain proportions or direction",
            "Ctrl": "Ctrl—multi-select / special function / precise control",
            "Alt":  "Alt—alternate mode / temporary tool / special functions"
        }
        tips = "; ".join(guide_map[m] for m in present)
        return f"Modifier: {tips}. "

    def _call_openai(self, prompt: str, crop_b64: Optional[str], full_b64: Optional[str]) -> str:
        """Send prompt+images to OpenAI API and return text output."""
        if not self.openai_key:
            raise RuntimeError("OPENAI_API_KEY missing in config/api_keys.json or environment.")
        url = f"{self.openai_base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        content = [{"type": "text", "text": prompt}]
        if crop_b64: content.append({"type": "image_url", "image_url": {"url": crop_b64}})
        if full_b64: content.append({"type": "image_url", "image_url": {"url": full_b64}})
        data = {"model": self.openai_model,
                "messages": [{"role": "user", "content": content}],
                "temperature": self.openai_temperature}
        r = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=self.openai_timeout,
            verify=self.openai_verify_ssl,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _call_claude(self, prompt: str, crop_b64: Optional[str], full_b64: Optional[str]) -> str:
        """Send prompt+images to Claude API and return text output."""
        if not self.claude_key:
            raise RuntimeError("CLAUDE_API_KEY missing in config/api_keys.json or environment.")
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        content = [{"type": "text", "text": prompt}]
        if crop_b64:
            content.append({"type": "image",
                            "source": {"type": "base64",
                                       "media_type": "image/jpeg",
                                       "data": crop_b64.split(",")[-1]}})
        if full_b64:
            content.append({"type": "image",
                            "source": {"type": "base64",
                                       "media_type": "image/jpeg",
                                       "data": full_b64.split(",")[-1]}})
        data = {"model": self.claude_model,
                "max_tokens": 1200,
                "messages": [{"role": "user", "content": content}]}
        r = requests.post(
            url, headers=headers, json=data,
            timeout=(self.claude_connect_timeout, self.claude_read_timeout),
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"]

    def generate_trace(self, recording_json_path: str,
                       screenshots_dir: str,
                       output_trace_path: str,
                       overall_task: str = "",
                       library_roots: list[str] | None = None,
                       run_icon_review: bool = False,
                       icon_review_timeout_seconds: int = 1800,
                       icon_review_decisions: dict | None = None,
                       icon_review_decisions_path: Path | None = None):
        """Main pipeline: read log JSON, pair screenshots, call LLM, and save trace.

        icon_review_decisions: if pre-loaded from disk (e.g. from a prior run),
        skip the icon-review window and use these. Otherwise the window pops.
        icon_review_decisions_path: if set, decisions are persisted here as JSON.
        """
        with open(recording_json_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        if not isinstance(items, list):
            raise ValueError("录制 JSON 根节点必须是数组")
        invalid_indexes = [index for index, item in enumerate(items) if not isinstance(item, dict)]
        if invalid_indexes:
            raise ValueError(f"录制 JSON 包含非对象步骤：{invalid_indexes}")
        by_ts = {float(it["timestamp"]): it for it in items if "timestamp" in it}

        traj, step_idx = [], 1

        for it in items:
            act_str = (it.get("action") or "").strip()
            if act_str.upper() == "CONFIG":
                continue
            if act_str.startswith("Active Window"):
                continue

            ts = float(it.get("timestamp") or 0.0)
            raw = by_ts.get(ts, it)

            crop = raw.get("screenshot_crop") or raw.get("screenshot")
            full = raw.get("screenshot_full") or raw.get("screenshot")
            if not crop and not full:
                raise RuntimeError(f"录制动作缺少截图：timestamp={ts}, action={act_str}")

            if isinstance(crop, str) and crop.startswith("screenshots/"):
                crop = crop.replace("screenshots/", "")
            if isinstance(full, str) and full.startswith("screenshots/"):
                full = full.replace("screenshots/", "")

            crop_path = os.path.join(screenshots_dir, crop) if crop else None
            full_path = os.path.join(screenshots_dir, full) if full else None
            crop_b64 = self._encode_image(crop_path) if crop_path else None
            full_b64 = self._encode_image(full_path) if full_path else None
            if not crop_b64 and not full_b64:
                raise RuntimeError(f"录制动作的截图无法读取：timestamp={ts}, action={act_str}")

            act = it.get("action") or ""
            expected_operation_type = self._recorded_operation_type(act)
            coords = it.get("coords")
            if coords and isinstance(coords, list):
                coord_str = ", ".join(f"({c.get('x')},{c.get('y')})" for c in coords)
            else:
                coord_str = ""
            print(f"parsing Step {step_idx}: {act} {coord_str}", flush=True)

            recent = []
            for prev in reversed(traj[-3:]):
                cap = prev.get("caption", {}) or {}
                recent.append({
                    "step_idx": prev.get("step_idx"),
                    "Observation": cap.get("observation", ""),
                    "Think": cap.get("think", ""),
                    "Action": cap.get("action", ""),
                    "Expectation": cap.get("expectation", ""),
                    "Operation": cap.get("operation", {})
                })

            prompt = self._prompt(it, overall_task, step_idx, recent)
            if self.api_provider == "claude":
                txt = self._call_claude(prompt, crop_b64, full_b64)
            else:
                txt = self._call_openai(prompt, crop_b64, full_b64)

            data = self._extract_json(txt)
            cap = {
                "observation": self._val(data, "Observation", "observation", default=""),
                "think": self._val(data, "Think", "think", default=""),
                "action": self._val(data, "Action", "action", default=""),
                "expectation": self._val(data, "Expectation", "expectation", default=""),
                "operation": self._val(data, "Operation", "operation", default={})
            }
            cap = self._sanitize_caption(cap)

            if self._caption_needs_retry(cap, expected_operation_type):
                operation_error = self._operation_error(
                    cap.get("operation"),
                    expected_operation_type,
                )
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"上一次输出缺少有效 Action 或 Operation：{operation_error or 'Action 为空'}。"
                    "请重新输出完整 JSON，必须包含非空 Action，"
                    "并且 Operation.type 必须是 click、doubleClick、input、keyboard 或 wait；"
                    "各类型的必需字段必须完整。"
                )
                if self.api_provider == "claude":
                    txt = self._call_claude(retry_prompt, crop_b64, full_b64)
                else:
                    txt = self._call_openai(retry_prompt, crop_b64, full_b64)

                data = self._extract_json(txt)
                cap = {
                    "observation": self._val(data, "Observation", "observation", default=""),
                    "think": self._val(data, "Think", "think", default=""),
                    "action": self._val(data, "Action", "action", default=""),
                    "expectation": self._val(data, "Expectation", "expectation", default=""),
                    "operation": self._val(data, "Operation", "operation", default={})
                }
                cap = self._sanitize_caption(cap)

            if self._caption_needs_retry(cap, expected_operation_type):
                operation_error = self._operation_error(
                    cap.get("operation"),
                    expected_operation_type,
                )
                raise RuntimeError(
                    f"trace step {step_idx} 在纠错重试后仍缺少可执行 operation："
                    f"{operation_error or 'Action 为空'}"
                )

            traj.append({
                "step_idx": step_idx,
                "timestamp": ts,
                "coords": list(coords) if isinstance(coords, list) and coords else None,
                "current_software": it.get("current_software", ""),
                "caption": cap,
            })
            step_idx += 1
            time.sleep(0.1)

        if not traj:
            raise RuntimeError("录制中没有可生成 trace 的操作步骤")

        # ---- Icon-review workflow ----
        # After LLM produced prompts, let the user mark which clicks are
        # icon clicks (where a desktop / taskbar icon was clicked) and pick
        # the matching label. The decision injects `images[]` into the
        # operation so Midscene's VLM uses the icon as a reference image.
        if run_icon_review:
            from icon_review_server import run_icon_review_session
            from icon_library import find_icon_by_label, load_icon_as_data_url

            if icon_review_decisions is None:
                if not library_roots:
                    library_roots = []
                # Build click metadata from LLM output: every "click" step
                # is a candidate (doubleClick and wait are not). We forward
                # the SC-action's timestamp/coords/software so the icon-review
                # window can render the right screenshot crop.
                clicks: list[dict] = []
                for step in traj:
                    cap = step.get("caption") or {}
                    op = cap.get("operation") or {}
                    if op.get("type") == "click":
                        ts = step.get("timestamp")
                        if not isinstance(ts, (int, float)):
                            # Fallback: skip the click rather than crash the
                            # icon-review window with a missing timestamp.
                            continue
                        coords = step.get("coords") or [None, None]
                        clicks.append({
                            "step_idx": step["step_idx"],
                            "timestamp": ts,
                            "coords": list(coords),
                            "current_software": step.get("current_software", ""),
                            "prompt": op.get("prompt", ""),
                        })

                # Run the icon-review window (blocks). Empty decisions is
                # the timeout fallback (caller treats as no-op).
                if clicks:
                    icon_review_decisions = run_icon_review_session(
                        clicks=clicks,
                        library_roots=library_roots,
                        screenshot_dir=Path(screenshots_dir),
                        timeout_seconds=icon_review_timeout_seconds,
                    )
                else:
                    icon_review_decisions = {}

            # Persist for re-use on next run.
            if icon_review_decisions_path is not None:
                icon_review_decisions_path.parent.mkdir(parents=True, exist_ok=True)
                icon_review_decisions_path.write_text(
                    json.dumps(
                        {
                            "schemaVersion": 1,
                            "decisions": icon_review_decisions,
                            "libraryRoots": library_roots,
                            "decidedAt": datetime.now().isoformat(timespec="seconds"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

            # Inject images into matching click operations.
            traj = apply_icon_decisions(traj, icon_review_decisions, library_roots)

        with open(output_trace_path, "w", encoding="utf-8") as f:
            json.dump({"trajectory": traj}, f, ensure_ascii=False, indent=2)


def apply_icon_decisions(
    traj: list[dict],
    decisions: dict,
    library_roots: list[str] | None = None,
) -> list[dict]:
    """Inject icon-reference images into click operations.

    decisions: {step_idx_str: {"is_icon": bool, "label": str | None}}.
    For every decision with is_icon=True and a non-empty label:
      1. Resolve the PNG via find_icon_by_label(label, library_roots).
      2. Encode as a data: URL via load_icon_as_data_url.
      3. Inject [{name, url}] into step["caption"]["operation"]["images"].

    Returns a new trajectory list (does not mutate input). Non-matching
    steps pass through unchanged.
    """
    from icon_library import find_icon_by_label, load_icon_as_data_url

    if not decisions:
        return traj

    roots = library_roots or []
    out: list[dict] = []
    for step in traj:
        step_idx = step.get("step_idx")
        decision = decisions.get(str(step_idx))
        # Deep-copy so callers can diff input vs. output safely.
        copied = json.loads(json.dumps(step, ensure_ascii=False))

        if not decision or not decision.get("is_icon"):
            out.append(copied)
            continue
        # Only click operations can be icon clicks — other ops don't carry
        # an icon reference semantic (doubleClick arguably could, but the
        # current scheme targets the primary click).
        op = copied.get("caption", {}).get("operation") or {}
        if op.get("type") != "click":
            out.append(copied)
            continue
        label = (decision.get("label") or "").strip()
        if not label:
            out.append(copied)
            continue
        if not roots:
            # No library roots configured. Pass through unchanged so a
            # missing config doesn't silently break traces.
            out.append(copied)
            continue
        icon_path = find_icon_by_label(label, roots)
        if icon_path is None:
            # Label not in any library root; keep the LLM prompt fallback.
            out.append(copied)
            continue
        cap = copied.setdefault("caption", {})
        op = cap.setdefault("operation", {})
        op["images"] = [{"name": label, "url": load_icon_as_data_url(icon_path)}]
        out.append(copied)
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--shots", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--provider", default="openai", choices=["openai", "claude"])
    parser.add_argument("--openai_model", default="gpt-4o")
    parser.add_argument("--claude_model", default="claude-sonnet-4-20250514")
    args = parser.parse_args()

    tg = TraceGenerator(
        default_prompt_path="default_prompt.json",
        api_provider=args.provider,
        openai_model=args.openai_model,
        claude_model=args.claude_model,
        api_keys_path="config/api_keys.json",
    )
    tg.generate_trace(args.log, args.shots, args.out, overall_task=args.task)
