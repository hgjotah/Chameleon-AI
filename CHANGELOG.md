# Changelog

## 0.6.0 · 2026-11-02

- Nueva interfaz en verdes bosque, musgo y salvia: superficies mate, menos controles simultáneos y vidrio reservado para las barras de acciones. Se conserva el logo original.
- Corregido el resplandor espectral del material que añadía colores ajenos a la paleta; refracción y bisel proporcionales a la resolución de caché, iluminación localizada y bordes más claros.
- Botones con desplazamiento magnético, contramovimiento del texto, luz radial y presión reversible. Adaptaciones nativas de código MIT de Codrops y Motion Primitives, con fuentes, revisiones y licencias incluidas.
- El panel «IA y permisos» aparece bajo demanda con transición; no cambia las dimensiones del PTY y devuelve el foco al terminal al cerrarse. Escape cierra el panel.
- Setup simplificado: opciones avanzadas y registro desplegables, estado compacto y actualización explícita cuando hay una versión anterior. Ajustes con navegación y permisos personalizados progresivos.
- Animaciones detenidas en reposo y al ocultar controles; respeto de la preferencia de movimiento reducido de Windows. Comprobaciones de instalación nueva y actualización en procesos Qt aislados.
- Se mantienen los modelos, permisos, comandos y configuración existentes.

## 0.5.1 · 2026-11-01

- Fundamentación en el sistema real: versión/edición/lenguaje del shell, ruta del ejecutable, arquitectura, idioma, carpetas conocidas redirigidas y variables permitidas; contexto seleccionado según la petición.
- PowerShell 7 se identifica correctamente también desde el wrapper. Los alias/funciones relevantes y el modo de lenguaje del shell llamante se transmiten sin enviar sus cuerpos.
- Consulta de ayuda nativa de Windows y metadatos/AST de PowerShell para revisar operación, parámetros, sintaxis y valores de propiedades antes de proponer la ejecución. La propuesta nunca se ejecuta durante esta inspección.
- Eliminados los pares de órdenes/respuestas del prompt. El modelo elige el comando; la aplicación aporta observaciones y errores nativos para corregirlo.
- Validación de operandos, comillas, contenido literal y tipo de operación en las tareas simples verificadas; rechazo de nombres inventados, rutas devueltas como texto y palabras de la petición usadas como argumentos.
- Lecturas de propiedades de sesión y cambios de apariencia limitados a sus permisos correspondientes, sin exigir acceso arbitrario a scripts.
- Los nombres ambiguos y destinos existentes se resuelven antes de llamar al modelo. La creación de contexto nativo ocurre fuera del hilo de interfaz.
- Normalización de un único delimitador de código; se siguen rechazando prosa y múltiples líneas.

## 0.5.0 · 2026-10-31

- Cinco perfiles de acceso: Solo lectura, Equilibrado, Desarrollador, Personalizado y Acceso total sin bloqueos/confirmaciones de aplicación.
- Permisos independientes de lectura, escritura, borrado, comandos, scripts, red, sistema y confirmaciones. Los scripts arbitrarios requieren todos los permisos de efectos; Windows conserva su autoridad sobre privilegios y ACL.
- Selección de qwen3:4b-instruct y qwen2.5:0.5b en Setup/Ajustes/Terminal; preparación, descarga y prueba del modelo seleccionado.
- Salida predeterminada de un único comando nativo, sin prosa/JSON/Markdown; ejemplos específicos por shell, contexto de rutas literal y reintento ante cmdlets inexistentes o fuentes inventadas.
- Planificador estructurado anterior disponible al desactivar «Responder sólo con el comando».
- Interfaz de vidrio con refracción real basada en módulos MIT de PyGlass, adaptación PySide6 y NumPy; licencia/revisión atribuidas, caché acotada y sin captura del escritorio.
- Cambio de modelo/perfil cancela una consulta en curso; la generación usa una instantánea de la configuración.
- Puente CMD adapta llamadas a .cmd/.bat y variables FOR al contexto batch transitorio.

## 0.4.0 · 2026-10-11

- Integración Ollama con streaming, progreso real de recepción y rechazo de respuestas interrumpidas o truncadas; cancelación conserva el control del terminal.
- Inicio automático del servidor local cuando Ollama ya está instalado pero detenido; se comprueba el puerto antes de lanzar otro servidor.
- Hilos de CPU configurables (4 por defecto), eliminación del esquema duplicado en el prompt y respuestas breves para reducir el tiempo de inferencia.
- Resúmenes con ruta explícita: lectura real previa y una sola llamada al modelo; las consultas ambiguas mantienen el flujo de inspección.
- Operaciones simples forzadas a Qwen limitan el esquema a la acción correspondiente, evitando comandos inexistentes como `create`.
- Las consultas directas de archivos/procesos generan salida nativa; cualquier otra inspección entra en la fase de respuesta, también con frases fuera de las reglas iniciales.
- Setup muestra el ejecutable de Ollama, el servidor y el modelo por separado; preparar IA instala el backend ausente con consentimiento, descarga el modelo y exige una inferencia real.
- Porcentajes de descarga reales, panel de opciones desplazable y diagnóstico del ejecutable de Ollama; los errores de descarga no ocultan que el terminal ya está instalado.
- Instalación por CLI con opciones explícitas para Ollama/modelo y código de salida 3 cuando queda IA pendiente.
- Nueva imagen exacta aportada por el usuario en todas las superficies, iconos y accesos directos; lanzadores utilizan el runtime independiente cuando está construido.
- Puente Qt registrado antes de cargar el renderizador: elimina el registro tardío y la recarga inicial; el lector del terminal espera al cliente preparado.

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
