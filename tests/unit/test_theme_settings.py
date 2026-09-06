import unittest

from mingo_assistant.ui.dialogs.settings_dialog import SettingsDialog
from mingo_assistant.ui.styles import THEME_OPTIONS, resolved_appearance_mode, stylesheet_for_theme


class ThemeSettingsTest(unittest.TestCase):
    def test_blue_theme_uses_requested_color(self) -> None:
        stylesheet = stylesheet_for_theme("sky_blue")
        self.assertIn("#AEE2FF", stylesheet)
        self.assertEqual(THEME_OPTIONS["sky_blue"]["color"], "#AEE2FF")

    def test_green_theme_uses_requested_color(self) -> None:
        stylesheet = stylesheet_for_theme("sage_green")
        self.assertIn("#8EC3B0", stylesheet)
        self.assertEqual(THEME_OPTIONS["sage_green"]["color"], "#8EC3B0")

    def test_dark_mode_uses_dark_application_surfaces(self) -> None:
        stylesheet = stylesheet_for_theme("ocean", 100, "dark")
        self.assertIn("#1A1C1F", stylesheet)
        self.assertEqual(resolved_appearance_mode("dark"), "dark")
        self.assertEqual(resolved_appearance_mode("system", True), "dark")

    def test_theme_stylesheet_is_cached_for_identical_selection(self) -> None:
        first = stylesheet_for_theme("ocean", 137, "dark")
        second = stylesheet_for_theme("ocean", 137, "dark")
        self.assertIs(first, second)

    def test_dark_mode_covers_workspace_surfaces_and_controls(self) -> None:
        stylesheet = stylesheet_for_theme("sage_green", 100, "dark")
        for selector in (
            "BusinessWorkspacePage",
            "CaseCardsContainer",
            "CccdResultCard",
            "SettingsButton",
            "QProgressBar",
        ):
            self.assertIn(selector, stylesheet)

    def test_additional_color_palettes_are_available(self) -> None:
        for theme_id in ("violet", "ocean", "amber", "olive_gray", "steel_blue"):
            self.assertIn(theme_id, THEME_OPTIONS)
            self.assertIn(THEME_OPTIONS[theme_id]["color"], stylesheet_for_theme(theme_id))

    def test_case_cards_follow_the_selected_theme(self) -> None:
        stylesheet = stylesheet_for_theme("olive_gray")
        self.assertIn("#CardHeader { background: #777466; }", stylesheet)
        self.assertIn("QLabel#StatusBadge { background: rgba(255, 255, 255, 0.88);", stylesheet)
        self.assertIn("color: #59574D;", stylesheet)

    def test_settings_has_storage_and_development_categories_without_recognition(self) -> None:
        pages = dict(SettingsDialog._PAGES)
        self.assertEqual(pages["storage"], "N\u01a1i l\u01b0u tr\u1eef")
        self.assertIn("pets", pages)
        self.assertIn("background_music", pages)
        self.assertIn("ai", pages)
        self.assertNotIn("recognition", pages)

    def test_unknown_theme_falls_back_to_default(self) -> None:
        self.assertEqual(stylesheet_for_theme("unknown"), stylesheet_for_theme("rose"))

    def test_theme_strength_changes_the_accent_color(self) -> None:
        self.assertIn("#AEE2FF", stylesheet_for_theme("sky_blue", 100))
        self.assertNotIn("#AEE2FF", stylesheet_for_theme("sky_blue", 60))
        self.assertNotEqual(
            stylesheet_for_theme("sage_green", 60),
            stylesheet_for_theme("sage_green", 140),
        )


if __name__ == "__main__":
    unittest.main()
