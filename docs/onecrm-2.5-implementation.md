# OneCRM 2.5 Implementation Notes

## Goal

OneCRM 2.5 replaces the static EnvPortal UI with a React/Ant Design enterprise interface and introduces FastAPI, PostgreSQL, Redis, and MinIO as the platform foundation.

## Decisions

- Product name: `OneCRM`.
- Frontend: React + Vite + TypeScript + Ant Design v5.
- Backend: FastAPI, with legacy `.jsp` endpoints kept as adapters for one transition release.
- Persistence: PostgreSQL is the source of truth after first startup.
- Cache: Redis is used by the backend, not directly by the browser.
- Object storage: MinIO is reserved for certificates, VPN/config packages, imports, and exports.
- Auth: 2.5.9 replaces the single administrator password with PostgreSQL-backed local users. If no user exists on startup, `Admin` is created from `AUTH_PASSWORD`.

## Authentication and Authorization

- User data is stored in `users`; sessions are stored in `user_sessions`; password reset links use `password_reset_tokens`.
- Passwords are saved as PBKDF2 hashes with per-password salt. Session and reset tokens are stored as SHA-256 hashes.
- `Admins` can write business data and maintain users. `Users` can read, copy, download, and connect, but write APIs return `403`.
- The top-bar gear menu is the system-function entry point for user management, profile, password change, and logout.
- Avatars are stored in MinIO and referenced by object key in PostgreSQL.
- Forgot-password sends an SMTP reset link built from `ONECRM_PUBLIC_URL`; `http://192.168.20.38:5000/` can be used to inspect test mails.

## Customer Master

2.5.15 adds the customer master as a first-class business page beside customer environment.

- Data remains in the existing `organizations` table: `id`, `code`, `name`, `created_at`, and `updated_at`.
- `GET /api/organizations` continues to be the read model for both customer environment and customer master. It returns customer metadata, VPN guides, and environments.
- `POST /api/organizations` creates a customer with required trimmed `code` and `name`.
- `PATCH /api/organizations/{organization_id}` updates customer code and name. Code remains case-preserving and database-unique.
- Both write APIs are protected by the existing Admin-only write gate. `Users` can open the customer master page but cannot create or edit customers.
- Customer deletion is intentionally omitted in this phase because it would need explicit cascade policy for environments, VPN guides, source files, remote connections, and audit history.
- The frontend customer master page shows existing environment summaries as read-only context and reserves non-mock placeholders for contracts, implemented products, custom development, and code comparison.

## VPN Credential Groups

AI workflow steps may include `credentialGroups`, an array of server/hop credential objects. Each group binds host/address, port, protocol, username, password, note, and auxiliary details to one exact connection target. This prevents the UI from showing unrelated lists of servers and passwords that operators cannot safely associate.

Raw VPN source files remain archived in MinIO for traceability, but the connection/VPN overview does not expose per-file download buttons. It presents parsed source counts/status instead.

The customer-level VPN guide panel is the only place that renders the full workflow card sequence. Server cards that select a VPN guide render a compact reference with the guide name, tags, AI status, step count, and source count. This avoids repeating the same procedure for every server that merely references the guide.

VPN workflow analysis prompts require Japanese operator-facing output by default. The prompt keeps main steps coarse-grained and stores server rows, credentials, URLs, ports, and remarks in `credentialGroups` or step details. Parser metadata is source context only and must not become workflow cards.

The backend also guards against over-fragmentation after AI returns. If the model still emits too many top-level steps, post-processing groups them into major phases such as preparation/request, LAPLINK, VPN connection, target server connection, and completion contact. The local fallback follows the same phase-based structure instead of splitting every source line.

## VPN File Ingestion

The VPN guide editor supports multi-file ingestion. Users can attach several files while creating or updating a VPN guide. The backend stores source files in MinIO, rebuilds source-derived text, then triggers the VPN workflow analysis pipeline.

This feature must be implemented as an asynchronous backend workflow rather than a blocking form submit. Saving the VPN guide should return quickly with a persisted record and an analysis status. File parsing, summarization, and workflow generation continue in the background.

### Hermes Agent Role

`Hermes Agent` is the orchestration layer for this workflow. It should decide which parser or analysis path to use for each file instead of sending every file directly to a large model.

Expected tool strategy:

- Text documents: use document parsers first, preserving headings, paragraphs, key-value pairs, lists, and tables.
- Spreadsheets: extract sheet names, row/column labels, tables, and likely configuration keys.
- Presentations: extract slide titles, notes, diagrams, and ordered instructions.
- Email exports or copied mail templates: extract recipients, CC/BCC, subject, and formatted body where possible.
- Images and scans: choose OCR, layout analysis, or vision-model interpretation depending on quality. Some screenshots may be better handled by vision models than by plain OCR.
- Archives: unpack, classify internal files, parse each file independently, then merge the results.

Large-model calls should be used for consolidation, deduplication, contradiction detection, missing-field inference, and final workflow structuring. They should not be the default first parser for every uploaded file.

### Data Flow

1. Frontend uploads one or more files with the VPN guide form. Directory uploads preserve recursive relative paths and client-side modified timestamps.
2. Backend stores each binary in MinIO by SHA-256 under `vpn-sources/sha256/<sha256>`.
3. Backend records `file_objects`, guide associations, and a `vpn_import_jobs` row with `mode=rebuild`.
4. Adding files to an existing guide does not analyze only the new files. The backend reloads every source file currently associated with that guide.
5. Hermes Agent parses each source file with the best available parser/tool path.
6. Hermes returns `sourceRawText`, `sourceMeta`, source fragments, warnings, and a source precedence summary.
7. Backend stores `sourceRawText`, keeps user-maintained `manualRawText`, and builds `analysisRawText = sourceRawText + manualRawText` after cleaning irrelevant customer-context duplicates.
8. VPN workflow analysis runs against `analysisRawText` and updates the guide with ordered steps, mail templates, automatic tags, and analysis status.

### Reanalysis

Users can rerun AI analysis from the VPN guide header without entering edit mode. Reanalysis means "rerun workflow AI against the current saved analysis text"; it must not call Hermes or rebuild source extraction. Hermes rebuilds are reserved for file upload/import paths, where the source set has actually changed. Reanalysis reuses the current `analysisRawText` or the cleaned combination of `manualRawText` and `sourceRawText`, strips parser metadata markers, and starts the AI workflow task directly. Reanalysis must set the guide to `analyzing` immediately so the frontend can show progress without requiring another upload.

### Source Text Fields

- `sourceRawText`: derived from the current full source-file set. It is rebuilt by Hermes and must not be manually edited.
- `manualRawText`: user-maintained supplemental text. It survives source rebuilds.
- `analysisRawText`: cleaned final input for AI workflow analysis. It is also exposed through the compatibility `rawText` field.
- Original files are immutable source archives. Cleaning and AI preparation only affect derived text.

### Source Precedence

Hermes includes filename, folder path, relative path, client modified time, upload time, path context, date hints, and source role in its output. Path and content hints such as `20260501以降`, `新サーバ`, `旧`, `追加`, `補足`, `差分`, and `変更` are treated as meaningful source context.

The AI workflow prompt uses source precedence to prefer current/override/supplement sources over historical material. When remote access requires a jump host, bastion, gateway, proxy, relay, `踏み台`, `経由`, or `中継`, the workflow must be split into ordered connection steps and keep credentials attached to the matching host or hop.

### UX Requirements

- File parsing and AI workflow analysis must not block the save action.
- While parsing/analyzing, the guide is shown as read-only with a clear status overlay.
- Users can inspect the generated raw text and manually adjust it after analysis completes.
- If parsing fails, the system keeps uploaded objects and partial text where possible, and exposes a retry path.
- Generated mail steps must render as mail-specific UI, not plain text blocks.

## Migration

On startup, the backend initializes tables and checks whether organizations or environments already exist. If not, it imports the legacy files:

- `data.csv` becomes organizations and environments.
- `tags.json` becomes tags and environment tag joins.
- `rdp.csv` becomes remote connection records.

Before importing, the original files are copied to `.tmp/migration-backup/`.

## Rollback

The legacy CSV/JSON files are retained. To roll back, stop OneCRM, switch back to the previous branch/version, and start the old server. PostgreSQL data can be left in place; the previous version will ignore it.

## Verification Checklist

- `npm run build` in `frontend/`.
- Python imports `onecrm.app` successfully.
- `docker compose config` passes.
- First startup creates PostgreSQL tables and imports the sample CSV/JSON data once.
- `/api/organizations` returns organizations, environments, manual tags, and automatic DB tags.
- `/api/env-check`, `/api/db-probe`, `/api/rdp/file`, `/api/guacamole/connect`, and `/rdp_signing_cert.cer` remain callable.
