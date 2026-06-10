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

    def test_proxy_admin_loads_roles_without_active_proxy(self):
        self.assertIn("roles_data.jsp", self.proxy_admin_html)
        self.assertIn("skipProxyRole: true", self.proxy_admin_html)
        self.assertIn("setPortalProxyRole(roleKey)", self.proxy_admin_html)
        self.assertIn("function escapeHtml(value)", self.proxy_admin_html)
        self.assertIn("function escapeJs(value)", self.proxy_admin_html)

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

    def test_page_edit_buttons_use_page_specific_permissions(self):
        self.assertIn("canEdit = Boolean(payload && payload.canEditPortal);", self.index_html)
        self.assertIn("canEdit = Boolean(result && result.canEditPortal);", self.index_html)
        self.assertNotIn("payload.canEditPortal || payload.canEdit", self.index_html)
        self.assertNotIn("result.canEditPortal || result.canEdit", self.index_html)

        self.assertIn("canEdit = Boolean(payload && payload.canEditProduction);", self.production_html)
        self.assertIn("canEdit = Boolean(result && result.canEditProduction);", self.production_html)
        self.assertNotIn("payload.canEditProduction || payload.canEdit", self.production_html)
        self.assertNotIn("result.canEditProduction || result.canEdit", self.production_html)


if __name__ == "__main__":
    unittest.main()
