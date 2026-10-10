# Correspondencia con el documento de requisitos

Esta tabla permite localizar la implementación de los 55 apartados. La evidencia ejecutada y las pruebas manuales pendientes se distinguen en [VALIDATION.md](VALIDATION.md); la existencia de una función no equivale a certificar todas las versiones de Windows o todos los programas interactivos.

| Apartado | Implementación / documentación |
|---|---|
| 1 · Asistente en la sesión actual | CLI, wrapper CMD y módulo PowerShell; tests reales del cwd padre |
| 2 · Terminal gráfica real | `terminal/`, `platform/windows/conpty.py`, xterm local |
| 3 · Python moderno | Python 3.13, Pydantic, PySide6; `pyproject.toml` |
| 4 · IA local | `llm/ollama.py`, modelo exacto `qwen3:4b-instruct` |
| 5 · Reglas sin IA | `core/intents.py`, navegación y consultas inequívocas |
| 6 · Comandos normales | Clasificación de builtins, PATH, scripts y aliases; entrada directa |
| 7 · CMD | `assets/shell/chameleon.cmd`, protocolo de acción temporal; sin AutoRun |
| 8 · PowerShell | `Chameleon.psm1`, perfiles descubiertos y bloque marcado |
| 9 · Administrador | Token heredado, comprobación de privilegios; sin elevación automática |
| 10 · Respuesta estructurada | `core/schemas.py`, acciones tipadas y validación antes de ejecutar |
| 11 · System prompt | `llm/prompts.py`, esquema contextual y sin pensamiento visible |
| 12 · Contexto | `core/context.py`; contexto limitado y redactado |
| 13 · Sesiones | `core/sessions.py`; PID + fecha de creación + caducidad |
| 14 · Privacidad | Historial optativo, redacción; PRIVACY.md |
| 15 · Safety Engine | `safety/engine.py`; SAFE / CONFIRM / BLOCKED independientes del modelo |
| 16 · Ambigüedad | Plan `clarify`, elección en CLI y GUI, cancelación segura |
| 17 · Visibilidad | Ocultación habitual, `--show`, `--dry-run`, vista de confirmación |
| 18 · Comportamiento GUI | Puente Qt, editor nativo, clasificación solo en prompt |
| 19 · Interactivos | Marcador OSC autenticado en shell hijo; entrada raw en REPL/TUI |
| 20 · Shell seleccionable | CMD predeterminado, Windows PowerShell y PowerShell 7 |
| 21 · Estética | Negro/verde, tipografía del sistema, barra discreta y estado de IA |
| 22 · Render | xterm 5.5, ANSI, selección, clipboard, scrollback, resize, zoom y F11 |
| 23 · Latencia | Reglas locales, worker de IA, indicador PROCESSING y keep-alive |
| 24 · Ollama | Setup, firma oficial, progreso de descarga y prueba de inferencia |
| 25 · Offline | Transporte de inferencia solo loopback; procedimiento de VM en VALIDATION.md |
| 26 · Installer | Setup autocontenido, instalación por usuario, PATH y shortcuts |
| 27 · Repair | Recopia/verificación del payload, integración y comprobación de IA |
| 28 · Uninstall | Manifest de propiedad; conserva perfil/PATH ajenos; extras con consentimiento |
| 29 · Settings | General, AI, Terminal, Safety y Privacy; validación y guardado atómico |
| 30 · Doctor | `setup/doctor.py`, CLI `chameleon doctor` |
| 31 · Multiplataforma | Interfaces PlatformAdapter, ShellAdapter, PtyBackend; Linux reservado |
| 32 · Repositorio | `src/chameleon`, `tests`, `scripts`, `installer`, `docs`, `.github` |
| 33 · Tests | Parser, quoting, riesgo, rutas, modelo, sesiones e instalación |
| 34 · Integración real | `test_windows_shells.py`, CMD / PS 5.1 / PS 7 reales |
| 35 · Terminal tests | ConPTY y GUI reales; matriz de pruebas manuales pendiente documentada |
| 36 · Errores | Diagnósticos accionables y planes inválidos sin ejecución |
| 37 · Logging | Rotación limitada; sin guardar prompts/salida normal por defecto |
| 38 · Configuración | TOML por usuario, valores tipados y recuperación con backup |
| 39 · Actualizaciones | Versión semántica, Setup Update sobre payload de nueva release |
| 40 · Documentación | README, ARCHITECTURE, BUILDING, INSTALLATION, integración, seguridad y privacidad |
| 41 · Build | `scripts/build.ps1`, dependencias fijadas, verificación de código/payload congelado |
| 42 · CI | GitHub Actions Windows; lint, tipos, tests, build y smoke de ejecutables |
| 43 · Calidad | Ruff, mypy, módulos separados, interfaces y workers |
| 44 · Temporales | Nombres aleatorios, ACL privada, escritura exclusiva, caducidad y limpieza |
| 45 · Protocolo | Token ASCII por archivo exclusivo; wrapper nunca interpreta texto del modelo |
| 46 · Cancelación | Cancelación asyncio desde Ctrl+C; test de carrera antes de crear el loop |
| 47 · Modelo ausente | AI OFFLINE; shell y reglas locales siguen disponibles |
| 48 · Rutas de usuario | Windows Known Folders y APIs de Windows; sin usuario fijo |
| 49 · Idiomas | Peticiones español/inglés; UI inicial española, preferencia preparada para i18n |
| 50 · Casos de uso | Navegación, PDF, confirmación, ambigüedad, búsqueda por tamaño y REPL |
| 51 · Exclusiones | Sin cloud, claves, telemetría, chat lateral, shell falso ni Python obligatorio en destino |
| 52 · Criterios | Build y pruebas reales de componentes; límites de certificación en VALIDATION.md |
| 53 · Fases | Investigación, core, integración, IA, seguridad, GUI, Setup y distribución |
| 54 · Revisión | Lint, tipos, tests, ejecutables y detección/corrección de fallos de empaquetado |
| 55 · Entrega | Fuente, tres ejecutables, Setup independiente, ZIPs, hashes, docs y CI |

Las decisiones técnicas que difieren del ejemplo conceptual —acciones tipadas, helper de consultas y runtime compartido— se explican en ARCHITECTURE.md. Ningún comando de texto del modelo se considera una autorización para ejecutarlo.
