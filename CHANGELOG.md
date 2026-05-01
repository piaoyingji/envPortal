# Changelog

All notable changes to EnvPortal are documented here.

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
