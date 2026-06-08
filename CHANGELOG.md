# Changelog

All notable changes to EnvPortal are documented here.

## [2.4.6] - 2026-06-08

### Fixed

- Fixed expanded environment card edit buttons failing because inline context lookup referenced a removed organization helper.

## [2.4.5] - 2026-06-08

### Fixed

- Kept TAG-filtered environment results in collapsed summary mode instead of expanding every matching environment automatically.

## [2.4.4] - 2026-06-07

### Changed

- Added up and down controls on environment group containers so administrators can adjust group display order per organization.
- Restricted environment group add, edit, delete, ordering, and environment group reassignment actions to system management permission.

## [2.4.3] - 2026-06-07

### Fixed

- Aligned the first row of organization summary group containers by removing sibling top margin from grid items.

## [2.4.2] - 2026-06-07

### Changed

- Limited expanded environment cards inside a group to two columns on desktop and one column on narrow screens.
- Moved environment group reassignment from the edit form into a dedicated group-move icon button and modal.

## [2.4.1] - 2026-06-07

### Changed

- Added a visible group-add button beside the organization edit button in organization summary and detail headers.

## [2.4.0] - 2026-06-07

### Changed

- Rendered environment groups as containers inside collapsed organization summaries so read-only users can see group context without expanding individual environments.
- Re-evaluated the environment group feature as the `2.4.0` MINOR release because it adds a compatible three-level hierarchy and runtime sidecar data file.

## [2.3.23] - 2026-06-07

### Changed

- Clarified that environments with an empty `環境グループ` appear in `デフォルト`, while explicit empty groups are maintained in `env_groups.json`.
- Allowed administrators to delete empty environment groups as long as the organization still has at least one group.
- Stopped forcing `デフォルト` back into `env_groups.json` when it has no environments and has been removed from an organization with other groups.

## [2.3.22] - 2026-06-07

### Added

- Added `env_groups.json` as a local runtime file for empty environment groups and explicit organization group order.
- Added maintainable `組織 → 環境グループ → 環境` hierarchy behavior with automatic `デフォルト` groups.
- Added group selection when creating or editing environments, with empty historical `環境グループ` values normalized to `デフォルト`.

### Changed

- Changed organization-level add action to create an empty environment group instead of creating an environment row.
- Changed group rendering so empty groups remain visible and can receive new environments.
- Changed portal bundle saves to include `env_groups.json` and protect it from direct static access.

### Fixed

- Fixed `read_tags_json()` returning `None` when `tags.json` existed after the environment group helper insertion.

## [2.3.21] - 2026-06-07

### Changed

- Changed the production page organization selector to use the same kana tab interaction as the environment search page.
- Removed the production page's older collapsible kana group selector state.

## [2.3.20] - 2026-06-07

### Changed

- Made `portal_config.jsp` return immediately by refreshing Guacamole availability in a background thread.
- Cached derived frontend data for row tags, card skins, organization groups, and RDP endpoint lookups.
- Deferred organization and TAG filter panel rendering until after the first summary view is rendered.

## [2.3.19] - 2026-06-06

### Fixed

- Added a cancel icon button to the environment card edit toolbar.
- Preserved expanded-card context while refreshing cards for edit, cancel, and save flows.

## [2.3.18] - 2026-06-06

### Fixed

- Fixed the expanded-card collapse button size by placing it inside the same action button group as edit and copy.
- Added a higher-priority collapse button size rule and standard SVG attributes for consistent icon rendering.

## [2.3.17] - 2026-06-06

### Fixed

- Fixed the expanded environment card collapse button rendering as a blank button.
- Stabilized collapse handling by routing toolbar clicks through a dedicated button handler with explicit card context.

## [2.3.16] - 2026-06-06

### Changed

- Rendered the expanded environment card collapse button directly inside the card action toolbar.
- Removed the legacy post-render collapse button append path so expanded and collapsed cards use the same button row model.

## [2.3.15] - 2026-06-06

### Changed

- Moved environment card status badges into the title row.
- Kept the action button group top-aligned so edit, copy, and collapse controls stay on one row.

## [2.3.14] - 2026-06-06

### Changed

- Applied the active TAG skin color scheme to matching TAG filter buttons.

## [2.3.13] - 2026-06-06

### Changed

- Removed applied skin labels from environment cards while keeping the color rendering itself.

## [2.3.12] - 2026-06-06

### Changed

- Changed the organization selector panel to start expanded on page load.

## [2.3.11] - 2026-06-06

### Fixed

- Stopped auto-generating no-hyphen UPDS alias TAGs such as `UPDSV7` when the canonical `UPDS-V7` TAG is already available.

## [2.3.10] - 2026-06-06

### Changed

- Consolidated environment card actions into a single icon button group.
- Moved card status badges into a separate status row so they no longer share a row with action buttons.
- Changed copy, delete, expand, and collapse actions to icon-only buttons for a consistent card toolbar.

## [2.3.9] - 2026-06-06

### Changed

- Applied TAG skin rendering to collapsed environment summary cards so color coding supports quick scanning before expansion.
- Added the applied skin marker to collapsed environment summary cards.

## [2.3.8] - 2026-06-06

### Added

- Added `activeSkinCategory` to TAG category settings so the system has one explicit TAG category used for card skin rendering.
- Added a TAG display settings control to set the current category as the system rendering category.

### Changed

- Changed environment card skin rendering to use only the configured system rendering category instead of scanning all categories by order.
- Clarified TAG display settings by showing both the system rendering category and the category currently being edited.

## [2.3.7] - 2026-06-06

### Changed

- Added color picker controls to TAG display settings while keeping optional hex text fields for clearing unset skins.

## [2.3.6] - 2026-06-06

### Changed

- Clarified the TAG display settings page so the current category marker explains that category tabs switch the editable skin group.
- Changed the applied skin marker on environment cards into a direct link to TAG display settings.

## [2.3.5] - 2026-06-06

### Changed

- Added an explicit current TAG skin category marker on the TAG display settings page.
- Added an applied skin marker on skinned environment cards, showing the active category and TAG.

## [2.3.4] - 2026-06-06

### Changed

- Changed TAG display settings to switch by TAG category tabs instead of per-TAG enable switches.
- Changed TAG skin saving so the current category is updated without clearing other category skin settings.
- Changed automatic TAG derivation to include environment group and product-system tokens such as UHR, PHR, UPDSV6, and UPDSV7.
- Strengthened environment card skin rendering with visible light background, border, and accent line.

## [2.3.3] - 2026-06-06

### Added

- Added TAG display settings under the system management menu.
- Added category-scoped TAG panel skins in `tag_categories.json` through `skins[categoryId][tag]`.
- Added default light panel skins for UHR, PHR, UPDS-V6, and UPDS-V7 related tags.

### Changed

- Changed environment cards to apply the first matching TAG skin by current TAG category order.
- Changed TAG skin normalization so incomplete color definitions are ignored.

## [2.3.2] - 2026-06-06

### Changed

- Changed the organization selector to use top kana tabs instead of nested kana expanders.
- Changed the organization selector panel to start collapsed to reduce initial screen space usage.

## [2.3.1] - 2026-06-06

### Changed

- Changed Japanese UI wording to prefer natural katakana or Japanese expressions where established, such as `タグ`, `バージョン`, `プラットフォーム`, and `サーバー`.
- Kept protocol and technical abbreviations such as URL, DB, RDP, SSH, VPN, AD, HTTP, TTL, and OS where they are customary.
- Added the Japanese terminology rule to the system design document.

## [2.3.0] - 2026-06-06

### Versioning

- Reclassified the current application state from the long `2.2.x` patch sequence to `2.3.0`.
- The `2.2.16` through `2.2.31` entries are kept below as detailed implementation snapshots that led into this minor release.
- Chose a MINOR release because the changes add compatible system management, authentication, role permission, TAG permission, i18n, and performance capabilities without requiring CSV data migration.

### Added

- Added top-right system management with user management, role management, and TAG category management.
- Added role functional permissions for environment query, environment edit, production query, production edit, and system management.
- Added role data permissions through `dataTags`, using current manual and automatic TAGs as the effective data visibility scope.
- Added managed TAG categories through `tag_categories.json`, including a fixed `other` category and category assignment normalization.
- Added domain proxy token flow so an EnvPortal server outside the AD domain can authorize users by their Windows domain identity.
- Added cached domain auth tokens to reduce repeated Windows authentication latency across pages.

### Changed

- Changed client IP from an authorization identity to audit and display metadata only.
- Changed portal data loading so public summary data renders first, then authorized data refreshes after domain token availability.
- Changed TAG filtering to use managed category assignments instead of hard-coded frontend grouping.
- Changed role management layout so each role renders functional permissions on the first row and data permission TAG selectors on a second row.
- Changed local deployment data handling so `roles.json` and `tag_categories.json` stay outside Git.

### Fixed

- Fixed i18n gaps across visible buttons, modal actions, role management, TAG management, and fallback labels.
- Fixed management menu display timing and stacking so authorized administrators see it reliably.
- Fixed production page script placement that previously rendered JavaScript text into the page.

## [2.2.31] - 2026-06-05

### Fixed

- Changed role management layout so data permission TAG selectors render on a second row for each role.
- Reduced role management table width to avoid horizontal scrolling caused by TAG selectors.

## [2.2.30] - 2026-06-05

### Fixed

- Added local `roles.json` to `.gitignore` because role master data is a deployment site data file.

## [2.2.29] - 2026-06-05

### Added

- Added role data permissions based on a configurable `dataTags` list.
- Added data permission TAG assignment checkboxes to role management.

### Changed

- Changed portal data filtering to intersect role `dataTags` with currently existing manual and automatic TAGs.
- Kept legacy `filterTag` compatibility while using `dataTags` as the effective role data permission model.

## [2.2.28] - 2026-06-05

### Added

- Added explicit TAG category management under the system management menu.
- Added `tag_categories.json` normalization so deleted categories move their TAGs to the fixed `other` category.

### Changed

- Changed home page TAG filters to use managed category assignments instead of automatic frontend grouping rules.

## [2.2.27] - 2026-06-05

### Added

- Added configurable role permissions for environment query, environment edit, production query, production edit, and system management in the role management UI.
- Instantiated role permissions in `roles.json` instead of relying on a single hard-coded edit flag for query behavior.

## [2.2.26] - 2026-06-05

### Fixed

- Localized the shared add action text instead of leaving the i18n resource value as `ADD`.

## [2.2.25] - 2026-06-05

### Changed

- Resourceized remaining visible page literals for buttons, placeholders, tag group labels, editor section titles, default names, and fallback role labels.

## [2.2.24] - 2026-06-05

### Fixed

- Showed the current user and system management menu immediately from a valid cached domain token, while background authentication refreshes the profile.

## [2.2.23] - 2026-06-05

### Fixed

- Improved home page perceived load time by rendering public summary data immediately, then refreshing with full authorized data after the domain token is available.

## [2.2.22] - 2026-06-05

### Fixed

- Cached the short-lived domain auth token across pages until expiry so management screens do not wait for Windows authentication again after the first successful probe.

## [2.2.21] - 2026-06-05

### Fixed

- Reduced refresh latency by using the domain proxy only to obtain a short-lived domain auth token, then calling protected EnvPortal APIs directly with that token.
- Restored direct calls for connectivity checks and organization reading sync because those endpoints do not require domain identity.

## [2.2.20] - 2026-06-05

### Fixed

- Moved the system management menu into the main navigation bar and raised its stacking layer so the dropdown appears above the page chrome.

## [2.2.19] - 2026-06-05

### Changed

- Removed IP whitelist authentication as an identity source because NAT can hide the real client user.
- Accepted trusted domain proxy Windows users directly and left authorization to user roles in `users.json`.
- Routed permission-controlled frontend requests through the configured domain proxy when automatic probing is enabled.
- Kept client IP as audit metadata only, not as an access-control identity.

## [2.2.18] - 2026-06-05

### Fixed

- Placed the system management menu inside the top-right metadata row so admin users can see it reliably.
- Prevented IP-only profiles from clearing an already detected domain user name in the header.

## [2.2.17] - 2026-06-05

### Fixed

- Added a versioned `i18n.js` script URL so browsers do not keep an older script without the system management menu.
- Changed the top-right metadata from client IP display to current user display, hiding IP-only identities.

## [2.2.16] - 2026-06-05

### Added

- Added role management as a separate CRUD screen backed by `roles.json`.
- Moved user management and role management into the top-right system management menu, visible only to the `admin` role.

### Changed

- User role selections now use role master data instead of hard-coded frontend options.
- User and role update endpoints now require user management permission.

## [2.2.15] - 2026-06-05

### Fixed

- Aligned the organization list title row and edit action button in the search page so the text and icon button sit centered on the same header line.

## [2.2.14] - 2026-06-05

### Added

- Added deletion for unnecessary users from the user management page.

## [2.2.13] - 2026-06-05

### Fixed

- Moved the production page portal config loader back inside the script block so JavaScript is not rendered as visible page text and production data can load normally.

## [2.2.12] - 2026-06-05

### Fixed

- Forced UTF-8 output for domain proxy PowerShell AD lookups so non-ASCII display names are forwarded without replacement characters.

## [2.2.11] - 2026-06-05

### Fixed

- Changed domain proxy AD attribute lookup to use Windows PowerShell ADSI with short lived caching after .NET directory service APIs were unavailable in the service runtime.

## [2.2.10] - 2026-06-05

### Fixed

- Changed domain proxy AD attribute lookup from ADSI based APIs to LDAP protocol queries so display name, email, department, and title can be read in the .NET Windows service runtime.

## [2.2.9] - 2026-06-05

### Changed

- Disabled automatic cross-origin domain proxy probing by default to prevent browser Windows credential prompts on 20.38 page refresh.
- Added `DOMAIN_AUTH_AUTO_PROBE=true` as the explicit opt-in for automatic domain proxy probing after browser integrated authentication is configured.

## [2.2.8] - 2026-06-05

### Fixed

- Replaced the domain proxy AD attribute lookup with LDAP search so display name, email, department, and title can be read on Windows service runtime.

## [2.2.7] - 2026-06-05

### Fixed

- Encoded forwarded AD attributes so non-ASCII display names can pass through proxy headers safely.

## [2.2.6] - 2026-06-05

### Added

- Added AD attribute lookup in the domain proxy for display name, email, department, and title.
- Stored forwarded AD user metadata in EnvPortal user profiles.

## [2.2.5] - 2026-06-05

### Added

- Added optional cross-origin domain-auth lookup so pages opened directly from 20.38 can query the domain proxy for the current Windows user.
- Added CORS support to the domain proxy for trusted EnvPortal origins.

## [2.2.4] - 2026-06-05

### Changed

- Display users in user management as `user（lastIp）`.
- Store `firstIp` and `lastIp` for domain/local user visits without using IP as a persisted user identity.
- Preserve user IP metadata when saving role and display name changes.

## [2.2.3] - 2026-06-04

### Added

- Added organization, environment group, and environment level editing in the environment search screen.
- Added backend default organization readings and frontend refresh through `org_readings_status.jsp`.

### Changed

- Localized the remaining hierarchy editing, production add, and user management UI text through shared i18n resources.
- Updated README and changelog documentation to reflect the current role, local data, hierarchy editing, reading sync, and bundled save behavior.
- Split environment search editing into organization, environment group, and environment levels.
- Moved organization add actions out of the left organization selector and into the main hierarchy area.
- Limited environment card editing to environment-owned fields while organization and group edits update matching rows in bulk.

### Fixed

- Fixed blank edit icon buttons in organization and group headers.
- Restored organization kana grouping when local `org_readings.js` does not exist.

## [2.2.2] - 2026-06-04

### Fixed

- Stopped tracking `.env` so deployed server-specific runtime configuration no longer blocks Git updates.

## [2.2.1] - 2026-06-04

### Fixed

- Stopped tracking runtime data and generated deployment files that can block automatic Git updates on deployed servers.

## [2.1.34] - 2026-06-03

### Added

- Added a Windows Integrated Authentication reverse proxy for domain-joined intermediary hosts.
- Added `TRUSTED_AUTH_PROXY_IPS` support so EnvPortal can limit trusted auth headers to known proxy sources.
- Added an elevated installer script for registering the domain proxy as an automatic Windows service.

## [2.1.33] - 2026-06-02

### Fixed

- Changed the Japanese client IP label from English to localized Japanese text.

## [2.1.32] - 2026-06-02

### Added

- Added client IP display before the application version in the shared header.
- Added `client_info.jsp` as a lightweight endpoint for current request client metadata.

## [2.1.28] - 2026-05-19

### Changed

- Restyled the legacy `index.html`, `admin.html`, and `rdp.html` pages with a restrained Base UI inspired visual language.
- Changed tag chips and tag filters to use soft translucent category colors instead of monochrome chips or dark selected states.
- Added the application version display to the header.

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
