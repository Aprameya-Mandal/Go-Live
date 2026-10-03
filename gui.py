import math
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QRadialGradient,
    QBrush,
    QPen,
    QIcon,
    QPixmap,
    QFont,
    QAction,
    QMouseEvent,
    QPaintEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSystemTrayIcon,
    QMenu,
    QGraphicsDropShadowEffect,
)

# --- State Colors & Text ---
STATE_CONFIG = {
    "IDLE": {
        "text": "Standby",
        "subtext": "Say 'Hey Jarvis' to wake",
        "color1": QColor(70, 80, 95),
        "color2": QColor(40, 45, 55),
        "pulse_speed": 0.03,
    },
    "LISTENING": {
        "text": "Listening...",
        "subtext": "Hearing your voice",
        "color1": QColor(56, 182, 255),    # Electric Cyan
        "color2": QColor(10, 90, 200),
        "pulse_speed": 0.08,
    },
    "PROCESSING": {
        "text": "Thinking...",
        "subtext": "Processing screen & intent",
        "color1": QColor(168, 85, 247),   # Gemini Purple
        "color2": QColor(79, 70, 229),    # Deep Indigo
        "pulse_speed": 0.12,
    },
    "SPEAKING": {
        "text": "Speaking...",
        "subtext": "Streaming audio response",
        "color1": QColor(52, 211, 153),   # Emerald / Bright Mint
        "color2": QColor(16, 185, 129),
        "pulse_speed": 0.15,
    },
}

# --- Sleek Gemini "Go Live" Style Sheet ---
BUBBLE_QSS = """
#MainContainer {
    background-color: rgba(18, 20, 26, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 28px;
}
QLabel#TitleLabel {
    color: #F3F4F6;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.2px;
}
QLabel#SubLabel {
    color: #9CA3AF;
    font-size: 11px;
}
QPushButton#CloseBtn {
    background-color: rgba(255, 255, 255, 0.06);
    color: #9CA3AF;
    border: none;
    border-radius: 14px;
    font-size: 14px;
    font-weight: bold;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}
QPushButton#CloseBtn:hover {
    background-color: rgba(239, 68, 68, 0.25);
    color: #EF4444;
}
"""


class GlowingOrbWidget(QWidget):
    """Pulsing visualizer orb representing the AI's current state."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.state = "IDLE"
        self.phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(25)  # 40 FPS refresh

    def set_state(self, state: str):
        if state in STATE_CONFIG:
            self.state = state
            self.update()

    def _animate(self):
        cfg = STATE_CONFIG.get(self.state, STATE_CONFIG["IDLE"])
        self.phase += cfg["pulse_speed"]
        self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cfg = STATE_CONFIG.get(self.state, STATE_CONFIG["IDLE"])
        pulse = (math.sin(self.phase) + 1.0) / 2.0  # 0.0 to 1.0

        center = self.rect().center()
        radius = 12.0 + (pulse * 4.0)

        # Outer glow
        glow_grad = QRadialGradient(center.x(), center.y(), radius + 4)
        c1 = QColor(cfg["color1"])
        c1.setAlpha(int(140 + 80 * pulse))
        c2 = QColor(cfg["color2"])
        c2.setAlpha(0)
        glow_grad.setColorAt(0.0, c1)
        glow_grad.setColorAt(1.0, c2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_grad))
        painter.drawEllipse(center, int(radius + 4), int(radius + 4))

        # Core circle
        core_color = QColor(cfg["color1"])
        core_color.setAlpha(240)
        painter.setBrush(QBrush(core_color))
        painter.drawEllipse(center, 7, 7)


class FloatingBubbleWindow(QWidget):
    """Borderless, draggable, translucent floating bubble window."""
    dismiss_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Frameless, Always on Top, Hidden from standard Taskbar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.drag_position = QPoint()

        self._build_ui()
        self.set_state("IDLE")

    def _build_ui(self):
        self.setObjectName("Root")
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        # Main translucent pill container
        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(BUBBLE_QSS)

        # Drop shadow for clean floating elevation
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(16, 8, 14, 8)
        container_layout.setSpacing(12)

        # Glowing Orb Indicator
        self.orb = GlowingOrbWidget(self.container)
        container_layout.addWidget(self.orb)

        # Status text container
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self.title_label = QLabel("Standby", self.container)
        self.title_label.setObjectName("TitleLabel")
        self.sub_label = QLabel("Listening for wake word", self.container)
        self.sub_label.setObjectName("SubLabel")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.sub_label)
        container_layout.addLayout(text_layout)

        # Dismiss / Sleep Button
        self.close_btn = QPushButton("✕", self.container)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setToolTip("Dismiss to background (Sleep)")
        self.close_btn.clicked.connect(self.dismiss_requested.emit)
        container_layout.addWidget(self.close_btn)

        root_layout.addWidget(self.container)
        self.resize(320, 80)

    def set_state(self, state: str):
        """Updates the indicator orb and text based on assistant activity."""
        if state in STATE_CONFIG:
            self.orb.set_state(state)
            self.title_label.setText(STATE_CONFIG[state]["text"])
            self.sub_label.setText(STATE_CONFIG[state]["subtext"])

    def show_bubble(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_bubble(self):
        self.hide()

    # --- Draggable Logic ---
    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                a0.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            a0.accept()

    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is not None and a0.buttons() == Qt.MouseButton.LeftButton:
            self.move(a0.globalPosition().toPoint() - self.drag_position)
            a0.accept()


class SystemTrayManager(QObject):
    """Controls the Windows System Tray icon, menu, and notifications."""
    show_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.tray_icon = QSystemTrayIcon(self._generate_icon(), self.app)
        self.tray_icon.setToolTip("Gemini Desktop Assistant")

        # Tray Context Menu
        menu = QMenu()
        show_action = QAction("Show Assistant (Go Live)", menu)
        show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(show_action)

        hide_action = QAction("Hide Assistant (Sleep)", menu)
        hide_action.triggered.connect(self.hide_requested.emit)
        menu.addAction(hide_action)

        menu.addSeparator()
        quit_action = QAction("Quit Assistant", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()

    def _generate_icon(self) -> QIcon:
        """Generates an in-memory sparkle icon for the system tray."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QRadialGradient(16, 16, 15)
        grad.setColorAt(0.0, QColor(56, 182, 255))
        grad.setColorAt(1.0, QColor(168, 85, 247))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        return QIcon(pixmap)