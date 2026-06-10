import unittest
from pathlib import Path


class FrontendStaticBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_html = Path("index.html").read_text(encoding="utf-8")
        cls.production_html = Path("production.html").read_text(encoding="utf-8")
        cls.i18n_js = Path("i18n.js").read_text(encoding="utf-8")
        cls.proxy_admin_html = Path("proxy-admin.html").read_text(encoding="utf-8")

    def test_environment_rendering_uses_product_display_order(self):
        self.assertIn("function environmentDisplayRank(row)", self.index_html)
        self.assertIn("function sortEnvironmentsByDisplayOrder(envs)", self.index_html)
        self.assertIn("sortEnvironmentsByDisplayOrder(envs).forEach((env, index)", self.index_html)
        self.assertIn("sortEnvironmentsByDisplayOrder(envs).forEach(env =>", self.index_html)
        self.assertIn("const orderedEnvs = sortEnvironmentsByDisplayOrder(envs);", self.index_html)

    def test_inline_expand_uses_sorted_environment_order(self):
        sorted_lookup = "sortEnvironmentsByDisplayOrder(getFilteredData().filter"
        self.assertGreaterEqual(self.index_html.count(sorted_lookup), 2)

    def test_system_menu_contains_proxy_login(self):
        self.assertIn('href="proxy-admin.html"', self.i18n_js)
        self.assertIn("nav.proxyLogin", self.i18n_js)

    def test_portal_fetch_sends_proxy_role_header(self):
        self.assertIn("PORTAL_PROXY_ROLE_STORAGE_KEY", self.i18n_js)
        self.assertIn("X-EnvPortal-Proxy-Role", self.i18n_js)
        self.assertIn("readPortalProxyRole()", self.i18n_js)

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
        self.assertIn("{ cache: 'no-store', refreshAuth: true }", self.i18n_js)
        self.assertIn("{ cache: 'no-store', refreshAuth: true }", self.index_html)
        self.assertIn("{ cache: 'no-store', refreshAuth: true }", self.production_html)
        self.assertIn("if (level > 1) {", self.index_html)

    def test_tag_filter_uses_authorized_filter_tags(self):
        self.assertIn("let portalFilterTags = null;", self.index_html)
        self.assertIn("payload.filterTags", self.index_html)
        self.assertIn("if (portalFilterTags && !portalFilterTags.has(tag)) return;", self.index_html)

    def test_filtered_data_keeps_role_tag_scope_as_base_condition(self):
        self.assertIn("let dataTagFilterActive = false;", self.index_html)
        self.assertIn("payload.dataTagFilterActive", self.index_html)
        self.assertIn("if (dataTagFilterActive) {", self.index_html)
        self.assertIn("if (!rowTags.some(tag => portalFilterTags.has(tag))) return false;", self.index_html)
        self.assertIn("return effectiveTags.every(tag => rowTags.includes(tag));", self.index_html)
        self.assertIn("function hasActiveRoleTagScope()", self.index_html)
        self.assertIn("else if (selectedTags.length > 0) renderTagEnvironments();", self.index_html)
        self.assertNotIn("selectedTags.length > 0 || hasActiveRoleTagScope()", self.index_html)
        self.assertIn("selectedTags.length === 0 && !hasActiveRoleTagScope()", self.index_html)
        self.assertIn("clearBtn.textContent = t('filter.clear');", self.index_html)
        self.assertNotIn("clearBtn.textContent = 'All';", self.index_html)

    def test_page_edit_buttons_use_page_specific_permissions(self):
        self.assertIn("canEdit = Boolean(payload && payload.canEditPortal);", self.index_html)
        self.assertIn("canEdit = Boolean(result && result.canEditPortal);", self.index_html)
        self.assertNotIn("payload.canEditPortal || payload.canEdit", self.index_html)
        self.assertNotIn("result.canEditPortal || result.canEdit", self.index_html)

        self.assertIn("canEdit = Boolean(payload && payload.canEditProduction);", self.production_html)
        self.assertIn("canEdit = Boolean(result && result.canEditProduction);", self.production_html)
        self.assertNotIn("payload.canEditProduction || payload.canEdit", self.production_html)
        self.assertNotIn("result.canEditProduction || result.canEdit", self.production_html)

    def test_feature_navigation_uses_view_permissions(self):
        self.assertIn('data-feature-nav="portal"', self.index_html)
        self.assertIn('data-feature-nav="production"', self.index_html)
        self.assertIn('data-feature-nav="portal"', self.production_html)
        self.assertIn('data-feature-nav="production"', self.production_html)
        self.assertIn("function applyFeatureNavigation(profile)", self.i18n_js)
        self.assertIn("portal: Boolean(profile && profile.canViewPortal)", self.i18n_js)
        self.assertIn("production: Boolean(profile && profile.canViewProduction)", self.i18n_js)
        self.assertIn("link.hidden = !visible;", self.i18n_js)

    def test_password_unlock_input_is_inside_form(self):
        self.assertIn('<form class="modal-content" onsubmit="submitPwdModal(); return false;">', self.index_html)
        self.assertIn('name="rdpUnlockPassword"', self.index_html)
        self.assertIn('autocomplete="current-password"', self.index_html)
        self.assertIn('type="submit" class="primary-btn"', self.index_html)
        self.assertNotIn("onkeypress=\"if(event.key==='Enter') submitPwdModal()\"", self.index_html)


if __name__ == "__main__":
    unittest.main()
