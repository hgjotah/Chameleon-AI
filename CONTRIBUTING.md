# Contributing

Use Python 3.13 x64 on Windows. Keep OS code under platform/windows, preserve typed actions and independent safety evaluation, and never add a cloud fallback. Each change affecting quoting/protocol must include real parent-shell tests; installation tests use temporary profiles and PATH strings, never real user files. Use `scripts/build.ps1` for all required checks.

Requirements and package-lock are release pins. Update dependencies deliberately and rerun Qt/ConPTY smoke checks. Include third-party license changes. UI text is isolated from APIs and config includes es/en preference; English is the application interface and documentation language; English and Spanish requests remain supported. Public identifiers and APIs stay in English.

Before a release complete `docs/TERMINAL_TEST_MATRIX.md`, record actual results in `docs/VALIDATION.md`, verify install/repair/uninstall with a clean Windows user and run offline checks. Never mark unperformed tests as passed. No repository secret is required to test/build. Publish installer and portable ZIP with SHA256SUMS; sign with an external certificate if available.
