# Chameleon AI · Chameleon Terminal

Asistente local para **Windows 10 1809+ y Windows 11 x64**, escrito en Python 3.13, con Ollama y `qwen3:4b-instruct`. Convierte español o inglés en acciones validadas que se ejecutan en la sesión actual. Incluye un terminal gráfico de verdad: PySide6, ConPTY y xterm.js local.

```cmd
chameleon ai ve a Downloads
chameleon ai lista los pdf
chameleon ai encuentra todos los PDF
chameleon ai crea un archivo llamado notas.txt con contenido "Hola"
chameleon ai crea una carpeta llamada proyecto
chameleon ai copia notas.txt a copia.txt
chameleon ai --dry-run busca archivos Python mayores de 1 MB
chameleon ai elimina old.txt
chameleon doctor
```

`cd` persiste en CMD y PowerShell. Los comandos generados se ocultan salvo confirmación, `--show` o `--dry-run`. `dir`, `git status`, `python` y todos tus comandos normales siguen usando su shell original.

En **0.2.0**, crear archivos/carpetas, leer, copiar, mover y navegar se resuelven con reglas locales cuando la petición es concreta. Crear/copiar/mover nunca sobrescribe un destino existente. Se pide confirmación antes de cualquier cambio. En Chameleon Terminal escribe la frase directamente; en CMD/PowerShell utiliza `chameleon ai`.

## Instalar y ejecutar

1. Ejecuta `dist/ChameleonSetup.exe` (release autocontenida; no requiere Python).
2. Pulsa **Instalar Chameleon**. Si falta Ollama, acepta su instalación oficial y la descarga del modelo. Se comprueba la firma de Ollama y su inferencia local.
3. Si PowerShell bloquea perfiles, Setup explica la política y ofrece **RemoteSigned CurrentUser** con consentimiento explícito. No modifica políticas silenciosamente.
4. Abre un **nuevo** CMD o PowerShell y utiliza `chameleon ai ...`.
5. Abre **Chameleon Terminal**, **Chameleon Settings** o **Uninstall Chameleon** desde Inicio.

Instalación por usuario en `%LOCALAPPDATA%\ChameleonAI`. El PATH se amplía conservando sus entradas. No se usa Command Processor AutoRun. Ollama no se redistribuye dentro del instalador; el modelo tampoco.

## Chameleon Terminal

CMD por defecto; abre otra sesión con el selector de shell o **+ Nueva sesión**. Los programas interactivos reciben entrada directa. En el prompt principal puedes escribir `Downloads` o una petición natural. Los comandos reconocidos, aliases y scripts van directamente al PTY. **Entrada directa** permite forzar entrada directa cuando lo necesites. **Guía** muestra ejemplos; **Ajustes** personaliza fuente, cursor, IA y privacidad.

Atajos: Ctrl+C interrumpe/cancela IA; Ctrl+Break cuando el proceso lo permite; Ctrl+Shift+C/V copia/pega; Ctrl+`+`/`-` cambia fuente; F11 pantalla completa. Las flechas, Tab e historial los gestiona el shell real. El pegado multilínea siempre se envía como entrada directa.

## IA, privacidad y seguridad

Solo se contacta `http://127.0.0.1:11434`, sin proxies ni fallback cloud. Las reglas claras funcionan aunque Ollama esté apagado. xterm.js y todos sus recursos vienen incluidos; después de descargar Ollama y Qwen no se necesita Internet.

No hay telemetría. El historial permanente está **desactivado**. El contexto externo se limita a seis elementos redactados y caduca a los 30 minutos; identifica PID y fecha de creación para evitar reutilización de PID. No pretende observar comandos normales en terminales externas. La GUI conserva solo una cola limitada de salida en memoria. La redacción de secretos es básica, no infalible.

El motor de riesgo es independiente del modelo: **SAFE**, **CONFIRM** (No por defecto), **BLOCKED**. No hay casilla que desactive BLOCKED. Los comandos opacos, intérpretes anidados, descargas y operaciones masivas de disco generadas por IA se bloquean. Las acciones normales escritas directamente mantienen el comportamiento de su shell.

## Construir desde código

Requisitos de desarrollo: Python **3.13 x64**, Node.js 22+ y Windows. Estos requisitos no son necesarios en el equipo de destino.

```powershell
.\scripts\build.ps1
```

El script instala dependencias fijadas, comprueba lint, tipos y tests, copia recursos npm locales, genera iconos y construye:

```text
dist/ChameleonSetup.exe                 Instalador autocontenido
dist/Chameleon/ChameleonCore.exe        CLI y protocolo de shell
dist/Chameleon/ChameleonTerminal.exe    GUI
dist/Chameleon/ChameleonSetup.exe       Setup / Settings / Uninstall
dist/Chameleon/_internal/               Runtime compartido (conservar completo)
dist/ChameleonAI-0.2.0-windows-x64.zip   Paquete portable con Setup integrado
dist/ChameleonAI-0.2.0-source.zip        Código fuente listo para GitHub
dist/SHA256SUMS.json                    Checksums
```

Desde fuente, después de preparar `.venv`: `scripts/run.ps1 terminal`, `scripts/run.ps1 setup`, `scripts/run.ps1 settings`. `python -m chameleon ai --dry-run ...` permite revisar planes; solo el wrapper/módulo puede modificar el shell padre.

## Mantener y publicar

GitHub Actions ejecuta lint, tipos, tests reales de shells y un build Windows sin secrets obligatorios. Los tests de Ollama requieren `CHAMELEON_TEST_OLLAMA=1`. Consulta [BUILDING](docs/BUILDING.md), [arquitectura](ARCHITECTURE.md), [instalación](docs/INSTALLATION.md), [integración](docs/SHELL_INTEGRATION.md), [seguridad](docs/SAFETY.md), [privacidad](docs/PRIVACY.md), [matriz de terminal](docs/TERMINAL_TEST_MATRIX.md), [validación de esta entrega](docs/VALIDATION.md) y [correspondencia con los 55 requisitos](docs/REQUIREMENTS.md).

Para subir este repositorio, crea un repositorio vacío en tu cuenta y ejecuta desde esta carpeta:

```powershell
git remote add origin https://github.com/TU_USUARIO/chameleon-ai.git
git push -u origin main
```

Si empiezas desde el ZIP de fuentes, prepara primero el repositorio con `git init -b main`, `git add .` y `git commit -m "Initial release"`. La carpeta de esta entrega ya contiene su repositorio Git local.

Publica los binarios de `dist` como assets de una GitHub Release; el runtime completo supera el límite por archivo del repositorio Git y está excluido por `.gitignore`.

El proyecto usa MIT; sus dependencias mantienen sus licencias. PySide6/Qt son LGPL/GPL/comerciales: se distribuyen bibliotecas compartidas, avisos y licencias. Los binarios de esta entrega no están firmados con un certificado comercial. Windows puede mostrar SmartScreen; la firma comercial puede añadirse al proceso de release.
