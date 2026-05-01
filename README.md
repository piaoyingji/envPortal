# EnvPortal

EnvPortal 是一个面向运维和实施人员的轻量级环境档案门户，用来集中维护客户/机构、环境地址、登录信息、数据库信息、远程连接信息和自由标签。

当前版本：`2.1.16`

## 核心能力

- 机构/客户按“编码 + 名称”管理，避免通过重复输入机构名称来分组。
- 每个服务器/环境支持独立标签，标签可以跨机构自由过滤，例如 `DEMO`、`教育`、`社内`。
- 标签过滤支持多选 AND 条件，并包含系统自动生成标签，例如数据库类型、数据库版本、RDP/SSH。
- 首页按机构显示紧凑摘要，鼠标悬停或点击环境后展开详情卡片，减少默认页面空白。
- 环境健康检查会返回 HTTP 状态、响应时间、TTL 和 OS 推测，并按分钟刷新。
- 数据库信息支持地址、端口、实例/库、用户、密码、类型、版本字段。
- 数据库类型和版本支持自动探测，当前支持 Oracle 与 PostgreSQL。
- 远程连接信息支持 RDP/SSH 类型，RDP 可一键启动 mstsc，并自动把密码复制到剪贴板。
- RDP 文件可生成并签名；工具会自动创建 EnvPortal 自签名证书，也提供证书下载。
- 全站 i18n 多语资源化，默认日文，支持中文，并记住上次选择语言。
- 顶部主题区使用 `images/sea01.jpg` 作为虚化海水背景，整体配色统一为蓝青色调。
- 数据存储使用本地 JSON/CSV 文件，不依赖真实数据库。
- 后端已切换为 Python，保留 `start.bat`，并提供 `start.sh`，为后续 Linux 部署做准备。
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

## 文件说明

- `index.html`：环境检索首页。
- `admin.html`：环境数据管理。
- `rdp.html`：服务器/远程连接信息管理。
- `i18n.js`：日文/中文多语资源。
- `server.py`：Python 后端，负责认证、文件保存、健康检查、DB 探测、RDP 生成/签名/连接。
- `run.py`：启动入口。
- `db_versions.json`：数据库类型和版本候选。
- `tags.json`：自由标签存储。
- `data.csv`：环境档案数据，本地运行数据文件。
- `rdp.csv`：远程连接档案数据，本地运行数据文件。
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

Guacamole 临时 RDP 连接会启用文件传输虚拟盘，远程桌面内显示为 `EnvPortal` 盘，对应服务器目录 `guacamole-drive/`。
