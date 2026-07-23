import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components_sync import IconRecord, sanitize_label, dedup_labels, ComponentEntry, build_component_entry


class SanitizeLabelTest(unittest.TestCase):
    def test_lowercases_and_replaces_spaces_with_underscores(self):
        self.assertEqual(sanitize_label("Start Button"), "start_button")

    def test_replaces_slashes_and_backslashes_with_dash(self):
        self.assertEqual(sanitize_label("a/b\\c"), "a-b-c")

    def test_strips_special_chars(self):
        self.assertEqual(sanitize_label("a:b?c*d"), "abcd")

    def test_truncates_to_30_chars(self):
        long = "a" * 50
        self.assertEqual(len(sanitize_label(long)), 30)

    def test_combined(self):
        # 空白 + 特殊字符 + 长度截断；输入 35 字符经清理后更长，截到 30
        self.assertEqual(sanitize_label("Clone Repository Tab  "), "clone_repository_tab")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            sanitize_label("")

    def test_all_special_chars_raises(self):
        with self.assertRaises(ValueError):
            sanitize_label("///??**")


class IconRecordTest(unittest.TestCase):
    def test_constructs_and_exposes_fields(self):
        r = IconRecord(
            filename="record_memory_icon_10.854s_crop.png",
            action="LClick at",
            coords=(820, 450),
            current_software="Explorer",
            base="10.854s",
        )
        self.assertEqual(r.filename, "record_memory_icon_10.854s_crop.png")
        self.assertEqual(r.action, "LClick at")
        self.assertEqual(r.coords, (820, 450))
        self.assertEqual(r.current_software, "Explorer")
        self.assertEqual(r.base, "10.854s")


class DedupLabelsTest(unittest.TestCase):
    def test_no_duplicates_returns_unchanged(self):
        self.assertEqual(
            dedup_labels(["start_button", "taskbar_search", "settings_gear"]),
            ["start_button", "taskbar_search", "settings_gear"],
        )

    def test_simple_duplicates_get_numeric_suffix(self):
        self.assertEqual(
            dedup_labels(["foo", "foo", "bar"]),
            ["foo", "foo_2", "bar"],
        )

    def test_suffix_collides_with_existing_label(self):
        # "x", "x_2", "x" -> third one must skip to "x_3"
        self.assertEqual(
            dedup_labels(["x", "x_2", "x"]),
            ["x", "x_2", "x_3"],
        )

    def test_empty_list(self):
        self.assertEqual(dedup_labels([]), [])


class BuildComponentEntryTest(unittest.TestCase):
    def test_returns_full_schema_with_all_fields(self):
        e = build_component_entry(
            label="start_button",
            icon_file="components/start_button.png",
            learned_at="2026-07-23 11:00:00",
            last_seen="2026-07-23 11:05:00",
            seen_count=3,
        )
        self.assertEqual(e, {
            "type": "icon",
            "source": "learn_batch",
            "icon_file": "components/start_button.png",
            "label": "start_button",
            "learned_at": "2026-07-23 11:00:00",
            "last_seen": "2026-07-23 11:05:00",
            "seen_count": 3,
            "consecutive_misses": 0,
            "base_memory": True,
        })

    def test_default_base_memory_is_true(self):
        e = build_component_entry(
            label="x",
            icon_file="components/x.png",
            learned_at="t",
            last_seen="t",
            seen_count=1,
        )
        self.assertTrue(e["base_memory"])

    def test_explicit_base_memory_true_is_honored(self):
        e = build_component_entry(
            label="x",
            icon_file="components/x.png",
            learned_at="t",
            last_seen="t",
            seen_count=1,
            base_memory=True,
        )
        self.assertTrue(e["base_memory"])

    def test_consecutive_misses_is_always_zero(self):
        # Upsert always resets to 0; callers should never set a non-zero value.
        e = build_component_entry(
            label="x",
            icon_file="components/x.png",
            learned_at="t",
            last_seen="t",
            seen_count=5,
        )
        self.assertEqual(e["consecutive_misses"], 0)


class ComponentEntryTest(unittest.TestCase):
    def test_constructs(self):
        e = ComponentEntry(
            type="icon",
            source="learn_batch",
            icon_file="components/x.png",
            label="x",
            learned_at="t",
            last_seen="t",
            seen_count=1,
            consecutive_misses=0,
            base_memory=True,
        )
        self.assertEqual(e.label, "x")
        self.assertEqual(e.seen_count, 1)
        self.assertTrue(e.base_memory)


if __name__ == "__main__":
    unittest.main()