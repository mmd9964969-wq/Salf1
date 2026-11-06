import ast
import html
import re
import unittest
from datetime import datetime
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "main.py"
FUNCTIONS = {
    "_clean_rich_inline",
    "_clean_rich_heading",
    "_clean_rich_data_line",
    "rich_message_html",
    "rich_button",
    "rich_button_row",
    "_presence_v2_time_active",
    "_presence_v2_window_active",
    "_presence_v2_engine_active",
    "_presence_v2_parse_clock",
    "_presence_date_style_page",
}
CONSTANTS = {"RICH_DIVIDER", "RICH_NATIVE_WIDTH_PAD"}

tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
nodes = []
found_functions = set()
found_constants = set()
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FUNCTIONS:
        nodes.append(node)
        found_functions.add(node.name)
    elif isinstance(node, ast.Assign):
        names = {
            target.id for target in node.targets
            if isinstance(target, ast.Name)
        }
        if names & CONSTANTS:
            nodes.append(node)
            found_constants.update(names & CONSTANTS)

missing = FUNCTIONS - found_functions
if missing or CONSTANTS - found_constants:
    raise RuntimeError(
        f"Could not extract helpers: functions={sorted(missing)}, "
        f"constants={sorted(CONSTANTS - found_constants)}"
    )

namespace = {
    "datetime": datetime,
    "html": html,
    "re": re,
}
module = ast.Module(body=nodes, type_ignores=[])
exec(compile(module, str(SOURCE), "exec"), namespace)

time_active = namespace["_presence_v2_time_active"]
window_active = namespace["_presence_v2_window_active"]
engine_active = namespace["_presence_v2_engine_active"]
parse_clock = namespace["_presence_v2_parse_clock"]
rich_button = namespace["rich_button"]
rich_button_row = namespace["rich_button_row"]
rich_message_html = namespace["rich_message_html"]
presence_date_style_page = namespace["_presence_date_style_page"]


class PresenceScheduleTests(unittest.TestCase):
    def test_regular_window_start_inclusive_end_exclusive(self):
        window = {"days": [5], "start": "08:00", "end": "18:00"}
        self.assertTrue(window_active(datetime(2026, 11, 7, 8, 0), window))
        self.assertTrue(window_active(datetime(2026, 11, 7, 17, 59, 59), window))
        self.assertFalse(window_active(datetime(2026, 11, 7, 18, 0), window))

    def test_overnight_interval_carries_into_next_day(self):
        window = {"days": [5], "start": "22:00", "end": "06:00"}
        self.assertTrue(window_active(datetime(2026, 11, 7, 22, 0), window))
        self.assertTrue(window_active(datetime(2026, 11, 8, 5, 59), window))
        self.assertFalse(window_active(datetime(2026, 11, 8, 6, 0), window))

    def test_midnight_end_is_supported(self):
        window = {"days": [5], "start": "06:00", "end": "00:00"}
        self.assertTrue(window_active(datetime(2026, 11, 7, 23, 59, 59), window))
        self.assertFalse(window_active(datetime(2026, 11, 8, 0, 0), window))

    def test_sunday_overnight_tail_reaches_monday(self):
        window = {"days": [6], "start": "22:00", "end": "06:00"}
        self.assertTrue(window_active(datetime(2026, 11, 9, 5, 0), window))

    def test_unselected_previous_day_does_not_activate_tail(self):
        window = {"days": [5], "start": "22:00", "end": "06:00"}
        self.assertFalse(window_active(datetime(2026, 11, 9, 5, 0), window))

    def test_equal_times_do_not_mean_all_day(self):
        self.assertFalse(time_active(datetime(2026, 11, 7, 12, 0).time(), "06:00", "06:00"))
        self.assertFalse(window_active(datetime(2026, 11, 7, 12, 0), {
            "days": [5], "start": "06:00", "end": "06:00"
        }))

    def test_schedule_mode_without_windows_is_not_always_online(self):
        config = {
            "online_enabled": True,
            "online_mode": "schedule",
            "online_schedule_enabled": False,
            "online_windows": [],
        }
        self.assertFalse(engine_active(config, "online", datetime(2026, 11, 7, 12, 0)))

    def test_schedule_only_runs_on_selected_weekday(self):
        config = {
            "online_enabled": True,
            "online_mode": "schedule",
            "online_schedule_enabled": True,
            "online_windows": [{"days": [5], "start": "08:00", "end": "18:00"}],
        }
        self.assertTrue(engine_active(config, "online", datetime(2026, 11, 7, 10, 0)))
        self.assertFalse(engine_active(config, "online", datetime(2026, 11, 8, 10, 0)))

    def test_always_mode_ignores_weekly_schedule(self):
        config = {
            "online_enabled": True,
            "online_mode": "always",
            "online_schedule_enabled": False,
            "online_windows": [],
        }
        self.assertTrue(engine_active(config, "online", datetime(2026, 11, 7, 12, 0)))

    def test_activity_keeps_legacy_default_when_no_schedule_is_enabled(self):
        config = {"activity_enabled": True, "activity_schedule_enabled": False}
        self.assertTrue(engine_active(config, "activity", datetime(2026, 11, 7, 12, 0)))

    def test_date_exception_overrides_weekly_window(self):
        config = {
            "online_enabled": True,
            "online_mode": "schedule",
            "online_schedule_enabled": True,
            "online_windows": [{"days": [5], "start": "06:00", "end": "18:00"}],
            "exceptions": [{"date": "2026-11-07", "engine": "online", "mode": "off"}],
        }
        self.assertFalse(engine_active(config, "online", datetime(2026, 11, 7, 12, 0)))

    def test_persian_and_arabic_digits_are_normalized(self):
        self.assertEqual(parse_clock("۶:۰۵"), "06:05")
        self.assertEqual(parse_clock("٠٦:٠٥"), "06:05")

    def test_invalid_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_clock("25:00")
        with self.assertRaises(ValueError):
            parse_clock("12:60")

    def test_button_data_is_html_escaped(self):
        rendered = rich_button("Open", 'a"&b', "success")
        self.assertIn('data="a&quot;&amp;b"', rendered)
        self.assertIn('style="success"', rendered)

    def test_button_rows_reject_more_than_eight_buttons(self):
        with self.assertRaises(ValueError):
            rich_button_row(*(["x"] * 9))

    def test_presence_page_uses_date_center_layout_and_separate_keyboard(self):
        source = """<b>Sᴀʟғ1 · مرکز وضعیت حضور</b>

<blockquote><b>وضعیت حساب</b>
اکانت : متصل
سرویس سلف : فعال</blockquote>

<blockquote><b>سلامت موتور</b>
Heartbeat : سالم</blockquote>

<tg-button-row align="center"><tg-button type="callback_data" style="success" data="prs_online_always">› همیشه آنلاین</tg-button><tg-button type="callback_data" style="primary" data="prs_online_schedule">› برنامه هفتگی</tg-button></tg-button-row>
<tg-button-row align="center"><tg-button type="callback_data" style="primary" data="self_features">‹ بازگشت</tg-button></tg-button-row>"""
        result = presence_date_style_page(source)
        self.assertIsNotNone(result)
        rendered = result["html"]
        self.assertIn('<table compact>', rendered)
        self.assertIn('<td align="center"><b>« مرکز وضعیت حضور »</b></td>', rendered)
        self.assertIn("مدیریت وضعیت آنلاین، برنامه هفتگی و فعالیت اکانت", rendered)
        self.assertIn('<th align="center"><b>مشخصات</b></th>', rendered)
        self.assertIn('<td align="right"><b>اکانت</b></td>', rendered)
        self.assertIn("<blockquote>برای ورود به بخش‌های بعدی", rendered)
        self.assertNotIn("<tg-button-row", rendered)
        self.assertEqual(
            result["reply_markup"]["inline_keyboard"][0][0]["callback_data"],
            "prs_online_always",
        )
        self.assertEqual(
            result["reply_markup"]["inline_keyboard"][-1][0]["callback_data"],
            "self_features",
        )
        parsed = rich_message_html(rendered)
        self.assertIn('<table compact>', parsed)
        self.assertIn("<hr/>", parsed)

    def test_presence_subpages_share_the_same_centered_header_and_footer(self):
        source = """<b>Sᴀʟғ1 · منطقه زمانی</b>

<blockquote><b>منطقه فعلی</b>
منطقه : <code>Asia/Tehran</code>
تنظیم منطقه زمانی مرجع.</blockquote>
<tg-button-row align="center"><tg-button type="callback_data" data="prs_timezone">› منطقه زمانی</tg-button></tg-button-row>"""
        result = presence_date_style_page(source)
        self.assertIsNotNone(result)
        self.assertIn('« منطقه زمانی »', result["html"])
        self.assertIn("تنظیم منطقه زمانی مرجع برای اجرای برنامه‌ها", result["html"])
        self.assertIn("<blockquote>برای ورود به بخش‌های بعدی", result["html"])
        self.assertEqual(
            result["reply_markup"]["inline_keyboard"][0][0]["callback_data"],
            "prs_timezone",
        )

    def test_non_presence_pages_are_not_reformatted(self):
        self.assertIsNone(
            presence_date_style_page("""<b>Sᴀʟғ1 · تنظیمات سلف</b>

متن عادی""")
        )

    def test_multiline_blockquote_is_preserved_as_one_rich_element(self):
        source = """<b>Sᴀʟғ1 · وضعیت</b>

<blockquote><b>اطلاعات</b>
خط اول
خط دوم</blockquote>"""
        rendered = rich_message_html(source)
        self.assertIn("<blockquote><b>اطلاعات</b>\nخط اول\nخط دوم</blockquote>", rendered)


if __name__ == "__main__":
    unittest.main()
