import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from log_processor import LogProcessor


def key_press(timestamp, key):
    return {
        "timestamp": timestamp,
        "action": f"Key Press: {key}",
        "coords": None,
        "current_software": "PcAccess.exe",
    }


class LogProcessorKeyboardMergeTest(unittest.TestCase):
    def test_merge_numpad_digits_into_typing_action(self):
        actions = [
            key_press(58.678, "NUMPAD_4"),
            key_press(59.028, "NUMPAD_7"),
            key_press(59.341, "NUMPAD_4"),
            key_press(59.767, "NUMPAD_0"),
            key_press(60.212, "NUMPAD_5"),
        ]

        merged = LogProcessor().merge_keyboard_events(actions)

        self.assertEqual(
            [{"timestamp": 60.212, "action": "Type: 47405", "coords": None, "current_software": "PcAccess.exe"}],
            merged,
        )


class LogProcessorDoubleClickTest(unittest.TestCase):
    def test_cleanup_keeps_ldoubleclick_and_removes_preceding_single_click(self):
        actions = [
            {
                "timestamp": 1.0,
                "action": "LClick at",
                "coords": [{"x": 320, "y": 240}],
                "current_software": "Explorer",
            },
            {
                "timestamp": 1.1,
                "action": "LDoubleClick at",
                "coords": [{"x": 321, "y": 239}],
                "current_software": "Explorer",
            },
        ]

        cleaned = LogProcessor().cleanup_preceded_double_clicks(actions)

        self.assertEqual([actions[1]], cleaned)


if __name__ == "__main__":
    unittest.main()
