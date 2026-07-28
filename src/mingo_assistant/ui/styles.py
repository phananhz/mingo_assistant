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
