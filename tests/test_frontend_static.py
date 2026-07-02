import unittest
from pathlib import Path


class FrontendStaticBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_html = Path("index.html").read_text(encoding="utf-8")
        cls.production_html = Path("production.html").read_text(encoding="utf-8")
        cls.i18n_js = Path("i18n.js").read_text(encoding="utf-8")
        cls.proxy_admin_html = Path("proxy-admin.html").read_text(encoding="utf-8")
        cls.role_admin_html = Path("role-admin.html").read_text(encoding="utf-8")

    def test_environment_rendering_uses_product_display_order(self):
        self.assertIn("function environmentDisplayRank(row)", self.index_html)
        self.assertIn("function sortEnvironmentsByDisplayOrder(envs)", self.index_html)
        self.assertIn("sortEnvironmentsByDisplayOrder(envs).forEach((env, index)", self.index_html)
        self.assertIn("sortEnvironmentsByDisplayOrder(envs).forEach(env =>", self.index_html)
        self.assertIn("const orderedEnvs = sortEnvironmentsByDisplayOrder(envs);", self.index_html)

    def test_inline_expand_uses_sorted_environment_order(self):
        sorted_lookup = "sortEnvironmentsByDisplayOrder(getFilteredData().filter"
        self.assertGreaterEqual(self.index_html.count(sorted_lookup), 2)

    def test_environment_save_rerenders_when_visible_order_changes(self):
        self.assertIn("function currentVisibleEnvRowIds()", self.index_html)
        self.assertIn("function shouldRenderActiveViewAfterEnvSave(rowId, beforeGroup, beforeVisibleRowIds)", self.index_html)
        self.assertIn("!currentVisibleEnvRowIds().includes(rowId)", self.index_html)
        self.assertIn("const beforeVisibleRowIds = currentVisibleEnvRowIds();", self.index_html)
        self.assertIn("if (shouldRenderActiveViewAfterEnvSave(rowId, beforeGroup, beforeVisibleRowIds))", self.index_html)

    def test_collapsing_editing_card_prompts_to_save_dirty_changes(self):
        self.assertIn("function currentEnvironmentEditorSnapshot(env, editor)", self.index_html)
        self.assertIn("function draftEnvironmentEditorSnapshot(env, editor)", self.index_html)
        self.assertIn("function isEnvironmentEditorDirty(rowId)", self.index_html)
        self.assertIn("if (rowId && editingEnvId === rowId) {", self.index_html)
        self.assertIn("isEnvironmentEditorDirty(rowId) && confirm(t('confirm.saveBeforeCollapse'))", self.index_html)
        self.assertIn("saveEnvironmentCard(rowId, { renderAfterSave: false, propagateError: true })", self.index_html)
        self.assertIn("editingEnvId = '';", self.index_html)
        self.assertIn("collapseInlineEnv(button.dataset.orgKey || '', item, rowId);", self.index_html)
        self.assertIn("'confirm.saveBeforeCollapse': '編集内容が変更されています。折りたたむ前に保存しますか？'", self.i18n_js)
        self.assertIn("'confirm.saveBeforeCollapse': '当前编辑内容已修改，收起前是否保存？'", self.i18n_js)

    def test_environment_groups_can_rename_default_and_delete_last_empty_group(self):
        self.assertIn("record.groups = nextGroups.length ? nextGroups : [DEFAULT_ENV_GROUP];", self.index_html)
        self.assertIn("const canDeleteGroup = canManageGroup && group.rows.length === 0;", self.index_html)
        self.assertNotIn("error.defaultGroupProtected", self.index_html)
        self.assertNotIn("error.lastGroupProtected", self.index_html)
        self.assertNotIn("groups.length <= 1", self.index_html)
        self.assertNotIn("normalizeGroupName(groupValue) === DEFAULT_ENV_GROUP", self.index_html)
        self.assertNotIn("normalizeGroupName(groupName) !== DEFAULT_ENV_GROUP", self.index_html)
        self.assertNotIn("normalizeGroupName(group.groupValue) !== DEFAULT_ENV_GROUP", self.index_html)

    def test_group_summary_action_buttons_are_real_icon_buttons(self):
        self.assertIn(".group-title-actions > button", self.index_html)
        self.assertIn(".group-title-actions > button svg", self.index_html)
        self.assertIn("width: 24px;", self.index_html)
        self.assertIn("width: 14px;", self.index_html)

    def test_add_environment_modal_persists_new_row(self):
        self.assertIn("const snapshot = portalStateSnapshot();", self.index_html)
        self.assertIn("savePortalFiles(changeSummaryFor('add-env', null, row))", self.index_html)
        self.assertIn("editEnvironmentCard(row.__rowId);", self.index_html)
        self.assertIn("restorePortalState(snapshot);", self.index_html)

    def test_home_uses_cached_auth_for_first_data_load(self):
        self.assertIn("const cachedPortalAuth = typeof readStoredPortalAuth === 'function' ? readStoredPortalAuth() : null;", self.index_html)
        self.assertIn("loadPortalData({ authenticated: Boolean(cachedPortalAuth) });", self.index_html)
        self.assertIn("skipDataReload: Boolean(cachedPortalAuth)", self.index_html)
        self.assertIn("refreshAuth: options.refreshAuth === true", self.index_html)
        self.assertIn("if (!options.skipDataReload) loadPortalData({ authenticated: true });", self.index_html)
        self.assertIn("function loadCurrentUser(options = {})", self.i18n_js)
        self.assertIn("options.skipIfCached && cachedProfile", self.i18n_js)
        self.assertIn("loadCurrentUser({ skipIfCached: Boolean(cachedProfile) });", self.i18n_js)
        self.assertNotIn("refreshAuth: true })", self.i18n_js)

    def test_server_info_editor_uses_editable_server_name(self):
        self.assertIn('"サーバ名"', self.index_html)
        self.assertIn('const RDP_FIELDS = ["組織名","構築環境名","サーバ名"', self.index_html)
        self.assertIn("SERVER_NAME_OPTION_KEYS", self.index_html)
        self.assertIn("function renderCardServerNameField(value)", self.index_html)
        self.assertIn("function addRdpEditorToCard(rowId)", self.index_html)
        self.assertIn("function removeRdpEditor(button)", self.index_html)
        self.assertIn("String(remote['構築環境名'] || '').trim() === envName", self.index_html)
        self.assertIn("target['構築環境名'] = env['構築環境名'] || '';", self.index_html)
        self.assertIn("function rdpHasExplicitEnv(remote)", self.index_html)
        self.assertIn("const explicitRdps = relatedRdpRowsForEnv(env).filter(rdpHasExplicitEnv);", self.index_html)
        self.assertIn("!rdpHasExplicitEnv(remote)", self.index_html)
        self.assertIn("relatedRdpRowsForEnv(env).forEach(remote =>", self.index_html)
        self.assertIn("savePortalFiles(changeSummaryFor('add-env', null, row))", self.index_html)
        self.assertIn("data-original-rdp-ids", self.index_html)
        self.assertIn("retainedRdpIds", self.index_html)
        self.assertIn(".server-editor-title .delete-btn svg", self.index_html)
        self.assertIn("flex: 0 0 30px;", self.index_html)
        self.assertIn("serverName.shared", self.i18n_js)

    def test_mobile_guacamole_shell_uses_i18n_and_fullscreen_wrapper(self):
        self.assertIn("function shouldUseMobileGuacamoleShell()", self.index_html)
        self.assertIn("function mobileGuacamoleShellHtml()", self.index_html)
        self.assertIn("function prepareMobileGuacamoleShell()", self.index_html)
        self.assertIn("allow=\"fullscreen; clipboard-read; clipboard-write\"", self.index_html)
        self.assertIn("screen.orientation.lock('landscape')", self.index_html)
        self.assertIn("popup.envPortalOpenRemote", self.index_html)
        self.assertIn("<\\/script>", self.index_html)
        self.assertIn("const mobileShell = prepareMobileGuacamoleShell();", self.index_html)
        self.assertIn("mobileShell && mobileShell.navigate(data.url)", self.index_html)
        self.assertIn("'remote.mobileLoadingTitle': '横画面表示を準備中...'", self.i18n_js)
        self.assertIn("'remote.mobileLoadingTitle': '正在准备横屏显示...'", self.i18n_js)
        self.assertIn("'remote.openDirect': '直接開く'", self.i18n_js)
        self.assertIn("'remote.openDirect': '直接打开'", self.i18n_js)

    def test_system_menu_contains_proxy_login(self):
        self.assertIn('href="proxy-admin.html"', self.i18n_js)
        self.assertIn("nav.proxyLogin", self.i18n_js)

    def test_portal_fetch_sends_proxy_role_header(self):
        self.assertIn("PORTAL_PROXY_ROLE_STORAGE_KEY", self.i18n_js)
        self.assertIn("X-EnvPortal-Proxy-Role", self.i18n_js)
        self.assertIn("readPortalProxyRole()", self.i18n_js)
        self.assertIn("'update_org_bundle.jsp'", self.i18n_js)

    def test_header_has_proxy_logout_status(self):
        self.assertIn("proxyLoginLabel", self.i18n_js)
        self.assertIn("proxyLogoutBtn", self.i18n_js)
        self.assertIn("exitPortalProxyLogin", self.i18n_js)
        self.assertIn("function clearStoredPortalAuth()", self.i18n_js)
        self.assertIn("const activeProxyRole = readPortalProxyRole();", self.i18n_js)
        self.assertIn("} else if (activeProxyRole) {", self.i18n_js)
        self.assertIn("clearStoredPortalAuth();", self.i18n_js)
        self.assertIn("location.href = 'index.html';", self.i18n_js)

    def test_proxy_admin_loads_roles_without_active_proxy(self):
        self.assertIn("roles_data.jsp", self.proxy_admin_html)
        self.assertIn("skipProxyRole: true", self.proxy_admin_html)
        self.assertIn("setPortalProxyRole(roleKey)", self.proxy_admin_html)
        self.assertIn("function escapeHtml(value)", self.proxy_admin_html)
        self.assertIn("function escapeJs(value)", self.proxy_admin_html)

    def test_auth_refresh_controls_system_menu(self):
        self.assertIn("delete nextOptions.refreshAuth;", self.i18n_js)
        self.assertIn("const forceRefreshAuth = options.refreshAuth === true;", self.i18n_js)
        self.assertIn("loadPortalAuth({ forceRefresh: forceRefreshAuth })", self.i18n_js)
        self.assertIn("refreshAuth: options.refreshAuth === true", self.i18n_js)
        self.assertIn("refreshAuth: options.refreshAuth === true", self.index_html)
        self.assertIn("index.html?mode=production", self.production_html)
        self.assertIn("if (level > 1) {", self.index_html)

    def test_tag_filter_uses_authorized_filter_tags(self):
        self.assertIn("let portalFilterTags = null;", self.index_html)
        self.assertIn("payload.filterTags", self.index_html)
        self.assertIn("if (portalFilterTags && !portalFilterTags.has(tag)) return;", self.index_html)

    def test_filtered_data_keeps_role_tag_scope_as_base_condition(self):
        self.assertIn("let dataTagFilterActive = false;", self.index_html)
        self.assertIn("payload.dataTagFilterActive", self.index_html)
        self.assertIn("if (dataTagFilterActive) {", self.index_html)
        self.assertIn("if (!permissionTagsForRow(row).some(tag => portalFilterTags.has(tag))) return false;", self.index_html)
        self.assertIn("return effectiveTags.every(tag => rowTags.includes(tag));", self.index_html)
        self.assertIn("function hasActiveRoleTagScope()", self.index_html)
        self.assertIn("else if (selectedTags.length > 0) renderTagEnvironments();", self.index_html)
        self.assertNotIn("selectedTags.length > 0 || hasActiveRoleTagScope()", self.index_html)
        self.assertIn("selectedTags.length === 0 && !hasActiveRoleTagScope()", self.index_html)
        self.assertIn("clearBtn.textContent = t('filter.clear');", self.index_html)
        self.assertNotIn("clearBtn.textContent = 'All';", self.index_html)

    def test_global_tag_filter_keeps_admin_org_actions(self):
        self.assertIn("function orgLevelActionsHtml(orgKey, envGroupName = DEFAULT_ENV_GROUP)", self.index_html)
        self.assertIn("${orgLevelActionsHtml(org.key)}", self.index_html)
        self.assertIn("${orgLevelActionsHtml(selectedOrgKey)}", self.index_html)
        self.assertIn("openOrganizationEdit('${escapeJs(orgKey)}', event)", self.index_html)
        self.assertIn("addEnvironmentToOrg('${escapeJs(orgKey)}', '${escapeJs(envGroupName)}')", self.index_html)
        self.assertIn("openGroupAdd('${escapeJs(orgKey)}', event)", self.index_html)
        self.assertIn("""<div class="active-org-name">${sanitizeHTML(org.label)}</div>
                        ${orgLevelActionsHtml(org.key)}""", self.index_html)

    def test_org_kana_tabs_are_wrapping_links(self):
        self.assertIn(".org-filter-tabs {\n            display: flex;\n            flex-wrap: wrap;", self.index_html)
        self.assertIn("const tab = document.createElement('a');", self.index_html)
        self.assertIn("tab.href = '#';", self.index_html)
        self.assertIn("event.preventDefault();", self.index_html)
        self.assertIn("white-space: nowrap;", self.index_html)
        self.assertNotIn("overflow-x: auto;\n            padding: 0 0.35rem 0.25rem;", self.index_html)
        self.assertNotIn("const tab = document.createElement('button');", self.index_html)

    def test_page_edit_buttons_use_page_specific_permissions(self):
        self.assertIn("function pageCanView(profile)", self.index_html)
        self.assertIn("function pageCanEdit(profile)", self.index_html)
        self.assertIn("canEdit = pageCanEdit(payload);", self.index_html)
        self.assertIn("canEdit = pageCanEdit(result);", self.index_html)
        self.assertIn("if (!profile || profile.role !== 'admin') return false;", self.index_html)
        self.assertIn("Boolean(profile.canViewPortal || profile.canViewProduction)", self.index_html)
        self.assertIn("const canViewPage = pageCanView(payload);", self.index_html)
        self.assertIn("Boolean(profile.canEditProduction)", self.index_html)
        self.assertIn("Boolean(profile.canEditPortal)", self.index_html)
        self.assertIn("function canEditEnvironment(env)", self.index_html)
        self.assertIn("isAuthenticated = canViewPage;", self.index_html)
        self.assertNotIn("payload.canEditPortal || payload.canEdit", self.index_html)
        self.assertNotIn("result.canEditPortal || result.canEdit", self.index_html)
        self.assertIn("index.html?mode=production", self.production_html)

    def test_production_tab_uses_page_scope_and_hides_empty_orgs(self):
        self.assertIn("function rowInPageScope(row)", self.index_html)
        self.assertIn("return pageMode !== 'production' || envPurposeValue(row) === '生産';", self.index_html)
        self.assertIn("function pageScopedData()", self.index_html)
        self.assertIn("return fullData.filter(rowInPageScope);", self.index_html)
        self.assertIn("pageScopedData().forEach(item =>", self.index_html)
        self.assertIn("return pageScopedData().filter(row =>", self.index_html)
        self.assertIn("if (pageMode !== 'production') {", self.index_html)
        self.assertIn("Object.values(envGroupStore.records || {}).forEach(record =>", self.index_html)

    def test_role_admin_keeps_non_admin_roles_read_only(self):
        self.assertIn("const isAdminRole = key === 'admin';", self.role_admin_html)
        self.assertIn("canEditPortal: isAdminRole && requestedEditPortal", self.role_admin_html)
        self.assertIn("canEditProduction: isAdminRole && requestedEditProduction", self.role_admin_html)
        self.assertIn("canManageUsers: isAdminRole && Boolean(role.canManageUsers)", self.role_admin_html)
        self.assertIn("const adminOnlyDisabled = 'disabled';", self.role_admin_html)
        self.assertIn("data-field=\"canEditPortal\" ${role.canEditPortal ? 'checked' : ''} ${adminOnlyDisabled}", self.role_admin_html)
        self.assertIn("data-field=\"canEditProduction\" ${role.canEditProduction ? 'checked' : ''} ${adminOnlyDisabled}", self.role_admin_html)
        self.assertIn("data-field=\"canManageUsers\" ${role.canManageUsers ? 'checked' : ''} ${adminOnlyDisabled}", self.role_admin_html)

    def test_feature_navigation_uses_view_permissions(self):
        self.assertIn('data-feature-nav="portal"', self.index_html)
        self.assertIn('data-feature-nav="production"', self.index_html)
        self.assertIn("index.html?mode=production", self.production_html)
        self.assertIn("function applyFeatureNavigation(profile)", self.i18n_js)
        self.assertIn("portal: Boolean(profile && (profile.canViewPortal || profile.canViewProduction))", self.i18n_js)
        self.assertIn("production: Boolean(profile && profile.canViewProduction)", self.i18n_js)
        self.assertIn("link.hidden = !visible;", self.i18n_js)
        self.assertIn("return Boolean(profile && profile.role === 'admin');", self.i18n_js)
        self.assertNotIn("profile.role === 'admin' || profile.canManageUsers === true", self.i18n_js)

    def test_environment_kind_and_purpose_are_enum_fields(self):
        self.assertIn('"環境種別"', self.index_html)
        self.assertIn('"用途"', self.index_html)
        self.assertIn("const ENV_KIND_OPTIONS = ['社内', '本番'];", self.index_html)
        self.assertIn("const ENV_PURPOSE_OPTIONS = ['生産', '開発', 'テスト', '受入'];", self.index_html)
        self.assertIn("function envKindValue(row)", self.index_html)
        self.assertIn("function envPurposeValue(row)", self.index_html)
        self.assertIn("function renderDimensionChips(row)", self.index_html)
        self.assertIn("'label.envKind': '環境区分'", self.i18n_js)
        self.assertIn("'envPurpose.生産': '生产'", self.i18n_js)
        self.assertIn("if (pageMode === 'production') {", self.index_html)
        self.assertIn("row['用途'] = '生産';", self.index_html)

    def test_structural_tags_are_hidden_from_display_filters_but_kept_for_permission_scope(self):
        self.assertIn("const STRUCTURAL_TAGS = new Set", self.index_html)
        self.assertIn("function tagsForRowRaw(row)", self.index_html)
        self.assertIn("function permissionTagsForRow(row)", self.index_html)
        self.assertIn("return tagsForRowRaw(row).filter(tag => !isStructuralTag(tag));", self.index_html)
        self.assertIn("permissionTagsForRow(row).some(tag => portalFilterTags.has(tag))", self.index_html)
        self.assertIn("const retainedStructuralTags = tagsForRowRaw(beforeEnv).filter(isStructuralTag);", self.index_html)

    def test_password_unlock_input_is_inside_form(self):
        self.assertIn('<form class="modal-content" onsubmit="submitPwdModal(); return false;">', self.index_html)
        self.assertIn('name="rdpUnlockPassword"', self.index_html)
        self.assertIn('autocomplete="current-password"', self.index_html)
        self.assertIn('type="submit" class="primary-btn"', self.index_html)
        self.assertNotIn("onkeypress=\"if(event.key==='Enter') submitPwdModal()\"", self.index_html)


if __name__ == "__main__":
    unittest.main()
