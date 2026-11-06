import ast
import html
import json
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "main.py"
FUNCTIONS = {
    "media_guard_default_config",
    "media_guard_normalize_config",
    "media_guard_has_selection",
    "media_guard_classify_message",
    "media_guard_render_page",
    "media_guard_main_markup",
    "media_guard_media_markup",
    "media_guard_scopes_markup",
    "media_guard_exceptions_markup",
    "_inline_panel_target",
    "_parse_inline_panel_target",
    "_inline_panel_callback_data",
}
CONSTANTS = {
    "RICH_DIVIDER",
    "MEDIA_GUARD_MEDIA_LABELS",
    "MEDIA_GUARD_SCOPE_LABELS",
    "MEDIA_GUARD_VIEW_ONCE_TTL",
}

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
        f"Could not extract Media Guard helpers. functions={sorted(missing)} constants={sorted(CONSTANTS - found_constants)}"
    )

namespace = {"html": html, "json": json}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)
defaults = namespace["media_guard_default_config"]
normalize = namespace["media_guard_normalize_config"]
has_selection = namespace["media_guard_has_selection"]
classify = namespace["media_guard_classify_message"]
render_page = namespace["media_guard_render_page"]
main_markup = namespace["media_guard_main_markup"]
media_markup = namespace["media_guard_media_markup"]
scopes_markup = namespace["media_guard_scopes_markup"]
exceptions_markup = namespace["media_guard_exceptions_markup"]


class MessageType:
    def __init__(self, ttl_seconds=None, mime_type=None):
        self.ttl_seconds = ttl_seconds
        self.document = type("Document", (), {"mime_type": mime_type})() if mime_type else None


class MediaGuardTests(unittest.TestCase):
    def message(self, media, **values):
        base = {
            "media": media,
            "photo": None,
            "video": None,
            "video_note": None,
            "voice": None,
            "audio": None,
            "gif": None,
            "sticker": None,
            "document": None,
            "file": None,
            "ttl_period": None,
            "noforwards": False,
        }
        base.update(values)
        return type("Message", (), base)()

    def test_inline_panel_target_round_trip(self):
        target = namespace["_inline_panel_target"]("Abcd1234", "AAAA1234.inline")
        self.assertEqual(target, "inline:Abcd1234:AAAA1234.inline")
        self.assertEqual(namespace["_parse_inline_panel_target"](target), ("Abcd1234", "AAAA1234.inline"))
        self.assertIsNone(namespace["_parse_inline_panel_target"](12345))
        self.assertEqual(namespace["_inline_panel_callback_data"]("Abcd1234", "7"), "ip:Abcd1234:7")

    def test_default_config_starts_disabled_and_private_only(self):
        config = defaults()
        self.assertFalse(config["enabled"])
        self.assertTrue(all(config["media"].values()))
        self.assertEqual(config["scopes"], {
            "private": True, "group": False, "channel": False
        })

    def test_config_normalization_preserves_defaults_for_new_fields(self):
        config = normalize({
            "enabled": True,
            "media": {"photo": False},
            "scopes": {"group": True},
        })
        self.assertTrue(config["enabled"])
        self.assertFalse(config["media"]["photo"])
        self.assertTrue(config["media"]["video"])
        self.assertTrue(config["scopes"]["private"])
        self.assertTrue(config["scopes"]["group"])
        self.assertFalse(config["scopes"]["channel"])

    def test_activation_requires_media_and_scope_selection(self):
        config = defaults()
        self.assertTrue(has_selection(config))
        config["media"] = {key: False for key in config["media"]}
        self.assertFalse(has_selection(config))
        config = defaults()
        config["scopes"] = {"private": False, "group": False, "channel": False}
        self.assertFalse(has_selection(config))

    def test_normal_photo_is_eligible(self):
        message = self.message(
            MessageType(),
            photo=object(),
        )
        result = classify(message)
        self.assertEqual(result["media_type"], "photo")
        self.assertEqual(result["reason"], "")

    def test_video_note_and_voice_are_distinguished(self):
        note = self.message(MessageType(), video_note=object())
        voice = self.message(MessageType(), voice=object())
        self.assertEqual(classify(note)["media_type"], "video_note")
        self.assertEqual(classify(voice)["media_type"], "voice")

    def test_gif_and_video_mime_types_are_distinguished(self):
        gif = self.message(MessageType(mime_type="image/gif"))
        video = self.message(MessageType(mime_type="video/mp4"))
        self.assertEqual(classify(gif)["media_type"], "gif")
        self.assertEqual(classify(video)["media_type"], "video")

    def test_document_without_special_media_attribute_is_a_file(self):
        message = self.message(MessageType(), document=object())
        self.assertEqual(classify(message)["media_type"], "document")

    def test_view_once_ttl_is_rejected(self):
        message = self.message(MessageType(ttl_seconds=0x7FFFFFFF), photo=object())
        result = classify(message)
        self.assertEqual(result["media_type"], "photo")
        self.assertEqual(result["reason"], "view_once")

    def test_timed_media_ttl_is_rejected(self):
        message = self.message(MessageType(ttl_seconds=8), photo=object())
        result = classify(message)
        self.assertEqual(result["reason"], "timed_media")
        self.assertEqual(result["ttl_seconds"], 8)

    def test_message_ttl_period_is_also_rejected(self):
        message = self.message(MessageType(), photo=object(), ttl_period=30)
        self.assertEqual(classify(message)["reason"], "timed_media")

    def test_protected_content_is_rejected_from_message_or_chat(self):
        message = self.message(MessageType(), photo=object())
        chat = type("Chat", (), {"noforwards": True})()
        self.assertEqual(classify(message, chat)["reason"], "protected")
        message.noforwards = True
        self.assertEqual(classify(message)["reason"], "protected")

    def test_unsupported_media_is_not_forwardable(self):
        message = self.message(MessageType())
        self.assertEqual(classify(message)["reason"], "unsupported")

    def test_non_media_message_is_ignored(self):
        message = self.message(None)
        self.assertIsNone(classify(message))

    def test_page_renderer_escapes_dynamic_values_and_uses_table_and_quote(self):
        rendered = render_page(
            "رسانه‌بان",
            "راهنما",
            [("عنوان", "<script>alert(1)</script>")],
            "برای ادامه از دکمه‌ها استفاده کنید.",
        )
        self.assertIn("<table compact>", rendered)
        self.assertIn('<td align="center"><b>رسانه‌بان</b></td>', rendered)
        self.assertNotIn("« رسانه‌بان »", rendered)
        self.assertIn("<blockquote>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertEqual(rendered.count("[[RICH_DIVIDER]]"), 2)
    def test_main_keyboard_uses_green_enable_and_red_disable(self):
        config = defaults()
        keyboard = main_markup(config)["inline_keyboard"]
        self.assertEqual(keyboard[0][0]["style"], "success")
        self.assertEqual(keyboard[-1][0]["style"], "primary")
        self.assertTrue(all(len(row) <= 2 for row in keyboard))
        self.assertTrue(all(button["text"].startswith(("›", "‹")) for row in keyboard for button in row))
        config["enabled"] = True
        keyboard = main_markup(config)["inline_keyboard"]
        self.assertEqual(keyboard[0][0]["style"], "danger")
        self.assertEqual(keyboard[0][0]["callback_data"], "mg_toggle_off")

    def test_media_keyboard_is_two_columns_and_keeps_blue_back(self):
        config = defaults()
        keyboard = media_markup(config)["inline_keyboard"]
        self.assertTrue(all(len(row) <= 2 for row in keyboard))
        self.assertEqual(keyboard[-1][0]["style"], "primary")
        self.assertEqual(len([button for row in keyboard[:-1] for button in row]), 8)

    def test_scope_keyboard_is_two_columns_and_keeps_blue_back(self):
        config = defaults()
        keyboard = scopes_markup(config)["inline_keyboard"]
        self.assertEqual([len(row) for row in keyboard], [2, 1, 1])
        self.assertEqual(keyboard[-1][0]["style"], "primary")

    def test_exception_keyboard_uses_danger_for_delete_and_valid_callback_ids(self):
        rows = [
            {"peer_id": -1001234567890, "title": "Group A"},
            {"peer_id": 123456789, "title": "User B"},
        ]
        keyboard = exceptions_markup(rows)["inline_keyboard"]
        self.assertEqual(keyboard[0][0]["callback_data"], "mg_exception_add")
        deletes = [button for row in keyboard[1:-1] for button in row]
        self.assertEqual(len(deletes), 2)
        self.assertTrue(all(button["style"] == "danger" for button in deletes))
        self.assertEqual(keyboard[-1][0]["style"], "primary")



if __name__ == "__main__":
    unittest.main()
