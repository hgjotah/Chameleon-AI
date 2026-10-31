import asyncio
import os
import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chameleon.core.config import Config, data_dir, save_config
from chameleon.llm.models import MODELS, model_description
from chameleon.ui.glass import install_glass
from chameleon.ui.widgets import BrandMark, MotionButton


class SettingsDialog(QDialog):
    model_status = Signal(str)
    model_finished = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config.model_copy(deep=True)
        self.setWindowTitle("Chameleon · Ajustes")
        self.resize(850, 630)
        self.setMinimumSize(760, 570)
        install_glass(self)
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
        navigation.setStyleSheet(
            "QListWidget{background:rgba(18,32,55,100);border:1px solid rgba(190,219,245,45);border-radius:18px;padding:8px} QListWidget::item{padding:14px 9px;border-radius:12px;color:#a9bfd5} QListWidget::item:selected{background:rgba(99,186,188,65);color:#c0fff0} QListWidget::item:hover{background:rgba(145,177,208,35)}"
        )
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
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(widget)
            tabs.addWidget(scroll)
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
        field(ai, "ai", "model", "Modelo", list(MODELS))
        self.model_combo = self.fields["ai", "model"]
        assert isinstance(self.model_combo, QComboBox)
        self.model_combo.setEditable(True)
        self.model_combo.setCurrentText(self.config.ai.model)
        model_note = QLabel(model_description(self.config.ai.model))
        model_note.setWordWrap(True)
        self.model_combo.currentTextChanged.connect(
            lambda tag: model_note.setText(model_description(tag))
        )
        ai.addRow(model_note)
        self.prepare_model = MotionButton("Descargar si falta y probar modelo")
        self.prepare_model.clicked.connect(self.download_model)
        ai.addRow(self.prepare_model)
        self.model_progress = QLabel("La selección se aplica al guardar.")
        self.model_progress.setWordWrap(True)
        self.model_status.connect(self.model_progress.setText)
        self.model_finished.connect(lambda: self.prepare_model.setEnabled(True))
        ai.addRow(self.model_progress)
        field(ai, "ai", "keep_alive", "Mantener cargado (ej. 5m, 0)")
        field(ai, "ai", "timeout", "Timeout (segundos)", bounds=(5, 600))
        field(ai, "ai", "num_threads", "Hilos de CPU", bounds=(1, 64))
        field(ai, "ai", "enabled", "Activar IA")
        field(ai, "ai", "prefer_model", "Usar Qwen incluso para acciones simples")
        field(ai, "ai", "command_only", "Responder sólo con el comando")
        terminal = page("Terminal")
        field(terminal, "terminal", "font", "Fuente")
        field(terminal, "terminal", "font_size", "Tamaño", bounds=(8, 40))
        field(terminal, "terminal", "cursor_style", "Cursor", ["block", "bar", "underline"])
        field(terminal, "terminal", "cursor_blink", "Parpadeo")
        field(terminal, "terminal", "scrollback", "Scrollback", bounds=(100, 100000))
        field(terminal, "ai", "show_generated_commands", "Mostrar comandos generados")
        safety = page("Acceso del modelo")
        field(
            safety,
            "safety",
            "mode",
            "Perfil",
            ["read_only", "balanced", "developer", "custom", "full"],
        )
        mode = self.fields["safety", "mode"]
        assert isinstance(mode, QComboBox)
        mode.clear()
        for key, label in (
            ("read_only", "Solo lectura"),
            ("balanced", "Equilibrado"),
            ("developer", "Desarrollador · confirmar"),
            ("custom", "Personalizado"),
            ("full", "Acceso total · sin confirmaciones"),
        ):
            mode.addItem(label, key)
        mode.setCurrentIndex(mode.findData(self.config.safety.mode))
        self.access_note = QLabel()
        self.access_note.setWordWrap(True)
        safety.addRow(self.access_note)
        for key, label in (
            ("read", "Leer y navegar"),
            ("write", "Crear, copiar, mover y modificar"),
            ("delete", "Borrar archivos y carpetas"),
            ("commands", "Ejecutar comandos"),
            ("scripts", "Ejecutar scripts e intérpretes"),
            ("network", "Red y descargas"),
            ("system", "Cambios de sistema"),
        ):
            field(safety, "safety", "allow_" + key, label)
        field(safety, "safety", "confirm_changes", "Confirmar antes de ejecutar")

        def access_changed() -> None:
            from chameleon.core.config import SafetyConfig

            chosen = mode.currentData()
            self.access_note.setText(
                "Acceso total elimina los bloqueos y confirmaciones de Chameleon. Windows conserva los permisos de tu usuario."
                if chosen == "full"
                else "Desarrollador permite cualquier comando/script con confirmación."
                if chosen == "developer"
                else "Los scripts son código arbitrario: necesitan todos los permisos de efectos. Estos controles no son un sandbox de Windows."
            )
            preset = SafetyConfig(mode=chosen)
            for key, enabled in preset.permissions().items():
                control = self.fields["safety", "allow_" + key]
                control.setEnabled(chosen == "custom")
                if chosen != "custom" and isinstance(control, QCheckBox):
                    control.setChecked(enabled)
            confirmation = self.fields["safety", "confirm_changes"]
            confirmation.setEnabled(chosen == "custom")
            if chosen != "custom" and isinstance(confirmation, QCheckBox):
                confirmation.setChecked(preset.confirms())

        mode.currentIndexChanged.connect(access_changed)
        access_changed()
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

    def download_model(self) -> None:
        from chameleon.llm.ollama import OllamaProvider
        from chameleon.setup.ollama_install import ensure_server

        assert isinstance(self.model_combo, QComboBox)
        try:
            candidate = self.config.ai.model_copy(deep=True)
            candidate.model = self.model_combo.currentText().strip()
        except ValueError as exc:
            self.model_status.emit(str(exc))
            return
        self.prepare_model.setEnabled(False)

        def worker() -> None:
            async def prepare() -> None:
                provider = OllamaProvider(candidate, progress=self.model_status.emit)
                online, present = await provider.status()
                if not online:
                    await ensure_server(self.model_status.emit)
                    _, present = await provider.status()
                if not present:
                    await provider.pull(self.model_status.emit)
                await provider.probe()

            try:
                asyncio.run(prepare())
                self.model_status.emit(
                    candidate.model + " · respuesta local verificada. Guarda para usarlo."
                )
            except Exception as exc:
                self.model_status.emit(str(exc))
            finally:
                self.model_finished.emit()

        threading.Thread(target=worker, daemon=True, name="Model preparation").start()

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
                    value = (
                        widget.currentData()
                        if section == "safety" and name == "mode"
                        else widget.currentText()
                    )
                else:
                    value = widget.text()
                values[section][name] = value
            self.config = Config.model_validate(values)
            if (
                self.config.safety.mode == "custom"
                and self.config.safety.allow_scripts
                and not all(self.config.safety.permissions().values())
            ):
                raise ValueError(
                    "Para ejecutar scripts arbitrarios activa todos los permisos, o elige Desarrollador. Sus efectos no se pueden aislar con filtros de comandos."
                )
            folder = self.config.terminal.start_directory
            if folder and not Path(folder).expanduser().is_dir():
                raise ValueError(
                    "El directorio inicial debe ser una carpeta existente. Déjalo vacío para usar tu carpeta de usuario."
                )
            from chameleon.platform.windows.system import shell_executable

            shell_executable(self.config.terminal.shell)
            save_config(self.config)
            self.accept()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Configuración inválida", str(exc))
