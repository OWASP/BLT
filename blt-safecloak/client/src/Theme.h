#pragma once

// BLT-SafeCloak dark theme, mirroring the web app palette in
// public/css/main.css (html.dark):
//   primary  #ff4444 (hover #ff6b6b)   bg #0f172a / surface #1f2937
//   hover    #2d3748                    border #374151
//   text     #f1f5f9 / #d1d5db / #9ca3af
namespace Theme {

inline const char *kPrimary = "#ff4444";
inline const char *kTextTertiary = "#9ca3af";

// Sender name colors, hashed per user.
inline const char *kSenderPalette[] = {"#ff6b6b", "#fbbf24", "#34d399",
                                       "#60a5fa", "#c084fc", "#f472b6",
                                       "#2dd4bf", "#fb923c"};
inline constexpr int kSenderPaletteSize = 8;

inline const char *kStyleSheet = R"(
* { outline: none; }
QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: 'Inter', 'Segoe UI', 'Cantarell', sans-serif;
    font-size: 14px;
}
QToolTip {
    background-color: #1f2937; color: #f1f5f9;
    border: 1px solid #374151; padding: 4px;
}

/* --- Setup page --- */
#setupCard {
    background-color: #1f2937;
    border: 1px solid #374151;
    border-radius: 12px;
}
#appTitle { font-size: 26px; font-weight: 800; background: transparent; }
#appTitleAccent { color: #ff4444; }
#appSubtitle { color: #9ca3af; background: transparent; }
#setupCard QLabel { background: transparent; }
QRadioButton { background: transparent; spacing: 8px; padding: 4px 0; }
QRadioButton::indicator {
    width: 16px; height: 16px; border-radius: 9px;
    border: 2px solid #4b5563; background: #111827;
}
QRadioButton::indicator:checked { border-color: #ff4444; background: #ff4444; }
#modeHint { color: #9ca3af; font-size: 12px; padding-left: 26px; background: transparent; }

QLineEdit, QSpinBox {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #7f1d1d;
}
QLineEdit:focus, QSpinBox:focus { border-color: #ff4444; }
QLineEdit:disabled, QSpinBox:disabled { color: #6b7280; border-color: #1f2937; }
QSpinBox::up-button, QSpinBox::down-button { width: 0; }

QPushButton {
    background-color: #2d3748;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover { background-color: #374151; }
QPushButton:pressed { background-color: #1f2937; }
QPushButton#primaryButton {
    background-color: #e10101; border: none; color: #fef2f2;
}
QPushButton#primaryButton:hover { background-color: #ff4444; }
QPushButton#primaryButton:pressed { background-color: #b91c1c; }
QPushButton#ghostButton {
    background: transparent; border: none; color: #9ca3af;
    font-weight: 500; padding: 4px 8px; text-align: left;
}
QPushButton#ghostButton:hover { color: #f1f5f9; }

/* --- Sidebar --- */
#sidebar { background-color: #111827; border-right: 1px solid #374151; }
#sidebar QLabel { background: transparent; }
#workspaceName {
    font-size: 17px; font-weight: 800; padding: 2px 0;
}
#statusLine { color: #9ca3af; font-size: 11px; }
#versionLabel { color: #6b7280; font-size: 11px; background: transparent; }
#sectionLabel {
    color: #9ca3af; font-size: 11px; font-weight: 700;
    letter-spacing: 1px; padding-top: 8px;
}
#sidebar QListWidget {
    background: transparent; border: none; padding: 0;
}
#sidebar QListWidget::item {
    color: #d1d5db; border-radius: 6px; padding: 5px 8px; margin: 1px 0;
}
#sidebar QListWidget::item:hover { background-color: #2d3748; }
#sidebar QListWidget::item:selected {
    background-color: #e10101; color: #fef2f2;
}

/* --- Chat area --- */
#chatHeader {
    background-color: #0f172a;
    border-bottom: 1px solid #374151;
}
#chatHeader QLabel { background: transparent; }
#channelTitle { font-size: 16px; font-weight: 700; }
#encryptionLabel { color: #9ca3af; font-size: 12px; }
#firewallBanner {
    background-color: #3d2419;
    border-bottom: 1px solid #7f1d1d;
}
#firewallBannerLabel {
    color: #fecaca; font-size: 13px; background: transparent;
}
#messageView, #messageContainer {
    background-color: #0f172a; border: none;
}
#typingLabel {
    background-color: #0f172a; color: #9ca3af; font-size: 12px;
    padding: 0 18px;
}
#messageRow:hover { background-color: #131c2e; }
#messageText { color: #f1f5f9; }
#fileChip {
    background-color: #1f2937; border: 1px solid #374151; border-radius: 8px;
}
#reactionChip {
    background-color: #1f2937; border: 1px solid #374151; border-radius: 11px;
    padding: 1px 8px; font-size: 12px; color: #f1f5f9;
}
#reactionChip:hover { border-color: #ff4444; }
#reactionAdd {
    background: transparent; border: none; color: #6b7280;
    font-size: 13px; padding: 1px 4px;
}
#reactionAdd:hover { color: #f1f5f9; }
#messageAction {
    background: transparent; border: 1px solid #374151; border-radius: 6px;
    color: #9ca3af; font-size: 11px; padding: 2px 7px;
}
#messageAction:hover { color: #f1f5f9; border-color: #ff4444; }
#iconButton {
    background: transparent; border: none; font-size: 18px; padding: 2px 6px;
}
#iconButton:hover { background-color: #2d3748; border-radius: 6px; }
/* Settings */
#settingsTitle { font-size: 20px; font-weight: 800; }
#avatarPreview {
    background-color: #111827; border: 1px solid #374151; border-radius: 14px;
    color: #6b7280; font-size: 11px;
}
#networkLog {
    background-color: #0b1220; border: 1px solid #374151; border-radius: 8px;
    color: #9ca3af; font-family: monospace; font-size: 12px;
}
#composerBar { background-color: #0f172a; border-top: 1px solid #374151; }
#messageInput {
    background-color: #1f2937; border: 1px solid #374151;
    border-radius: 10px; padding: 10px 12px; font-size: 14px;
}
#messageInput:focus { border-color: #ff4444; }

QScrollBar:vertical {
    background: transparent; width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #374151; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #4b5563; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QMessageBox, QInputDialog { background-color: #1f2937; }
)";

} // namespace Theme
