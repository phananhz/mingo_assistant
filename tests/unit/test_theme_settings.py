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

    def test_extensive_theme_palettes_available(self) -> None:
        self.assertGreaterEqual(len(THEME_OPTIONS), 20)
        categories = {info.get("category") for info in THEME_OPTIONS.values()}
        self.assertTrue({"executive", "vibrant", "pastel", "cyber"}.issubset(categories))
        for theme_id, info in THEME_OPTIONS.items():
            self.assertIn("color", info)
            self.assertTrue(info["color"].startswith("#"))
            css = stylesheet_for_theme(theme_id)
            self.assertTrue(len(css) > 1000)

    def test_custom_color_theme_generation(self) -> None:
        from mingo_assistant.ui.styles import generate_theme_palette
        replacements, sidebar = generate_theme_palette("#FF5722")
        self.assertTrue(len(replacements) > 0)
        self.assertEqual(len(sidebar), 3)
        css = stylesheet_for_theme("custom", custom_color="#FF5722")
        self.assertIn("#FF5722", css)

    def test_layout_options_supported(self) -> None:
        from mingo_assistant.ui.styles import LAYOUT_OPTIONS
        self.assertEqual(len(LAYOUT_OPTIONS), 8)
        for layout_key in (
            "default",
            "modern_studio",
            "top_nav",
            "executive",
            "compact_legal",
            "slim_sidebar",
            "centered_focus",
            "vibrant",
        ):
            self.assertIn(layout_key, LAYOUT_OPTIONS)
            css = stylesheet_for_theme("ocean", layout=layout_key)
            self.assertTrue(len(css) > 1000)

        css_default = stylesheet_for_theme("ocean", layout="default")
        css_modern = stylesheet_for_theme("ocean", layout="modern_studio")
        css_top_nav = stylesheet_for_theme("ocean", layout="top_nav")
        css_exec = stylesheet_for_theme("ocean", layout="executive")
        self.assertNotEqual(css_default, css_modern)
        self.assertIn("Modern Studio IDE Layout", css_modern)
        self.assertIn("Top Navigation Horizon Layout", css_top_nav)
        self.assertIn("Executive KPI Dashboard Layout", css_exec)

    def test_font_size_and_border_radius_options(self) -> None:
        from mingo_assistant.ui.styles import BORDER_RADIUS_OPTIONS, FONT_SIZE_OPTIONS
        self.assertIn("small", FONT_SIZE_OPTIONS)
        self.assertIn("large", FONT_SIZE_OPTIONS)
        self.assertIn("sharp", BORDER_RADIUS_OPTIONS)
        self.assertIn("pill", BORDER_RADIUS_OPTIONS)

        css_large = stylesheet_for_theme("ocean", font_size="large")
        self.assertIn("14.5px", css_large)

        css_pill = stylesheet_for_theme("ocean", border_radius="pill")
        self.assertIn("18px", css_pill)

    def test_high_contrast_mode(self) -> None:
        css_hc = stylesheet_for_theme("ocean", high_contrast=True)
        self.assertIn("High Contrast Mode", css_hc)
        self.assertIn("!important", css_hc)

    def test_settings_dialog_reset_to_default(self) -> None:
        import sys
        from PySide6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication(sys.argv)
        dlg = SettingsDialog(selected_theme="ocean", appearance_mode="dark", selected_layout="modern_studio")
        self.assertEqual(dlg.selected_theme(), "ocean")
        self.assertEqual(dlg.selected_appearance_mode(), "dark")
        self.assertEqual(dlg.selected_layout(), "modern_studio")

        dlg._reset_to_default_theme()

        self.assertEqual(dlg.selected_theme(), "rose")
        self.assertEqual(dlg.selected_appearance_mode(), "light")
        self.assertEqual(dlg.selected_layout(), "default")
        self.assertEqual(dlg.selected_font_size(), "medium")
        self.assertEqual(dlg.selected_border_radius(), "rounded")
        self.assertFalse(dlg.selected_high_contrast())
        self.assertEqual(dlg.selected_custom_color(), "")

    def test_main_window_layout_switching(self) -> None:
        import sys
        from PySide6.QtWidgets import QApplication
        from mingo_assistant.ui.main_window import MainWindow
        from mingo_assistant.ui.styles import LAYOUT_OPTIONS

        _app = QApplication.instance() or QApplication(sys.argv)
        win = MainWindow()
        win.show()

        for layout_key in LAYOUT_OPTIONS:
            win._apply_layout_structure(layout_key)
            self.assertEqual(win.current_layout, layout_key)

        win._apply_layout_structure("top_nav")
        self.assertFalse(win.top_nav_bar.isHidden())
        self.assertTrue(win.sidebar.isHidden())

        win._apply_layout_structure("default")
        self.assertFalse(win.sidebar.isHidden())
        self.assertTrue(win.top_nav_bar.isHidden())


if __name__ == "__main__":
    unittest.main()
