# EnvPortal

EnvPortal 是一个面向运维和实施人员的轻量级环境档案门户，用来集中维护客户/机构、环境地址、登录信息、数据库信息、远程连接信息和自由标签。

当前版本：`2.2.16`

## 核心能力

- 环境检索按 `组织 → 环境组 → 环境` 三层管理。环境组使用 `data.csv` 的 `環境グループ` 字段，例如 `UHR-V6`、`PHR-V7`。
- 机构/客户按“编码 + 名称”管理，组织属性可在环境检索画面直接编辑，并批量反映到该组织下的环境。
- 组属性可在环境检索画面直接编辑，并批量反映到该组织该组下的环境。
- 环境卡片只维护该环境自身的 URL、登录信息、DB、AP/DB RDP 和 tags，组织/组信息不再混在环境编辑里。
- 每个服务器/环境支持独立标签，标签可以跨机构自由过滤，例如 `DEMO`、`教育`、`社内`。
- 标签过滤支持分类展示、多选 AND 条件，并包含系统自动生成标签，例如数据库类型、数据库版本、RDP/SSH。
- 组织选择支持五十音分类。`org_readings.js` 不存在时，后端会通过 `/org_readings_status.jsp` 自动补齐并生成本地读音映射。
- 首页按机构显示紧凑摘要，环境卡片通过显式展开/收回按钮查看详情，减少默认页面空白。
- 首页环境摘要使用流式网格布局，适配多服务器机构。
- 环境健康检查会返回 HTTP 状态、响应时间、TTL 和 OS 推测，并按分钟刷新。
- 数据库信息支持地址、端口、实例/库、用户、密码、类型、版本字段。
- 数据库类型和版本支持自动探测，当前支持 Oracle 与 PostgreSQL。
- 远程连接信息支持 RDP/SSH 类型，RDP 可一键启动 mstsc，并自动把密码复制到剪贴板。
- RDP 文件可生成并签名；工具会自动创建 EnvPortal 自签名证书，也提供证书下载。
- 全站 i18n 多语资源化，默认日文，支持中文，并记住上次选择语言。
- 主画面 header 会显示当前客户端 IP 与应用版本，便于确认访问来源。
- 角色权限支持 `admin`、`staff`、`import_staff`、`new_employee`。管理员可编辑全部信息和管理用户，其他角色按规则查看脱敏或限定数据。用户管理画面用 `域用户（最近访问IP）` 显示访问者，并可删除多余用户。
- 环境搜索、本番环境和用户管理合并为当前主页面，不再使用独立的旧管理页面。
- 数据存储使用本地 JSON/CSV 文件，不依赖真实数据库。运行数据文件不进入 Git，避免部署更新覆盖现场数据。
- 环境检索保存使用统一的 `update_portal_bundle.jsp`，一次保存 `data.csv`、`rdp.csv`、`tags.json`，change log 记录差分摘要而不是整份 CSV。
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

启动时读取本地 `.env`。`.env` 已从 Git 管理中移除并加入 `.gitignore`，用于保存部署服务器自己的端口、认证代理和 Guacamole 配置。

如果 `.env` 不存在，`server.py` 使用默认端口 `8080`。如果需要沿用既有端口 `8999`，请在本地重新创建 `.env`：

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

未创建 `.env` 时访问地址为：

```text
http://localhost:8080
```

## Windows 远端部署 / 自启动

推荐远端服务器直接从 Git 更新代码，并注册开机自启动：

```powershell
.\scripts\deploy-remote.ps1 -ComputerName 192.168.20.38 -UserName Administrator -Branch main -InstallDir C:\EnvPortal
```

该脚本会通过 PowerShell Remoting 登录远端，执行：

- clone / pull `https://github.com/piaoyingji/envPortal.git`
- 安装 `requirements.txt`
- 优先使用 `nssm.exe` 注册 `EnvPortal` Windows Service
- 如果远端没有 nssm，则注册 `EnvPortal Startup` 计划任务作为开机自启动兜底

如果要注册真正的 Windows Service，请把 `nssm.exe` 放在远端以下任一位置后重跑脚本：

```text
C:\EnvPortal\tools\nssm.exe
C:\Tools\nssm\nssm.exe
C:\nssm\nssm.exe
```

不要把服务器密码或可解密凭据提交到 Git。远程部署脚本会在执行时通过 `Get-Credential` 输入凭据。

`BIND_ADDRESS=0.0.0.0` 时会监听所有网卡，局域网内可使用本机 IP 访问。

Windows 下启动器会为 EnvPortal 端口和 Guacamole 端口检查入站防火墙规则。未配置 `.env` 时 EnvPortal 默认端口为 `8080`，Guacamole 默认端口为 `8088`。如果当前终端不是管理员权限，启动不会失败，但会打印需要在管理员 PowerShell 中执行的 `New-NetFirewallRule` 命令。

## 用户角色与认证

EnvPortal 通过 `auth_windows.jsp` 判断当前访问者，并返回 `role`、`canEdit`、`canManageUsers`。用户信息保存在本地 `users.json`，角色主数据保存在本地 `roles.json`：

- `admin`：管理员，可查看全部信息、编辑环境/本番环境、维护用户。
- `staff`：一般职员，可查看环境检索中的非敏感摘要。
- `import_staff`：导入职员，只能查看带 `OneHR` tag 的环境。
- `new_employee`：新员工，只能查看带 `社内学習` tag 的环境。

首次访问的域用户会自动登记为 `staff`。既有 Windows/IP 白名单用户首次迁移为 `admin`。右上角系统管理菜单仅 `admin` 角色可见，用户管理和角色管理写入接口需要管理权限。

## 域认证反向代理

当 EnvPortal 服务器未加入 AD 域、且客户端 IP 可能被 NAT 改写时，可以在一台已加入域的 Windows 主机上运行 `EnvPortal Domain Proxy`。该代理使用 Windows Integrated Authentication 识别访问者，再把认证用户通过 `X-Remote-User` 转发给 20.38 上的 EnvPortal。

如果希望用户仍然直接打开 20.38 页面，也可以让页面跨域访问域代理获取当前 Windows 域用户。20.38 的 `.env` 中配置：

```env
DOMAIN_AUTH_PROXY_URL=http://OHR0067:8998/auth_windows.jsp
```

域代理地址优先使用已入域主机的机器名。用 IP 访问时，浏览器更容易把目标识别为普通 Internet 站点，从而弹出 Windows 用户名密码框。使用机器名仍要求访问端能解析该主机名，且浏览器或系统策略允许对该内网站点静默发送当前 Windows 登录凭据。

跨域探测默认关闭，避免浏览器在未配置静默 Windows 认证时弹出用户名密码框。确认浏览器策略或 Local Intranet 区域已允许对域代理主机名静默发送当前登录凭据后，再设置：

```env
DOMAIN_AUTH_AUTO_PROBE=true
```

域代理会对受信任的 EnvPortal 来源返回 CORS header，默认允许 `http://192.168.20.38:8999` 读取认证结果。

域代理会尝试从 AD 读取 `displayName`、`mail`、`department`、`title`，并同步到 EnvPortal 本地用户档案。若 AD 中没有这些属性，则至少保留域账号名。

安装代理需要在已入域 Windows 主机上以管理员权限运行：

```powershell
.\scripts\install-domain-proxy.ps1 -ListenPrefix http://+:8998/ -TargetBaseUrl http://192.168.20.38:8999/
```

允许访问的域用户写在代理安装目录的 `allowed-users.txt`，每行一个账号。20.38 侧建议设置 `TRUSTED_AUTH_PROXY_IPS`，只信任该代理主机传来的认证 header。

## 文件说明

- `index.html`：环境检索首页，包含组织、环境组、环境、tags、AP/DB RDP 的查看与编辑。
- `production.html`：本番环境查看与编辑。
- `user-admin.html`：用户和角色管理。
- `i18n.js`：日文/中文多语资源。
- `server.py`：Python 后端，负责认证、文件保存、健康检查、DB 探测、RDP 生成/签名/连接。
- `tools/domain-proxy/`：已入域主机使用的 Windows 认证反向代理。
- `run.py`：启动入口。
- `db_versions.json`：数据库类型和版本候选。
- `data.csv`：环境档案数据，本地运行数据文件，包含 `環境グループ`。
- `rdp.csv`：远程连接档案数据，本地运行数据文件。
- `production.csv`：本番环境数据，本地运行数据文件。
- `tags.json`：自由标签存储，本地运行数据文件。
- `users.json`：用户角色存储，本地运行数据文件。
- `org_readings.js`：组织名读音映射，本地自动生成文件。
- `images/sea01.jpg`：旧版顶部主题背景图保留文件，当前默认样式不再使用该背景。

以下文件均为部署现场数据或配置，已加入 `.gitignore`，不要提交到 Git：`.env`、`data.csv`、`rdp.csv`、`production.csv`、`tags.json`、`users.json`、`org_readings.js`、`ip_auth_whitelist.txt`、`windows_auth_whitelist.txt`。

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
