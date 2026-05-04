# OneCRM

OneCRM 是一个面向运维和实施人员的客户环境管理门户，用来集中维护客户/机构、环境地址、登录信息、数据库信息、远程连接信息、VPN/连接方式和自由标签。

当前版本：`2.5.15`

> 2.5 版本完成了从 EnvPortal 到 OneCRM 的产品升级：前端切换为 React + Ant Design，后端切换为 FastAPI，数据持久化切换为 PostgreSQL，并引入 Redis 与 MinIO 作为平台基础设施。

## 详细文档

- [2.5 产品需求总文档](docs/onecrm-2.5-requirements.md)
- [2.5 实施与迁移说明](docs/onecrm-2.5-implementation.md)
- [2.5 UI/UX 改进计划](docs/onecrm-2.5-ui-ux-improvement-plan.md)

README 只保留部署和日常使用需要的稳定说明；需求、设计决策和后续优化计划统一记录在 `docs/`。

## 核心能力

- 机构/客户按“编码 + 名称”管理，并提供客户主档入口维护客户编码和名称。
- 每个服务器/环境支持独立标签，标签可以跨机构自由过滤，例如 `DEMO`、`教育`、`社内`。
- 标签过滤支持多选 AND 条件，并包含系统自动生成标签，例如数据库类型、数据库版本、RDP/SSH。
- 首页按机构显示紧凑摘要，环境卡片通过显式展开/收回按钮查看详情，减少默认页面空白。
- 首页环境摘要使用流式网格布局，适配多服务器机构。
- 环境健康检查会返回 HTTP 状态、响应时间、TTL 和 OS 推测，并按分钟刷新。
- 数据库信息支持地址、端口、实例/库、用户、密码、类型、版本字段。
- 数据库类型和版本支持自动探测，当前支持 Oracle 与 PostgreSQL。
- 远程连接信息支持 RDP/SSH 类型，RDP 可一键启动 mstsc，并自动把密码复制到剪贴板。
- RDP 文件可生成并签名；工具会自动创建 EnvPortal 自签名证书，也提供证书下载。
- 全站 i18n 多语资源化，默认日文，支持中文，并记住上次选择语言。
- 顶部主题区使用 `images/sea01.jpg` 作为虚化海水背景，整体配色统一为蓝青色调。
- 数据存储使用 PostgreSQL。首次启动时会自动读取旧版 `data.csv`、`rdp.csv`、`tags.json`，迁移到数据库并在 `.tmp/migration-backup/` 下保留备份。
- 后端使用 FastAPI，保留 `start.bat`，并提供 `start.sh`，为 Linux 部署做准备。
- 前端使用 React + Vite + TypeScript + Ant Design，统一为 OneCRM 企业管理系统风格。
- Redis 用于服务端缓存健康检查、探测结果、Guacamole 会话和短期接口结果。
- MinIO 用于证书、配置包、导入导出文件等对象存储。
- Windows 启动时会检查并尝试开放 EnvPortal 与 Guacamole 的入站端口。

## 启动方式

Windows:

```bat
start.bat
```

Linux / macOS:

```sh
./start.sh
```

默认读取 `.env`：

```env
PORT=8999
BIND_ADDRESS=0.0.0.0
AUTH_PASSWORD=...
ONECRM_DATABASE_URL=postgresql://onecrm:onecrm_pass@127.0.0.1:15432/onecrm
ONECRM_REDIS_URL=redis://127.0.0.1:16379/0
ONECRM_MINIO_ENDPOINT=127.0.0.1:19000
ONECRM_MINIO_ACCESS_KEY=onecrm
ONECRM_MINIO_SECRET_KEY=onecrm_minio_pass
ONECRM_SECRET_KEY=change-me
ONECRM_PUBLIC_URL=http://<server>:8999
ONECRM_MAIL_MODE=smtp
ONECRM_SMTP_HOST=192.168.20.38
ONECRM_SMTP_PORT=25
ONECRM_SMTP_USERNAME=
ONECRM_SMTP_PASSWORD=
ONECRM_SMTP_FROM=onecrm@example.local
GUACAMOLE_URL=
GUACAMOLE_PUBLIC_URL=
GUACAMOLE_USERNAME=
GUACAMOLE_PASSWORD=
```

访问地址：

```text
http://localhost:8999
```

`BIND_ADDRESS=0.0.0.0` 时会监听所有网卡，局域网内可使用本机 IP 访问。

Windows 下启动器会为 EnvPortal 端口和 Guacamole 端口检查入站防火墙规则。默认端口为 `8999` 和 `8088`，规则会开放所有本地地址和远程地址。由于默认 `BIND_ADDRESS=0.0.0.0`，换服务器时通常不需要修改 `.env`。如果当前终端不是管理员权限，启动不会失败，但会打印需要在管理员 PowerShell 中执行的 `New-NetFirewallRule` 命令。

## 2.5 架构说明

- `frontend/`：React + Vite 前端工程，构建产物由 FastAPI 静态托管。
- `onecrm/`：FastAPI 应用、数据库迁移、加密和 API。
- `legacy_server.py`：保留 2.1 系列中已经稳定的环境检查、数据库探测、RDP、Guacamole 工具函数。
- `server.py`：新的 ASGI 启动入口。
- `docker-compose.yml`：OneCRM 平台 compose，包含 PostgreSQL、Redis、MinIO 和 Guacamole。

## 用户、权限与登录

2.5.9 起，OneCRM 使用 PostgreSQL 保存用户资料和会话。首次启动时，如果 `users` 表为空，系统会自动创建 `Admin` 用户，初始密码沿用 `AUTH_PASSWORD`。密码使用 PBKDF2 哈希保存，不保存明文。

- `Admins`：可以维护全部业务数据和全部用户。
- `Users`：可以查看、复制、下载、远程连接，但不能新增、编辑、删除、上传或保存业务数据。
- 用户可以修改自己的密码和头像。
- 顶部齿轮是系统功能菜单，不属于 CRM 业务导航。

忘记密码功能通过 SMTP 发送重置链接。测试环境可把 SMTP 指向 `192.168.20.38:25`，然后在 [虚拟邮件服务](http://192.168.20.38:5000/) 查看邮件。

启动时执行顺序：

1. 安装 `requirements.txt`。
2. 检查并开放 Web / Guacamole 端口。
3. 检测 Docker；可用时启动 PostgreSQL、Redis、MinIO、Guacamole。
4. 检测 `frontend/node_modules`，必要时执行 `npm install`。
5. 执行 `npm run build`，由 FastAPI 托管构建结果。
6. 启动 FastAPI 服务。

## 数据迁移与回滚

首次启动时，如果 PostgreSQL 中尚无组织/环境数据，系统会自动迁移：

- `data.csv` → `organizations`、`environments`、自动数据库标签。
- `rdp.csv` → `remote_connections`。
- `tags.json` → `tags`、`environment_tags`。

旧文件不会被删除。迁移前会复制到：

```text
.tmp/migration-backup/
```

如果需要回滚到 2.1 系列，可停止服务，切回旧分支/版本，并继续使用原 CSV/JSON 文件。

## Docker 服务

`docker-compose.yml` 默认启动：

- `onecrm-postgres`：应用数据库，默认只绑定 `127.0.0.1:15432`，避免和本机已有 PostgreSQL 冲突。
- `onecrm-redis`：服务端缓存，默认只绑定 `127.0.0.1:16379`。
- `onecrm-minio`：对象存储，默认只绑定 `127.0.0.1:19000/19001`。
- `onecrm-hermes`：VPN 资料解析 Agent，默认只绑定 `127.0.0.1:19100`，供本机 FastAPI 调用。
- `guacamole` / `guacd` / `guacamole-db` / `guacamole-https`：浏览器远程桌面。

Web 端口和 Guacamole 端口面向内网开放；PostgreSQL、Redis、MinIO、Hermes 默认不对局域网暴露。

## VPN 记录多文件解析

VPN 记录支持多文件和文件夹递归导入。原始文件按 SHA-256 去重后归档到 MinIO，后台由 Hermes Agent 解析并重建 `sourceRawText`，再和用户手工维护的 `manualRawText` 合并为 `analysisRawText`，自动触发 VPN 流程 AI 分析。

上传保存不会等待 AI 分析完成。界面会显示解析中/分析中状态，完成后刷新流程卡片、邮件模板、来源文件和自动标签。

默认拒绝 `*.dmp` 文件；其他原始资料长期保留用于审计和溯源。补充文件时系统会重新分析当前 VPN guide 关联的全部来源文件，而不是只解析新增文件。详细规则见 [2.5 实施与迁移说明](docs/onecrm-2.5-implementation.md)。

相关环境变量：`ONECRM_HERMES_URL`、`ONECRM_HERMES_TIMEOUT_SECONDS`、`ONECRM_UPLOAD_REJECT_EXTENSIONS`、`ONECRM_UPLOAD_MAX_FILE_MB`、`ONECRM_UPLOAD_MAX_JOB_MB`。

## 文件说明

- `frontend/`：React 前端。
- `onecrm/`：FastAPI 后端。
- `hermes/`：VPN 多文件解析 Agent。
- `legacy_server.py`：旧版运维工具函数兼容层。
- `server.py`：FastAPI 启动入口。
- `run.py`：启动入口。
- `db_versions.json`：数据库类型和版本候选。
- `tags.json`、`data.csv`、`rdp.csv`：旧版迁移输入和回滚数据。
- `images/sea01.jpg`：顶部主题背景图。

## 版本规则

本项目从 `2.0.0` 开始使用语义化版本号：

- `MAJOR`：数据结构、运行方式或主要交互发生不兼容变化。
- `MINOR`：新增功能但保持兼容。
- `PATCH`：修复问题、微调样式或文案。

每次升级都应同步更新：

- `VERSION`
- `CHANGELOG.md`
- `README.md` 中的当前版本和功能说明

## RDP 自动登录说明

Windows 自带 `mstsc` 没有官方密码参数。EnvPortal 会尝试写入 Windows Credential Manager，并启动 `mstsc`；但在部分 Windows / NLA / CredSSP / 组策略环境中，保存凭据可能仍被忽略。

因此当前 RDP 连接按钮会同时把密码复制到剪贴板。若 Windows 弹出密码输入框，直接粘贴即可。

当 EnvPortal 不是从本机 `localhost` 访问，而是通过例如 `http://192.168.20.38:8999` 访问时，网页不能直接启动访问者电脑上的 `mstsc.exe`。这种情况下，RDP 按钮会自动下载 `.rdp` 文件，并把密码复制到访问者电脑的剪贴板。

## Guacamole 网页远程桌面

EnvPortal 支持 Apache Guacamole QuickConnect 试集成。配置 `.env`：

```env
GUACAMOLE_URL=http://192.168.20.38:8080/guacamole
GUACAMOLE_PUBLIC_URL=
GUACAMOLE_USERNAME=guacadmin
GUACAMOLE_PASSWORD=...
```

配置后，RDP 环境会出现“浏览器远程控制”按钮。行为如下：

- 配置了 Guacamole 用户名/密码时，EnvPortal 会尝试调用 Guacamole QuickConnect API 并直接打开浏览器远程桌面。
- 未配置用户名/密码时，EnvPortal 会复制 `rdp://...` QuickConnect URI 并打开 Guacamole 首页，用户可粘贴到 QuickConnect 输入框。

Guacamole 侧需要安装并启用 QuickConnect extension。

如果本机有 Docker（包括 Windows 11 WSL / Docker Desktop 提供的 `docker` 命令），EnvPortal 可自动启动内置 Guacamole 试用实例：

```env
GUACAMOLE_AUTO_START=true
GUACAMOLE_URL=http://localhost:8088/guacamole
GUACAMOLE_USERNAME=guacadmin
GUACAMOLE_PASSWORD=guacadmin
```

`GUACAMOLE_URL` 是 EnvPortal 后端访问 Guacamole API 用的地址，可以保留 `localhost`，换服务器时通常不用改。用户从局域网访问 EnvPortal 时，系统会自动把前端打开的 Guacamole 地址换成 EnvPortal 服务器的主机名。需要固定公网或反向代理地址时，才设置 `GUACAMOLE_PUBLIC_URL`。

启动时会执行：

```sh
docker compose -f docker-compose.guacamole.yml up -d
```

如果未检测到 Docker，EnvPortal 不会报错，只是不显示浏览器远程控制能力，仍保留 RDP 文件下载和密码复制。启动器会依次检查 Windows PATH、Docker Desktop 标准安装目录以及 WSL 内的 Docker。

Windows 下未检测到 Docker 时，启动器会在可用 `winget` 的情况下提示是否安装 Docker Desktop。若 Docker Desktop 已安装但尚未启动，启动器会尝试自动启动 Docker Desktop，并等待 Docker CLI 与 Docker engine 就绪后再部署 Guacamole。

Docker Desktop 刚安装后，即使当前终端的 `PATH` 尚未刷新，启动器也会为 Docker 子进程补充 Docker Desktop 的 `resources\bin` 路径，确保 `docker-credential-desktop.exe` 等凭据助手可被 Docker 调用。

Guacamole 自动启动后，启动器会在服务器本机等待 `127.0.0.1:8088/guacamole/` 就绪。如果未能就绪，会直接打印 `docker compose ps` 以及 Guacamole / PostgreSQL 的最近日志，便于在部署服务器上定位问题。

首页的浏览器远程控制按钮只会在 Guacamole 实际可达时显示。若 `.env` 已配置但 `8088` 服务未就绪，EnvPortal 会隐藏按钮并在后端接口返回不可达原因。

EnvPortal 内置的 Guacamole 实例使用 Guacamole 官方 PostgreSQL 初始化脚本。若启动时发现旧版本创建的 Guacamole schema 不兼容，会自动重建 EnvPortal 管理的 Guacamole Docker volume。

从 EnvPortal 打开 Guacamole 时，若 `.env` 配置了 `GUACAMOLE_USERNAME` 和 `GUACAMOLE_PASSWORD`，EnvPortal 会通过 Guacamole 前端原生支持的登录参数跳转，避免停在 Guacamole 原生登录页。

点击浏览器远程控制时，EnvPortal 会优先使用 Guacamole QuickConnect 创建会话。如果 QuickConnect 未返回可打开的连接，EnvPortal 会通过 Guacamole REST API 创建一个临时 RDP 连接，并直接跳转到该连接页面。

QuickConnect 失败或抛错时，EnvPortal 会继续尝试 REST 临时连接创建，并在服务器控制台输出失败原因；前端也会显示 fallback 的具体消息。

Guacamole 临时 RDP 连接会显式启用复制/粘贴通道，并按 Windows 剪贴板换行格式规范化文本。

内置 Guacamole 会额外通过 nginx 提供 HTTPS 入口，默认端口为 `8443`。启动器会自动生成 `certs/guacamole.crt` 和 `certs/guacamole.key`；如已有站点证书，可替换这两个文件。`.env` 默认使用 `GUACAMOLE_PUBLIC_URL=https://localhost:8443/guacamole`，局域网访问时会自动替换为服务器主机名。

Guacamole 临时 RDP 连接会启用文件传输虚拟盘，远程桌面内显示为 `EnvPortal` 盘。每次打开远程连接都会分配独立会话目录，避免多名使用者共享同一个文件交换目录；服务器侧文件位于 `guacamole-drive/sessions/` 下。会话目录默认保留 24 小时，超过后会在启动时或创建新远程连接时自动清理，清理时目录内文件会一起删除。可通过 `.env` 的 `GUACAMOLE_DRIVE_RETENTION_HOURS` 调整，设为 `0` 可关闭自动清理。
