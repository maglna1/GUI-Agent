import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from icon_library import find_icon_by_label, list_labels, load_icon_as_data_url
from trace_generator import apply_icon_decisions

PNG_BYTES = bytes(
    [
        0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
        0x00, 0x00, 0x00, 0x0d,
    ]
)


def _write_icon(library_root: Path, project: str, label: str) -> Path:
    """Create <library>/<project>/components_review_ui_mutimodal_memory_manual/components/<label>.png"""
    comp_dir = (
        library_root
        / project
        / "components_review_ui_mutimodal_memory_manual"
        / "components"
    )
    comp_dir.mkdir(parents=True, exist_ok=True)
    icon = comp_dir / f"{label}.png"
    icon.write_bytes(PNG_BYTES)
    return icon


class FindIconByLabelTest(unittest.TestCase):
    def test_returns_first_match(self):
        with tempfile.TemporaryDirectory() as root:
            root_p = Path(root)
            icon = _write_icon(root_p, "projA", "minimax_code")
            got = find_icon_by_label("minimax_code", [str(root_p)])
            self.assertEqual(got, str(icon.resolve()))

    def test_lexicographic_order_across_projects(self):
        with tempfile.TemporaryDirectory() as root:
            root_p = Path(root)
            _write_icon(root_p, "projB", "chrome")
            icon_a = _write_icon(root_p, "projA", "chrome")
            got = find_icon_by_label("chrome", [str(root_p)])
            self.assertEqual(got, str(icon_a.resolve()))

    def test_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as root:
            root_p = Path(root)
            _write_icon(root_p, "projA", "exists")
            self.assertIsNone(find_icon_by_label("missing", [str(root_p)]))

    def test_skips_non_project_dirs(self):
        with tempfile.TemporaryDirectory() as root:
            root_p = Path(root)
            # Some random file at root, not a project.
            (root_p / "readme.md").write_text("x")
            icon = _write_icon(root_p, "projA", "ssrun")
            got = find_icon_by_label("ssrun", [str(root_p)])
            self.assertEqual(got, str(icon.resolve()))

    def test_skips_nonexistent_root(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(find_icon_by_label("x", [str(Path(root) / "nonexistent")]))

    def test_empty_label_raises(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                find_icon_by_label("", [str(Path(root))])

    def test_empty_roots_raises(self):
        with self.assertRaises(ValueError):
            find_icon_by_label("x", [])

    def test_multiple_roots(self):
        with tempfile.TemporaryDirectory() as t1:
            with tempfile.TemporaryDirectory() as t2:
                _write_icon(Path(t1), "projA", "edge")
                icon_b = _write_icon(Path(t2), "projB", "edge")
                # First root wins (projA < projB alphabetically anyway).
                got = find_icon_by_label("edge", [t1, t2])
                self.assertNotEqual(got, str(Path(icon_b).resolve()))


class LoadIconAsDataUrlTest(unittest.TestCase):
    def test_returns_data_url_with_correct_base64(self):
        with tempfile.TemporaryDirectory() as tmp:
            icon = Path(tmp) / "x.png"
            icon.write_bytes(PNG_BYTES)
            url = load_icon_as_data_url(str(icon))
            self.assertTrue(url.startswith("data:image/png;base64,"))
            b64 = url[len("data:image/png;base64,"):]
            self.assertEqual(base64.b64decode(b64), PNG_BYTES)


class ListLabelsTest(unittest.TestCase):
    def test_returns_all_labels_sorted_deduped(self):
        with tempfile.TemporaryDirectory() as root:
            root_p = Path(root)
            _write_icon(root_p, "projA", "minimax_code")
            _write_icon(root_p, "projA", "ssrun")
            _write_icon(root_p, "projB", "chrome")  # dedup with projA if any
            labels = list_labels([str(root_p)])
            self.assertEqual(labels, ["chrome", "minimax_code", "ssrun"])


def _make_click_step(step_idx: int, prompt: str = "点击 ssrun 图标") -> dict:
    return {
        "step_idx": step_idx,
        "caption": {
            "observation": "x",
            "think": "y",
            "action": "z",
            "expectation": "w",
            "operation": {"type": "click", "prompt": prompt},
        },
    }


class ApplyIconDecisionsTest(unittest.TestCase):
    def _setup_icon(self, root: Path, label: str = "ssrun") -> None:
        _write_icon(root, "projA", label)

    def test_injects_data_url_for_confirmed_icon(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root), label="ssrun")
            traj = [_make_click_step(3), _make_click_step(4)]
            decisions = {"3": {"is_icon": True, "label": "ssrun"}}

            out = apply_icon_decisions(traj, decisions, [str(root)])

            self.assertEqual(out[0]["caption"]["operation"]["prompt"], "点击 ssrun 图标")
            self.assertNotIn("images", out[1]["caption"]["operation"])
            images = out[0]["caption"]["operation"]["images"]
            self.assertEqual(len(images), 1)
            entry = images[0]
            self.assertEqual(entry["name"], "ssrun")
            self.assertTrue(entry["url"].startswith("data:image/png;base64,"))
            b64 = entry["url"][len("data:image/png;base64,"):]
            self.assertEqual(base64.b64decode(b64), PNG_BYTES)

    def test_is_icon_false_leaves_prompt_only(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root))
            traj = [_make_click_step(7)]
            decisions = {"7": {"is_icon": False}}
            out = apply_icon_decisions(traj, decisions, [str(root)])
            self.assertNotIn("images", out[0]["caption"]["operation"])
            self.assertEqual(out[0]["caption"]["operation"]["prompt"], "点击 ssrun 图标")

    def test_missing_label_in_library_passes_through(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root), label="ssrun")
            traj = [_make_click_step(2)]
            decisions = {"2": {"is_icon": True, "label": "minimax_code"}}
            out = apply_icon_decisions(traj, decisions, [str(root)])
            self.assertNotIn("images", out[0]["caption"]["operation"])
            self.assertEqual(out[0]["caption"]["operation"]["prompt"], "点击 ssrun 图标")

    def test_empty_decisions_returns_input_unchanged_object(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root))
            traj = [_make_click_step(1)]
            out = apply_icon_decisions(traj, {}, [str(root)])
            self.assertIs(out, traj)

    def test_no_library_roots_passes_through(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root))
            traj = [_make_click_step(5)]
            decisions = {"5": {"is_icon": True, "label": "ssrun"}}
            out = apply_icon_decisions(traj, decisions, library_roots=None)
            self.assertNotIn("images", out[0]["caption"]["operation"])

    def test_does_not_mutate_input(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root))
            traj = [_make_click_step(8)]
            decisions = {"8": {"is_icon": True, "label": "ssrun"}}
            apply_icon_decisions(traj, decisions, [str(root)])
            self.assertNotIn("images", traj[0]["caption"]["operation"])

    def test_step_keys_are_stringified(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root))
            traj = [_make_click_step(12)]
            decisions = {"12": {"is_icon": True, "label": "ssrun"}}
            out = apply_icon_decisions(traj, decisions, [str(root)])
            self.assertIn("images", out[0]["caption"]["operation"])

    def test_non_click_step_left_alone(self):
        with tempfile.TemporaryDirectory() as root:
            self._setup_icon(Path(root))
            input_step = {
                "step_idx": 9,
                "caption": {
                    "observation": "x",
                    "think": "y",
                    "action": "z",
                    "expectation": "w",
                    "operation": {"type": "wait", "condition": "页面稳定"},
                },
            }
            decisions = {"9": {"is_icon": True, "label": "ssrun"}}
            out = apply_icon_decisions([input_step], decisions, [str(root)])
            self.assertNotIn("images", out[0]["caption"]["operation"])