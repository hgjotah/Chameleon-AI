import os
import shutil
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chameleon.core.config import Config, data_dir, save_config
from chameleon.ui.widgets import BrandMark, MotionButton


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config.model_copy(deep=True)
        self.setWindowTitle("Chameleon · Ajustes")
        self.resize(850, 630)
        self.setMinimumSize(760, 570)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(20)
        header = QHBoxLayout()
        header.addWidget(BrandMark())
        heading = QLabel("Hazlo tuyo.")
        heading.setObjectName("heading")
        header.addWidget(heading)
        header.addStretch()
        badge = QLabel("AJUSTES LOCALES")
        badge.setObjectName("badge")
        header.addWidget(badge)
        layout.addLayout(header)
        content = QHBoxLayout()
        content.setSpacing(22)
        navigation = QListWidget()
        navigation.setFixedWidth(158)
        navigation.setStyleSheet("QListWidget{background:#101925;border:1px solid #293a50;border-radius:12px;padding:8px} QListWidget::item{padding:14px 9px;border-radius:7px;color:#9db1c8} QListWidget::item:selected{background:#244639;color:#a0f0ce} QListWidget::item:hover{background:#1b2c3e}")
        tabs = QStackedWidget()
        content.addWidget(navigation)
        content.addWidget(tabs, 1)
        layout.addLayout(content, 1)
        fade = QGraphicsOpacityEffect(tabs)
        tabs.setGraphicsEffect(fade)
        self.page_animation = QPropertyAnimation(fade, b"opacity", self)
        self.page_animation.setDuration(180)
        self.page_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        def select_page(index: int) -> None:
            tabs.setCurrentIndex(index)
            self.page_animation.stop()
            self.page_animation.setStartValue(0.45)
            self.page_animation.setEndValue(1.0)
            self.page_animation.start()
        navigation.currentRowChanged.connect(select_page)
        self.fields: dict[tuple[str, str], QLineEdit | QComboBox | QSpinBox | QCheckBox] = {}

        def page(name: str) -> QFormLayout:
            widget = QWidget()
            form = QFormLayout(widget)
            form.setContentsMargins(8, 12, 8, 12)
            form.setVerticalSpacing(18)
            form.setHorizontalSpacing(20)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            tabs.addWidget(widget)
            navigation.addItem(name)
            return form

        def field(
            form: QFormLayout,
            section: str,
            name: str,
            label: str,
            choices: list[str] | None = None,
            bounds: tuple[int, int] | None = None,
        ) -> None:
            value = getattr(getattr(self.config, section), name)
            widget: QLineEdit | QComboBox | QSpinBox | QCheckBox
            if choices:
                widget = QComboBox()
                widget.addItems(choices)
                widget.setCurrentText(str(value))
            elif isinstance(value, bool):
                widget = QCheckBox()
                widget.setChecked(value)
            elif isinstance(value, int):
                widget = QSpinBox()
                widget.setRange(*(bounds or (0, 100000)))
                widget.setValue(value)
            else:
                widget = QLineEdit(str(value))
            self.fields[section, name] = widget
            form.addRow(label, widget)

        general = page("General")
        field(
            general, "terminal", "shell", "Shell (nuevas sesiones)", ["cmd", "powershell", "pwsh"]
        )
        field(general, "terminal", "start_directory", "Directorio inicial")
        field(general, "general", "language", "Idioma", ["es", "en"])
        field(general, "general", "startup_checks", "Comprobar al iniciar")
        ai = page("IA local")
        ai.addRow("Proveedor", QLabel("Ollama · exclusivamente local"))
        field(ai, "ai", "model", "Modelo")
        field(ai, "ai", "keep_alive", "Mantener cargado (ej. 5m, 0)")
        field(ai, "ai", "timeout", "Timeout (segundos)", bounds=(5, 600))
        field(ai, "ai", "num_threads", "Hilos de CPU para Qwen", bounds=(1, 64))
        field(ai, "ai", "enabled", "Activar IA")
        field(ai, "ai", "prefer_model", "Usar Qwen incluso para acciones simples")
        terminal = page("Terminal")
        field(terminal, "terminal", "font", "Fuente")
        field(terminal, "terminal", "font_size", "Tamaño", bounds=(8, 40))
        field(terminal, "terminal", "cursor_style", "Cursor", ["block", "bar", "underline"])
        field(terminal, "terminal", "cursor_blink", "Parpadeo")
        field(terminal, "terminal", "scrollback", "Scrollback", bounds=(100, 100000))
        field(terminal, "ai", "show_generated_commands", "Mostrar comandos generados")
        safety = page("Seguridad")
        safety.addRow(
            QLabel(
                "Confirmaciones obligatorias para cambios.\nLas acciones BLOCKED siempre permanecen bloqueadas."
            )
        )
        field(safety, "safety", "strict_mode", "Confirmar también consultas AI")
        privacy = page("Privacidad")
        field(privacy, "privacy", "save_ai_history", "Guardar historial de IA")
        privacy.addRow(QLabel("Redacción básica de secretos; no garantiza detectar todos."))
        clear = MotionButton("Borrar historial local y sesiones")
        clear.clicked.connect(self.clear_history)
        privacy.addRow(clear)
        open_folder = MotionButton("Abrir carpeta de datos")
        open_folder.clicked.connect(self.open_data_folder)
        privacy.addRow(open_folder)
        footer = QHBoxLayout()
        note = QLabel("Los cambios de shell se aplican a nuevas sesiones.")
        note.setObjectName("muted")
        note.setStyleSheet("color:#8b9fb7;font-size:11px")
        footer.addWidget(note, 1)
        cancel = MotionButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = MotionButton("Guardar cambios", primary=True)
        save.clicked.connect(self.save)
        save.setDefault(True)
        footer.addWidget(cancel)
        footer.addWidget(save)
        layout.addLayout(footer)
        navigation.setCurrentRow(0)

    def open_data_folder(self) -> None:
        try:
            data_dir().mkdir(parents=True, exist_ok=True)
            os.startfile(data_dir())
        except OSError as exc:
            QMessageBox.warning(self, "Carpeta de datos", str(exc))

    def clear_history(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Privacidad",
                "¿Borrar historial y contexto local?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            for path in (data_dir() / "history", data_dir() / "runtime" / "sessions"):
                if path.exists():
                    shutil.rmtree(path)

    def save(self) -> None:
        try:
            values = self.config.model_dump()
            for (section, name), widget in self.fields.items():
                if isinstance(widget, QCheckBox):
                    value: object = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                else:
                    value = widget.text()
                values[section][name] = value
            self.config = Config.model_validate(values)
            folder = self.config.terminal.start_directory
            if folder and not Path(folder).expanduser().is_dir():
                raise ValueError("El directorio inicial debe ser una carpeta existente. Déjalo vacío para usar tu carpeta de usuario.")
            from chameleon.platform.windows.system import shell_executable

            shell_executable(self.config.terminal.shell)
            save_config(self.config)
            self.accept()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Configuración inválida", str(exc))
