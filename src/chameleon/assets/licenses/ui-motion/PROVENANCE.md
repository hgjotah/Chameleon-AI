# Native motion adaptations · Chameleon 0.6.0

## Codrops MagneticButtons · MIT

Source: https://github.com/codrops/MagneticButtons
Revision: b2ee8ac9cd561e13198335cca5684fe1c31d543c
Original: src/js/demo1/buttonCtrl.js (bundled here as Codrops-buttonCtrl.js).
Copyright (c) 2009–2020 Codrops. Full license: Codrops-LICENSE.

ui/controls.py adapts the pointer-relative .3 translation, .1 interpolation and
.6 text counter-translation to QPainter. Native hit areas stay fixed and movement
is bounded. GSAP and the website's event/DOM infrastructure are not bundled or run.
Qt supplies the press/release and highlight transitions. Timers stop at rest,
when hidden or disabled; Windows animation preferences are respected.

## Motion Primitives Spotlight · MIT

Source: https://github.com/ibelick/motion-primitives
Revision: 120f64f6ca60348e251f929e9c81f11ccbe45eda
Original: components/core/spotlight.tsx (bundled alongside this notice).
Copyright (c) 2024 ibelick. Full license: Motion-Primitives-LICENSE.md.

ui/controls.py and ui/glass.py adapt local pointer coordinates, a clipped radial
light and hover visibility to native painting. React/Motion are not dependencies
of the Windows application. These are native adaptations, not embedded web demos.
