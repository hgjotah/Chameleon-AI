# PyGlass reuse

Source: https://github.com/neomosh8/pyglass
Pinned revision: c12d91f1526badbe18f619ff893d2cdbbd86dac5
License: MIT, copyright 2026 neomosh8 (LICENSE included).

Vendored complete modules: pyglass/effect.py and pyglass/refract.py, under
chameleon/ui/vendor/pyglass/. Changes: Qt binding imports from PyQt6 to PySide6;
QImage.constBits memoryview adaptation; formatting/type/lint annotations only.

Chameleon's glass.py connects the upstream renderer/compositor to native layouts.
Backdrop pixels come exclusively from the application's own painted background;
desktop/window capture modules are not included. Refraction is cached, resolution
bounded, and recomputed after resize/move rather than on each terminal output.
