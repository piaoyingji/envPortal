const I18N_STORAGE_KEY = 'envPortalLang';
const I18N_DEFAULT_LANG = 'ja';
const APP_VERSION_FALLBACK = '2.2.24';

const I18N_MESSAGES = {
    ja: {
        'app.searchTitle': '環境検索',
        'app.adminTitle': 'データ管理',
        'app.rdpTitle': 'サーバ接続情報管理',
        'app.productionTitle': '本番環境',
        'app.productionAdminTitle': '本番環境データ管理',
        'app.version': 'Version {version}',
        'app.currentUser': 'ユーザー {name}',
        'header.searchDesc': '特定の組織の各種テストおよび本番環境のログイン情報をすばやく検索',
        'header.adminDesc': '既存の環境情報を修正、または新しい組織の情報を追加します',
        'header.rdpDesc': 'Windows / Linux などのサーバ遠隔接続情報を管理します',
        'header.productionDesc': '本番環境の接続情報を検索・表示します',
        'header.productionAdminDesc': '本番環境の VPN、踏み台、AP、DB 接続情報を管理します',
        'nav.search': '環境検索',
        'nav.admin': 'データ管理',
        'nav.rdp': 'サーバ接続情報管理',
        'nav.production': '本番環境',
        'nav.productionAdmin': '本番環境データ管理',
        'nav.users': 'ユーザー管理',
        'nav.roles': 'ロール管理',
        'nav.system': 'システム管理',
        'nav.org': '対象組織',
        'lang.label': '言語',
        'filter.tags': 'タグで絞り込み',
        'filter.tagsHint': '複数選択で AND 条件',
        'filter.noTags': 'タグがありません',
        'filter.clear': 'クリア',
        'select.loading': '-- データ読み込み中... --',
        'select.loadFailed': '読み込み失敗',
        'select.allOrgSummary': '▼ 全ての組織の概要を表示',
        'select.allOrgs': '▼ 全ての組織を表示',
        'state.loading': 'データ読み込み中...',
        'state.noData': 'データがありません。',
        'state.noOrgEnv': 'この組織に関連する環境データはありません。',
        'state.noTagEnv': 'このタグに関連する環境データはありません。',
        'state.noAdminData': 'データがありません。「新規行を追加」をクリックして開始してください。',
        'state.noMatchedOrg': '条件に一致する組織がありません。',
        'button.addRow': '＋ 新規行を追加',
        'button.saveAll': '保存する (一括更新)',
        'button.search': '検索',
        'button.addEnvToOrg': '＋ 環境追加',
        'button.probeDb': '再探測',
        'button.probeAllDb': 'DB再探測',
        'button.delete': '削除',
        'button.deleteEnv': '環境を削除',
        'button.deleteRdp': '接続情報を削除',
        'button.copy': 'コピー',
        'button.add': 'ADD',
        'button.save': '保存',
        'button.edit': '編集',
        'button.downloadRdp': 'RDPファイルをダウンロード',
        'button.connectRdp': 'RDP接続を開始',
        'button.downloadRdpCert': 'RDP署名証明書をダウンロード',
        'button.openGuacamole': 'ブラウザで遠隔操作',
        'button.cancel': 'キャンセル',
        'button.confirm': '確認',
        'button.unlock': '解除',
        'button.backList': '≪ 一覧に戻る',
        'modal.unlockTitle': 'ロック解除',
        'modal.unlockDesc': '編集用のパスワードを入力してください',
        'modal.rdpUnlockTitle': 'サーバ接続情報 解除',
        'modal.rdpUnlockDesc': 'サーバ接続情報を表示するにはパスワードを入力してください',
        'remote.loadingTitle': '遠隔操作を準備中...',
        'remote.loadingMessage': '接続画面が開くまでお待ちください',
        'toast.copied': 'コピーしました',
        'toast.passwordCopiedForRdp': 'RDPパスワードをクリップボードへコピーしました',
        'toast.rdpConnecting': 'RDP接続を開始しました',
        'toast.rdpDownloadedForClient': 'RDPファイルをダウンロードしました。パスワードはクリップボードへコピー済みです。',
        'toast.rdpDownloaded': 'RDPファイルを作成しました',
        'toast.guacamoleManual': 'Guacamole QuickConnect URIをクリップボードへコピーしました',
        'toast.guacamoleDisabled': 'Guacamoleが利用できません',
        'toast.saved': '保存成功。',
        'toast.savedDetail': '保存成功。サーバーのデータが更新されました。',
        'toast.dbProbeOk': 'DBタイプとバージョンを更新しました',
        'toast.dbProbeNeedCredential': 'DBタイプを識別しました。バージョン探測にはDBユーザとパスワードが必要です。',
        'toast.dbProbeVersionFailed': 'DBタイプを識別しました。バージョン探測に失敗: {reason}',
        'toast.dbProbeAllDone': 'DB再探測が完了しました',
        'toast.authOk': '認証成功！データ管理を開始します。',
        'toast.rdpAuthOk': '認証成功！サーバ接続情報を表示します。',
        'error.authWrong': 'パスワードが正しくありません。',
        'error.auth': '認証でエラーが発生しました。サーバーと通信できません。',
        'error.network': 'ネットワークエラー。サーバー上で実行されているか確認してください。',
        'error.save': '保存エラー: ',
        'error.orgNameRequired': '組織名を入力してください',
        'error.groupRequired': '環境グループを入力してください',
        'error.noCopyTargetOrg': 'コピー先組織がありません',
        'confirm.delete': 'このデータを完全に削除してもよろしいですか？（※即座にサーバーから削除されます）',
        'confirm.deleteEnv': 'この環境を削除しますか？',
        'admin.stat': '組織 <strong>{org}</strong> / 環境 <strong>{env}</strong>',
        'admin.sectionAccess': 'アクセス情報',
        'admin.sectionDatabase': 'データベース接続',
        'admin.dbManual': '手動設定',
        'rdp.stat': '組織 <strong>{org}</strong> / 接続 <strong>{rdp}</strong>',
        'production.stat': '組織 <strong>{org}</strong> / 本番環境 <strong>{production}</strong>',
        'label.orgCode': '組織コード',
        'label.orgName': '組織名',
        'label.orgList': '組織一覧',
        'label.orgSelect': '組織選択',
        'label.envGroup': '環境グループ',
        'label.copyTargetOrg': 'コピー先組織',
        'label.envName': '構築環境名',
        'label.url': 'URL',
        'label.tags': 'タグ',
        'label.loginId': 'ログインID',
        'label.password': 'パスワード',
        'label.dbName': 'DB名',
        'label.dbHost': 'DBアドレス',
        'label.dbPort': 'ポート',
        'label.dbInstance': 'インスタンス / DB',
        'label.dbType': 'DBタイプ',
        'label.dbVersion': 'DBバージョン',
        'label.dbUser': 'DBユーザ',
        'label.dbPwd': 'DB Pwd',
        'label.action': '操作',
        'label.user': 'ユーザー',
        'label.role': 'ロール',
        'label.roleKey': 'ロールID',
        'label.roleLabel': '表示名',
        'label.canEdit': '編集権限',
        'label.canManageUsers': '管理権限',
        'label.filterTag': '表示制限タグ',
        'label.displayName': '表示名',
        'label.firstSeen': '初回アクセス',
        'label.lastSeen': '最終アクセス',
        'label.connection': 'アドレス',
        'label.remoteAccess': '遠隔',
        'label.remoteType': 'タイプ',
        'label.remoteUser': 'ユーザー',
        'label.remotePassword': 'パスワード',
        'label.keyword': 'キーワード',
        'label.prodVpn': '使用VPN',
        'label.prodVpnIp': 'VPN IP',
        'label.prodVpnUser': 'VPNユーザー名',
        'label.prodVpnPassword': 'VPNパスワード',
        'label.prodBastionIp': '踏み台IP',
        'label.prodBastionUser': '踏み台ユーザー名',
        'label.prodBastionPassword': '踏み台パスワード',
        'label.prodApIp': 'AP IP',
        'label.prodApUser': 'APユーザー名',
        'label.prodApPassword': 'APパスワード',
        'label.prodDbIp': 'DB IP',
        'label.prodDbUser': 'DBユーザー名',
        'label.prodDbPassword': 'DBパスワード',
        'section.db': '▼ データベース情報',
        'section.rdp': '▼ サーバ情報',
        'section.dbRdp': '▼ DBサーバ情報',
        'section.productionVpn': 'VPN',
        'section.productionBastion': '踏み台',
        'section.productionAp': 'AP',
        'section.productionDb': 'DB',
        'modal.add': '追加',
        'modal.orgAdd': '組織追加',
        'modal.orgEdit': '組織編集',
        'modal.groupAdd': 'グループ追加',
        'modal.groupEdit': 'グループ編集',
        'modal.envAdd': '環境追加',
        'modal.envCopy': '環境コピー',
        'modal.productionAdd': '本番環境追加',
        'userAdmin.description': 'ユーザー権限を管理します',
        'roleAdmin.description': 'ロールと権限を管理します',
        'roleAdmin.noRoles': 'ロールがありません。',
        'roleAdmin.noPermission': 'ロール管理権限がありません。',
        'roleAdmin.filterHelp': '空欄の場合は全データを表示します。タグ名を入れると該当タグのデータだけ表示します。',
        'userAdmin.noPermission': 'アクセス権限がありません。',
        'userAdmin.noUsers': 'ユーザーがありません。',
        'status.checking': '確認中...',
        'status.up': '稼働中',
        'status.down': '停止',
        'status.error': '接続不可',
        'status.responseTime': '{ms} ms',
        'status.platform': 'Platform',
        'status.server': 'Server',
        'status.http': 'HTTP {status}',
        'status.basicCheck': 'Basic check',
        'status.guess': '推測',
        'status.osGuess': 'OS推測',
        'status.ttl': 'TTL {ttl}',
        'page': 'ページ {current} / {total}',
        'unset.org': '（未設定の組織・新規）',
        'unset.name': '（名称未設定）',
        'unset.value': '(未設定)'
    },
    zh: {
        'app.searchTitle': '环境检索',
        'app.adminTitle': '数据管理',
        'app.rdpTitle': '远程连接信息管理',
        'app.productionTitle': '本番環境',
        'app.productionAdminTitle': '本番環境データ管理',
        'app.version': 'Version {version}',
        'app.currentUser': '用户 {name}',
        'header.searchDesc': '快速检索指定机构的测试环境和生产环境登录信息',
        'header.adminDesc': '维护既有环境信息，或为机构追加新的环境档案',
        'header.rdpDesc': '维护 Windows / Linux 等服务器远程连接信息',
        'header.productionDesc': '检索并显示生产环境连接信息',
        'header.productionAdminDesc': '维护生产环境的 VPN、跳板机、AP、DB 连接信息',
        'nav.search': '环境检索',
        'nav.admin': '数据管理',
        'nav.rdp': '远程连接信息管理',
        'nav.production': '本番環境',
        'nav.productionAdmin': '本番環境データ管理',
        'nav.users': '用户管理',
        'nav.roles': '角色管理',
        'nav.system': '系统管理',
        'nav.org': '目标机构',
        'lang.label': '语言',
        'filter.tags': '按标签过滤',
        'filter.tagsHint': '多选时按 AND 条件过滤',
        'filter.noTags': '暂无标签',
        'filter.clear': '清除',
        'select.loading': '-- 数据读取中... --',
        'select.loadFailed': '读取失败',
        'select.allOrgSummary': '▼ 显示全部机构概要',
        'select.allOrgs': '▼ 显示全部机构',
        'state.loading': '数据读取中...',
        'state.noData': '暂无数据。',
        'state.noOrgEnv': '该机构下没有相关环境数据。',
        'state.noTagEnv': '没有匹配该标签的环境数据。',
        'state.noAdminData': '暂无数据。点击“新增行”开始维护。',
        'state.noMatchedOrg': '没有符合条件的机构。',
        'button.addRow': '＋ 新增行',
        'button.saveAll': '保存（批量更新）',
        'button.search': '检索',
        'button.addEnvToOrg': '＋ 新增环境',
        'button.probeDb': '重新探测',
        'button.probeAllDb': 'DB重新探测',
        'button.delete': '删除',
        'button.deleteEnv': '删除环境',
        'button.deleteRdp': '删除连接信息',
        'button.copy': '复制',
        'button.add': 'ADD',
        'button.save': '保存',
        'button.edit': '编辑',
        'button.downloadRdp': '下载RDP文件',
        'button.connectRdp': '启动RDP连接',
        'button.downloadRdpCert': '下载RDP签名证书',
        'button.openGuacamole': '在浏览器中远程控制',
        'button.cancel': '取消',
        'button.confirm': '确认',
        'button.unlock': '解锁',
        'button.backList': '≪ 返回列表',
        'modal.unlockTitle': '解除锁定',
        'modal.unlockDesc': '请输入编辑密码',
        'modal.rdpUnlockTitle': '解除远程连接信息',
        'modal.rdpUnlockDesc': '请输入密码后查看远程连接信息',
        'remote.loadingTitle': '正在准备远程操作...',
        'remote.loadingMessage': '请稍等，连接画面即将打开',
        'toast.copied': '已复制',
        'toast.passwordCopiedForRdp': 'RDP密码已复制到剪贴板',
        'toast.rdpConnecting': '已启动RDP连接',
        'toast.rdpDownloadedForClient': '已下载RDP文件，密码已复制到剪贴板。',
        'toast.rdpDownloaded': '已生成RDP文件',
        'toast.guacamoleManual': 'Guacamole QuickConnect URI 已复制到剪贴板',
        'toast.guacamoleDisabled': 'Guacamole 当前不可用',
        'toast.saved': '保存成功。',
        'toast.savedDetail': '保存成功。服务器数据已更新。',
        'toast.dbProbeOk': '已更新数据库类型和版本',
        'toast.dbProbeNeedCredential': '已识别数据库类型。探测版本需要DB用户和密码。',
        'toast.dbProbeVersionFailed': '已识别数据库类型。版本探测失败：{reason}',
        'toast.dbProbeAllDone': '数据库重新探测完成',
        'toast.authOk': '认证成功！可以开始数据管理。',
        'toast.rdpAuthOk': '认证成功！正在显示远程连接信息。',
        'error.authWrong': '密码不正确。',
        'error.auth': '认证发生错误。请确认服务器连接。',
        'error.network': '网络错误。请确认服务是否正在运行。',
        'error.save': '保存错误: ',
        'error.orgNameRequired': '请输入机构名称',
        'error.groupRequired': '请输入环境组',
        'error.noCopyTargetOrg': '没有可复制到的目标机构',
        'confirm.delete': '确定要永久删除这条数据吗？（会立即从服务器删除）',
        'confirm.deleteEnv': '确定要删除这个环境吗？',
        'admin.stat': '机构 <strong>{org}</strong> / 环境 <strong>{env}</strong>',
        'admin.sectionAccess': '访问信息',
        'admin.sectionDatabase': '数据库连接',
        'admin.dbManual': '手动维护',
        'rdp.stat': '机构 <strong>{org}</strong> / 连接 <strong>{rdp}</strong>',
        'production.stat': '机构 <strong>{org}</strong> / 生产环境 <strong>{production}</strong>',
        'label.orgCode': '机构编码',
        'label.orgName': '机构名称',
        'label.orgList': '机构列表',
        'label.orgSelect': '机构选择',
        'label.envGroup': '环境组',
        'label.copyTargetOrg': '复制目标机构',
        'label.envName': '环境名称',
        'label.url': 'URL',
        'label.tags': '标签',
        'label.loginId': '登录ID',
        'label.password': '密码',
        'label.dbName': 'DB名',
        'label.dbHost': 'DB地址',
        'label.dbPort': '端口',
        'label.dbInstance': '实例 / 库',
        'label.dbType': '数据库类型',
        'label.dbVersion': '数据库版本',
        'label.dbUser': 'DB用户',
        'label.dbPwd': 'DB密码',
        'label.action': '操作',
        'label.user': '用户',
        'label.role': '角色',
        'label.roleKey': '角色ID',
        'label.roleLabel': '显示名',
        'label.canEdit': '编辑权限',
        'label.canManageUsers': '管理权限',
        'label.filterTag': '显示限制标签',
        'label.displayName': '显示名',
        'label.firstSeen': '首次访问',
        'label.lastSeen': '最后访问',
        'label.connection': '地址',
        'label.remoteAccess': '远程',
        'label.remoteType': '类型',
        'label.remoteUser': '用户',
        'label.remotePassword': '密码',
        'label.keyword': '关键词',
        'label.prodVpn': '使用VPN',
        'label.prodVpnIp': 'VPN IP',
        'label.prodVpnUser': 'VPN用户名',
        'label.prodVpnPassword': 'VPN密码',
        'label.prodBastionIp': '跳板机IP',
        'label.prodBastionUser': '跳板机用户名',
        'label.prodBastionPassword': '跳板机密码',
        'label.prodApIp': 'AP IP',
        'label.prodApUser': 'AP用户名',
        'label.prodApPassword': 'AP密码',
        'label.prodDbIp': 'DB IP',
        'label.prodDbUser': 'DB用户名',
        'label.prodDbPassword': 'DB密码',
        'section.db': '▼ 数据库信息',
        'section.rdp': '▼ 服务器信息',
        'section.dbRdp': '▼ DB服务器信息',
        'section.productionVpn': 'VPN',
        'section.productionBastion': '跳板机',
        'section.productionAp': 'AP',
        'section.productionDb': 'DB',
        'modal.add': '追加',
        'modal.orgAdd': '机构追加',
        'modal.orgEdit': '机构编辑',
        'modal.groupAdd': '环境组追加',
        'modal.groupEdit': '环境组编辑',
        'modal.envAdd': '环境追加',
        'modal.envCopy': '环境复制',
        'modal.productionAdd': '本番环境追加',
        'userAdmin.description': '管理用户权限',
        'roleAdmin.description': '管理角色与权限',
        'roleAdmin.noRoles': '暂无角色。',
        'roleAdmin.noPermission': '没有角色管理权限。',
        'roleAdmin.filterHelp': '留空时显示全部数据。填写标签名时只显示包含该标签的数据。',
        'userAdmin.noPermission': '没有访问权限。',
        'userAdmin.noUsers': '没有用户。',
        'status.checking': '确认中...',
        'status.up': '运行中',
        'status.down': '停止',
        'status.error': '无法连接',
        'status.responseTime': '{ms} ms',
        'status.platform': '平台',
        'status.server': '服务',
        'status.http': 'HTTP {status}',
        'status.basicCheck': '基础检查',
        'status.guess': '推测',
        'status.osGuess': 'OS推测',
        'status.ttl': 'TTL {ttl}',
        'page': '第 {current} / {total} 页',
        'unset.org': '（未设置机构・新建）',
        'unset.name': '（名称未设置）',
        'unset.value': '(未设置)'
    }
};

let PORTAL_RUNTIME_CONFIG_PROMISE = null;
let PORTAL_RUNTIME_CONFIG = null;
let PORTAL_AUTH_PROMISE = null;
let PORTAL_AUTH_PROFILE = null;
const PORTAL_AUTH_STORAGE_KEY = 'envPortalAuthProfile';

function loadPortalRuntimeConfig() {
    if (PORTAL_RUNTIME_CONFIG_PROMISE) return PORTAL_RUNTIME_CONFIG_PROMISE;
    PORTAL_RUNTIME_CONFIG_PROMISE = fetch('portal_config.jsp?t=' + new Date().getTime(), { cache: 'no-store' })
        .then(res => res.ok ? res.json() : {})
        .then(config => {
            PORTAL_RUNTIME_CONFIG = config || {};
            return PORTAL_RUNTIME_CONFIG;
        })
        .catch(() => {
            PORTAL_RUNTIME_CONFIG = {};
            return PORTAL_RUNTIME_CONFIG;
        });
    return PORTAL_RUNTIME_CONFIG_PROMISE;
}

function portalProxyEnabled() {
    return Boolean(PORTAL_RUNTIME_CONFIG && PORTAL_RUNTIME_CONFIG.domainAuthAutoProbe && PORTAL_RUNTIME_CONFIG.domainAuthProxyUrl);
}

function portalProxyUrl(path) {
    const authUrl = String(PORTAL_RUNTIME_CONFIG.domainAuthProxyUrl || '').trim();
    if (!authUrl) return path;
    const base = authUrl.replace(/auth_windows\.jsp(?:\?.*)?$/i, '');
    return base + String(path || '').replace(/^\/+/, '');
}

function isAuthEndpoint(path) {
    return String(path || '').replace(/^\/+/, '').split('?', 1)[0] === 'auth_windows.jsp';
}

function isProtectedPortalEndpoint(path) {
    const endpoint = String(path || '').replace(/^\/+/, '').split('?', 1)[0];
    return [
        'portal_data.jsp',
        'production_data.jsp',
        'users_data.jsp',
        'roles_data.jsp',
        'auth.jsp',
        'db_probe.jsp',
        'rdp_file.jsp',
        'rdp_connect.jsp',
        'guacamole_connect.jsp',
        'update_csv.jsp',
        'update_rdp.jsp',
        'update_tags.jsp',
        'update_production.jsp',
        'update_users.jsp',
        'update_roles.jsp',
        'update_portal_bundle.jsp'
    ].includes(endpoint);
}

function readStoredPortalAuth() {
    try {
        const raw = localStorage.getItem(PORTAL_AUTH_STORAGE_KEY) || sessionStorage.getItem(PORTAL_AUTH_STORAGE_KEY) || 'null';
        const profile = JSON.parse(raw);
        if (!profile || !profile.authToken || !profile.authTokenExpiresAt) return null;
        if (Number(profile.authTokenExpiresAt) * 1000 <= Date.now() + 30000) {
            localStorage.removeItem(PORTAL_AUTH_STORAGE_KEY);
            sessionStorage.removeItem(PORTAL_AUTH_STORAGE_KEY);
            return null;
        }
        return profile;
    } catch (e) {
        return null;
    }
}

function storePortalAuth(profile) {
    if (!profile || !profile.authToken || !profile.authTokenExpiresAt) return;
    PORTAL_AUTH_PROFILE = profile;
    try {
        localStorage.setItem(PORTAL_AUTH_STORAGE_KEY, JSON.stringify(profile));
        sessionStorage.setItem(PORTAL_AUTH_STORAGE_KEY, JSON.stringify(profile));
    } catch (e) {
        // Browser storage can be disabled by policy.
    }
}

function applyCachedPortalIdentity() {
    const profile = readStoredPortalAuth();
    if (!profile) return null;
    setCurrentUser(profile);
    setSystemMenuVisible(isSystemAdmin(profile));
    return profile;
}

function loadPortalAuth() {
    const stored = readStoredPortalAuth();
    if (stored) {
        PORTAL_AUTH_PROFILE = stored;
        return Promise.resolve(stored);
    }
    if (PORTAL_AUTH_PROMISE) return PORTAL_AUTH_PROMISE;
    PORTAL_AUTH_PROMISE = loadPortalRuntimeConfig()
        .then(() => {
            const authPath = 'auth_windows.jsp?t=' + new Date().getTime();
            const url = portalProxyEnabled() ? portalProxyUrl(authPath) : authPath;
            const options = portalProxyEnabled()
                ? { cache: 'no-store', credentials: 'include' }
                : { cache: 'no-store' };
            return fetch(url, options);
        })
        .then(res => res.ok ? res.json() : null)
        .then(profile => {
            if (profile && profile.authToken) storePortalAuth(profile);
            return profile;
        })
        .catch(() => null)
        .finally(() => {
            PORTAL_AUTH_PROMISE = null;
        });
    return PORTAL_AUTH_PROMISE;
}

function portalFetch(path, options = {}) {
    return loadPortalRuntimeConfig().then(() => {
        if (!portalProxyEnabled()) return fetch(path, options);
        if (isAuthEndpoint(path)) {
            return loadPortalAuth().then(profile => new Response(JSON.stringify(profile || { ok: false }), {
                status: profile && profile.ok ? 200 : 401,
                headers: { 'Content-Type': 'application/json' }
            }));
        }
        if (!isProtectedPortalEndpoint(path)) return fetch(path, options);
        return loadPortalAuth().then(profile => {
            const headers = new Headers(options.headers || {});
            if (profile && profile.authToken) headers.set('X-EnvPortal-Auth', profile.authToken);
            return fetch(path, { ...options, headers });
        });
    });
}

function getLang() {
    const cached = localStorage.getItem(I18N_STORAGE_KEY);
    return I18N_MESSAGES[cached] ? cached : I18N_DEFAULT_LANG;
}

function setLang(lang) {
    if (!I18N_MESSAGES[lang]) return;
    localStorage.setItem(I18N_STORAGE_KEY, lang);
    applyI18n();
    window.dispatchEvent(new CustomEvent('i18n:changed', { detail: { lang } }));
}

function t(key, params = {}) {
    const message = (I18N_MESSAGES[getLang()] && I18N_MESSAGES[getLang()][key]) || I18N_MESSAGES[I18N_DEFAULT_LANG][key] || key;
    return Object.keys(params).reduce((text, name) => text.replaceAll(`{${name}}`, params[name]), message);
}

function applyI18n(root = document) {
    const lang = getLang();
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'ja';
    root.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-html]').forEach(el => {
        el.innerHTML = t(el.dataset.i18nHtml);
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    root.querySelectorAll('[data-i18n-title]').forEach(el => {
        el.title = t(el.dataset.i18nTitle);
    });
    const titleKey = document.body && document.body.dataset.titleKey;
    if (titleKey) document.title = `EnvPortal - ${t(titleKey)}`;
    const switcher = document.getElementById('langSelect');
    if (switcher) switcher.value = lang;
    const versionLabel = document.getElementById('appVersionLabel');
    if (versionLabel) versionLabel.textContent = t('app.version', { version: versionLabel.dataset.version || APP_VERSION_FALLBACK });
    const currentUserLabel = document.getElementById('currentUserLabel');
    if (currentUserLabel && currentUserLabel.dataset.name) currentUserLabel.textContent = t('app.currentUser', { name: currentUserLabel.dataset.name });
    const systemMenuLabel = document.getElementById('systemMenuLabel');
    if (systemMenuLabel) systemMenuLabel.textContent = t('nav.system');
}

function loadAppVersion() {
    const versionLabel = document.getElementById('appVersionLabel');
    if (!versionLabel) return;
    fetch('VERSION?t=' + new Date().getTime(), { cache: 'no-store' })
        .then(res => res.ok ? res.text() : APP_VERSION_FALLBACK)
        .then(text => {
            const version = String(text || APP_VERSION_FALLBACK).trim() || APP_VERSION_FALLBACK;
            versionLabel.dataset.version = version;
            versionLabel.textContent = t('app.version', { version });
        })
        .catch(() => {
            versionLabel.dataset.version = APP_VERSION_FALLBACK;
            versionLabel.textContent = t('app.version', { version: APP_VERSION_FALLBACK });
        });
}

function isIpLikeUser(value) {
    const text = String(value || '').trim();
    return /^(\d{1,3}\.){3}\d{1,3}$/.test(text) || text.includes(':');
}

function setCurrentUser(profile) {
    const label = document.getElementById('currentUserLabel');
    if (!label) return;
    const name = String((profile && (profile.displayName || profile.user)) || '').trim();
    if (!name || isIpLikeUser(name)) {
        if (label.dataset.name) return;
        label.hidden = true;
        label.dataset.name = '';
        label.textContent = '';
        return;
    }
    label.dataset.name = name;
    label.textContent = t('app.currentUser', { name });
    label.hidden = false;
}

function loadCurrentUser() {
    portalFetch('auth_windows.jsp?t=' + new Date().getTime(), { cache: 'no-store' })
        .then(res => res.ok ? res.json() : null)
        .then(profile => {
            setCurrentUser(profile);
            if (isSystemAdmin(profile)) setSystemMenuVisible(true);
        })
        .catch(() => setCurrentUser(null));
}

function initI18n() {
    const logoArea = document.querySelector('.logo-area');
    if (logoArea && !document.getElementById('langSelect')) {
        const wrap = document.createElement('div');
        wrap.className = 'language-switch';
        wrap.innerHTML = `
            <div class="language-control">
                <label for="langSelect">${t('lang.label')}</label>
                <select id="langSelect">
                    <option value="ja">日本語</option>
                    <option value="zh">中文</option>
                </select>
            </div>
            <div class="client-meta">
                <span id="currentUserLabel" class="client-ip" hidden></span>
                <span id="appVersionLabel" class="app-version" data-version="${APP_VERSION_FALLBACK}">${t('app.version', { version: APP_VERSION_FALLBACK })}</span>
            </div>
        `;
        logoArea.appendChild(wrap);
        wrap.querySelector('select').addEventListener('change', e => setLang(e.target.value));
        loadAppVersion();
    }
    const navInner = document.querySelector('.main-nav-inner');
    if (navInner && !document.getElementById('systemMenu')) {
        const menu = document.createElement('details');
        menu.id = 'systemMenu';
        menu.className = 'system-menu';
        menu.hidden = true;
        menu.innerHTML = `
            <summary id="systemMenuLabel">${t('nav.system')}</summary>
            <div class="system-menu-panel">
                <a href="user-admin.html" data-system-link="user-admin.html" data-i18n="nav.users">${t('nav.users')}</a>
                <a href="role-admin.html" data-system-link="role-admin.html" data-i18n="nav.roles">${t('nav.roles')}</a>
            </div>
        `;
        navInner.appendChild(menu);
    }
    applyCachedPortalIdentity();
    loadCurrentUser();
    applyI18n();
}

function setSystemMenuVisible(visible) {
    const menu = document.getElementById('systemMenu');
    if (!menu) return;
    menu.hidden = !visible;
    if (visible) {
        const current = location.pathname.split('/').pop() || 'index.html';
        menu.querySelectorAll('[data-system-link]').forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === current);
        });
    }
}

function isSystemAdmin(profile) {
    return Boolean(profile && (profile.role === 'admin' || profile.canManageUsers === true));
}

document.addEventListener('DOMContentLoaded', initI18n);
