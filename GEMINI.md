# 🛡️ AI Project Rules & Constitution

## 1. Zero-Tolerance for Lazy Editing
- **NEVER** use placeholders like `// ... rest of code`, `// ... unchanged`, or `...`.
- When updating a file, you MUST provide the **complete, functional code** for the section being replaced.
- If a file is small (< 300 lines), prefer rewriting the entire file to ensure integrity.

## 2. Logging Standards
- **No Base64 in Logs:** All image data (base64 strings) must be truncated or removed from file logs to prevent bloat.
- **Telemetry:** Telemetry (high-frequency data) should be kept to the console (stdout) and excluded from persistent logs unless debugging is explicitly enabled.

## 4. Infrastructure & Boilerplate Integrity
- **Sacred Code:** All code related to MQTT connectivity, retry loops, environment variable parsing, and configuration loading is considered **Sacred**.
- **Conservation Mandate:** Never remove or simplify infrastructure boilerplate during feature implementation or bug fixing unless the task specifically and explicitly requires a refactoring of the connection layer.
- **Surgical Preference:** Always prefer the `replace` tool over `write_file` to isolate changes to logic and prevent "accidental cleanup" of essential service code.
