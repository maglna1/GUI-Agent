import base64
import os
import shutil
import cv2
import json
from pathlib import Path
import numpy as np
import requests
from datetime import datetime

from components_sync import (
    IconRecord,
    sanitize_label,
    dedup_labels,
    build_component_entry,
    merge_components_json,
)
from review_server import run_review_session


class ComponentsLLMError(Exception):
    """Raised when the components-naming LLM call fails for any reason.

    The orchestrator catches this and falls back to timestamp-keyed labels so
    process_project() keeps running.
    """


class VideoScreenshotExtractor:
    """Extract full + crop screenshots per action and scale coordinates to a target resolution."""

    def __init__(self, target_width=1920, target_height=1080, jpeg_quality=95, crop_size=256, x_size=30, x_thick=6, icon_crop_size=30):
        self.target_width = target_width
        self.target_height = target_height
        self.jpeg_quality = jpeg_quality
        self.crop_size = crop_size
        self.x_size = x_size
        self.x_thick = x_thick
        self.icon_crop_size = icon_crop_size

    def scale_path(self, path, scale_x, scale_y):
        """Scale a list of {x,y} points for drag path."""
        if not path:
            return path
        out = []
        for p in path:
            out.append({
                "x": p["x"] * scale_x,
                "y": p["y"] * scale_y
            })
        return out

    def _bbox_with_padding(self, pts, w, h, pad=50):
        """Compute bbox of points with padding, clamped to frame bounds."""
        xs = [int(p["x"]) for p in pts]
        ys = [int(p["y"]) for p in pts]
        x1 = max(0, min(xs) - pad)
        y1 = max(0, min(ys) - pad)
        x2 = min(w, max(xs) + pad)
        y2 = min(h, max(ys) + pad)
        # Ensure non-empty crop
        if x2 <= x1: x2 = min(w, x1 + 1)
        if y2 <= y1: y2 = min(h, y1 + 1)
        return x1, y1, x2, y2

    def _get_frame_at(self, video_path, timestamp_seconds):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                return None
            frame = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_LANCZOS4)
            return frame
        finally:
            cap.release()

    def _save_jpg(self, path, img):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])

    def _save_png(self, path, img):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return cv2.imwrite(path, img)

    def _request_component_labels(self, records, screenshots_dir):
        """Single batched multimodal call to the configured OpenAI-compatible LLM.

        Builds a system prompt instructing the model to assign snake_case
        content labels to each click icon, sends all icons inline as base64
        PNGs plus per-icon metadata, and parses the JSON-object response.

        screenshots_dir is a pathlib.Path pointing at the project's screenshots/
        directory. Icons are read from <screenshots_dir>/icons/<record.filename>.

        Raises ComponentsLLMError on any failure (HTTP, JSON parse, missing
        keys, unknown keys, missing API key/model, empty result).
        """
        api_key = (
            os.environ.get("OPENAI_API_KEY", "")
            or os.environ.get("MIDSCENE_MODEL_API_KEY", "")
        )
        if not api_key:
            raise ComponentsLLMError("OPENAI_API_KEY missing")

        base_url = (
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        )
        model = os.environ.get("OPENAI_MODEL", "")
        if not model:
            raise ComponentsLLMError("OPENAI_MODEL missing")

        verify_ssl = os.environ.get("OPENAI_VERIFY_SSL", "true").lower() not in ("0", "false", "no")

        system_prompt = (
            "You label desktop UI click crops. For each input icon, return a "
            "snake_case content label (lowercase letters, digits, underscores "
            "only; max 30 chars) describing what UI element the click targets. "
            "Respond with a JSON object mapping each input filename to its "
            "label. Do not add commentary or wrap in markdown."
        )

        filenames = [r.filename for r in records]
        content = [{"type": "text", "text": "Icon metadata follows."}]
        for r in records:
            icon_path = screenshots_dir / "icons" / r.filename
            with open(icon_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            content.append({
                "type": "text",
                "text": (
                    f"{r.filename} | action={r.action} | "
                    f"coords=({r.coords[0]},{r.coords[1]}) | "
                    f"software={r.current_software} | timestamp={r.base}"
                ),
            })
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            r = requests.post(url, headers=headers, json=payload,
                              timeout=120, verify=verify_ssl)
            r.raise_for_status()
            body = r.json()
            content_text = body["choices"][0]["message"]["content"]
            parsed = json.loads(content_text)
        except Exception as e:
            raise ComponentsLLMError(f"LLM call/parse failed: {e}") from e

        if not isinstance(parsed, dict):
            raise ComponentsLLMError(f"LLM response is not a JSON object: {type(parsed).__name__}")

        missing = [fn for fn in filenames if fn not in parsed]
        if missing:
            raise ComponentsLLMError(f"LLM response missing filenames: {missing}")
        unknown = [k for k in parsed.keys() if k not in filenames]
        if unknown:
            raise ComponentsLLMError(f"LLM response contains unknown filenames: {unknown}")

        return {fn: str(parsed[fn]) for fn in filenames}

    def _safe_crop(self, frame, x, y, crop_size=256):
        if x is None or y is None:
            return frame
        h, w = frame.shape[:2]
        half = crop_size // 2
        x1, y1 = max(0, x - half), max(0, y - half)
        x2, y2 = min(w, x + half), min(h, y + half)
        return frame[y1:y2, x1:x2]

    def _primary_point_from_coords(self, coords):
        if not coords:
            return None
        if isinstance(coords, list):
            c = coords[0]
        elif isinstance(coords, dict):
            c = next(iter(coords.values()))
        else:
            return None
        if not isinstance(c, dict) or c.get("x") is None or c.get("y") is None:
            return None
        return int(c["x"]), int(c["y"])

    def _parse_config_resolution(self, actions):
        for a in actions:
            if (a.get("action") or "").startswith("CONFIG"):
                monitors = a.get("coords", {})
                primary = monitors.get("0") if isinstance(monitors, dict) else None

                if not primary:
                    return None, None

                width = primary.get("width")
                height = primary.get("height")
                sf = primary.get("scale_factor", 1.0) or 1.0

                # Use *logical* resolution as base for coords / video
                logical_w = int(round(width / sf))
                logical_h = int(round(height / sf))

                return logical_w, logical_h

        return None, None

    def scale_coordinates(self, coords, scale_x, scale_y):
        if not coords:
            return coords
        # Only handle list of dicts with x/y
        if isinstance(coords, list):
            out = []
            for c in coords:
                if isinstance(c, dict) and ("x" in c) and ("y" in c):
                    out.append({"x": c["x"] * scale_x, "y": c["y"] * scale_y})
            # If we got valid points, return them; else fall back to original
            return out if out else coords
        # e.g. CONFIG block uses a dict schema; leave it as-is
        return coords

    def process_actions(self, actions, video_path, screenshots_path, need_scaling, scale_x, scale_y):
        updated = []
        for a in actions:
            act_str = (a.get("action") or "").strip()
            if act_str == "CONFIG" or act_str.startswith("Active Window"):
                continue
            ua = a.copy()
            raw_coords = a.get('coords')
            ua['coords'] = self.scale_coordinates(raw_coords, scale_x, scale_y) if need_scaling else raw_coords
            if act_str == "DragStart at" and "path" in a and isinstance(a["path"], list):
                ua["path"] = self.scale_path(a["path"], scale_x, scale_y) if need_scaling else a["path"]
            else:
                ua["path"] = None
            timestamp = abs(a['timestamp']-0.1)
            base = f"{timestamp:.3f}s"
            full_fn = f"{base}.jpg"
            crop_fn = f"{base}.crop.jpg"

            full_path = screenshots_path / full_fn
            crop_path = screenshots_path / crop_fn

            frame = self._get_frame_at(video_path, timestamp)
            if frame is None:
                raise RuntimeError(f"Could not read video frame for action at {timestamp}s: {act_str}")

            H, W = frame.shape[:2]
            pt = self._primary_point_from_coords(ua.get('coords'))
            actt = act_str.lower()
            no_coor = ("scroll" in actt) or ("wheel" in actt) or ("hotkey" in actt) or ("type" in actt) or ("press" in actt)

            if act_str == "DragStart at" and ua.get('path') and len(ua['path']) >= 2:
                # === DragStart special handling ===
                # Full image: UNCHANGED
                full_ok = self._save_jpg(str(full_path), frame)

                # Compute tight bbox around path with 25px padding
                x1, y1, x2, y2 = self._bbox_with_padding(ua['path'], W, H, pad=25)
                crop_region = frame[y1:y2, x1:x2].copy()

                # Prepare polyline points relative to crop
                pts = []
                for p in ua['path']:
                    px = int(round(p["x"])) - x1
                    py = int(round(p["y"])) - y1
                    pts.append([px, py])
                # Simplify to "best-fit" polyline using approxPolyDP
                pts_arr = cv2.approxPolyDP(
                    np.array(pts, dtype=np.int32), epsilon=2.0, closed=False
                )
                if pts_arr.ndim == 3:
                    pts_arr = pts_arr.reshape(-1, 2)
                # Draw the simplified polyline in RED
                for i in range(1, len(pts_arr)):
                    cv2.line(
                        crop_region,
                        tuple(pts_arr[i - 1]),
                       tuple(pts_arr[i]),
                        (0, 0, 255),
                        max(2, self.x_thick)  # a bit thicker for visibility
                    )

                crop_ok = self._save_jpg(str(crop_path), crop_region)
            elif (no_coor):
                full_ok = self._save_jpg(str(full_path), frame)
                crop_ok = self._save_jpg(str(crop_path), frame)
            else:
                # === Default handling (pad crop first, then draw centered semi-transparent X) ===
                if pt is None:
                    raise ValueError(f"Action requires coordinates but none were recorded: {act_str}")
                draw_frame = frame.copy()

                # 1) Crop around click with black padding (keeps center fixed, no shifting)
                cx_raw, cy_raw = pt
                crop_img = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.crop_size)

                # 1.5) Save small original click crop (no X marker) as PNG for icon memory
                icon_crop = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.icon_crop_size)
                icon_fn = f"record_memory_icon_{base}_crop.png"
                icon_path = screenshots_path / "icons" / icon_fn
                icon_ok = self._save_png(str(icon_path), icon_crop)
                if not icon_ok:
                    raise RuntimeError(f"Could not save icon crop for action at {timestamp}s: {act_str}")

                # 2) Draw semi-transparent X AFTER padding so it's fully visible
                # X centered in the crop
                cx = cy = self.crop_size // 2
                outline = self.x_thick + 2
                # ensure the whole X (including outline) fits inside the crop
                max_half = (self.crop_size // 2) - 1 - outline
                half_x = max(1, min(self.x_size // 2, max_half))

                overlay = crop_img.copy()
                # white outline
                cv2.line(overlay, (cx - half_x, cy - half_x), (cx + half_x, cy + half_x), (255, 255, 255), outline)
                cv2.line(overlay, (cx - half_x, cy + half_x), (cx + half_x, cy - half_x), (255, 255, 255), outline)
                # red core
                cv2.line(overlay, (cx - half_x, cy - half_x), (cx + half_x, cy + half_x), (0, 0, 255), self.x_thick)
                cv2.line(overlay, (cx - half_x, cy + half_x), (cx + half_x, cy - half_x), (0, 0, 255), self.x_thick)
                # blend 50%
                crop_img = cv2.addWeighted(overlay, 0.5, crop_img, 0.5, 0)

                full_ok = self._save_jpg(str(full_path), frame)
                crop_ok = self._save_jpg(str(crop_path), crop_img)


            if not full_ok or not crop_ok:
                raise RuntimeError(f"Could not save screenshots for action at {timestamp}s: {act_str}")
            ua['screenshot_full'] = f"screenshots/{full_fn}"
            ua['screenshot_crop'] = f"screenshots/{crop_fn}"

            updated.append(ua)
        return updated
    
    def _collect_icon_records(self, actions, screenshots_dir):
        """Walk actions + screenshots_dir/icons/ to build IconRecord list.

        Only default-click branches produce icons in this repo's flow
        (see process_actions at line ~189-205). We match each icon file
        to the action whose base (timestamp - 0.1) corresponds to its filename.
        """
        icon_dir = screenshots_dir / "icons"
        if not icon_dir.exists():
            return []

        # Map base -> action for O(1) lookup
        base_to_action = {}
        for a in actions:
            ts = abs(a.get("timestamp", 0) - 0.1)
            base = f"{ts:.3f}s"
            base_to_action[base] = a

        records = []
        for icon_path in sorted(icon_dir.glob("record_memory_icon_*_crop.png")):
            filename = icon_path.name
            # filename = "record_memory_icon_<base>_crop.png"; strip prefix/suffix
            base = filename[len("record_memory_icon_"):-len("_crop.png")]
            if base not in base_to_action:
                continue
            a = base_to_action[base]
            coords_list = a.get("coords", [])
            if not coords_list or not isinstance(coords_list, list):
                continue
            coords = (int(coords_list[0]["x"]), int(coords_list[0]["y"]))
            records.append(IconRecord(
                filename=filename,
                action=str(a.get("action", "")),
                coords=coords,
                current_software=str(a.get("current_software", "")),
                base=base,
            ))
        return records

    def _sync_components_to_dest(self, actions, screenshots_dir, dest):
        """End-to-end sync orchestration; returns the meta-delta dict."""
        records = self._collect_icon_records(actions, screenshots_dir)

        if not records:
            # Nothing to sync but the dest may still need to be touched
            # (e.g. ensure components.json exists). We keep meta consistent.
            return {
                "components_synced": True,
                "components_dest": str(dest),
                "components_keys_added": [],
                "components_keys_updated": [],
                "components_fallback_to_timestamp": False,
            }

        # Ask the LLM for labels; fall back to timestamp keys on any failure.
        # timestamp_keys are already snake_case + safe, so they bypass sanitize.
        fallback = False
        timestamp_keys = {
            r.filename: f"record_memory_icon_{r.base.replace('.', '_')}_crop"
            for r in records
        }
        try:
            label_map = self._request_component_labels(records, screenshots_dir)
        except ComponentsLLMError as e:
            print(f"[sync] WARNING: LLM labeling failed ({e}); using timestamp keys")
            label_map = dict(timestamp_keys)
            fallback = True

        # Sanitize LLM-returned labels (skip the safe timestamp keys).
        safe_labels = []
        for r in records:
            raw = label_map[r.filename]
            if raw in timestamp_keys.values():
                # Already a valid timestamp key — preserve verbatim (incl. >30 chars).
                safe_labels.append(raw)
            else:
                try:
                    safe_labels.append(sanitize_label(raw))
                except ValueError as e:
                    print(f"[sync] WARNING: sanitize_label failed for {r.filename} ({e}); using timestamp key")
                    safe_labels.append(timestamp_keys[r.filename])
                    fallback = True

        safe_labels = dedup_labels(safe_labels)

        # Pair safe_label with the source filename for the helper.
        additions = {
            safe: (safe, rec.filename)
            for safe, rec in zip(safe_labels, records)
        }

        existing = self._load_components_json(dest)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keys_added, keys_updated = self._apply_components_updates(
            dest, existing, additions, screenshots_dir / "icons", now_str,
        )

        return {
            "components_synced": True,
            "components_dest": str(dest),
            "components_keys_added": keys_added,
            "components_keys_updated": keys_updated,
            "components_fallback_to_timestamp": fallback,
        }

    def _load_components_json(self, dest):
        """Read dest/components.json. Missing or corrupt -> {} (with warning)."""
        json_path = dest / "components.json"
        if not json_path.exists():
            return {}
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print(f"[sync] WARNING: {json_path} is not a JSON object; treating as empty")
                return {}
            return data
        except json.JSONDecodeError as e:
            print(f"[sync] WARNING: {json_path} is corrupt ({e}); treating as empty")
            return {}

    def _apply_components_updates(self, dest, existing, additions, src_icons_dir, now_str):
        """Copy PNGs and upsert dest/components.json.

        Args:
            dest: target components dir (we'll create dest/components/ inside).
            existing: dict loaded from dest/components.json (may be empty).
            additions: dict mapping safe_label -> (safe_label, source_filename).
                The first element duplicates the key for convenience; the
                source_filename lives in src_icons_dir.
            src_icons_dir: directory containing the source PNGs
                (typically <project>/screenshots/icons/).
            now_str: timestamp string ("YYYY-MM-DD HH:MM:SS") for last_seen and
                new learned_at.

        Returns:
            (keys_added, keys_updated) per merge_components_json semantics.
        """
        components_dir = dest / "components"
        try:
            components_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Could not create {components_dir}: {e}") from e

        # Build full entries up-front, then copy PNGs, then upsert+write.
        entry_additions = {}
        for safe_label, source_filename in additions.values():
            src = src_icons_dir / source_filename
            entry = build_component_entry(
                label=safe_label,
                icon_file=f"components/{safe_label}.png",
                learned_at=now_str,
                last_seen=now_str,
                seen_count=1,
            )
            entry_additions[safe_label] = (entry, source_filename)
            dst = components_dir / f"{safe_label}.png"
            try:
                shutil.copyfile(src, dst)
            except OSError as e:
                raise RuntimeError(
                    f"Could not copy {src} -> {dst}: {e}"
                ) from e

        merged, keys_added, keys_updated = merge_components_json(
            existing, entry_additions, now_str,
        )

        json_path = dest / "components.json"
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise RuntimeError(f"Could not write {json_path}: {e}") from e

        return keys_added, keys_updated

    def _crop_with_black_padding(self, frame, x, y, crop_size=256):
        if x is None or y is None:
            return frame

        h, w = frame.shape[:2]
        half = crop_size // 2

        # desired box
        x1 = int(x) - half
        y1 = int(y) - half
        x2 = x1 + crop_size
        y2 = y1 + crop_size

        # compute bounds and padding
        pad_left   = max(0, -x1)
        pad_top    = max(0, -y1)
        pad_right  = max(0,  x2 - w)
        pad_bottom = max(0,  y2 - h)

        x1c = max(0, x1)
        y1c = max(0, y1)
        x2c = min(w, x2)
        y2c = min(h, y2)

        crop = frame[y1c:y2c, x1c:x2c]

        # fill missing area with black canvas
        if pad_left or pad_top or pad_right or pad_bottom:
            crop = cv2.copyMakeBorder(
                crop, pad_top, pad_bottom, pad_left, pad_right,
                borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )

        # ensure final shape
        if crop.shape[:2] != (crop_size, crop_size):
            crop = cv2.resize(crop, (crop_size, crop_size), interpolation=cv2.INTER_AREA)

        return crop


    def process_project(self, project_name):
        # --- Normalize input path ---
        project_path = Path(project_name)

        # If user passed only the name (e.g., "mathQuiz"), try to locate under ./projects/
        if not project_path.exists():
            possible_root = Path.cwd() / "projects" / project_name
            if possible_root.exists():
                project_path = possible_root
            else:
                raise FileNotFoundError(
                    f"Project folder not found: {project_path}\n"
                    f"Tried also: {possible_root}"
                )

        project_dir = project_path.resolve()
        inputs_dir = project_dir / "inputs"

        if not inputs_dir.exists():
            raise FileNotFoundError(f"Inputs directory not found: {inputs_dir}")

        # --- Locate video ---
        preferred_name = project_dir.name.lower().replace("-", "_")
        candidate_videos = sorted(inputs_dir.glob("*.mp4"))
        video_path = None

        for v in candidate_videos:
            v_name = v.stem.lower().replace("-", "_")
            if v_name == preferred_name:
                video_path = v
                break

        if video_path is None:
            if not candidate_videos:
                raise FileNotFoundError(f"No .mp4 files found in {inputs_dir}")
            elif len(candidate_videos) == 1:
                video_path = candidate_videos[0]
                print(f"[Info] Using the only video: {video_path.name}")
            else:
                all_names = ", ".join(v.name for v in candidate_videos)
                raise FileNotFoundError(
                    f"No exact match for '{preferred_name}.mp4' and multiple videos exist: {all_names}"
                )

        # --- Locate processed log (strict naming) ---
        log_path = project_dir / f"{project_dir.name}_processed_log.json"
        if not log_path.exists():
            raise FileNotFoundError(f"Processed log not found: {log_path}")

        screenshots_dir = project_dir / "screenshots"

        # --- Load actions ---
        with open(log_path, "r", encoding="utf-8") as f:
            actions = json.load(f)

        ow, oh = self._parse_config_resolution(actions)
        if ow is None or oh is None:
            raise ValueError("Could not find screen resolution in the CONFIG action")

        frame_w, frame_h = self.target_width, self.target_height
        need_scaling = not (ow == frame_w and oh == frame_h)
        scale_x = frame_w / ow if ow else 1.0
        scale_y = frame_h / oh if oh else 1.0

        updated_actions = self.process_actions(
            actions, video_path, screenshots_dir, need_scaling, scale_x, scale_y
        )
        out_json_sc = project_dir / f"{project_dir.name}_processed_log_sc.json"
        with open(out_json_sc, "w", encoding="utf-8") as f:
            json.dump(updated_actions, f, ensure_ascii=False, indent=2)

        meta = {
            "video_file": str(video_path),
            "log_file": str(log_path),
            "coordinate_scaling": need_scaling,
            "original_resolution": f"{ow}x{oh}" if ow and oh else "unknown",
            "target_resolution": f"{frame_w}x{frame_h}",
            "saved_log_sc": str(out_json_sc)
        }

        # Optional: sync icons to a configured harness components/ dir.
        dest_str = os.environ.get("GUI_AGENT_COMPONENTS_DEST", "").strip()
        review_disable = os.environ.get("GUI_AGENT_REVIEW_DISABLE", "").strip()

        if dest_str:
            dest_path = Path(dest_str)
            if review_disable:
                # === Existing path: write LLM auto-labels directly. ===
                sync_meta = self._sync_components_to_dest(
                    actions, screenshots_dir, dest_path,
                )
                meta.update(sync_meta)
                meta["review_decisions"] = {
                    "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                }
                meta["review_manual_mode"] = False
                meta["review_timed_out"] = False
                meta["review_port"] = None
            else:
                # === Review path: do NOT call _sync_components_to_dest;
                #     let the review session do the single final write. ===
                records = self._collect_icon_records(actions, screenshots_dir)
                timestamp_keys = {
                    r.filename: f"record_memory_icon_{r.base.replace('.', '_')}_crop"
                    for r in records
                }
                if records:
                    try:
                        label_map = self._request_component_labels(records, screenshots_dir)
                        fallback = False
                    except ComponentsLLMError as e:
                        print(f"[review] WARNING: LLM labeling failed ({e}); using timestamp keys")
                        label_map = dict(timestamp_keys)
                        fallback = True
                    try:
                        review_result = run_review_session(
                            records, label_map, screenshots_dir, dest_path,
                        )
                    except RuntimeError:
                        # dist missing or other hard failure — propagate per AGENT.md #2
                        raise
                    meta["components_synced"] = True
                    meta["components_dest"] = str(dest_path)
                    meta["components_keys_added"] = review_result.get("keys_added", [])
                    meta["components_keys_updated"] = review_result.get("keys_updated", [])
                    meta["components_fallback_to_timestamp"] = fallback
                    meta["review_decisions"] = {
                        "accepted": review_result.get("accepted", 0),
                        "edited": review_result.get("edited", 0),
                        "skipped": review_result.get("skipped", 0),
                        "sanitize_fallback": review_result.get("sanitize_fallback", 0),
                    }
                    meta["review_manual_mode"] = bool(review_result.get("manual_mode", False))
                    meta["review_timed_out"] = bool(review_result.get("timed_out", False))
                    meta["review_port"] = review_result.get("port")
                else:
                    # No records: same shape as sync's empty path.
                    meta["components_synced"] = True
                    meta["components_dest"] = str(dest_path)
                    meta["components_keys_added"] = []
                    meta["components_keys_updated"] = []
                    meta["components_fallback_to_timestamp"] = False
                    meta["review_decisions"] = {
                        "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                    }
                    meta["review_manual_mode"] = False
                    meta["review_timed_out"] = False
                    meta["review_port"] = None
        else:
            meta["components_synced"] = False
            meta["components_dest"] = None
            meta["components_keys_added"] = []
            meta["components_keys_updated"] = []
            meta["components_fallback_to_timestamp"] = False
            meta["review_decisions"] = {
                "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
            }
            meta["review_manual_mode"] = False
            meta["review_timed_out"] = False
            meta["review_port"] = None

        return updated_actions, screenshots_dir, meta
    
if __name__ == "__main__":
    import argparse
    import traceback
    import sys

    parser = argparse.ArgumentParser(description="Extract screenshots from project recordings.")
    parser.add_argument(
        "project_name",
        help="Project name or full path to the project folder (e.g., 'mathQuiz' or 'projects/mathQuiz')."
    )
    args = parser.parse_args()

    extractor = VideoScreenshotExtractor()

    try:
        actions, shots_dir, meta = extractor.process_project(args.project_name)
        print("\n=== Screenshot Extraction Complete ===")
        print(f"Project: {args.project_name}")
        print(f"Video File: {meta.get('video_file')}")
        print(f"Log File: {meta.get('log_file')}")
        print(f"Original Resolution: {meta.get('original_resolution')}")
        print(f"Target Resolution: {meta.get('target_resolution')}")
        print(f"Screenshots saved in: {shots_dir}")
        print(f"Updated log (with screenshot paths) saved to: {meta.get('saved_log_sc')}")
        print("=====================================\n")

    except Exception as e:
        print("\n!!! Extraction failed !!!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print("\n--- Full traceback ---")
        traceback.print_exc()
        print("----------------------\n")
        sys.exit(1)


