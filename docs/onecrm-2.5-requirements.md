# OneCRM 2.5 Requirements

## Product Direction

OneCRM 2.5 upgrades EnvPortal from a small static operations helper into an internal customer environment management portal. The tool is still optimized for operations and implementation staff, but the product language changes from file-based quick lookup to a structured customer, server, VPN, database, and remote-access workspace.

The product name is `OneCRM`. The legacy `EnvPortal` name is kept only in migration notes, older file names, or compatibility explanations.

## Core Users and Jobs

- Operations staff need to quickly find a customer, identify the right server/environment, copy credentials, and connect by RDP, browser remote desktop, or SSH-related information.
- Implementation staff need to maintain customer environments, database information, VPN procedures, application/service hosts, tags, and remote connection metadata.
- Support staff need VPN procedures to be rendered as practical steps, including request emails, contacts, jump hosts, credentials, and source-document traceability.

## Frontend Requirements

- Use React, Vite, TypeScript, and Ant Design v5.
- Use the OneCRM design language: deep navy navigation, gold accent, warm light workspace, rounded but restrained panels, and dense operational cards.
- The customer environment page is the primary workspace. Data management and remote-connection management are hidden from the main navigation until they become full product surfaces.
- The main navigation must only expose usable entries. Inactive future modules must not look clickable.
- The right-side data navigator is the customer navigation surface. It contains customer search, customer code, customer name, and all-customer selection.
- Language is global, not page-scoped. Default language is Japanese; Chinese is used only when the user explicitly selects it. The selection is cached per browser user.
- Tags are visual buttons/chips, not dropdown-only filters. Tag colors must be consistent between filter area, server cards, VPN guide tags, database auto tags, and source-role tags.
- Server/environment cards default to collapsed state. Users explicitly expand/collapse each card. Hover-driven expansion and auto-collapse are not used.
- Each server card has a three-dot action menu. Editing and deletion are launched from that menu.
- Empty server cards must stay compact. No large blank body should be reserved for missing app/database/service data.
- VPN workflow cards render structured steps. Email steps render as email UI with recipients, CC/BCC, subject, formatted body, copy buttons, and mailto/default mail action when recipients exist.
- A server referencing a VPN guide must not duplicate the full workflow inside the server card. Server cards show only a compact guide reference; the complete workflow appears once in the customer-level VPN guide area.

## Backend and Platform Requirements

- Use FastAPI as the primary backend under `/api/*`.
- Keep stable legacy capabilities through adapters during the 2.5 transition: environment check, DB probe, RDP file generation, RDP direct connect, certificate download, Guacamole connection, and selected legacy `.jsp` endpoints.
- PostgreSQL is the source of truth after first startup.
- Redis is backend-only cache infrastructure, not a browser cache.
- MinIO stores binary objects such as certificates, VPN source files, configuration packages, imports, and exports.
- Docker Compose provides PostgreSQL, Redis, MinIO, Hermes, and Guacamole-related services. When Docker is unavailable, core text/manual maintenance should still work where possible, but file parsing and Guacamole may be disabled.
- `start.bat` and `start.sh` remain one-command launchers. Server startup prints status and URLs but does not automatically open a browser.
- Windows startup checks or creates firewall rules for the OneCRM web port and Guacamole port when permissions allow.

## Data Requirements

- Organizations have a stable customer/organization code and name.
- Servers/environments belong to organizations and have independent tags.
- Tags are free grouping attributes and may cross organization boundaries. Tags can be manual, migration-derived, or automatic.
- Automatic tags include VPN, request-required VPN, database type/version, remote connection type, and other future system-derived attributes.
- Database fields include host, port, instance/database, username, password, type, and version. Oracle and PostgreSQL are the initial probe targets.
- Servers may have optional app/system access, optional database information, optional remote connections, and multiple app/service records.
- App/service records are generic. They may represent Apache, Tomcat, Nginx, MinIO, Nacos, AP servers, WEB servers, or other service roles. They support auxiliary key/value information such as Java path/version.
- Password and secret fields are user-friendly for copy/display but are encrypted at rest using the application secret key.

## Remote Connection Requirements

- RDP and SSH are remote connection types, but the product language should be server/remote connection rather than RDP-only.
- RDP supports direct connect on trusted local/server contexts when the browser/server environment allows it.
- When direct local execution is not possible, OneCRM falls back to signed `.rdp` file download and copies the password to the clipboard.
- RDP file and certificate actions are disabled when the target server is unavailable or remote information is incomplete.
- Apache Guacamole integration is preserved. If available, OneCRM can create/open browser remote desktop sessions.
- Guacamole drive sharing must isolate per-connection session directories to avoid mixing user files.

## VPN and Hermes Requirements

- Customers may have one or more VPN guides.
- Servers can choose whether VPN is required and which VPN guide applies.
- Enabling a VPN guide adds an automatic `VPN` tag to the server.
- If the selected VPN workflow contains application/request/contact/mail/phone approval requirements, the server inherits the automatic `申请必要` tag.
- VPN guide saving must not block on AI or file parsing. Save returns quickly, then the guide enters parsing/analyzing status.
- Existing VPN guides must support explicit reanalysis without requiring users to edit text or re-upload files. Reanalysis reruns workflow AI against current saved analysis text; it does not reparse archived files.
- VPN source files are stored in MinIO by SHA-256 and associated with the guide in PostgreSQL.
- `.dmp` uploads are rejected; `.dmp` files inside ZIP archives are skipped with warnings.
- Adding more files to an existing VPN guide triggers source-set rebuild analysis, not incremental-only analysis.
- Reanalysis of a file-backed guide reuses the current derived text. Full source-file rebuild happens only when uploading or adding source files.
- Original files are read-only source archives. Cleaning and AI preparation only modify derived text.
- Hermes parses files into `sourceRawText` and `sourceMeta`, preserving filename, recursive relative path, client modified time, uploaded time, source role, date hints, and source fragments.
- The backend combines `sourceRawText` and `manualRawText`, cleans irrelevant context, and stores `analysisRawText` for AI workflow analysis.
- AI must use source precedence, file/folder date semantics, content date hints, and source role to decide current effective procedure.
- Jump hosts, bastion hosts, gateways, proxies, relay servers, `踏み台`, `経由`, and `中継` must be split into ordered connection steps, with credentials attached to the matching host/hop.
- VPN guide references and source references are traceability metadata. They must not cause repeated workflow rendering or encourage read-only users to download raw source files when structured AI output is available.

## i18n Requirements

- Only Japanese and Chinese are supported initially.
- Japanese is the default when no language is cached.
- Chinese is shown only after explicit selection.
- The selection is stored in frontend local storage and is user/browser specific.
- No Traditional Chinese filler copy should be used to pad missing translations.

## Current 2.5 Improvement Backlog

## User Authentication and Permissions

2.5.9 introduces local OneCRM accounts stored in PostgreSQL. The system creates the first `Admin` account from `AUTH_PASSWORD` when no users exist. Passwords must be PBKDF2 hashes; reset tokens and session tokens are stored only as hashes.

- Roles are fixed to `Admins` and `Users`.
- Admins can maintain all users and all business data.
- Users can read, copy, download, and connect, but cannot modify business records.
- Users can update their own password and avatar.
- Login, logout, forgot-password, reset-password, profile, and user maintenance must follow the OneCRM visual language.
- System functions are exposed from the top-bar gear menu, not the CRM business navigation.
- Password reset mail is sent by SMTP configured through `ONECRM_SMTP_*`; the virtual mail viewer at `http://192.168.20.38:5000/` is used for testing.

## VPN AI Source and Credential Presentation

- AI source files are operator inputs and audit references, not normal end-user downloads. The connection/VPN overview should show source counts and parsed status, not raw-file download actions.
- VPN workflow analysis must preserve credential association. When source material lists multiple servers, hosts, jump hosts, usernames, passwords, ports, or protocols, the result must group them by exact server/hop instead of rendering detached lists of usernames and passwords.
- The UI should render grouped credentials as compact server credential cards with copy buttons for each value.

- Finish UI/UX design-language consolidation: token system, navigation cleanup, compact header, consistent tags, responsive breakpoints.
- Split the large environment page into smaller feature components without changing behavior.
- Keep README focused on deployment/usage and move deeper product/technical rationale into docs.
- Add browser screenshot verification once Browser/IAB tooling is available in the current environment.
