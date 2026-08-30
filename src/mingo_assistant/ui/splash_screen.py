from __future__ import annotations

from PySide6.QtCore import QEventLoop, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QSplashScreen, QVBoxLayout, QWidget


class StartupSplash(QSplashScreen):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setFixedSize(460, 270)

        panel = QWidget(self)
        panel.setObjectName("SplashPanel")
        panel.setGeometry(self.rect())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(42, 36, 42, 34)
        layout.setSpacing(10)

        eyebrow = QLabel("MINGO ASSISTANT")
        eyebrow.setObjectName("SplashEyebrow")
        title = QLabel("Hỗ trợ lập hồ sơ")
        title.setObjectName("SplashTitle")
        subtitle = QLabel("Chuẩn bị không gian làm việc của bạn...")
        subtitle.setObjectName("SplashSubtitle")
        subtitle.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.status = QLabel("Đang khởi động ứng dụng")
        self.status.setObjectName("SplashStatus")

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)

        self.setStyleSheet(
            """
            #SplashPanel { background: #fff7fb; border: 1px solid #f3c5d9; border-radius: 20px; }
            #SplashEyebrow { color: #a51d55; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
            #SplashTitle { color: #3d1428; font-size: 28px; font-weight: 700; }
            #SplashSubtitle, #SplashStatus { color: #7f5369; font-size: 13px; }
            QProgressBar { height: 7px; border: 0; border-radius: 3px; background: #f7dce8; }
            QProgressBar::chunk { border-radius: 3px; background: #c83d76; }
            """
        )

    def set_status(self, message: str) -> None:
        self.status.setText(message)


def show_startup_splash(app: QApplication, window) -> None:
    splash = StartupSplash()
    splash.show()
    app.processEvents()
    splash.set_status("Đang tải dữ liệu và mẫu hồ sơ")
    app.processEvents()
    QTimer.singleShot(180, app.processEvents)

    window.show()
    app.processEvents()

    animation = QPropertyAnimation(splash, b"windowOpacity")
    animation.setDuration(420)
    animation.setStartValue(1.0)
    animation.setEndValue(0.0)
    loop = QEventLoop()
    animation.finished.connect(loop.quit)
    animation.start()
    loop.exec()
    splash.close()
