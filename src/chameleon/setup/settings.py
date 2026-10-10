import os
import shutil

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from chameleon.core.config import Config, data_dir, save_config


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config.model_copy(deep=True)
        self.setWindowTitle("Chameleon Settings")
        self.resize(560, 510)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.fields: dict[tuple[str, str], QLineEdit | QComboBox | QSpinBox | QCheckBox] = {}

        def page(name: str) -> QFormLayout:
            widget = QWidget()
            form = QFormLayout(widget)
            tabs.addTab(widget, name)
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
        ai = page("AI")
        ai.addRow("Proveedor", QLabel("Ollama · exclusivamente local"))
        field(ai, "ai", "model", "Modelo")
        field(ai, "ai", "keep_alive", "Mantener cargado (ej. 5m, 0)")
        field(ai, "ai", "timeout", "Timeout (segundos)", bounds=(5, 600))
        field(ai, "ai", "enabled", "AI enabled")
        terminal = page("Terminal")
        field(terminal, "terminal", "font", "Fuente")
        field(terminal, "terminal", "font_size", "Tamaño", bounds=(8, 40))
        field(terminal, "terminal", "cursor_style", "Cursor", ["block", "bar", "underline"])
        field(terminal, "terminal", "cursor_blink", "Parpadeo")
        field(terminal, "terminal", "scrollback", "Scrollback", bounds=(100, 100000))
        field(terminal, "ai", "show_generated_commands", "Mostrar comandos generados")
        safety = page("Safety")
        safety.addRow(
            QLabel(
                "Confirmaciones obligatorias para cambios.\nLas acciones BLOCKED siempre permanecen bloqueadas."
            )
        )
        field(safety, "safety", "strict_mode", "Confirmar también consultas AI")
        privacy = page("Privacy")
        field(privacy, "privacy", "save_ai_history", "Save AI history (local)")
        privacy.addRow(QLabel("Redacción básica de secretos; no garantiza detectar todos."))
        clear = QPushButton("Borrar historial local y sesiones")
        clear.clicked.connect(self.clear_history)
        privacy.addRow(clear)
        open_folder = QPushButton("Abrir carpeta de datos")
        open_folder.clicked.connect(self.open_data_folder)
        privacy.addRow(open_folder)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
            save_config(self.config)
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, "Configuración inválida", str(exc))
