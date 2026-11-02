# Third-party notices

Chameleon source is MIT. Bundled components retain their own licenses:

- Python 3.13: Python Software Foundation license.
- PySide6 / Shiboken6 / Qt 6.10.2: LGPL v3 / GPL v3 / commercial; shared libraries are shipped in `_internal`. [Qt licensing](https://doc.qt.io/qt-6/licensing.html), [Qt source archive](https://download.qt.io/archive/qt/6.10/). Users may replace compatible shared libraries. Chameleon does not prohibit reverse engineering for debugging changes to LGPL components.
- xterm.js and addons: MIT; verbatim licenses are vendored beside JavaScript.
- pywinpty: MIT; its Rust binding/runtime dependencies retain their licenses.
- Microsoft Terminal's side-by-side ConPTY (`conpty.dll`, `OpenConsole.exe`) and WinPTY's native library: MIT. Matching published pywinpty wheel binaries are bundled, with the [Microsoft Terminal license](https://github.com/microsoft/terminal/blob/main/LICENSE) and [WinPTY license](https://github.com/rprichard/winpty/blob/master/LICENSE) included.
- Pydantic, httpx, psutil, tomli-w and build tools: their wheel metadata/license files accompany the distribution where provided.
- PyInstaller: GPL with bootloader exception permitting distribution of built applications under their own license.
- Ollama and Qwen are separately downloaded from their official sources and not included as copied binaries/weights in Chameleon.

Build scripts collect distribution license metadata into `Chameleon/_internal/chameleon/assets/licenses`. The Qt/Python licensing texts are included with the produced release. No proprietary font is bundled; Cascadia Mono and Consolas are used only if available on the system, with monospace fallback.
# PyGlass Liquid Glass renderer

Copyright (c) 2026 neomosh8. MIT License.
Source: https://github.com/neomosh8/pyglass
Revision: c12d91f1526badbe18f619ff893d2cdbbd86dac5.
Complete effect.py/refract.py modules adapted from PyQt6 to PySide6. Full license
and provenance: assets/licenses/pyglass/. NumPy's bundled notices are included
under assets/licenses/numpy/.

# Native motion adaptations

- Codrops MagneticButtons, MIT, revision b2ee8ac9cd561e13198335cca5684fe1c31d543c.
  https://github.com/codrops/MagneticButtons
- Motion Primitives Spotlight, MIT, revision 120f64f6ca60348e251f929e9c81f11ccbe45eda.
  https://github.com/ibelick/motion-primitives

Pointer translation/counter-translation and spotlight geometry are adapted to
Qt painting. Original source files, licenses and exact adaptation notes accompany
the runtime in assets/licenses/ui-motion. React/Motion/GSAP are not bundled.
The PyGlass app adapter disables spectral glow; its reflected light is tuned to
the forest/sage palette. See assets/licenses/pyglass/PROVENANCE.md.
