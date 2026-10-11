from chameleon.core.config import asset_dir

STYLE = """
QWidget { background:#091319; color:#dae3ed; font-family:'Segoe UI'; font-size:13px; }
QMainWindow, QDialog { background:#091319; }
QLabel { background:transparent; }
QLabel#eyebrow { color:#72dfb4; font-size:10px; font-weight:700; letter-spacing:2px; }
QLabel#heading { font-size:34px; font-weight:600; color:#f0f6fc; }
QLabel#muted { color:#89a5a4; }
QLabel#path { color:#a8b7c9; font-family:'Cascadia Mono','Consolas'; font-size:11px; }
QFrame#heroCard { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #173c3b,stop:0.55 #123037,stop:1 #10212b); border:1px solid #2c5351; border-radius:22px; }
QFrame#summaryCard { background:#10252b; border:1px solid #294347; border-radius:14px; }
QFrame#insightPanel { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #132d32,stop:1 #0d1e26); border:1px solid #29484c; border-radius:16px; }
QFrame#divider { background:#29464a; border:none; }
QLabel#setupStep { color:#abcac3; font-weight:600; font-size:13px; margin-top:10px; }
QFrame#card { background:#102128; border:1px solid #274044; border-radius:14px; }
QFrame#terminalFrame { background:#091319; border:1px solid #29464a; border-radius:12px; }
QFrame#workspaceBar { background:#0d1f27; border-bottom:1px solid #274044; }
QLabel#badge { background:#152a27; color:#78e7bc; border:1px solid #264c40; border-radius:10px; padding:5px 10px; font-size:11px; }
QPushButton, QToolButton { background:#172d34; border:1px solid #314258; border-radius:8px; padding:9px 16px; font-weight:600; }
QPushButton:hover, QToolButton:hover { background:#25364a; border-color:#637d99; }
QPushButton:pressed, QToolButton:pressed { background:#101a28; }
QPushButton:focus, QToolButton:focus { border:1px solid #78e7bc; }
QPushButton:disabled { color:#637186; background:#131c27; border-color:#233044; }
QLineEdit, QSpinBox, QComboBox, QTextEdit { background:#0c1420; border:1px solid #2c3b50; border-radius:8px; padding:8px; selection-background-color:#255c4b; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus { border-color:#70d8b0; }
QComboBox::drop-down { border:none; width:24px; }
QComboBox QAbstractItemView { background:#182435; border:1px solid #3b5069; padding:6px; selection-background-color:#284939; }
QCheckBox { background:transparent; spacing:10px; padding:5px 0; }
QCheckBox::indicator { width:17px; height:17px; border-radius:5px; border:1px solid #4a6079; background:#0c1420; }
QCheckBox::indicator:checked { background:#69d6ac; border-color:#8ceac7; image:none; }
QCheckBox::indicator:checked:hover { background:#93ebcb; }
QTabWidget::pane { border:1px solid #27384e; border-radius:10px; padding:16px; background:#111a27; }
QTabBar::tab { background:#091319; color:#92a4b9; padding:12px 17px; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#81e3bc; border-bottom:2px solid #81e3bc; }
QProgressBar { background:#1b293a; border:none; border-radius:3px; height:6px; max-height:6px; color:transparent; }
QProgressBar::chunk { background:#73dfb5; border-radius:3px; }
QScrollBar:vertical { background:transparent; width:8px; margin:4px; }
QScrollBar::handle:vertical { background:#33475e; border-radius:3px; min-height:24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QMenu { background:#142031; border:1px solid #344861; border-radius:8px; padding:6px; }
QMenu::item { padding:9px 22px; border-radius:5px; }
QMenu::item:selected { background:#244a3e; }
QToolTip { background:#182537; color:#e1edf8; border:1px solid #405771; padding:6px; }
QMessageBox { background:#0d1f27; }
QDialogButtonBox { background:transparent; }
"""

STYLE += 'QCheckBox::indicator:checked { image:url("' + (asset_dir() / "icons/check.png").as_posix() + '"); }'
