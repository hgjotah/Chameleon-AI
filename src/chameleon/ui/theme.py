from chameleon.core.config import asset_dir

STYLE = """
QWidget { background:transparent; color:#dce8de; font-family:'Segoe UI'; font-size:13px; }
QMainWindow, QDialog { background:#0b110d; }
QLabel { background:transparent; }
QLabel#eyebrow { color:#8eaf91; font-size:10px; font-weight:700; letter-spacing:2px; }
QLabel#heading { font-size:31px; font-weight:600; color:#f0f5ec; }
QLabel#muted { color:#9aaf9d; }
QLabel#path { color:#90a294; font-family:'Cascadia Mono','Consolas'; font-size:11px; }
QFrame#heroCard { background:rgba(21,38,26,120); border:1px solid #293d2c; border-radius:24px; }
QFrame#card, QFrame#summaryCard { background:rgba(19,31,23,190); border:1px solid #2c3e30; border-radius:16px; }
QFrame#terminalFrame { background:#0b100d; border:1px solid #2b3a2e; border-radius:16px; }
QFrame#insightPanel { background:#111c15; border:1px solid #2a3d2f; border-radius:16px; }
QFrame#divider { background:#29382d; border:none; }
QLabel#setupStep { color:#b5c8b4; font-weight:600; font-size:13px; margin-top:10px; }
QFrame#workspaceBar { background:transparent; border-bottom:1px solid rgba(174,202,156,24); border-top-left-radius:20px; border-top-right-radius:20px; }
QLabel#badge { background:#1c2c20; color:#b6d8a1; border:1px solid #354f37; border-radius:10px; padding:5px 10px; font-size:11px; }
QPushButton, QToolButton { background:#1b2b20; border:1px solid rgba(158,190,150,35); border-radius:12px; padding:10px 17px; font-weight:600; }
QPushButton:hover, QToolButton:hover { background:#293f2e; border-color:#70956c; }
QPushButton:pressed, QToolButton:pressed { background:#142218; }
QPushButton:focus, QToolButton:focus { border:1px solid #b6d8a1; }
QPushButton:disabled { color:#657c69; background:#152019; border-color:#29372c; }
QLineEdit, QSpinBox, QComboBox, QTextEdit { background:#0f1b13; border:1px solid rgba(158,190,150,40); border-radius:11px; padding:9px; selection-background-color:#405d40; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus { border-color:#aacd90; }
QComboBox::drop-down { border:none; width:24px; }
QComboBox QAbstractItemView { background:#17261c; border:1px solid #516c51; padding:8px; selection-background-color:#324c34; }
QCheckBox { background:transparent; spacing:10px; padding:5px 0; }
QCheckBox::indicator { width:17px; height:17px; border-radius:5px; border:1px solid #536e54; background:#0d1710; }
QCheckBox::indicator:checked { background:#b7d69f; border-color:#c4deb0; image:none; }
QCheckBox::indicator:checked:hover { background:#cce6b8; }
QTabWidget::pane { border:1px solid #304633; border-radius:10px; padding:16px; background:#132017; }
QTabBar::tab { background:#0c160f; color:#92a896; padding:12px 17px; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#c0d8ab; border-bottom:2px solid #c0d8ab; }
QProgressBar { background:#223427; border:none; border-radius:3px; height:6px; max-height:6px; color:transparent; }
QProgressBar::chunk { background:#abc989; border-radius:3px; }
QScrollBar:vertical { background:transparent; width:8px; margin:4px; }
QScrollBar::handle:vertical { background:#3b5140; border-radius:3px; min-height:24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QMenu { background:#15231a; border:1px solid #39533c; border-radius:8px; padding:6px; }
QMenu::item { padding:9px 22px; border-radius:5px; }
QMenu::item:selected { background:#304c32; }
QToolTip { background:#203424; color:#ecf4e6; border:1px solid #5d7e57; padding:6px; }
QMessageBox { background:#142218; }
QDialogButtonBox { background:transparent; }
"""

STYLE += (
    'QCheckBox::indicator:checked { image:url("'
    + (asset_dir() / "icons/check.png").as_posix()
    + '"); }'
)
