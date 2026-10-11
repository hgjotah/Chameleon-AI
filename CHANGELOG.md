# Changelog

## 0.3.0 · 2026-10-11

- Logo aportado por el usuario: PNG original en Terminal, Setup, Settings, bootstrap, iconos Windows y accesos directos.
- Borrado «un archivo en Downloads llamado Prueba.txt» y nombres sin extensión; los candidatos ambiguos requieren selección explícita.
- Subrutas de carpetas conocidas y Descargas redirigidas se resuelven contra sus ubicaciones reales.
- Inspecciones de solo lectura para fundamentar respuestas en archivos y procesos reales; límites explícitos, redacción de secretos y lectura UTF-16 con BOM.
- Origen visible con llamadas, tokens, modelo y duración reales; selector Automático/Qwen y opción CLI `--model`.
- Cierre explícito de la ronda de herramientas y resúmenes acotados para evitar lecturas repetidas y explicaciones largas antes de actuar.
- Setup y Terminal rediseñados con panel de respuesta, jerarquía tipográfica, tarjetas, controles y transiciones; apertura del terminal tras instalar.
- Actualización por usuario desde el Core congelado conservando preferencias, perfiles y PATH.
- Permisos del runtime aplicados antes de crear staging y backup, evitando el timeout encontrado en una actualización real; error de permisos con diagnóstico específico.

## 0.2.0 · 2026-10-10

- Creación literal de archivos UTF-8 y carpetas; copia y movimiento sin sobrescritura, compartidos por CMD, PowerShell y GUI. Lectura UTF-8 explícita también en PowerShell 5.1.
- Aclaraciones conservan la operación solicitada; los permisos administrativos se calculan independientemente de las sugerencias del modelo.
- Actualización a pywinpty 3.0.5, que incorpora el cierre de ConPTY mediante eventos y corrige el bucle de CPU de la versión anterior; comprobación explícita de sus tres binarios nativos.
- Arranque de PowerShell con sus módulos correctos aunque el proceso padre sea PowerShell 7; Doctor deja de marcar políticas desconocidas como correctas.
- Reparación con recuperación de binarios, perfiles, configuración, PATH y registro ante errores antes de confirmar el manifiesto; hashes y manifiesto atómico.
- El lanzador de desarrollo usa el instalador independiente para evitar la redirección privada de AppData/registro de Python de Microsoft Store.
- Prueba mínima de inferencia; errores de IA se notifican por separado de una instalación correcta del terminal.
- Interfaz nativa renovada: terminal con selector de shell, sesiones, guía, ruta y actividad; instalador con estados; ajustes con navegación lateral; botones y transiciones animados.
- Entrada sincronizada con el editor nativo para evitar texto truncado al pulsar Enter; las repeticiones de títulos de ConPTY no activan IA dentro de programas interactivos.
- Pruebas de creación con contenido Unicode y símbolos en el terminal real, en los wrappers de tres shells y en los ejecutables distribuidos.

## 0.1.0 · 2026-10-10

- Core híbrido español/inglés, Ollama local con JSON Schema y validación Pydantic.
- Integraciones CMD y Windows PowerShell/PowerShell 7 con estado de sesión.
- Motor de riesgo independiente, confirmación por defecto negativa y bloqueo permanente.
- Terminal ConPTY con xterm.js local, prompt markers, modos AI y raw, Settings.
- Setup por usuario, Repair, Update y Uninstall, gestión consentida de Ollama y políticas.
- Build Windows autocontenido, tests pytest, ruff, mypy y GitHub Actions.
