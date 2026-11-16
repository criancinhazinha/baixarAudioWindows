from __future__ import annotations

DARK_STUDIO_QSS = """
QMainWindow, QDialog {
    background-color: #0F1218;
    color: #E6EDF3;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #E6EDF3;
    font-family: "Segoe UI", "Inter", sans-serif;
}

QFrame#Card, QGroupBox {
    background-color: #161B23;
    border: 1px solid #262E3B;
    border-radius: 10px;
}

QGroupBox {
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
    color: #C9D1D9;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #7DD3FC;
}

QFrame#BannerWarning {
    background-color: #2A1F0D;
    border: 1px solid #B45309;
    border-radius: 8px;
}

QFrame#BannerInfo {
    background-color: #0E2233;
    border: 1px solid #0284C7;
    border-radius: 8px;
}

QLabel#MutedLabel {
    color: #8B949E;
    font-size: 12px;
}

QLabel#TitleLabel {
    font-size: 16px;
    font-weight: 700;
    color: #F0F6FC;
}

QLabel#BadgeMaster {
    background-color: #064E3B;
    color: #6EE7B7;
    border: 1px solid #10B981;
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#BadgeStandard {
    background-color: #21262D;
    color: #9CA3AF;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#BadgePremium {
    background-color: #3B2809;
    color: #FCD34D;
    border: 1px solid #F59E0B;
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #0D1117;
    border: 1px solid #30363D;
    border-radius: 7px;
    padding: 7px 10px;
    color: #F0F6FC;
    selection-background-color: #0284C7;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38BDF8;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #161B23;
    border: 1px solid #30363D;
    selection-background-color: #0EA5E9;
    color: #F0F6FC;
}

QPushButton {
    background-color: #21262D;
    border: 1px solid #30363D;
    border-radius: 7px;
    padding: 7px 14px;
    color: #E6EDF3;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2B313B;
    border-color: #484F58;
}

QPushButton:pressed {
    background-color: #1C2026;
}

QPushButton:disabled {
    background-color: #161A20;
    color: #57606A;
    border-color: #21262D;
}

QPushButton#PrimaryButton {
    background-color: #0284C7;
    border: 1px solid #0EA5E9;
    color: #FFFFFF;
}

QPushButton#PrimaryButton:hover {
    background-color: #0EA5E9;
}

QPushButton#PrimaryButton:disabled {
    background-color: #12364A;
    border-color: #1A4B66;
    color: #7D9AAA;
}

QPushButton#MasterButton {
    background-color: #065F46;
    border: 1px solid #10B981;
    color: #ECFDF5;
}

QPushButton#MasterButton:hover {
    background-color: #047857;
}

QPushButton#DangerButton {
    background-color: #451A1D;
    border: 1px solid #991B1B;
    color: #FCA5A5;
}

QPushButton#DangerButton:hover {
    background-color: #7F1D1D;
}

QTableWidget, QListWidget {
    background-color: #0D1117;
    border: 1px solid #262E3B;
    border-radius: 8px;
    gridline-color: #1F2630;
    alternate-background-color: #121720;
    selection-background-color: #0C4A6E;
    selection-color: #F0F6FC;
}

QHeaderView::section {
    background-color: #161B23;
    color: #9CA3AF;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #262E3B;
    font-weight: 600;
    font-size: 12px;
}

QProgressBar {
    background-color: #0D1117;
    border: 1px solid #262E3B;
    border-radius: 5px;
    text-align: center;
    color: #E6EDF3;
    font-size: 11px;
    min-height: 14px;
}

QProgressBar::chunk {
    background-color: #0EA5E9;
    border-radius: 4px;
}

QPlainTextEdit#LogView {
    background-color: #0A0D12;
    border: 1px solid #262E3B;
    border-radius: 7px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    color: #A5D6FF;
}

QScrollBar:vertical {
    background: #0F1218;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #30363D;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #484F58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
