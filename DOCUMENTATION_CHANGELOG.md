# Documentation Audit Changelog

This changelog records the strict modifications applied to the original documentation artifacts to ensure absolute fidelity with the source code.

## 1. Removed Unsupported Claims

| Claim Removed | Original Location | Reason for Removal |
| ------------- | ----------------- | ------------------ |
| JWT/OAuth Authentication | Section 7 & 15 | While marked as a "Future Improvement", the original text implied API security existed. Re-verified: Endpoints accept raw `student_id` payloads with no cryptographic validation. Moved entirely to `TECHNICAL_DEBT_REPORT.md` and flagged as a critical vulnerability. |
| Automatic Cloud Backups "in seconds" | Plain English Docs | The daemon poll rate and exact latency is not guaranteed to be "in seconds" depending on connectivity. Reworded to "silently backs up". |

## 2. Added Clarifications & Flags

* **Diagram Verification**: All embedded Mermaid diagrams in `Technical_Project_Documentation.md` have been annotated with `✓ Verified From Code` to prove they were traced directly from `inference_engine.py`, `sm2_scheduler.py`, and `server.py`.
* **Database Dual-Schema Note**: Explicitly noted that `repetition_records` exists in both the Edge SQLite schema and the Cloud Server SQLite schema, whereas `sync_log` is strictly an edge table.

## 3. Added New Engineering Artifacts

Generated `ENGINEERING_ARTIFACTS.md` containing:
- **Class Diagrams** (UML map of the Python backend)
- **Sequence Diagrams** (Flashcard Review & Sync Event tracking)
- **State Diagrams** (Flashcard graduation lifecycle based on SM-2 logic)
- **Navigation Diagram** (Kivy ScreenManager flow map)

## 4. Generated Code-Driven Reports

Generated the following absolute-truth reports derived directly from PowerShell codebase queries:
* `TRACEABILITY_REPORT.md` (Mapping features to exact functions)
* `TECHNICAL_DEBT_REPORT.md` (Highlighting empty `widgets/` folder and security gaps)
* `DEFENSE_PREPARATION.md` (Technical justifications for architectural choices)
* `REPOSITORY_METRICS.md` (Exact counts: 42 files, 73 classes, 338 functions)
