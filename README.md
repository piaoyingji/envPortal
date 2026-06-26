# EnvPortal

EnvPortal 是一个面向运维和实施人员的轻量级环境档案门户，用来集中维护客户/机构、环境地址、登录信息、数据库信息、远程连接信息和自由标签。

当前版本：`2.6.3`

## 核心能力

- 环境检索按 `组织 → 环境组 → 环境` 三层管理。环境所属组使用 `data.csv` 的 `環境グループ` 字段，空值按 `デフォルト` 处理；空环境组和组顺序保存在 `env_groups.json`。
- 环境数据使用显式枚举字段管理环境区分和用途。`環境種別` 只允许 `社内`、`本番`，`用途` 只允许 `生産`、`開発`、`テスト`、`受入`；这些维度不再作为普通 TAG 参与显示过滤。
- 分组、TAG 和同组环境卡片的产品相关显示排序统一使用 `UPDS-V6 < UHR < UPDS-V7 < PHR` 的低到高顺序，未知项排在后面。
- 机构详情中，未设置环境组的历史环境会显示在 `デフォルト` 组。管理员可在机构标题旁直接新增组、改名任意组、调整组显示顺序、把环境移动到指定组、将整个组移动到其他机构，并删除空组；如果最后一个空组被删除，系统会自动重建 `デフォルト`。向只有空 `デフォルト` 组的机构新增或迁入非默认组时，系统会自动删除该空默认组。机构摘要的收缩态会按环境组画成容器，方便查看人员快速识别。
- 环境追加弹窗提交后会立即保存新增环境行，保存成功后再进入该环境的编辑态；保存失败时会恢复提交前的前端状态。
- 机构/客户按“编码 + 名称”管理，组织属性可在环境检索画面直接编辑，并批量反映到该组织下的环境。
- 组属性可在环境检索画面直接编辑，并批量反映到该组织该组下的环境。分组的新增、改名、删除、排序、整体迁移和环境转组都属于管理员权限范围。
- 环境卡片只维护该环境自身的 URL、登录信息、DB、服务器信息和 tags，组织/组信息不再混在环境编辑里。服务器信息支持多条维护，每条可编辑 `サーバ名`、连接类型、用户、密码和连接地址；`サーバ名` 可用于 AP、DB、AP/DB 共用、踏み台或自定义名称。
- 环境组移动使用环境卡片标题区的独立图标按钮，选择目标组并确认后立即保存并重新渲染机构画面。
- 每个服务器/环境支持独立业务标签，标签可以跨机构自由过滤，例如 `DEMO`、`教育`、`OneHR`。环境区分和用途改为枚举字段，不再作为普通标签显示。
- 标签过滤支持分类展示、多选 AND 条件，分类由系统管理中的 TAG 分类管理画面显式维护；系统自动生成标签默认进入“其他”。Clear 只清除用户手工选择的 TAG 条件，角色 TAG 数据权限仍作为基础数据范围生效，右侧画面回到普通组织摘要布局。TAG 分类保存会保留 TAG 显示设定，并通知已打开的首页重新读取分类和配色后刷新渲染。
- TAG 显示设定支持按分类页签切换，并为当前分类内指定 TAG 配置环境面板皮肤，例如 UHR 浅绿、PHR 浅蓝、UPDS-V6 浅灰、UPDS-V7 浅橙；颜色可通过颜色选择器设置，也可清空文本值让该 TAG 不套皮肤。设定页显示当前系统正在使用的配色分类和当前正在编辑的配色分类，可将当前分类设为系统渲染使用。首页收缩摘要卡片、展开详情卡片和命中的 TAG 过滤按钮会直接应用配色效果，不额外显示系统设定标签。
- 角色支持功能权限和数据权限分层维护，数据权限通过一组有效业务 TAG 控制可见环境数据。同一 TAG 分类内的授权 TAG 按 OR 处理，不同 TAG 分类之间按 AND 处理，例如“产品=UHR/PHR”并且“客户组=OneHR”。
- 组织选择支持五十音页签切换。`org_readings.js` 不存在时，后端会通过 `/org_readings_status.jsp` 自动补齐并生成本地读音映射。
- 生产环境页签复用环境检索的同一套组织、环境组、环境卡片和保存逻辑，只显示 `用途=生産` 的记录。新增生产记录时固定写入 `環境種別=本番`、`用途=生産`。
- 首页按机构显示紧凑摘要，环境卡片通过显式展开/收回按钮查看详情，减少默认页面空白。展开后的环境卡片可直接进入编辑态。TAG 过滤结果也保持摘要态，只在用户点击展开时显示详情。
- 首页环境摘要使用流式网格布局，适配多服务器机构。
- 首页首屏优先输出摘要列表，组织/TAG 过滤面板延后补充；TAG、配色、组织和 RDP 匹配等派生数据会在前端缓存，`portal_config.jsp` 的 Guacamole 状态改为后台刷新。
- 环境健康检查会返回 HTTP 状态、响应时间、TTL 和 OS 推测，并按分钟刷新。
- 数据库信息支持地址、端口、实例/库、用户、密码、类型、版本字段。
- 数据库类型和版本支持自动探测，当前支持 Oracle 与 PostgreSQL。
- 远程连接信息支持 RDP/SSH 类型，RDP 可一键启动 mstsc，并自动把密码复制到剪贴板。
- RDP 文件可生成并签名；工具会自动创建 EnvPortal 自签名证书，也提供证书下载。
- 全站 i18n 多语资源化，默认日文，支持中文，并记住上次选择语言。
- 主画面 header 会显示当前识别出的用户与应用版本，客户端 IP 仅作为审计和辅助信息。
- 系统管理菜单集中放置用户管理、角色管理、代理登录、TAG 分类管理和 TAG 显示设定，仅管理员可见。代理登录只在当前浏览器会话中临时切换有效角色，用于验证指定角色下的权限和数据可见性，退出后恢复真实管理员身份。
- 角色权限支持 `admin`、`staff`、`import_staff`、`new_employee` 以及手工新增角色。只有管理员可编辑环境、本番环境和系统设置；其他角色即使残留或提交了编辑权限字段，运行时也会被强制视为只读。其他角色按查看权限和数据权限限定可见环境范围；具备环境查询权限的用户可查看其可见环境的完整登录、DB 和远程连接信息。用户管理画面用 `域用户（最近访问IP）` 显示访问者，并可删除多余用户。
- Windows 机器账号等非人工账号不会进入用户管理。后端会排除标准机器账号格式，也就是规范化用户名以 `$` 结尾的账号，例如服务器本机回退认证产生的 `win-...$`。
- 运行 JSON 文件使用统一的结构化安全读写。`users.json`、`roles.json`、`tags.json`、`tag_categories.json`、`env_groups.json` 读取失败时会优先回退到最近的有效 `*.bak*` 本地备份；写入时会生成 `*.bak_autosave_*` 备份，再用临时文件替换。用户保存会继续过滤 Windows 机器账号。
- 环境检索运行 CSV 使用同样的受保护写入方式。`data.csv`、`rdp.csv` 和环境检索批量保存会先生成 `*.bak_autosave_*`，再用临时文件原子替换，避免异常保存或并发写入导致现场数据不可恢复。
- 当现有 `data.csv` 已有环境行时，环境检索批量保存会拒绝 0 行 CSV 覆盖，避免前端异常状态或空请求把首页数据清空。
- 环境搜索、生产环境和用户管理合并为当前主页面，不再使用独立的旧管理页面。
- 数据存储使用本地 JSON/CSV 文件，不依赖真实数据库。运行数据文件不进入 Git，避免部署更新覆盖现场数据。
- 环境检索保存使用统一的 `update_portal_bundle.jsp`，一次保存 `data.csv`、`rdp.csv`、`tags.json`、`env_groups.json`，change log 记录差分摘要而不是整份 CSV。
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

EnvPortal 通过 `auth_windows.jsp` 判断当前访问者，并返回角色和权限。用户信息保存在本地 `users.json`，角色主数据保存在本地 `roles.json`：

- `admin`：管理员，可查看全部信息、编辑环境/生产环境、维护用户。
- `staff`：一般职员，可查看环境检索中的非敏感摘要。
- `import_staff`：导入职员，只能查看带 `OneHR` tag 的环境。
- `new_employee`：新员工，只能查看带 `社内学習` tag 的环境。

首次访问的域用户会自动登记为 `staff`。既有 Windows 白名单用户首次迁移为 `admin`。角色权限可在系统管理的角色管理画面维护，包括环境查询、环境编辑、生产查询、生产编辑、系统管理和数据权限 TAG。右上角系统管理菜单仅管理员权限用户可见，用户管理和角色管理写入接口需要管理权限。代理登录不会修改真实用户角色，后端会先校验真实管理员身份，再按请求的代理角色计算有效权限。客户端 IP 仅用于审计和辅助显示，不能作为登录身份或授权依据。

`FORCED_ADMIN_USERS` 用于配置永久管理员账号，默认包含 `x02851`。这些账号在自动登记、登录刷新和用户管理保存时都会被强制保持为 `admin`。

代理退出会清除当前浏览器会话中的代理角色和认证缓存，并返回首页重新取得真实用户权限。
系统管理菜单只由当前用户认证结果控制，首屏快速数据载入不会覆盖管理员菜单状态。页面认证会刷新本地缓存，避免旧角色缓存导致管理员菜单不显示。

角色数据权限使用 `dataTags` 数组保存。管理员角色不限制数据，其他角色只显示命中 `dataTags` 中任一有效业务 TAG 的环境。有效 TAG 只来自 `tags.json` 中手工维护的业务 TAG；如果某个 TAG 已经从数据中删除，即使仍残留在角色配置中，也不会继续授予可见数据。为避免旧角色配置在升级瞬间失效，旧数据中残留的 `社内`、`本番`、`受入`、`テスト`、`開発` 等结构性 TAG 仍可用于既有角色匹配，但首页 TAG 过滤、编辑框和显示皮肤不再把它们作为普通 TAG 展示。

环境可能同时拥有多个 TAG。角色命中任一授权 TAG 时，该环境可见；首页 TAG 过滤器只显示该角色已授权的 TAG，不把同一环境上的其他 TAG 作为可点击过滤条件。执行过滤时，角色授权 TAG 永远作为基础条件，用户追加勾选的 TAG 作为 AND 条件继续收窄结果。
TAG 过滤器的清除按钮只清除用户追加勾选的 TAG，不清除角色数据权限的基础条件。

操作按钮按管理员身份和页面级编辑权限共同控制。环境检索的追加、编辑、删除、移动、保存要求 `role=admin` 且 `canEditPortal=true`；生产环境的追加、编辑、保存要求 `role=admin` 且 `canEditProduction=true`。非管理员角色即使现场 `roles.json` 残留了编辑字段，后端也会归一化为只读。
顶部功能导航按查看权限显示。没有 `canViewProduction` 的角色不会看到“生产环境”，没有 `canViewPortal` 的角色不会看到“环境检索”。
RDP 解锁密码框使用标准 form、label 和 autocomplete 属性，避免浏览器把弹窗密码字段识别为异常密码表单。

## 域认证反向代理

当 EnvPortal 服务器未加入 AD 域、且客户端 IP 可能被 NAT 改写时，可以在一台已加入域的 Windows 主机上运行 `EnvPortal Domain Proxy`。该代理使用 Windows Integrated Authentication 识别访问者，再把认证用户通过 `X-Remote-User` 转发给 20.38 上的 EnvPortal。

如果希望用户仍然直接打开 20.38 页面，也可以让页面跨域访问域代理获取当前 Windows 域用户。启用跨域探测后，前端会通过域代理获取一次当前域用户，并由 20.38 签发短期认证 token。token 会在浏览器本地缓存到过期时间，后续需要权限的业务接口会直连 20.38 并携带 token，使 20.38 按域用户角色判断权限，而不是按客户端 IP 判断权限。20.38 的 `.env` 中配置：

```env
DOMAIN_AUTH_PROXY_URL=http://OHR0067:8998/auth_windows.jsp
```

域代理地址优先使用已入域主机的机器名。用 IP 访问时，浏览器更容易把目标识别为普通 Internet 站点，从而弹出 Windows 用户名密码框。使用机器名仍要求访问端能解析该主机名，且浏览器或系统策略允许对该内网站点静默发送当前 Windows 登录凭据。

跨域探测默认关闭，避免浏览器在未配置静默 Windows 认证时弹出用户名密码框。确认浏览器策略或 Local Intranet 区域已允许对域代理主机名静默发送当前登录凭据后，再设置：

```env
DOMAIN_AUTH_AUTO_PROBE=true
```

域代理会对受信任的 EnvPortal 来源返回 CORS header，默认允许 `http://192.168.20.38:8999` 读取认证结果。业务数据接口不需要每次绕行域代理。

域代理会尝试从 AD 读取 `displayName`、`mail`、`department`、`title`，并同步到 EnvPortal 本地用户档案。若 AD 中没有这些属性，则至少保留域账号名。

安装代理需要在已入域 Windows 主机上以管理员权限运行：

```powershell
.\scripts\install-domain-proxy.ps1 -ListenPrefix http://+:8998/ -TargetBaseUrl http://192.168.20.38:8999/
```

代理配置 `AllowedUsersFile` 为空或指向不存在的文件时，已通过 Windows 集成认证的域用户默认都可进入代理。需要禁用个别人时，在代理安装目录的 `denied-users.txt` 中每行写一个账号。20.38 侧建议设置 `TRUSTED_AUTH_PROXY_IPS`，只信任该代理主机传来的认证 header。

## 文件说明

- `index.html`：环境检索首页，包含组织、环境组、环境、tags、服务器信息的查看与编辑。
- `production.html`：生产环境兼容入口，会跳转到 `index.html?mode=production`。
- `user-admin.html`：用户管理。
- `role-admin.html`：角色管理。
- `proxy-admin.html`：管理员代理登录。
- `tag-admin.html`：TAG 分类管理。
- `tag-skin-admin.html`：TAG 显示设定。
- `i18n.js`：日文/中文多语资源。
- `server.py`：Python 后端，负责认证、文件保存、健康检查、DB 探测、RDP 生成/签名/连接。
- `tools/domain-proxy/`：已入域主机使用的 Windows 认证反向代理。
- `run.py`：启动入口。
- `db_versions.json`：数据库类型和版本候选。
- `data.csv`：环境档案数据，本地运行数据文件，包含 `環境グループ`、`環境種別`、`用途`。
- `env_groups.json`：组织下环境组主数据，本地运行数据文件，用于保存空组和显式组顺序，缺失时自动补齐 `デフォルト`。
- `rdp.csv`：远程连接档案数据，本地运行数据文件。`サーバ名` 是兼容新增字段，用于保存环境卡片中服务器信息的显示名；旧文件缺失该列时会按空值读取，并在下次保存时补齐。
- `production.csv`：旧生产环境数据文件，当前主页面不再使用独立格式，保留为遗留接口兼容文件。
- `tags.json`：自由标签存储，本地运行数据文件。
- `tag_categories.json`：TAG 分类、TAG 归属和 TAG 显示设定，本地运行数据文件，缺失时后端默认生成“其他”分类。
- `users.json`：用户角色存储，本地运行数据文件。
- `roles.json`：角色权限主数据，本地运行数据文件。
- `org_readings.js`：组织名读音映射，本地自动生成文件。
- `images/sea01.jpg`：旧版顶部主题背景图保留文件，当前默认样式不再使用该背景。

以下文件均为部署现场数据或配置，已加入 `.gitignore`，不要提交到 Git：`.env`、`data.csv`、`env_groups.json`、`rdp.csv`、`production.csv`、`tags.json`、`tag_categories.json`、`users.json`、`roles.json`、`org_readings.js`、`ip_auth_whitelist.txt`、`windows_auth_whitelist.txt`、`*.bak_*`。

## 版本规则

本项目从 `2.0.0` 开始使用语义化版本号：

- `MAJOR`：数据结构、运行方式或主要交互发生不兼容变化。
- `MINOR`：新增功能但保持兼容。
- `PATCH`：修复问题、微调样式或文案。

`2.3.0` 是一次功能整理版，合并了 `2.2.16` 到 `2.2.31` 期间连续加入的系统管理、域认证 token、角色功能权限、角色数据权限、TAG 分类管理、i18n 和加载性能优化。该版本新增了 `roles.json`、`tag_categories.json` 等现场数据文件，但保留旧字段兼容和默认生成逻辑，因此按 MINOR 递进，不升级 MAJOR。

`2.4.0` 引入环境组完整维护能力，包括 `env_groups.json`、空组、默认组、环境移动和摘要分组容器。这是较大的兼容性功能新增，保留 `data.csv` 的 `環境グループ` 字段并兼容历史空值，因此按 MINOR 递进，不升级 MAJOR。

`2.6.0` 将生产环境页签并入环境检索统一格式，并为 `data.csv` 增加兼容字段 `環境種別` 和 `用途`。历史数据可由旧 TAG 推断初始值，保存后写回枚举字段，因此属于兼容性功能新增，按 MINOR 递进。

`2.6.1` 调整环境组维护规则：所有组都允许改名，空组允许删除到最后一个，删除后由系统自动重建 `デフォルト`。这属于既有分组维护行为修正，按 PATCH 递进。

`2.6.2` 修复环境组摘要操作区的图标按钮尺寸，并增加项目级测试规则：所有修改必须测试，UI 修改必须启动页面并截图确认。该版本属于 PATCH 递进。

`2.6.3` 将编辑权限收敛为管理员专属。非管理员角色保留查看权限和数据权限，编辑权限、生产编辑权限和管理权限在后端规范化时强制无效化，角色管理画面也同步显示为只读固定项。该版本属于 PATCH 递进。

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

