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

#TopNavBrand {
    color: #c46a93;
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 0.8px;
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

/* Visual Theme Mockup Tiles */
QFrame#VisualThemeTile {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}
QFrame#VisualThemeTile:hover {
    border-color: #cbd5e1;
    background: #f8fafc;
}
QFrame#VisualThemeTile[selected="true"] {
    border: 2px solid #c46a93;
    background: #fff7fa;
}
QLabel#VisualThemeLabel {
    font-size: 13px;
    font-weight: 700;
    color: #1e293b;
}

/* Layout Mode Tiles */
QFrame#LayoutTile {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}
QFrame#LayoutTile:hover {
    border-color: #cbd5e1;
    background: #f8fafc;
}
QFrame#LayoutTile[selected="true"] {
    border: 2px solid #c46a93;
    background: #fff7fa;
}
QLabel#LayoutTileTitle {
    font-size: 13.5px;
    font-weight: 700;
    color: #1e293b;
}
QLabel#LayoutTileDesc {
    font-size: 11.5px;
    color: #64748b;
    line-height: 1.3;
}

/* Color Category Tabs */
QPushButton#ColorCategoryTab {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    color: #475569;
}
QPushButton#ColorCategoryTab:hover {
    background: #f1f5f9;
    border-color: #cbd5e1;
    color: #1e293b;
}
QPushButton#ColorCategoryTab[active="true"] {
    background: #c46a93;
    color: #ffffff;
    border-color: #c46a93;
}

/* Color Chip Card */
QFrame#ColorChipCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame#ColorChipCard:hover {
    border-color: #cbd5e1;
    background: #f8fafc;
}
QFrame#ColorChipCard[selected="true"] {
    border: 2px solid #c46a93;
    background: #fff7fa;
}
QLabel#ColorChipName {
    font-size: 12px;
    font-weight: 700;
    color: #1e293b;
}
QLabel#ColorChipHex {
    font-size: 10.5px;
    color: #64748b;
}
QLabel#ColorChipCheck {
    font-size: 12px;
    font-weight: 900;
    color: #ffffff;
}

/* Reset to Default Button */
QPushButton#SettingsResetButton {
    background: #fff1f5;
    color: #be185d;
    border: 1px solid #fbcfe8;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#SettingsResetButton:hover {
    background: #fce7f3;
    border-color: #f472b6;
    color: #9d174d;
}

/* View Mode Toggle Buttons on MainWindow */
QPushButton#ViewModeBtn {
    background: #ffffff;
    border: 1px solid #f0d4df;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #765565;
}
QPushButton#ViewModeBtn:hover {
    background: #fffafd;
    border-color: #d798b5;
}
QPushButton#ViewModeBtn[active="true"] {
    background: #c46a93;
    color: #ffffff;
    border-color: #c46a93;
}

QTableWidget#CasesTable {
    background: #ffffff;
    border: 1px solid #f0d4df;
    border-radius: 8px;
    gridline-color: #f7eaf0;
    selection-background-color: #fff0f6;
    selection-color: #4b2434;
}
QTableWidget#CasesTable::item {
    padding: 6px 10px;
    border-bottom: 1px solid #f7eaf0;
}
"""

THEME_CATEGORIES = {
    "all": "Tất cả",
    "executive": "Doanh nghiệp",
    "vibrant": "Tươi sáng",
    "pastel": "Dịu nhẹ",
    "cyber": "Cyber / Tối",
}

THEME_OPTIONS = {
    # 1. Doanh nghiệp & Pháp lý (Executive & Corporate)
    "rose": {"label": "Hồng", "color": "#C46A93", "category": "executive"},
    "steel_blue": {"label": "Xanh thép", "color": "#3B7597", "category": "executive"},
    "corporate_navy": {"label": "Xanh navy", "color": "#1E3A8A", "category": "executive"},
    "royal_indigo": {"label": "Chàm hoàng gia", "color": "#4338CA", "category": "executive"},
    "burgundy": {"label": "Đỏ Bordeaux", "color": "#881337", "category": "executive"},
    "charcoal": {"label": "Xám than chì", "color": "#475569", "category": "executive"},

    # 2. Tươi sáng & Năng động (Vibrant & Energetic)
    "ocean": {"label": "Xanh biển", "color": "#63C5DA", "category": "vibrant"},
    "sky_blue": {"label": "Xanh trời", "color": "#AEE2FF", "category": "vibrant"},
    "turquoise": {"label": "Lam ngọc tươi", "color": "#06B6D4", "category": "vibrant"},
    "mint": {"label": "Bạc hà tươi", "color": "#10B981", "category": "vibrant"},
    "amber": {"label": "Vàng hổ phách", "color": "#F5C16C", "category": "vibrant"},
    "sunset": {"label": "Cam san hô", "color": "#F97316", "category": "vibrant"},
    "crimson": {"label": "Đỏ Ruby", "color": "#E11D48", "category": "vibrant"},

    # 3. Dịu nhẹ & Thư thái (Pastel & Aesthetic)
    "sage_green": {"label": "Xanh lá", "color": "#8EC3B0", "category": "pastel"},
    "violet": {"label": "Tím lavender", "color": "#B7A7F7", "category": "pastel"},
    "olive_gray": {"label": "Xám olive", "color": "#A8A492", "category": "pastel"},
    "sakura": {"label": "Hoa anh đào", "color": "#F472B6", "category": "pastel"},
    "peach": {"label": "Kem đào ấm", "color": "#FB923C", "category": "pastel"},
    "warm_sand": {"label": "Cát vàng ấm", "color": "#D4A373", "category": "pastel"},

    # 4. Công nghệ & Cyber (Cyber & Modern)
    "cyber_green": {"label": "Xanh Cyber", "color": "#06D6A0", "category": "cyber"},
    "synthwave": {"label": "Tím Synthwave", "color": "#A855F7", "category": "cyber"},
    "obsidian": {"label": "Đen huyền bí", "color": "#27272A", "category": "cyber"},
}

LAYOUT_OPTIONS = {
    "default": {
        "title": "Cổ điển (Classic)",
        "description": "Bố cục nguyên bản quen thuộc, thanh bên 220px màu đồng bộ",
        "icon": "🏛",
    },
    "modern_studio": {
        "title": "Hiện đại Studio",
        "description": "Topbar toàn cục, ô tìm kiếm trung tâm, sidebar phẳng thanh lịch",
        "icon": "💻",
    },
    "top_nav": {
        "title": "Điều hướng trên",
        "description": "Thanh menu ngang trên đỉnh, không gian 100% full-width thoáng đãng",
        "icon": "🧭",
    },
    "executive": {
        "title": "Bảng điều khiển KPI",
        "description": "Dải 4 thẻ thống kê số liệu nhanh, quản lý hồ sơ chuyên nghiệp",
        "icon": "📊",
    },
    "compact_legal": {
        "title": "Pháp lý 2 Cột",
        "description": "Cột danh sách bên trái + Khung xem chi tiết & thao tác bên phải",
        "icon": "⚖",
    },
    "slim_sidebar": {
        "title": "Tối giản Icon Bar",
        "description": "Sidebar thanh icon 60px siêu gọn, tối đa không gian hiển thị",
        "icon": "📱",
    },
    "centered_focus": {
        "title": "Tập trung trang nhã",
        "description": "Khung nội dung căn giữa 1180px phong cách Apple với Floating Toolbar",
        "icon": "🎯",
    },
    "vibrant": {
        "title": "Sinh động Floating",
        "description": "Thẻ floating bo cong mềm mại (18px), tươi mới và giàu năng lượng",
        "icon": "🎨",
    },
}

FONT_SIZE_OPTIONS = {
    "small": {"label": "Nhỏ (12px)", "size": "12px", "scale": 0.92},
    "medium": {"label": "Tiêu chuẩn (13px)", "size": "13px", "scale": 1.0},
    "large": {"label": "Lớn (14.5px)", "size": "14.5px", "scale": 1.12},
    "xlarge": {"label": "Rất lớn (16px)", "size": "16px", "scale": 1.25},
}

BORDER_RADIUS_OPTIONS = {
    "rounded": {"label": "Bo tròn (12px)", "radius": "12px"},
    "sharp": {"label": "Góc vuông (4px)", "radius": "4px"},
    "pill": {"label": "Bo cong (18px)", "radius": "18px"},
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
    "steel_blue": {
        "#fff7fa": "#F3F8FB", "#c46a93": "#3B7597", "#e38ab0": "#6FA6C5",
        "#fff0f6": "#E3EFF5", "#9b315f": "#24536E", "#765565": "#59707D",
        "#f0d4df": "#C9DDE8", "#4b2434": "#203D4D", "#8b6877": "#687B86",
        "#a15b78": "#4B7890", "#fffafd": "#FAFCFD", "#f1d8e3": "#DCEAF0",
        "#d798b5": "#77A2B8", "#ffe8f0": "#E5F1F6", "#efc4d6": "#BDD4E1",
        "#d878a2": "#679AB5", "#70455a": "#3E6477", "#ffe5ef": "#E0EDF3",
        "#dfa0ba": "#80ADC2", "#aa527b": "#2F6788",
    },
}

_THEME_SIDEBAR = {
    "sky_blue": ("#AEE2FF", "#173B53", "#86C8F2"),
    "sage_green": ("#8EC3B0", "#183D31", "#72AD98"),
    "violet": ("#B7A7F7", "#30285A", "#9D8BE1"),
    "ocean": ("#63C5DA", "#163E49", "#4FAEC4"),
    "amber": ("#F5C16C", "#50370E", "#DEA549"),
    "olive_gray": ("#A8A492", "#303029", "#918D7B"),
    "steel_blue": ("#3B7597", "#F5FAFC", "#5C92B1"),
}


def _hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    clean = hex_code.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(char * 2 for char in clean)
    if len(clean) != 6:
        return (196, 106, 147)
    try:
        return tuple(int(clean[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (196, 106, 147)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(channel))):02X}" for channel in rgb)


def _blend_rgb(color1: tuple[int, int, int], color2: tuple[int, int, int], ratio: float) -> str:
    return _rgb_to_hex(tuple(c1 + (c2 - c1) * ratio for c1, c2 in zip(color1, color2)))


def generate_theme_palette(accent_hex: str) -> tuple[dict[str, str], tuple[str, str, str]]:
    """Compute a complete coherent color replacement map and sidebar colors for any hex code."""
    accent = _hex_to_rgb(accent_hex)
    white = (255, 255, 255)
    black = (0, 0, 0)
    gray = (100, 100, 100)

    lum = (0.299 * accent[0] + 0.587 * accent[1] + 0.114 * accent[2]) / 255.0

    replacements = {
        "#fff7fa": _blend_rgb(accent, white, 0.96),
        "#c46a93": accent_hex,
        "#e38ab0": _blend_rgb(accent, white, 0.45),
        "#fff0f6": _blend_rgb(accent, white, 0.92),
        "#9b315f": _blend_rgb(accent, black, 0.50 if lum > 0.4 else 0.25),
        "#765565": _blend_rgb(accent, gray, 0.55),
        "#f0d4df": _blend_rgb(accent, white, 0.82),
        "#4b2434": _blend_rgb(accent, black, 0.70),
        "#8b6877": _blend_rgb(accent, gray, 0.45),
        "#a15b78": _blend_rgb(accent, black, 0.40),
        "#fffafd": _blend_rgb(accent, white, 0.98),
        "#f1d8e3": _blend_rgb(accent, white, 0.86),
        "#d798b5": _blend_rgb(accent, white, 0.35),
        "#ffe8f0": _blend_rgb(accent, white, 0.93),
        "#efc4d6": _blend_rgb(accent, white, 0.78),
        "#d878a2": _blend_rgb(accent, white, 0.25),
        "#70455a": _blend_rgb(accent, black, 0.60),
        "#ffe5ef": _blend_rgb(accent, white, 0.90),
        "#dfa0ba": _blend_rgb(accent, white, 0.50),
        "#aa527b": _blend_rgb(accent, black, 0.25),
    }

    sidebar_bg = accent_hex
    sidebar_text = "#FFFFFF" if lum < 0.65 else "#17202A"
    sidebar_active = _blend_rgb(accent, white, 0.35) if lum < 0.65 else _blend_rgb(accent, black, 0.25)
    sidebar = (sidebar_bg, sidebar_text, sidebar_active)

    return replacements, sidebar


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


def _accent_colors(theme_id: str, replacements: dict[str, str], sidebar: tuple[str, str, str]) -> set[str]:
    if theme_id == "rose":
        return {"#c46a93", "#e38ab0", "#d878a2", "#aa527b", "#dfa0ba", "#d798b5"}
    colors = set(replacements.values())
    colors.update(sidebar[::2])
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
QTableWidget, QTableWidget#CasesTable {{ background: #24272C; alternate-background-color: #202328; gridline-color: #41464E; border-color: #41464E; color: #F1F3F5; selection-background-color: {accent}; }}
QTableWidget::item:selected {{ background: {accent}; color: #101214; }}
QPushButton#PrimaryButton, QPushButton#CompactPrimaryButton {{ background: {accent}; color: #101214; }}
QPushButton#GhostButton, QPushButton#CompactGhostButton {{ background: #2B2F35; color: #F1F3F5; border-color: #454A52; }}
#CardHeader {{ background: {accent}; }}
#SettingsFooter {{ background: #202328; border-color: #34383E; }}
QPushButton#AppearanceModeTile {{ background: #25282D; color: #E9EDF1; border-color: #41464E; }}
QPushButton#AppearanceModeTile:hover {{ background: #2B2F35; border-color: {accent}; }}
QPushButton#AppearanceModeTile:checked {{ background: #30353B; border-color: {accent}; }}
QFrame#VisualThemeTile {{ background: #25282D; border-color: #41464E; }}
QFrame#VisualThemeTile:hover {{ border-color: {accent}; }}
QFrame#VisualThemeTile[selected=\"true\"] {{ border-color: {accent}; background: #2B2F35; }}
QLabel#VisualThemeLabel {{ color: #E9EDF1; }}
QFrame#LayoutTile {{ background: #25282D; border-color: #41464E; }}
QFrame#LayoutTile:hover {{ border-color: {accent}; }}
QFrame#LayoutTile[selected=\"true\"] {{ border-color: {accent}; background: #30353B; }}
QLabel#LayoutTileTitle {{ color: #F1F3F5; }}
QLabel#LayoutTileDesc {{ color: #A0AAB4; }}
QPushButton#ColorCategoryTab {{ border-color: #41464E; color: #B9C0C8; }}
QPushButton#ColorCategoryTab:hover {{ background: #2F343B; }}
QPushButton#ColorCategoryTab[active=\"true\"] {{ background: {accent}; color: #101214; border-color: {accent}; }}
QFrame#ColorChipCard {{ background: #24272C; border-color: #383D44; }}
QFrame#ColorChipCard:hover {{ border-color: {accent}; background: #2B2F35; }}
QFrame#ColorChipCard[selected=\"true\"] {{ border-color: {accent}; background: #322A30; }}
QLabel#ColorChipName {{ color: #F1F3F5; }}
QLabel#ColorChipHex {{ color: #94A3B8; }}
QPushButton#SettingsResetButton {{ background: #2D1F27; color: #F472B6; border-color: #5C2B42; }}
QPushButton#SettingsResetButton:hover {{ background: #3D2633; border-color: {accent}; }}
QPushButton#ViewModeBtn {{ background: #25282D; border-color: #41464E; color: #B9C0C8; }}
QPushButton#ViewModeBtn:hover {{ background: #30353B; color: #F1F3F5; }}
QPushButton#ViewModeBtn[active=\"true\"] {{ background: {accent}; color: #101214; border-color: {accent}; }}
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


def _layout_stylesheet(layout: str, accent: str, is_dark: bool, sidebar_bg: str | None = None) -> str:
    border_col = "#2E3440" if is_dark else "#E2E8F0"
    card_bg = "#24272C" if is_dark else "#FFFFFF"
    subtle_bg = "#1E2227" if is_dark else "#F8FAFC"
    text_primary = "#F1F5F9" if is_dark else "#0F172A"
    text_muted = "#94A3B8" if is_dark else "#64748B"

    if layout == "modern_studio":
        bar_bg = "#181A1F" if is_dark else "#F3F5F8"
        bar_text = "#D1D5DB" if is_dark else "#334155"
        return f"""
/* Modern Studio IDE Layout */
QFrame#GlobalTopbar {{
    background: {card_bg};
    border-bottom: 1px solid {border_col};
    min-height: 48px;
    max-height: 48px;
}}
QFrame#Sidebar {{
    background: {bar_bg};
    border-right: 1px solid {border_col};
}}
#AppEyebrow, #AppTitle, QLabel#SidebarFooter {{ color: {bar_text}; }}
QPushButton#NavButton {{
    color: {bar_text};
    border-radius: 6px;
    padding: 9px 12px;
    margin: 1px 6px;
}}
QPushButton#NavButton:hover {{
    background: rgba(125, 125, 125, 0.15);
}}
QPushButton#NavButton[active="true"] {{
    background: rgba(125, 125, 125, 0.22);
    border-left: 3px solid {accent};
    color: {text_primary};
    font-weight: 700;
}}
#Card {{
    border-radius: 10px;
    border: 1px solid {border_col};
}}
"""
    elif layout == "top_nav":
        nav_bg = "#181A1F" if is_dark else "#FFFFFF"
        nav_text = "#94A3B8" if is_dark else "#475569"
        brand_color = text_primary
        return f"""
/* Top Navigation Horizon Layout */
QFrame#TopNavBar {{
    background: {nav_bg};
    border-bottom: 1px solid {border_col};
    min-height: 52px;
    max-height: 52px;
}}
QLabel#TopNavBrand {{
    color: {brand_color};
    font-weight: 800;
    font-size: 15px;
}}
QPushButton#TopNavButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    color: {nav_text};
}}
QPushButton#TopNavButton:hover {{
    background: {subtle_bg};
    color: {text_primary};
}}
QPushButton#TopNavButton[active="true"] {{
    background: {accent};
    color: #FFFFFF;
}}
#Card {{
    border-radius: 12px;
    border: 1px solid {border_col};
}}
"""
    elif layout == "executive":
        return f"""
/* Executive KPI Dashboard Layout */
QFrame#KPICard {{
    background: {card_bg};
    border: 1px solid {border_col};
    border-radius: 10px;
    padding: 10px 14px;
}}
QFrame#KPICard:hover {{
    border-color: {accent};
}}
QLabel#KPIValue {{
    font-size: 22px;
    font-weight: 800;
    color: {accent};
}}
QLabel#KPILabel {{
    font-size: 11px;
    font-weight: 600;
    color: {text_muted};
    text-transform: uppercase;
}}
#Card {{
    border-radius: 10px;
    border: 1px solid {border_col};
}}
"""
    elif layout == "compact_legal":
        return f"""
/* Compact Legal 2-Column Layout */
QFrame#Sidebar {{
    min-width: 190px;
    max-width: 190px;
}}
QPushButton#NavButton {{
    padding: 7px 10px;
    font-size: 12px;
}}
QFrame#DetailPreviewPanel {{
    background: {card_bg};
    border-left: 1px solid {border_col};
    min-width: 320px;
    max-width: 380px;
}}
QFrame#DetailSectionBox {{
    background: {subtle_bg};
    border: 1px solid {border_col};
    border-radius: 5px;
    padding: 6px 10px;
}}
"""
    elif layout == "slim_sidebar":
        slim_bg = "#16181D" if is_dark else (sidebar_bg if sidebar_bg else accent)
        logo_bg = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(255, 255, 255, 0.25)"
        logo_border = "rgba(255, 255, 255, 0.18)" if is_dark else "rgba(255, 255, 255, 0.35)"
        btn_color = "#94A3B8" if is_dark else "rgba(255, 255, 255, 0.9)"
        btn_hover_bg = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(255, 255, 255, 0.22)"
        btn_hover_color = "#FFFFFF"
        btn_active_bg = accent if is_dark else "#FFFFFF"
        btn_active_color = "#FFFFFF" if is_dark else accent
        border_right_col = "#252932" if is_dark else "rgba(0, 0, 0, 0.08)"

        return f"""
/* Slim Icon Bar Layout */
QFrame#SlimSidebar {{
    background: {slim_bg};
    border-right: 1px solid {border_right_col};
    min-width: 64px;
    max-width: 64px;
}}
QLabel#SlimSidebarLogo {{
    background: {logo_bg};
    color: #FFFFFF;
    font-size: 20px;
    font-weight: 900;
    border-radius: 12px;
    border: 1px solid {logo_border};
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
}}
QPushButton#SlimNavButton {{
    background: transparent;
    border: none;
    border-radius: 10px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    font-size: 19px;
    color: {btn_color};
    padding: 0px;
    margin: 2px 0px;
}}
QPushButton#SlimNavButton:hover {{
    background: {btn_hover_bg};
    color: {btn_hover_color};
}}
QPushButton#SlimNavButton[active="true"] {{
    background: {btn_active_bg};
    color: {btn_active_color};
    font-weight: bold;
}}
#Card {{
    border-radius: 10px;
    border: 1px solid {border_col};
}}
"""
    elif layout == "centered_focus":
        return f"""
/* Centered Focus Canvas Layout */
QFrame#CenteredContainer {{
    max-width: 1180px;
}}
QFrame#FloatingActionToolbar {{
    background: {card_bg};
    border: 1px solid {border_col};
    border-radius: 12px;
    padding: 6px 12px;
}}
#Card {{
    border-radius: 12px;
    border: 1px solid {border_col};
}}
#CardHeader {{
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
"""
    elif layout == "vibrant":
        return f"""
/* Vibrant Dashboard Layout */
#Card {{
    border-radius: 18px;
    border: 1px solid rgba(0, 0, 0, 0.08);
}}
#CardHeader {{
    border-top-left-radius: 18px;
    border-top-right-radius: 18px;
}}
QLabel#StatusBadge, QLabel#WarningBadge {{
    border-radius: 12px;
    padding: 3px 10px;
    font-weight: 800;
}}
QPushButton#PrimaryButton, QPushButton#GhostButton {{
    border-radius: 14px;
    padding: 8px 16px;
}}
#SummaryCard, #DocumentsPanel, #SettingsCard {{
    border-radius: 18px;
}}
"""
    return ""


def _font_scale_stylesheet(font_size: str) -> str:
    cfg = FONT_SIZE_OPTIONS.get(font_size, FONT_SIZE_OPTIONS["medium"])
    base = cfg["size"]
    scale = cfg["scale"]
    p_title = round(25 * scale)
    sec_title = round(16 * scale)
    app_title = round(20 * scale)
    return f"""
* {{ font-size: {base}; }}
#PageTitle {{ font-size: {p_title}px; }}
#SectionTitle, #SettingsSectionTitle {{ font-size: {sec_title}px; }}
#AppTitle {{ font-size: {app_title}px; }}
"""


def _border_radius_stylesheet(border_radius: str) -> str:
    rad = BORDER_RADIUS_OPTIONS.get(border_radius, BORDER_RADIUS_OPTIONS["rounded"])["radius"]
    return f"""
#Card, #SummaryCard, #DocumentsPanel, #SettingsCard {{
    border-radius: {rad};
}}
#CardHeader {{
    border-top-left-radius: {rad};
    border-top-right-radius: {rad};
}}
"""


def _high_contrast_stylesheet(is_dark: bool, accent: str) -> str:
    border_color = "#FFFFFF" if is_dark else "#0F172A"
    return f"""
/* High Contrast Mode */
#Card, #SummaryCard, #DocumentsPanel, #SettingsCard, QLineEdit, QComboBox, QTextEdit, QTableWidget {{
    border: 2px solid {border_color} !important;
}}
QPushButton#PrimaryButton {{
    border: 2px solid {border_color} !important;
    font-weight: 800 !important;
}}
QPushButton#GhostButton {{
    border: 2px solid {border_color} !important;
    font-weight: 700 !important;
}}
QLabel {{
    font-weight: 600;
}}
"""


@lru_cache(maxsize=128)
def stylesheet_for_theme(
    theme_id: str | None,
    strength: int | str | None = 100,
    appearance_mode: str | None = "light",
    system_is_dark: bool = False,
    layout: str | None = "default",
    font_size: str | None = "medium",
    border_radius: str | None = "rounded",
    high_contrast: bool | str = False,
    custom_color: str | None = None,
) -> str:
    """Return the stylesheet for a persisted color palette, appearance mode, and layout."""
    is_custom = theme_id == "custom" and custom_color
    if is_custom and custom_color:
        replacements, sidebar = generate_theme_palette(custom_color)
        selected_theme = "custom"
        raw_accent = custom_color
    elif theme_id == "rose" or (theme_id not in _THEME_REPLACEMENTS and theme_id not in THEME_OPTIONS):
        selected_theme = "rose"
        replacements = {}
        sidebar = ("#c46a93", "#FFFFFF", "#e38ab0")
        raw_accent = "#c46a93"
    elif theme_id in _THEME_REPLACEMENTS:
        replacements = _THEME_REPLACEMENTS[theme_id]
        sidebar = _THEME_SIDEBAR.get(theme_id, (THEME_OPTIONS[theme_id]["color"], "#FFFFFF", THEME_OPTIONS[theme_id]["color"]))
        selected_theme = theme_id
        raw_accent = THEME_OPTIONS[theme_id]["color"]
    elif theme_id in THEME_OPTIONS:
        replacements, sidebar = generate_theme_palette(THEME_OPTIONS[theme_id]["color"])
        selected_theme = theme_id
        raw_accent = THEME_OPTIONS[theme_id]["color"]
    else:
        selected_theme = "rose"
        replacements = {}
        sidebar = ("#c46a93", "#FFFFFF", "#e38ab0")
        raw_accent = "#c46a93"

    normalized_strength = _theme_strength(strength)
    stylesheet = APP_STYLESHEET + SETTINGS_STYLESHEET

    for source, target in replacements.items():
        stylesheet = stylesheet.replace(source, target)

    if selected_theme != "rose" and sidebar:
        sidebar_bg, text, active = sidebar
        stylesheet += f"""
QFrame#Sidebar {{ background: {sidebar_bg}; }}
#AppEyebrow, #AppTitle {{ color: {text}; }}
QPushButton#NavButton {{ color: {text}; }}
QPushButton#NavButton:hover {{ background: rgba(255, 255, 255, 0.34); }}
QPushButton#NavButton[active=\"true\"] {{ background: {active}; border-color: rgba(23, 59, 53, 0.14); }}
QLabel#SidebarFooter {{ color: {text}; }}
"""

    accent_set = _accent_colors(selected_theme, replacements, sidebar)
    for color in accent_set:
        stylesheet = stylesheet.replace(color, _adjust_color(color, normalized_strength))

    theme_accent = _adjust_color(replacements.get("#c46a93", raw_accent), normalized_strength)
    card_text = _adjust_color(replacements.get("#9b315f", "#9b315f"), normalized_strength)
    stylesheet += f"""
#CardHeader {{ background: {theme_accent}; }}
QLabel#StatusBadge {{ background: rgba(255, 255, 255, 0.88); color: {card_text}; }}
"""

    is_dark = resolved_appearance_mode(appearance_mode, system_is_dark) == "dark"
    if is_dark:
        stylesheet += _dark_stylesheet(theme_accent)

    # Layout specific overrides
    normalized_layout = layout or "default"
    current_sidebar_bg = "#181A1F" if is_dark else (sidebar[0] if sidebar else theme_accent)
    layout_css = _layout_stylesheet(normalized_layout, theme_accent, is_dark, current_sidebar_bg)
    if layout_css:
        stylesheet += layout_css

    # Font sizing
    if font_size:
        stylesheet += _font_scale_stylesheet(font_size)

    # Border radius
    if border_radius and border_radius != "rounded":
        stylesheet += _border_radius_stylesheet(border_radius)

    # High contrast
    is_high_contrast = str(high_contrast).lower() in ("true", "1")
    if is_high_contrast:
        stylesheet += _high_contrast_stylesheet(is_dark, theme_accent)

    return stylesheet
