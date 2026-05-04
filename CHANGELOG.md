# Changelog

All notable changes to OneCRM are documented here.

## [Unreleased]

### Versioning

- NewUI branch development is versioned continuously. Every stable feature or behavior batch should receive a 2.5.x patch version before commit instead of accumulating indefinitely under 2.5.0.

## [2.5.10] - 2026-05-04

### Changed

- Raised the current application version to `2.5.10`.
- Removed source-file download buttons from the connection/VPN overview. The section now shows parsed AI source counts/status instead of encouraging users to download raw source files.
- Added structured VPN credential groups so AI-recognized server hosts, users, passwords, ports, and protocols can stay visually bound to the exact server or connection hop they belong to.
- Changed server-card VPN guide references to compact summaries. The complete VPN workflow now appears only once at the customer-level VPN guide area instead of being duplicated inside every server that references it.

## [2.5.9] - 2026-05-04

### Added

- Added PostgreSQL-backed local users with `Admins` and `Users` roles.
- Added PBKDF2 password hashing, server-side sessions, password reset tokens, and first-start `Admin` migration from `AUTH_PASSWORD`.
- Added OneCRM-styled login, forgot-password, reset-password, profile, avatar, logout, and top-bar system menu surfaces.
- Added Admin-only user maintenance APIs and UI for creating users, editing profile fields, resetting passwords, and enabling/disabling accounts.
- Added SMTP password reset mail configuration and documented testing with the virtual mail viewer at `http://192.168.20.38:5000/`.

### Changed

- Raised the current application version to `2.5.9`.
- Protected business write APIs so `Users` can read, copy, download, and connect, but cannot modify customer environment data.

## [2.5.8] - 2026-05-03

### Changed

- Raised the current application version to `2.5.8`.
- Corrected the overview visibility rules: full-dimension statistic cards appear only in the all-customer, unfiltered view.
- Changed the connection/VPN section to appear only in scoped views, such as a selected customer or tag-filtered range, because it describes the currently visible customer network context.

## [2.5.7] - 2026-05-03

### Changed

- Raised the current application version to `2.5.7`.
- Changed the dashboard statistics and connection/VPN summary into a global overview that appears only when all customers are shown without customer or tag filtering.
- Moved the connection/VPN summary from the bottom of the page into the global overview area below the statistic cards.
- Hid the global overview when the page is filtered by customer or tags, so single-customer views focus on that customer's VPN guides and server cards.

### Verification

- `npm run test:connection-summary` passed.
- `npm run build` passed.
- `python -m compileall onecrm hermes` passed.

## [2.5.6] - 2026-05-03

### Added

- Added the connection/VPN section implementation plan in `docs/onecrm-2.5-connection-vpn-section.md`.
- Added real connection summary calculation for direct access, VPN-required access, and dedicated-line access from the currently visible organizations.
- Added real VPN guide rows in the connection/VPN section, including organization context, usage count, and request-required status.
- Added real VPN source-file rows in the connection/VPN section, with download buttons backed by archived MinIO file objects.
- Added `GET /api/files/{file_id}/download` to download stored source files by file id.
- Added a frontend unit-style smoke test for connection summary rules.

### Changed

- Raised the current application version to `2.5.6`.
- Removed the hard-coded VPN names, fake file rows, and fixed connection counts from the connection/VPN dashboard section.

### Verification

- `npm run test:connection-summary` passed.
- `npm run build` passed.
- `python -m compileall onecrm hermes` passed.

## [2.5.5] - 2026-05-03

### Added

- Added the 2.5 requirements archive in `docs/onecrm-2.5-requirements.md`.
- Added the UI/UX improvement plan in `docs/onecrm-2.5-ui-ux-improvement-plan.md`.
- Added reusable frontend helpers for OneCRM tags, dashboard statistics, data navigation, and remote action buttons.

### Changed

- Raised the current application version to `2.5.5`.
- Consolidated README into stable operator/deployer guidance and moved detailed requirements and design decisions into `docs/`.
- Documented the version growth policy for continued NewUI branch development.
- Tightened the OneCRM design token layer, compressed the workspace header, tag filter, and statistic cards, and added responsive breakpoints for desktop, 1K, tablet, and phone widths.
- Hid inactive main-navigation entries and kept the customer environment page as the primary maintenance surface.
- Lazy-loaded data and remote admin pages so hidden legacy surfaces no longer sit in the main bundle path.
- Centralized tag color mapping so filter buttons, server tags, VPN tags, database tags, and service tags can share the same visual vocabulary.

### Verification

- `npm run build` passed.
- `python -m compileall onecrm hermes` passed.

## [2.5.4] - 2026-05-03

### Added

- Added source-set rebuild analysis for VPN imports: adding files to an existing VPN guide reprocesses every current source file instead of only the new upload.
- Added source metadata concepts for relative path, client modified time, upload time, source role, date hints, effective dates, and source precedence.
- Added explicit source text separation: `sourceRawText`, `manualRawText`, and `analysisRawText`, while keeping `rawText` as compatibility output.

### Changed

- Updated Hermes/VPN planning so original files remain immutable and cleaning only affects derived text.
- Required filename, folder name, path semantics, file modified time, and content date hints to participate in VPN analysis.
- Required jump hosts, bastion hosts, gateways, relays, and multi-hop remote access to be rendered as ordered workflow steps with credentials bound to the matching hop.

## [2.5.3] - 2026-05-03

### Added

- Added editable server/environment records under each customer so one organization can maintain multiple independent servers with their own names, tags, VPN setting, and service roles.
- Added server/service information blocks for web, app, database, middleware, remote access, and other generic service records.
- Added auxiliary service metadata so items such as Java path/version, Tomcat details, maintenance notes, or jump-host notes can be attached without forcing a fixed schema.
- Added automatic `VPN` tag inheritance when a server enables a VPN guide.
- Added automatic `申请必要` tagging when the selected VPN guide contains request, contact, phone, or email application steps.

### Fixed

- Fixed server creation UX so create dialogs close after success, refresh the selected customer, and avoid duplicate creation caused by repeated clicks.
- Fixed server deletion flow so the server action menu can delete records and refresh the current customer state.
- Fixed empty server cards so they stay compact instead of reserving a large blank detail body.

## [2.5.2] - 2026-05-02

### Added

- Added VPN guide authoring with raw text, AI-generated structured workflow steps, source display, automatic tags, and editable guide content.
- Added asynchronous VPN save/analyze behavior: saving returns quickly and AI analysis runs in the background with frontend status feedback.
- Added email-aware VPN workflow rendering with recipient, CC/BCC, subject, formatted body, copy controls, and mail action support.
- Added compact VPN step cards with sequence numbers, title, full summary, tags, expandable child details, and copy buttons for structured values.
- Added multi-file VPN guide ingestion: users can attach multiple source files when creating or editing a VPN record, while saving returns immediately and parsing continues asynchronously.
- Added a standalone Hermes Agent service for VPN file ingestion, with document parsers, spreadsheet parsers, archive unpacking, OCR, and local extraction before AI workflow analysis.
- Added MinIO hash-based source-file storage for VPN records, with PostgreSQL indexes for file metadata, guide associations, import jobs, progress, warnings, errors, and source references.
- Added upload validation that rejects `.dmp` files on both frontend and backend; ZIP-contained `.dmp` files are skipped with warnings by Hermes.
- Added frontend VPN upload UI, source-file display, and import-job polling so parsed text and workflow cards appear after background analysis completes.

### Changed

- Changed VPN guide analysis to keep useful credentials, URLs, application procedures, and mail templates as structured workflow information instead of flattening them into prose.
- Changed VPN file import from incremental parsing to source-set rebuild analysis planning, later formalized in `2.5.4`.

## [2.5.1] - 2026-05-02

### Added

- Added OneCRM-style customer environment UI refinements based on the reference design: compact data navigator, warm content surface, gold accent, card focus elevation, and three-dot action affordances.
- Added explicit server card expand/collapse controls and removed hover-driven expansion and timed auto-collapse behavior.
- Added RDP file download, RDP direct connection, certificate download, and Guacamole browser connection actions into the new React UI.
- Added remote action loading feedback to reduce repeated clicks while a connection is being prepared.
- Added VPN selector placement on server cards so users can choose whether a server requires VPN and which customer VPN guide it uses.

### Changed

- Changed the main customer environment page to favor dense card grids and compact collapsed cards rather than large blank default panels.
- Changed the top keyword search area to remain hidden until a real full-text search feature exists.
- Changed statistics to business-oriented dimensions: customer count, server count, VPN-managed customers, and current issues.
- Changed left navigation to hide future placeholder modules until they are usable.

### Fixed

- Fixed collapsed navigation alignment for icons, brand mark, and bottom admin controls.
- Fixed several tag/VPN UI refresh cases where backend state changed but the frontend did not immediately update.
- Fixed action icon semantics so direct connection, RDP file download, certificate download, browser open, and copy actions use distinct icon-only buttons.

## [2.5.0] - 2026-05-01

### Added

- Added a React + Vite + TypeScript frontend with Ant Design components and a OneCRM-style enterprise dashboard layout.
- Added a FastAPI backend under `/api/*` while keeping legacy `.jsp` compatibility endpoints for one transition release.
- Added PostgreSQL persistence for organizations, environments, tags, remote connections, audit logs, and file metadata.
- Added first-start migration from `data.csv`, `rdp.csv`, and `tags.json`, including backup copies under `.tmp/migration-backup/`.
- Added encrypted-at-rest storage for password fields using `ONECRM_SECRET_KEY`.
- Added Docker Compose services for application PostgreSQL, Redis, MinIO, and the existing Guacamole stack.
- Added server-side infrastructure defaults for Redis cache and MinIO object storage.
- Added a full 2.5 architecture, migration, Docker, and rollback section to the README.

### Changed

- Renamed the product from EnvPortal to OneCRM.
- Changed the Python server entry from `http.server` to FastAPI/Uvicorn.
- Changed static frontend delivery so FastAPI serves the built React application.
- Changed startup to build the React frontend automatically when Node/npm are available.

### Compatibility

- Legacy environment check, DB probe, RDP generation, RDP direct connect, certificate download, and Guacamole connect endpoints remain available.

## [2.1.27] - 2026-05-01

### Changed

- Clarified remote action icons: RDP file generation now uses a file-download icon, while browser remote control uses the connection icon.

## [2.1.26] - 2026-05-01

### Added

- Added a full-screen loading overlay for remote connection actions to prevent repeated clicks while RDP or Guacamole sessions are being prepared.

## [2.1.25] - 2026-05-01

### Fixed

- Fixed home page summary/detail card sizing so expanded cards use the same grid width as summary cards and wrap long content instead of overflowing.

## [2.1.24] - 2026-05-01

### Changed

- Removed the automatic browser launch after the Python server starts; startup now only prints console URLs and status.

## [2.1.23] - 2026-05-01

### Fixed

- Fixed overlapping expanded environment cards by increasing the home page grid column minimum and constraining card detail flex overflow.

## [2.1.22] - 2026-05-01

### Changed

- Changed expanded home page environment cards to stay in the same responsive grid columns as summaries, allowing multiple expanded cards to sit side by side.

## [2.1.21] - 2026-05-01

### Changed

- Moved the expanded home page environment collapse button into the right side of the card title area.

## [2.1.20] - 2026-05-01

### Added

- Added automatic cleanup for Guacamole per-connection drive session directories.
- Added `GUACAMOLE_DRIVE_RETENTION_HOURS` to control how long shared-drive session files are retained.

## [2.1.19] - 2026-05-01

### Changed

- Moved the home page environment summary expand button to the right-side action area for easier access.

## [2.1.18] - 2026-05-01

### Changed

- Changed Guacamole file transfer drives to use a per-connection session directory instead of one shared `guacamole-drive/` root.
- Added the same isolated drive path to both QuickConnect URI generation and REST-created temporary RDP connections.

## [2.1.17] - 2026-05-01

### Changed

- Reworked the home page organization summary into a wider responsive layout.
- Changed environment expansion from hover/auto-collapse behavior to explicit expand and collapse buttons.
- Changed multi-environment organization summaries to use an in-flow responsive grid so expanded cards stay aligned.

## [2.1.16] - 2026-05-01

### Added

- Added Guacamole RDP file transfer support through an `EnvPortal` virtual drive.
- Added the Docker shared directory `guacamole-drive/` for Guacamole file upload/download exchange.

## [2.1.15] - 2026-05-01

### Added

- Added an nginx HTTPS sidecar for the bundled Guacamole instance on port `8443`.
- Added automatic self-signed Guacamole HTTPS certificate generation in `certs/guacamole.crt` and `certs/guacamole.key`.
- Added firewall handling for both the Guacamole HTTPS public port and backend HTTP port.
- Changed the default Guacamole public URL to HTTPS.

## [2.1.14] - 2026-05-01

### Fixed

- Explicitly enabled Guacamole RDP copy/paste channels for temporary browser remote connections.
- Added Windows clipboard newline normalization for Guacamole RDP sessions.

## [2.1.13] - 2026-05-01

### Fixed

- Ensured Guacamole REST temporary connection creation runs even when QuickConnect throws an exception.
- Added server-side diagnostics for Guacamole token, QuickConnect, and REST connection creation failures.
- Displayed Guacamole fallback messages in the frontend instead of silently opening the Guacamole home page.

## [2.1.12] - 2026-05-01

### Fixed

- Added a Guacamole REST fallback that creates a temporary RDP connection and opens it directly when QuickConnect does not return a usable client identifier.
- Fixed Guacamole fallback behavior that previously logged in successfully but left users on the empty Guacamole home page.

## [2.1.11] - 2026-05-01

### Fixed

- Changed Guacamole auto-login to use Guacamole's frontend-supported username/password route parameters instead of a pre-issued token URL.
- Changed Guacamole QuickConnect fallback URLs to use the EnvPortal auto-login endpoint instead of opening the raw Guacamole login page.

## [2.1.10] - 2026-05-01

### Added

- Added `guacamole_auto_login.jsp` to redirect users into Guacamole with a backend-issued auth token when Guacamole credentials are configured.
- Changed the Guacamole URL exposed to the frontend to use the EnvPortal auto-login endpoint by default.

## [2.1.9] - 2026-05-01

### Fixed

- Replaced the hand-written Guacamole PostgreSQL init SQL with the official schema generated by the Guacamole image.
- Added startup detection for incompatible old Guacamole schemas and automatic recreation of the EnvPortal-managed Guacamole volume.
- Changed Guacamole availability checks to verify API token creation when Guacamole credentials are configured.

## [2.1.8] - 2026-05-01

### Fixed

- Added Docker Desktop's `resources\bin` directory to Docker subprocess PATH so `docker-credential-desktop.exe` can be found after a fresh Docker Desktop install.

## [2.1.7] - 2026-05-01

### Fixed

- Improved Docker Desktop detection after a fresh install by checking standard install locations even when PATH has not been refreshed.
- Added automatic Docker Desktop startup and Docker engine readiness waiting before Guacamole deployment.
- Added clearer startup output when Docker CLI exists but the Docker engine is not ready.

## [2.1.6] - 2026-05-01

### Added

- Added an optional Docker Desktop install prompt through `winget` when Guacamole is enabled but Docker is unavailable on Windows.

### Fixed

- Suppressed noisy traceback output when a browser aborts a request before EnvPortal finishes writing the response.

## [2.1.5] - 2026-05-01

### Fixed

- Changed Guacamole availability from static configuration to a live backend reachability check.
- Hid browser remote-control buttons when Guacamole is configured but not actually reachable on the deployment server.
- Added explicit unavailable responses for Guacamole connection requests.
- Changed Docker Compose port binding to `0.0.0.0:8088:8080`.
- Added optional UAC elevation for Windows Firewall rule creation when EnvPortal is started without Administrator rights.

## [2.1.4] - 2026-05-01

### Added

- Added server-side Guacamole readiness waiting after Docker Compose startup.
- Added automatic Docker Compose diagnostics when Guacamole is not reachable on the deployment server.

## [2.1.3] - 2026-05-01

### Fixed

- Changed Windows Firewall rules to explicitly allow all local and remote addresses for EnvPortal-managed ports.
- Updated existing EnvPortal firewall rules instead of leaving mismatched old rules untouched.
- Clarified that `BIND_ADDRESS=0.0.0.0` and automatic Guacamole public URL detection avoid per-server `.env` changes.

## [2.1.2] - 2026-05-01

### Added

- Added Windows Firewall startup checks for the EnvPortal and Guacamole TCP ports.
- Added elevated PowerShell firewall commands to startup output when EnvPortal is not running as Administrator.
- Added concrete LAN URL output based on detected local IPv4 addresses.
- Added a local Guacamole port reachability check after Docker Compose startup.

## [2.1.1] - 2026-05-01

### Fixed

- Improved Guacamole Docker detection by checking PATH, Docker Desktop's standard Windows install path, and WSL Docker.
- Added WSL Docker Compose startup support for Guacamole when Windows cannot see Docker directly.
- Changed Guacamole public URLs so LAN users are sent to the EnvPortal server address instead of `localhost`.
- Made startup logging clearer when Docker is unavailable and Guacamole is disabled.

## [2.1.0] - 2026-05-01

### Added

- Added Apache Guacamole QuickConnect trial integration for browser-based RDP control.
- Added `GUACAMOLE_URL`, `GUACAMOLE_USERNAME`, and `GUACAMOLE_PASSWORD` configuration.
- Added Docker-based Guacamole auto-start through `docker-compose.guacamole.yml` when Docker is available.
- Added a bundled PostgreSQL initialization script for the Guacamole trial instance.
- Added a browser remote-control button for RDP environments when Guacamole is configured.
- Added fallback behavior that copies the Guacamole QuickConnect URI and opens Guacamole when API credentials are not configured.

## [2.0.2] - 2026-05-01

### Changed

- Changed RDP connection behavior for non-local EnvPortal access. When the portal is opened through a LAN address, EnvPortal now downloads an `.rdp` file and copies the password to the client clipboard instead of trying to launch `mstsc.exe` on the server.
- Kept direct backend `mstsc` launch only for `localhost`, `127.0.0.1`, and `::1` access.

## [2.0.1] - 2026-04-30

### Fixed

- Changed the default Python server bind address to `0.0.0.0` so EnvPortal listens on all network interfaces.
- Updated startup output and README to distinguish local and LAN access URLs.

## [2.0.0] - 2026-04-30

### Added

- Added semantic version tracking through `VERSION`.
- Added Japanese/Chinese i18n resource support with cached language selection.
- Added organization code management and redesigned organization grouping around code + name.
- Added environment-level free tags with cross-organization filtering.
- Added tag library persistence through JSON and automatic tag cleanup when no records use a tag.
- Added automatic system tags for database type/version and remote connection type.
- Added compact organization summaries on the home page with animated inline expansion.
- Added environment health checks with HTTP status, response time, TTL, and OS guess.
- Added minute-based status refresh for visible environment cards.
- Added database host/port/instance fields and DB type/version fields.
- Added database version catalog in `db_versions.json`.
- Added Oracle and PostgreSQL database probe support through the Python backend.
- Added RDP/SSH remote connection type management.
- Added RDP connection launch support through `mstsc`.
- Added RDP password clipboard preparation because `mstsc` may ignore saved credentials under NLA or policy controls.
- Added RDP file generation, DPAPI password field generation on Windows, RDP signing, and downloadable signing certificate.
- Added automatic self-signed certificate creation for EnvPortal RDP signing on Windows.
- Added Linux/macOS startup script `start.sh`.
- Added Python dependency manifest `requirements.txt`.
- Added top header background image support using `images/sea01.jpg`.

### Changed

- Migrated the primary backend from PowerShell to Python while keeping `start.bat`.
- Improved `start.bat` Python detection and installation guidance.
- Improved Ctrl-C/service shutdown behavior by running the Python server directly.
- Renamed visible RDP wording to server/remote connection wording where appropriate.
- Redesigned the home page layout to reduce unused space and show richer environment summaries.
- Redesigned data management into card-based editors with pagination.
- Redesigned remote connection management with the same card-based style.
- Reworked global color tokens and page styling to match the sea-blue theme image.
- Reworked copy buttons into icon-only controls and added URL browse controls.
- Disabled URL/RDP/certificate actions when environment health checks report unavailable status.
- Updated database display from icon-only to visible tag-style database type/version labels.

### Fixed

- Fixed inconsistent tag colors between filter area and cards.
- Fixed organization code visual hierarchy on the home page.
- Fixed tag rows wrapping awkwardly in detail cards.
- Fixed unreachable environments staying in checking state too long.
- Fixed RDP/WebAuthn redirect prompts by disabling local redirection fields in generated RDP files.
- Fixed RDP signing certificate generation when PowerShell module paths include PowerShell 7 modules.
- Fixed stale RDP credentials by deleting old target credentials before writing new ones.

### Notes

- `mstsc` does not provide a supported plaintext password argument. EnvPortal now copies the RDP password to the clipboard before launching the connection as a reliable fallback.
- `data.csv`, `rdp.csv`, and `.env` remain local runtime files and should be handled carefully when publishing.
