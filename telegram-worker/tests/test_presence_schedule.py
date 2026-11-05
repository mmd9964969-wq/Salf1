import ast
import html
import unittest
from datetime import datetime
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "main.py"
TARGETS = {
    "rich_button",
    "rich_button_row",
    "_presence_v2_time_active",
    "_presence_v2_window_active",
    "_presence_v2_engine_active",
    "_presence_v2_parse_clock",
}
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
nodes = [
    node for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name in TARGETS
]
found = {node.name for node in nodes}
if found != TARGETS:
    raise RuntimeError(f"Presence helper extraction failed: {TARGETS - found}")

namespace = {"datetime": datetime, "html": html}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)

rich_button = namespace["rich_button"]
rich_button_row = namespace["rich_button_row"]
time_active = namespace["_presence_v2_time_active"]
window_active = namespace["_presence_v2_window_active"]
engine_active = namespace["_presence_v2_engine_active"]
parse_clock = namespace["_presence_v2_parse_clock"]


class PresenceScheduleTests(unittest.TestCase):
    def test_regular_window_start_inclusive_end_exclusive(self):
        window = {"days": [5], "start": "08:00", "end": "18:00"}
        self.assertTrue(window_active(datetime(2026, 11, 7, 8, 0), window))
        self.assertTrue(window_active(datetime(2026, 11, 7, 17, 59), window))
        self.assertFalse(window_active(datetime(2026, 11, 7, 18, 0), window))

    def test_overnight_window_tail_is_carried_to_next_day(self):
        window = {"days": [5], "start": "22:00", "end": "06:00"}
        self.assertTrue(window_active(datetime(2026, 11, 7, 22, 0), window))
        self.assertTrue(window_active(datetime(2026, 11, 8, 5, 59), window))
        self.assertFalse(window_active(datetime(2026, 11, 8, 6, 0), window))

    def test_midnight_end_is_supported(self):
        window = {"days": [5], "start": "06:00", "end": "00:00"}
        self.assertTrue(window_active(datetime(2026, 11, 7, 23, 59), window))
        self.assertFalse(window_active(datetime(2026, 11, 8, 0, 0), window))

    def test_sunday_overnight_tail_reaches_monday(self):
        window = {"days": [6], "start": "22:00", "end": "06:00"}
        self.assertTrue(window_active(datetime(2026, 11, 9, 5, 0), window))

    def test_unselected_previous_day_does_not_activate_overnight_tail(self):
        window = {"days": [5], "start": "22:00", "end": "06:00"}
        self.assertFalse(window_active(datetime(2026, 11, 9, 5, 0), window))

    def test_equal_endpoints_do_not_mean_all_day(self):
        self.assertFalse(time_active(datetime(2026, 11, 7, 12, 0).time(), "06:00", "06:00"))
        self.assertFalse(window_active(datetime(2026, 11, 7, 12, 0), {
            "days": [5], "start": "06:00", "end": "06:00"
        }))

    def test_schedule_mode_without_schedule_is_not_always_online(self):
        config = {
            "online_enabled": True,
            "online_mode": "schedule",
            "online_schedule_enabled": False,
            "online_windows": [],
        }
        self.assertFalse(engine_active(config, "online", datetime(2026, 11, 7, 12, 0)))

    def test_schedule_activates_on_selected_weekday(self):
        config = {
            "online_enabled": True,
            "online_mode": "schedule",
            "online_schedule_enabled": True,
            "online_windows": [{"days": [5], "start": "08:00", "end": "18:00"}],
        }
        self.assertTrue(engine_active(config, "online", datetime(2026, 11, 7, 10, 0)))
        self.assertFalse(engine_active(config, "online", datetime(2026, 11, 8, 10, 0)))

    def test_always_mode_is_independent_from_weekly_schedule(self):
        config = {
            "online_enabled": True,
            "online_mode": "always",
            "online_schedule_enabled": False,
            "online_windows": [],
        }
        self.assertTrue(engine_active(config, "online", datetime(2026, 11, 7, 12, 0)))

    def test_activity_without_explicit_schedule_keeps_legacy_behavior(self):
        config = {"activity_enabled": True, "activity_schedule_enabled": False}
        self.assertTrue(engine_active(config, "activity", datetime(2026, 11, 7, 12, 0)))

    def test_date_exception_overrides_weekly_schedule(self):
        config = {
            "online_enabled": True,
            "online_mode": "schedule",
            "online_schedule_enabled": True,
            "online_windows": [{"days": [5], "start": "06:00", "end": "18:00"}],
            "exceptions": [{"date": "2026-11-07", "engine": "online", "mode": "off"}],
        }
        self.assertFalse(engine_active(config, "online", datetime(2026, 11, 7, 12, 0)))

    def test_persian_and_arabic_digits_are_accepted(self):
        self.assertEqual(parse_clock("۶:۰۵"), "06:05")
        self.assertEqual(parse_clock("٠٦:٠٥"), "06:05")

    def test_invalid_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_clock("25:00")
        with self.assertRaises(ValueError):
            parse_clock("12:60")

    def test_button_callback_data_is_html_escaped(self):
        rendered = rich_button("Open", 'a"&b', "primary")
        self.assertIn('data="a&quot;&amp;b"', rendered)
        self.assertIn('style="primary"', rendered)

    def test_button_row_rejects_more_than_eight_buttons(self):
        with self.assertRaises(ValueError):
            rich_button_row(*(["x"] * 9))


if __name__ == "__main__":
    unittest.main()
