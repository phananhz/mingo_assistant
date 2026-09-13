import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from mingo_assistant.app.container import AppContainer
from mingo_assistant.app.lifecycle import SingleInstanceGuard
from mingo_assistant.app.paths import get_app_paths, load_settings, save_settings
from mingo_assistant.core.errors import CorruptDataError
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.styles import (
    THEME_OPTIONS,
    apply_app_palette,
    resolved_appearance_mode,
    stylesheet_for_theme,
)
from mingo_assistant.ui.dialogs.storage_location_dialog import StorageLocationDialog
from mingo_assistant.ui.splash_screen import show_startup_splash


def _prepare_storage_location(paths) -> None:
    settings = load_settings(paths)
    configured = settings.get("export_root", "").strip()
    if configured:
        paths.documents_root = Path(configured)
        paths.documents_root.mkdir(parents=True, exist_ok=True)
        return

    dialog = StorageLocationDialog(paths.documents_root)
    if dialog.exec() == dialog.DialogCode.Accepted:
        selected = dialog.selected_path()
        if selected:
            paths.documents_root = selected
    paths.documents_root.mkdir(parents=True, exist_ok=True)
    save_settings(paths, {"export_root": str(paths.documents_root), "setup_completed": "true"})


def main() -> int:
    app = QApplication(sys.argv)
    paths = get_app_paths()
    app.setApplicationName("Min Assistant")
    app.setOrganizationName("Min Assistant")
    app_icon_path = paths.bundle_root / "assets" / "branding" / "min-assistant.ico"
    if app_icon_path.is_file():
        app.setWindowIcon(QIcon(str(app_icon_path)))
    paths.ensure_user_dirs()
    instance_guard = SingleInstanceGuard(paths.user_data_root / ".instance.lock")
    if not instance_guard.acquire():
        QMessageBox.information(
            None,
            "Min Assistant đang chạy",
            "Min Assistant đã được mở. Vui lòng sử dụng cửa sổ hiện có để tránh ghi đè dữ liệu.",
        )
        return 0
    settings = load_settings(paths)
    system_is_dark = False
    try:
        system_is_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        pass
    mode = settings.get("appearance_mode", "light")
    is_dark = resolved_appearance_mode(mode, system_is_dark) == "dark"
    theme_id = settings.get("theme", "rose")
    custom_color = settings.get("custom_color", "")
    raw_accent = custom_color if (theme_id == "custom" and custom_color) else THEME_OPTIONS.get(theme_id, {}).get("color", "#c46a93")
    apply_app_palette(app, is_dark=is_dark, accent=raw_accent)
    app.setStyleSheet(
        stylesheet_for_theme(
            theme_id=theme_id,
            strength=settings.get("theme_strength", "100"),
            appearance_mode=mode,
            system_is_dark=system_is_dark,
            layout=settings.get("layout", "default"),
            font_size=settings.get("font_size", "medium"),
            border_radius=settings.get("border_radius", "rounded"),
            high_contrast=settings.get("high_contrast", "false").lower() in ("true", "1"),
            custom_color=custom_color,
            animations_enabled=settings.get("animations_enabled", "true").lower() in ("true", "1"),
            card_shadow=settings.get("card_shadow", "subtle"),
            hover_glow=settings.get("hover_glow", "true").lower() in ("true", "1"),
            glassmorphism=settings.get("glassmorphism", "false").lower() in ("true", "1"),
        )
    )
    container = AppContainer.build(paths)
    try:
        window = MainWindow(
            app_paths=paths,
            case_repository=container.case_repository,
            case_use_cases=container.case_use_cases,
            authorized_person_repository=container.authorized_person_repository,
            authorized_person_use_cases=container.authorized_person_use_cases,
            registration_services=container.registration_services,
            industry_catalog=container.industry_catalog,
        )
    except CorruptDataError as exc:
        backup_text = f"\n\nBản sao phục hồi: {exc.backup_path}" if exc.backup_path else ""
        QMessageBox.critical(
            None,
            "Không thể đọc dữ liệu hồ sơ",
            "Tệp dữ liệu hồ sơ bị hỏng. Ứng dụng đã giữ nguyên tệp gốc và không ghi đè."
            f"{backup_text}",
        )
        instance_guard.release()
        return 2
    show_startup_splash(app, window)
    _prepare_storage_location(paths)

    try:
        return app.exec()
    finally:
        instance_guard.release()
