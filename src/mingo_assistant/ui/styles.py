from functools import lru_cache


APP_STYLESHEET = """
* {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #3d2430;
}

QMainWindow {
    background: #fff7fa;
}

#Sidebar {
    background: #c46a93;
}

#AppEyebrow {
    color: #fff0f6;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0px;
}

#AppTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
}

QPushButton#NavButton {
    text-align: left;
    color: #fff7fb;
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 11px 12px;
    font-weight: 600;
}

QPushButton#NavButton:hover {
    background: rgba(255, 255, 255, 0.14);
}

QPushButton#NavButton[active="true"] {
    background: #e38ab0;
    border: 1px solid rgba(255, 255, 255, 0.24);
}

#Content {
    background: #fff7fa;
}

#PageTitle {
    color: #9b315f;
    font-size: 25px;
    font-weight: 800;
}

#PageDescription {
    color: #765565;
    font-size: 13px;
}

#DocumentsEyebrow {
    color: #c46a93;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}

#SummaryCard,
#DocumentsPanel {
    background: #ffffff;
    border: 1px solid #f0d4df;
    border-radius: 12px;
}

#SectionTitle {
    color: #4b2434;
    font-size: 16px;
    font-weight: 800;
}

#SectionCount,
#SectionHint,
#VersionMeta,
#DocumentMeta {
    color: #8b6877;
    font-size: 12px;
}

#SummaryLabel {
    color: #a15b78;
    font-size: 10px;
    font-weight: 800;
}

#SummaryValue {
    color: #4b2434;
    font-size: 14px;
    font-weight: 700;
}

#SummaryPath,
#DocumentPath {
    color: #8b6877;
    font-size: 11px;
}

#SummaryStatus {
    background: #e9f8ef;
    color: #27804c;
    border-radius: 12px;
    padding: 5px 11px;
    font-size: 11px;
    font-weight: 800;
}

#VersionCard {
    background: #fffafd;
    border: 1px solid #f1d8e3;
    border-radius: 9px;
}

QRadioButton#VersionSelector {
    color: #9b315f;
    font-size: 14px;
    font-weight: 800;
    spacing: 8px;
}

QRadioButton#VersionSelector::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #d798b5;
    border-radius: 8px;
    background: #ffffff;
}

QRadioButton#VersionSelector::indicator:checked {
    border: 5px solid #c46a93;
    background: #ffffff;
}

#DocumentRow {
    background: #ffffff;
    border: 1px solid #f3dfe7;
    border-radius: 8px;
}

#DocumentIndex {
    background: #ffe8f0;
    color: #9b315f;
    border-radius: 8px;
    padding: 8px 4px;
    font-size: 11px;
    font-weight: 800;
}

#DocumentTitle {
    color: #4b2434;
    font-size: 14px;
    font-weight: 800;
}

QPushButton#CompactPrimaryButton,
QPushButton#CompactGhostButton {
    min-width: 68px;
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 12px;
}

QPushButton#CompactPrimaryButton {
    background: #c46a93;
    color: #ffffff;
    border: none;
    font-weight: 800;
}

QPushButton#CompactPrimaryButton:hover {
    background: #aa527b;
}

QPushButton#CompactGhostButton {
    background: #ffffff;
    color: #9b315f;
    border: 1px solid #efc4d6;
    font-weight: 700;
}

#FilterLabel {
    color: #70455a;
    font-size: 10px;
    font-weight: 800;
}

QLineEdit,
QComboBox,
QTextEdit {
    background: #ffffff;
    border: 1px solid #efc4d6;
    border-radius: 5px;
    padding: 9px 10px;
    min-height: 20px;
}

QLineEdit:focus,
QComboBox:focus,
QTextEdit:focus {
    border: 1px solid #c46a93;
}

QGroupBox {
    background: #ffffff;
    border: 1px solid #f0d4df;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 800;
    color: #9b315f;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QGroupBox#CccdResultCard {
    background: #fbfdff;
    border: 1px solid #b9d7f2;
    color: #1f5f99;
}

QGroupBox#CccdResultCard QLineEdit,
QGroupBox#CccdResultCard QTextEdit {
    border: 1px solid #b9d7f2;
}

QGroupBox#CccdResultCard QLineEdit:focus,
QGroupBox#CccdResultCard QTextEdit:focus {
    border: 1px solid #2f80ed;
}

#ResultText {
    color: #9b315f;
    font-size: 15px;
    font-weight: 700;
}

#Card {
    background: #ffffff;
    border: 1px solid #f0d4df;
    border-radius: 8px;
}

#CardHeader {
    background: #d878a2;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

#CardTitle {
    color: #4b2434;
    font-size: 17px;
    font-weight: 800;
}

#CardSubtitle {
    color: #765565;
    font-size: 11px;
    font-weight: 800;
}

#MetaText {
    color: #765565;
    font-size: 12px;
}

#TableHeader {
    background: #fff0f6;
    border: 1px solid #efc4d6;
    color: #9b315f;
    font-size: 12px;
    font-weight: 800;
    padding: 8px;
}

#TableCell {
    background: #ffffff;
    border: 1px solid #efc4d6;
}

#StatusBadge {
    background: #ffe5ef;
    color: #9b315f;
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 800;
}

#WarningBadge {
    background: #fff0d5;
    color: #9b5b00;
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 800;
}

QPushButton#HeaderDeleteButton {
    background: rgba(255, 255, 255, 0.18);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.36);
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 800;
}

QPushButton#HeaderDeleteButton:hover {
    background: rgba(255, 255, 255, 0.28);
}

QPushButton#PrimaryButton {
    background: #c46a93;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 9px 12px;
    font-weight: 800;
}

QPushButton#PrimaryButton:hover {
    background: #aa527b;
}

QPushButton#GhostButton {
    background: #ffffff;
    color: #9b315f;
    border: 1px solid #efc4d6;
    border-radius: 6px;
    padding: 8px 11px;
    font-weight: 700;
}

#CreateCard {
    background: #ffffff;
    border: 1px dashed #dfa0ba;
    border-radius: 8px;
}

#CreateIcon {
    color: #c46a93;
    font-size: 38px;
    font-weight: 300;
}

#CreateTitle {
    color: #9b315f;
    font-size: 17px;
    font-weight: 800;
}

#CreateDescription,
#EmptyDescription {
    color: #765565;
    font-size: 13px;
}

#ComingSoonTitle {
    color: #9b315f;
    font-size: 24px;
    font-weight: 800;
}

QTableWidget {
    background: #ffffff;
    alternate-background-color: #fff7fa;
    gridline-color: #efc4d6;
    border: 1px solid #efc4d6;
    selection-background-color: #c46a93;
    selection-color: #ffffff;
}

QHeaderView::section {
    background: #fff0f6;
    color: #9b315f;
    border: 1px solid #efc4d6;
    padding: 7px 8px;
    font-weight: 800;
}

QTableWidget::item {
    padding: 4px 6px;
}

QTableWidget::item:selected {
    background: #c46a93;
    color: #ffffff;
}

QWidget#IndustryLookupPage {
    background: #f3f7fc;
}

QLabel#IndustryLookupTitle {
    color: #1f3a5f;
    font-size: 25px;
    font-weight: 800;
}

QLabel#IndustryLookupDescription,
QLabel#IndustryLookupSubSource,
QLabel#IndustryLookupStatus {
    color: #526173;
    font-size: 13px;
}

QFrame#IndustryLookupPanel {
    background: #ffffff;
    border: 1px solid #bfd2e8;
    border-radius: 6px;
}

QLabel#IndustryLookupSource {
    color: #1f3a5f;
    font-size: 15px;
    font-weight: 800;
}

QLineEdit#IndustrySearchInput {
    background: #ffffff;
    border: 1px solid #cfd8e3;
    border-radius: 5px;
    color: #172033;
}

QLineEdit#IndustrySearchInput:focus {
    border: 1px solid #2f80ed;
}

QTableWidget#IndustryTable {
    background: #ffffff;
    alternate-background-color: #ffffff;
    gridline-color: #1f2937;
    border: 1px solid #1f2937;
    selection-background-color: #d9ebff;
    selection-color: #ffffff;
    color: #111827;
}

QTableWidget#IndustryTable QHeaderView::section {
    background: #f8fbff;
    color: #111827;
    border: 1px solid #1f2937;
    padding: 9px 6px;
    font-weight: 800;
}

QTableWidget#IndustryTable::item {
    padding: 8px 6px;
    border-color: #1f2937;
}

QTableWidget#IndustryTable::item:selected {
    background: #d9ebff;
    color: #0f172a;
}
"""


SETTINGS_STYLESHEET = """
QDialog#SettingsDialog {
    background: #fff7fa;
}

#SettingsSidebar {
    background: #fffafd;
    border-right: 1px solid #f0d4df;
}

QPushButton#SettingsBackButton {
    text-align: left;
    background: transparent;
    border: none;
    color: #4b2434;
    padding: 8px 6px;
    font-size: 14px;
}

QLineEdit#SettingsSearch {
    background: #f3edf0;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
}

#SettingsEyebrow {
    color: #8b6877;
    font-size: 10px;
    font-weight: 800;
    padding: 10px 6px 2px;
}

QPushButton#SettingsCategory {
    text-align: left;
    color: #4b2434;
    background: transparent;
    border: none;
    border-radius: 7px;
    padding: 9px 10px;
    font-size: 14px;
}

QPushButton#SettingsCategory:hover {
    background: #f3e7ed;
}

QPushButton#SettingsCategory[active="true"] {
    background: #ead6e0;
    font-weight: 700;
}

#SettingsSidebarNote {
    color: #8b6877;
    font-size: 11px;
    padding: 8px 6px;
}

#SettingsContent,
#SettingsCanvas {
    background: #fff7fa;
}

#SettingsPageTitle {
    color: #4b2434;
    font-size: 28px;
    font-weight: 700;
}

#SettingsPageDescription {
    color: #765565;
    font-size: 14px;
}

#SettingsSectionTitle {
    color: #4b2434;
    font-size: 16px;
    font-weight: 800;
    margin-top: 8px;
}

#SettingsCard {
    background: #ffffff;
    border: 1px solid #f0d4df;
    border-radius: 14px;
}

#ThemeOption {
    border-radius: 9px;
}

#ThemeOption:hover {
    background: #fff7fa;
}

QPushButton#AppearanceModeTile {
    min-height: 98px;
    background: #ffffff;
    color: #4b2434;
    border: 1px solid #f0d4df;
    border-radius: 12px;
    padding: 10px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#AppearanceModeTile:hover {
    border-color: #d798b5;
    background: #fffafd;
}

QPushButton#AppearanceModeTile:checked {
    border: 2px solid #c46a93;
    background: #fff0f6;
}

#SettingsItemTitle {
    color: #4b2434;
    font-size: 14px;
    font-weight: 700;
}

#SettingsItemDescription,
#SettingsHint {
    color: #765565;
    font-size: 12px;
}

#SettingsStrengthValue {
    color: #9b315f;
    font-size: 13px;
    font-weight: 800;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #f0d4df;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #c46a93;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: #ffffff;
    border: 2px solid #c46a93;
    border-radius: 9px;
}

#SettingsFooter {
    background: #ffffff;
    border-top: 1px solid #f0d4df;
}
"""

THEME_OPTIONS = {
    "rose": {"label": "Hồng", "color": "#C46A93"},
    "sky_blue": {"label": "Xanh trời", "color": "#AEE2FF"},
    "sage_green": {"label": "Xanh lá", "color": "#8EC3B0"},
    "violet": {"label": "Tím lavender", "color": "#B7A7F7"},
    "ocean": {"label": "Xanh biển", "color": "#63C5DA"},
    "amber": {"label": "Vàng hổ phách", "color": "#F5C16C"},
    "olive_gray": {"label": "Xám olive", "color": "#A8A492"},
}

_THEME_REPLACEMENTS = {
    "sky_blue": {
        "#fff7fa": "#F4FAFF", "#c46a93": "#4F93C4", "#e38ab0": "#8FCBF0",
        "#fff0f6": "#E7F5FF", "#9b315f": "#2D6F9E", "#765565": "#5C7485",
        "#f0d4df": "#CFE8FA", "#4b2434": "#243D4D", "#8b6877": "#627B8A",
        "#a15b78": "#4B7A9B", "#fffafd": "#FAFDFF", "#f1d8e3": "#DCEEF9",
        "#d798b5": "#7BB7DF", "#ffe8f0": "#E3F4FF", "#efc4d6": "#BFDDF1",
        "#d878a2": "#79B5DD", "#70455a": "#416B84", "#ffe5ef": "#E0F3FF",
        "#dfa0ba": "#8FCBF0", "#aa527b": "#3C82B2",
    },
    "sage_green": {
        "#fff7fa": "#F4FAF6", "#c46a93": "#4D947B", "#e38ab0": "#7DBDA7",
        "#fff0f6": "#E8F5EE", "#9b315f": "#276651", "#765565": "#5B746A",
        "#f0d4df": "#CBE4D8", "#4b2434": "#254438", "#8b6877": "#62776D",
        "#a15b78": "#4D806B", "#fffafd": "#FAFDFC", "#f1d8e3": "#DDECE4",
        "#d798b5": "#72AD98", "#ffe8f0": "#E0F3E9", "#efc4d6": "#BBDCCF",
        "#d878a2": "#6EAD96", "#70455a": "#426B59", "#ffe5ef": "#DDF1E7",
        "#dfa0ba": "#7DBDA7", "#aa527b": "#3B8068",
    },
    "violet": {
        "#fff7fa": "#FAF8FF", "#c46a93": "#7866C6", "#e38ab0": "#B7A7F7",
        "#fff0f6": "#F0ECFF", "#9b315f": "#5949A1", "#765565": "#6E6792",
        "#f0d4df": "#DDD6FA", "#4b2434": "#342B59", "#efc4d6": "#CDC4F2",
        "#d878a2": "#9D8BE1", "#aa527b": "#5F4EAC",
    },
    "ocean": {
        "#fff7fa": "#F2FBFD", "#c46a93": "#278CA7", "#e38ab0": "#63C5DA",
        "#fff0f6": "#E5F7FA", "#9b315f": "#176A82", "#765565": "#55757D",
        "#f0d4df": "#C8E8EE", "#4b2434": "#193F49", "#efc4d6": "#B5DEE7",
        "#d878a2": "#4FAEC4", "#aa527b": "#1E7790",
    },
    "amber": {
        "#fff7fa": "#FFF9F0", "#c46a93": "#B77A22", "#e38ab0": "#F5C16C",
        "#fff0f6": "#FFF0D5", "#9b315f": "#895912", "#765565": "#7A6850",
        "#f0d4df": "#F1DEB9", "#4b2434": "#4A3516", "#efc4d6": "#EACF9C",
        "#d878a2": "#DEA549", "#aa527b": "#986117",
    },
    "olive_gray": {
        "#fff7fa": "#FAF9F4", "#c46a93": "#777466", "#e38ab0": "#A8A492",
        "#fff0f6": "#F0EFE8", "#9b315f": "#59574D", "#765565": "#727066",
        "#f0d4df": "#DDDACE", "#4b2434": "#37362F", "#efc4d6": "#D0CDC0",
        "#d878a2": "#918D7B", "#aa527b": "#666356",
    },
}

_THEME_SIDEBAR = {
    "sky_blue": ("#AEE2FF", "#173B53", "#86C8F2"),
    "sage_green": ("#8EC3B0", "#183D31", "#72AD98"),
    "violet": ("#B7A7F7", "#30285A", "#9D8BE1"),
    "ocean": ("#63C5DA", "#163E49", "#4FAEC4"),
    "amber": ("#F5C16C", "#50370E", "#DEA549"),
    "olive_gray": ("#A8A492", "#303029", "#918D7B"),
}


def _theme_strength(value: int | str | None) -> int:
    try:
        return max(60, min(140, int(value or 100)))
    except (TypeError, ValueError):
        return 100


def _adjust_color(color: str, strength: int) -> str:
    """Lighten or deepen an accent while retaining a legible palette."""
    if strength == 100 or not color.startswith("#") or len(color) != 7:
        return color
    rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    if strength < 100:
        factor = strength / 100
        adjusted = tuple(round(255 - (255 - channel) * factor) for channel in rgb)
    else:
        factor = 1 - (strength - 100) / 160
        adjusted = tuple(round(channel * factor) for channel in rgb)
    return "#" + "".join(f"{channel:02X}" for channel in adjusted)


def _accent_colors(theme_id: str) -> set[str]:
    if theme_id == "rose":
        return {"#c46a93", "#e38ab0", "#d878a2", "#aa527b", "#dfa0ba", "#d798b5"}
    colors = set(_THEME_REPLACEMENTS[theme_id].values())
    colors.update(_THEME_SIDEBAR[theme_id][::2])
    return colors


def resolved_appearance_mode(mode: str | None, system_is_dark: bool = False) -> str:
    if mode == "dark":
        return "dark"
    if mode == "system" and system_is_dark:
        return "dark"
    return "light"


def _dark_stylesheet(accent: str) -> str:
    return f"""
* {{ color: #E9EDF1; }}
QMainWindow, QDialog#SettingsDialog, #Content, #SettingsContent, #SettingsCanvas {{ background: #1A1C1F; }}
QFrame#Sidebar, #SettingsSidebar {{ background: #202328; border-color: #34383E; }}
#AppEyebrow, #AppTitle, #SidebarFooter, #SettingsSidebarNote {{ color: #E9EDF1; }}
QPushButton#NavButton, QPushButton#SettingsCategory, QPushButton#SettingsBackButton {{ color: #E9EDF1; }}
QPushButton#NavButton:hover, QPushButton#SettingsCategory:hover {{ background: #2A2E34; }}
QPushButton#NavButton[active=\"true\"], QPushButton#SettingsCategory[active=\"true\"] {{ background: #30353B; border-color: {accent}; }}
#PageTitle, #SectionTitle, #CardTitle, #DocumentTitle, #SummaryValue, #SettingsPageTitle, #SettingsSectionTitle, #SettingsItemTitle {{ color: #F5F7F9; }}
#PageDescription, #MetaText, #CardSubtitle, #SummaryPath, #DocumentPath, #SettingsPageDescription, #SettingsItemDescription, #SettingsHint {{ color: #B9C0C8; }}
#SummaryCard, #DocumentsPanel, #Card, #VersionCard, #DocumentRow, #SettingsCard {{ background: #24272C; border-color: #383D44; }}
QLineEdit, QComboBox, QTextEdit, QLineEdit#SettingsSearch {{ background: #25282D; color: #F1F3F5; border-color: #41464E; }}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border-color: {accent}; }}
QGroupBox {{ background: #24272C; border-color: #383D44; color: #F1F3F5; }}
#TableHeader, QHeaderView::section {{ background: #2B2F35; color: #F1F3F5; border-color: #41464E; }}
QTableWidget {{ background: #24272C; alternate-background-color: #202328; gridline-color: #41464E; border-color: #41464E; color: #F1F3F5; selection-background-color: {accent}; }}
QTableWidget::item:selected {{ background: {accent}; color: #101214; }}
QPushButton#PrimaryButton, QPushButton#CompactPrimaryButton {{ background: {accent}; color: #101214; }}
QPushButton#GhostButton, QPushButton#CompactGhostButton {{ background: #2B2F35; color: #F1F3F5; border-color: #454A52; }}
#CardHeader {{ background: {accent}; }}
#SettingsFooter {{ background: #202328; border-color: #34383E; }}
QPushButton#AppearanceModeTile {{ background: #25282D; color: #E9EDF1; border-color: #41464E; }}
QPushButton#AppearanceModeTile:hover {{ background: #2B2F35; border-color: {accent}; }}
QPushButton#AppearanceModeTile:checked {{ background: #30353B; border-color: {accent}; }}
QWidget#BusinessCasesPage, QWidget#BusinessWorkspacePage, QWidget#CaseCardsContainer, QWidget#PeopleListContainer {{ background: #1A1C1F; }}
QScrollArea#CaseCardsScroll, QScrollArea#BusinessWorkspaceScroll, QScrollArea#PeopleListScroll {{ background: #1A1C1F; }}
QScrollArea#CaseCardsScroll::viewport, QScrollArea#BusinessWorkspaceScroll::viewport, QScrollArea#PeopleListScroll::viewport {{ background: #1A1C1F; }}
QScrollArea#CaseCardsScroll > QWidget > QWidget, QScrollArea#BusinessWorkspaceScroll > QWidget > QWidget, QScrollArea#PeopleListScroll > QWidget > QWidget {{ background: #1A1C1F; }}
QGroupBox#CccdResultCard {{ background: #24272C; border-color: #3D4651; color: #E9EDF1; }}
QGroupBox#CccdResultCard QLineEdit, QGroupBox#CccdResultCard QTextEdit {{ background: #202328; border-color: #46515E; color: #F1F3F5; }}
#CreateCard {{ background: #24272C; border-color: {accent}; }}
#CreateIcon, #CreateTitle {{ color: #F1F3F5; }}
#CreateDescription, #EmptyDescription, #SectionCount, #SectionHint, #VersionMeta, #DocumentMeta, #MetaText {{ color: #B9C0C8; }}
#FilterLabel, #ResultText, #DocumentsEyebrow, #SummaryLabel {{ color: {accent}; }}
QPushButton#SettingsButton {{ background: #2B2F35; color: #F1F3F5; border: 1px solid #454A52; border-radius: 6px; min-width: 38px; min-height: 34px; font-size: 18px; }}
QPushButton#SettingsButton:hover {{ border-color: {accent}; background: #343941; }}
QComboBox QAbstractItemView {{ background: #25282D; color: #F1F3F5; selection-background-color: {accent}; selection-color: #101214; }}
QProgressBar {{ background: #30343A; border: 1px solid #474D55; border-radius: 4px; color: #F1F3F5; text-align: center; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
QScrollBar:vertical {{ background: #202328; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #454A52; min-height: 28px; border-radius: 5px; }}
QSlider::groove:horizontal {{ background: #3A3F47; }}
QSlider::sub-page:horizontal {{ background: {accent}; }}
QSlider::handle:horizontal {{ background: #1A1C1F; border-color: {accent}; }}
"""


@lru_cache(maxsize=128)
def stylesheet_for_theme(
    theme_id: str | None,
    strength: int | str | None = 100,
    appearance_mode: str | None = "light",
    system_is_dark: bool = False,
) -> str:
    """Return the stylesheet for a persisted color palette and appearance mode."""
    selected = theme_id if theme_id in THEME_OPTIONS else "rose"
    normalized_strength = _theme_strength(strength)
    stylesheet = APP_STYLESHEET + SETTINGS_STYLESHEET
    for source, target in _THEME_REPLACEMENTS.get(selected, {}).items():
        stylesheet = stylesheet.replace(source, target)
    if selected != "rose":
        sidebar, text, active = _THEME_SIDEBAR[selected]
        stylesheet += f"""
QFrame#Sidebar {{ background: {sidebar}; }}
#AppEyebrow, #AppTitle {{ color: {text}; }}
QPushButton#NavButton {{ color: {text}; }}
QPushButton#NavButton:hover {{ background: rgba(255, 255, 255, 0.34); }}
QPushButton#NavButton[active=\"true\"] {{ background: {active}; border-color: rgba(23, 59, 53, 0.14); }}
QLabel#SidebarFooter {{ color: {text}; }}
"""
    for color in _accent_colors(selected):
        stylesheet = stylesheet.replace(color, _adjust_color(color, normalized_strength))
    if resolved_appearance_mode(appearance_mode, system_is_dark) == "dark":
        accent = _adjust_color(_THEME_REPLACEMENTS.get(selected, {}).get("#c46a93", "#c46a93"), normalized_strength)
        stylesheet += _dark_stylesheet(accent)
    return stylesheet
