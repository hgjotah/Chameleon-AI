STYLE = """
QWidget { background:#0b1017; color:#dae3ed; font-family:'Segoe UI'; font-size:13px; }
QMainWindow, QDialog { background:#0b1017; }
QLabel { background:transparent; }
QLabel#eyebrow { color:#72dfb4; font-size:10px; font-weight:700; letter-spacing:2px; }
QLabel#heading { font-size:30px; font-weight:600; color:#f0f6fc; }
QLabel#muted { color:#8493a7; }
QLabel#path { color:#a8b7c9; font-family:'Cascadia Mono','Consolas'; font-size:11px; }
QFrame#card { background:#121a25; border:1px solid #243143; border-radius:14px; }
QFrame#terminalFrame { background:#0b1017; border:1px solid #273444; border-radius:12px; }
QFrame#workspaceBar { background:#101823; border-bottom:1px solid #243143; }
QLabel#badge { background:#152a27; color:#78e7bc; border:1px solid #264c40; border-radius:10px; padding:5px 10px; font-size:11px; }
QPushButton, QToolButton { background:#192434; border:1px solid #314258; border-radius:8px; padding:9px 16px; font-weight:600; }
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
QTabBar::tab { background:#0b1017; color:#92a4b9; padding:12px 17px; border-bottom:2px solid transparent; }
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
QMessageBox { background:#101823; }
QDialogButtonBox { background:transparent; }
"""
