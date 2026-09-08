"""Glass presentation and Qt-native hover lighting, independent of case data."""
from PySide6.QtCore import QObject, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QGraphicsDropShadowEffect


def glass_stylesheet(dark=False):
    base = '#253443' if dark else '#e8e0df'
    end = '#344354' if dark else '#c4dce3'
    ink = '#f5f4ff' if dark else '#283444'
    pane = 'rgba(40, 48, 65, 190)' if dark else 'rgba(255, 255, 255, 155)'
    sidebar = ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(93,101,139,210),stop:0.35 rgba(34,48,66,235),stop:1 rgba(41,80,89,215))' if dark else
               'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(255,255,255,235),stop:0.32 rgba(228,220,247,190),stop:0.7 rgba(224,243,247,195),stop:1 rgba(255,255,255,225))')
    muted = '#afbed2' if dark else '#596b82'
    hover = '#35435b' if dark else '#dfe8f5'
    return f'''
/* Liquid Glass */
QMainWindow, #Content, #BusinessCasesPage, #SettingsCanvas {{
 background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {base},stop:0.48 {end},stop:1 {base});
}}
QFrame#SettingsSidebar {{background: {pane}; border: 1px solid rgba(255,255,255,160); border-radius: 20px;}}
QFrame#Card, QFrame#SettingsCard, QFrame#VisualThemeTile, QFrame#LayoutTile {{
 background: {pane}; border: 1px solid rgba(255,255,255,200); border-radius: 20px;
}}
QFrame#Card:hover, QFrame#LayoutTile:hover {{border: 1px solid #a88aff;}}
QPushButton {{color: {ink}; background: {pane}; border: 1px solid rgba(255,255,255,200); border-radius: 14px; padding: 8px 14px;}}
QPushButton:hover {{color: #ffffff; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a98bfa,stop:0.5 #8874e4,stop:1 #56cbd0); border: 1px solid #d2fcff;}}
QPushButton:pressed {{background: #7660ce;}}
QPushButton:disabled {{color: #8b929b; background: {pane};}}
QLineEdit {{color: {ink}; background: {pane}; border: 1px solid rgba(255,255,255,180); border-radius: 12px; padding: 8px;}}
QLineEdit:hover, QLineEdit:focus {{border: 1px solid #9b81ed; background: {pane};}}
QFrame#CardHeader {{background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #b596e5,stop:0.5 #9aade0,stop:1 #70cfd0); border-top-left-radius: 20px; border-top-right-radius: 20px;}}
QFrame#Sidebar {{background: transparent; border: 1px solid rgba(255,255,255,120); border-radius: 20px;}}
QFrame#Sidebar QLabel#AppTitle {{color: #ffffff; font-size: 18px; font-weight: 800; background: transparent;}}
QFrame#Sidebar QLabel#AppEyebrow {{color: rgba(255, 255, 255, 0.88); font-size: 11px; font-weight: 700; letter-spacing: 0.5px; background: transparent;}}
QFrame#Sidebar QLabel#SidebarFooter {{color: rgba(255, 255, 255, 0.82); font-size: 12px; background: transparent;}}
QFrame#Sidebar QPushButton#NavButton {{
 color: rgba(255, 255, 255, 0.95); background: transparent; border: 1px solid transparent;
 border-radius: 12px;
 text-align: left; padding: 11px 14px; font-size: 13px; font-weight: 500;
}}
QFrame#Sidebar QPushButton#NavButton:hover {{
 color: #ffffff; background: rgba(255, 255, 255, 0.16); border: 1px solid rgba(255, 255, 255, 0.25);
}}
QFrame#Sidebar QPushButton#NavButton[active="true"] {{
 color: #ffffff; background: rgba(255, 255, 255, 0.25);
 border: 1.5px solid rgba(255, 255, 255, 0.50); border-radius: 12px; font-weight: 700;
}}
QFrame#Sidebar QPushButton#NavButton[active="true"]:hover {{
 background: rgba(255, 255, 255, 0.32); color: #ffffff;
}}
QFrame#Sidebar QPushButton#NavButton:disabled {{color: rgba(255, 255, 255, 0.45); background: transparent;}}
''' + glass_controls(dark)


def glass_controls(dark=False):
    """Frosted panels with bright rims, with solid popup reading surfaces."""
    ink = '#eef2fa' if dark else '#243247'
    muted = '#b4c0d2' if dark else '#53647c'
    surface = '#253347' if dark else '#fbfcff'
    canvas = '#1c2738' if dark else '#eff2f8'
    border = '#53647c' if dark else '#bdc9dc'
    hover = '#354560' if dark else '#e8e3fa'
    accent = '#bdaaff' if dark else '#7154b6'
    canvas = ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #343248,stop:0.4 #24394a,stop:0.75 #28384c,stop:1 #403650)' if dark else
              'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ede3ee,stop:0.35 #dae4f1,stop:0.7 #d9eeec,stop:1 #e9e0f4)')
    glass = ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(100,109,142,180),stop:0.12 rgba(42,56,75,235),stop:0.75 rgba(36,54,70,220),stop:1 rgba(81,97,128,200))' if dark else
             'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(255,255,255,245),stop:0.12 rgba(255,255,255,190),stop:0.7 rgba(248,250,255,165),stop:1 rgba(222,241,247,210))')
    rim = 'rgba(203,216,247,110)' if dark else 'rgba(255,255,255,235)'
    css = f"""
QDialog, QMessageBox {{background: {canvas}; color: {ink};}}
QLabel, QCheckBox, QRadioButton, QGroupBox {{color: {ink};}}
QWidget#BusinessCasesPage, QWidget#BusinessWorkspacePage, QWidget#TrashPage,
QWidget#CategoryHubPage, QWidget#AuthorizedPersonPage, QWidget#SettingsCanvas {{
 background: {canvas}; color: {ink};
}}
QScrollArea, QScrollArea > QWidget > QWidget,
QScrollArea#CaseCardsScroll > QWidget > QWidget,
QScrollArea#BusinessWorkspaceScroll > QWidget > QWidget,
QScrollArea#PeopleListScroll > QWidget > QWidget,
QWidget#CaseCardsContainer {{background: transparent; border: none;}}
QLabel#PageTitle, QLabel#CardTitle, QLabel#CreateTitle, QLabel#ModalTitle,
QLabel#CompanyTypeTitle, QLabel#DossierItemTitle {{color: {ink};}}
QLabel#CardSubtitle, QLabel#CreateDescription, QLabel#ModalSubtitle,
QLabel#CompanyTypeSubtitle, QLabel#DossierItemDesc {{color: {muted};}}
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit,
QLineEdit#SettingsSearch, QLineEdit#IndustrySearchInput,
QGroupBox#CccdResultCard QLineEdit, QGroupBox#CccdResultCard QTextEdit {{
 background: {surface}; color: {ink}; border: 1px solid {border};
 border-radius: 10px; padding: 7px 10px;
 selection-background-color: #7154b6; selection-color: white;
}}
QLineEdit:hover, QComboBox:hover, QTextEdit:hover {{border-color: {accent}; background: {surface}; color: {ink};}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
 border: 1px solid {accent}; background: {surface}; color: {ink};
}}
QComboBox {{padding-right: 30px;}}
QComboBox::drop-down {{width: 26px; border: none; border-left: 1px solid {border}; border-top-right-radius: 10px; border-bottom-right-radius: 10px; background: {hover};}}
QComboBox QAbstractItemView {{
 background: {surface}; color: {ink}; border: 1px solid {border};
 selection-background-color: #6750a4; selection-color: white;
 padding: 4px; outline: 0;
}}
QComboBox QAbstractItemView::item {{min-height: 28px; padding: 4px 8px;}}
QTableView, QTreeView, QListView, QTableWidget {{
 background: {surface}; alternate-background-color: {canvas}; color: {ink};
 border: 1px solid {border}; border-radius: 10px;
 selection-background-color: #6750a4; selection-color: white; gridline-color: {border};
}}
QHeaderView::section {{background: {hover}; color: {ink}; padding: 8px; border: none; border-bottom: 1px solid {border};}}
QTabWidget::pane, QGroupBox {{background: {surface}; border: 1px solid {border}; border-radius: 12px;}}
QTabBar::tab {{background: {canvas}; color: {muted}; padding: 8px 14px; border-bottom: 2px solid transparent;}}
QTabBar::tab:selected {{background: {surface}; color: {ink}; border-bottom: 2px solid {accent};}}
QTabBar::tab:hover {{background: {hover}; color: {ink};}}
QMenu, QToolTip {{background: {surface}; color: {ink}; border: 1px solid {border}; padding: 6px;}}
QMenu::item:selected {{background: #6750a4; color: white;}}
QScrollBar:vertical {{background: {canvas}; width: 10px; margin: 0;}}
QScrollBar::handle:vertical {{background: {border}; min-height: 28px; border-radius: 5px;}}
QScrollBar::handle:vertical:hover {{background: {accent};}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{height: 0;}}
QCheckBox::indicator, QRadioButton::indicator {{width: 16px; height: 16px;}}
"""
    for name in ('Card', 'CreateCard', 'SettingsCard', 'BusinessCreationModalBox',
                 'CompanyTypeCard', 'DossierListItem', 'DetailPreviewPanel'):
        css += f'QFrame#{name} {{background: {glass}; color: {ink}; border: 1px solid {rim}; border-bottom: 1px solid {border}; border-radius: 20px;}}\n'
    for name in ('PrimaryButton', 'CompactPrimaryButton', 'ModalCreateButton',
                 'GhostButton', 'CompactGhostButton', 'ModalDismissButton',
                 'SettingsBackButton', 'ModalCloseButton'):
        primary = name in ('PrimaryButton', 'CompactPrimaryButton', 'ModalCreateButton')
        fill = 'qlineargradient(x1:0,y1:0,x2:0.3,y2:1,stop:0 #a189d4,stop:0.16 #7b5aba,stop:0.8 #536caa,stop:1 #789bc0)' if primary else glass
        text = '#ffffff' if primary else ink
        css += f"""
QPushButton#{name} {{background: {fill}; color: {text}; border: 1px solid {border}; border-radius: 10px; padding: 7px 12px; font-weight: 600;}}
QPushButton#{name}:hover {{background: {'#62499f' if primary else hover}; color: {text}; border-color: {accent};}}
QPushButton#{name}:pressed {{background: #4b407d; color: white;}}
QPushButton#{name}:focus {{border: 1px solid {accent};}}
QPushButton#{name}:disabled {{background: {canvas}; color: {muted}; border-color: {border};}}
"""
    return css


class GlassHover(QObject):
    """Animate only owned effects; never replace other widgets' effects."""
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.active = False
        self.motion = True
        self.effects = {}

    def configure(self, active, motion=True):
        self.active, self.motion = active, motion
        if not active:
            for widget, (effect, animation) in list(self.effects.items()):
                animation.stop()
                widget.removeEventFilter(self)
                if widget.graphicsEffect() is effect:
                    widget.setGraphicsEffect(None)
            self.effects.clear()

    def eventFilter(self, widget, event):
        if widget in self.effects and event.type() in (QEvent.Enter, QEvent.Leave):
            effect, animation = self.effects[widget]
            animation.stop()
            target = 22.0 if event.type() == QEvent.Enter else 3.0
            if self.motion:
                animation.setStartValue(effect.blurRadius())
                animation.setEndValue(target)
                animation.start()
            else:
                effect.setBlurRadius(target)
        return False

    def attach(self):
        if not self.active:
            return
        for widget in self.window.findChildren(QWidget):
            # Transparent navigation buttons cast shadows on their text glyphs.
            # Keep sidebar text crisp and use background/edge hover styling.
            if widget.objectName() == 'NavButton':
                continue
            if not isinstance(widget, (QPushButton, QLineEdit)) or widget.graphicsEffect() is not None:
                continue
            effect = QGraphicsDropShadowEffect(widget)
            effect.setColor(QColor(141, 113, 222, 120))
            effect.setOffset(0, 2)
            effect.setBlurRadius(3)
            widget.setGraphicsEffect(effect)
            animation = QPropertyAnimation(effect, b'blurRadius', effect)
            animation.setDuration(180)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            self.effects[widget] = (effect, animation)
            widget.destroyed.connect(lambda _=None, key=widget: self.effects.pop(key, None))
            widget.installEventFilter(self)
