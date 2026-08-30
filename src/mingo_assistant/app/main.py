import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from mingo_assistant.app.paths import get_app_paths, load_settings, save_settings
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.styles import APP_STYLESHEET
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
    app.setApplicationName("Mingo Assistant")
    app.setOrganizationName("Mingo Assistant")
    app.setStyleSheet(APP_STYLESHEET)

    paths = get_app_paths()
    paths.ensure_user_dirs()
    window = MainWindow(app_paths=paths)
    show_startup_splash(app, window)
    _prepare_storage_location(paths)

    return app.exec()
