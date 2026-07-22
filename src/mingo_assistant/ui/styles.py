APP_STYLESHEET = """
* {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #3d2430;
}

QMainWindow {
    background: #fff5f8;
}

#Sidebar {
    background: #b84f78;
}

#AppEyebrow {
    color: #ffe3ec;
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
    color: #effaf2;
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 11px 12px;
    font-weight: 600;
}

QPushButton#NavButton:hover {
    background: rgba(255, 255, 255, 0.10);
}

QPushButton#NavButton[active="true"] {
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.20);
}

#Content {
    background: #fff5f8;
}

#PageTitle {
    color: #8f3158;
    font-size: 25px;
    font-weight: 800;
}

#PageDescription {
    color: #80606c;
    font-size: 13px;
}

#FilterLabel {
    color: #7a5061;
    font-size: 10px;
    font-weight: 800;
}

QLineEdit,
QComboBox,
QTextEdit {
    background: #ffffff;
    border: 1px solid #f0c8d6;
    border-radius: 5px;
    padding: 9px 10px;
    min-height: 20px;
}

QLineEdit:focus,
QComboBox:focus,
QTextEdit:focus {
    border: 1px solid #c75f8a;
}

QGroupBox {
    background: #ffffff;
    border: 1px solid #f0d5df;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 800;
    color: #8f3158;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

#ResultText {
    color: #8f3158;
    font-size: 15px;
    font-weight: 700;
}

#Card {
    background: #ffffff;
    border: 1px solid #f0d5df;
    border-radius: 8px;
}

#CardHeader {
    background: #c75f8a;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

#CardTitle {
    color: #4b2434;
    font-size: 17px;
    font-weight: 800;
}

#CardSubtitle {
    color: #7b4059;
    font-size: 11px;
    font-weight: 800;
}

#MetaText {
    color: #80606c;
    font-size: 12px;
}

#TableHeader {
    background: #fff0f5;
    border: 1px solid #f0c8d6;
    color: #8f3158;
    font-size: 12px;
    font-weight: 800;
    padding: 8px;
}

#TableCell {
    background: #ffffff;
    border: 1px solid #f0c8d6;
}

#StatusBadge {
    background: #ffe1eb;
    color: #9a315d;
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
    background: #b84f78;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 9px 12px;
    font-weight: 800;
}

QPushButton#PrimaryButton:hover {
    background: #9f4166;
}

QPushButton#GhostButton {
    background: #fff5f8;
    color: #8f3158;
    border: 1px solid #edc6d4;
    border-radius: 6px;
    padding: 8px 11px;
    font-weight: 700;
}

#CreateCard {
    background: #ffffff;
    border: 1px dashed #dc91ad;
    border-radius: 8px;
}

#CreateIcon {
    color: #b84f78;
    font-size: 38px;
    font-weight: 300;
}

#CreateTitle {
    color: #8f3158;
    font-size: 17px;
    font-weight: 800;
}

#CreateDescription,
#EmptyDescription {
    color: #80606c;
    font-size: 13px;
}

#ComingSoonTitle {
    color: #8f3158;
    font-size: 24px;
    font-weight: 800;
}
"""
