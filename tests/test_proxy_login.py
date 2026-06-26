import unittest
from unittest import mock

import server


class ProxyLoginTest(unittest.TestCase):
    def roles(self):
        return {
            "admin": server.normalize_role_record("admin", {}),
            "staff": server.normalize_role_record("staff", {}),
            "viewer": server.normalize_role_record("viewer", {
                "label": "Viewer",
                "canViewPortal": True,
                "canEditPortal": False,
                "canViewProduction": False,
                "canEditProduction": False,
                "canManageUsers": False,
                "dataTags": ["OneHR"],
            }),
        }

    def admin_profile(self):
        return {
            "user": "x02851",
            "displayName": "Admin User",
            "role": "admin",
            "canViewPortal": True,
            "canEditPortal": True,
            "canViewProduction": True,
            "canEditProduction": True,
            "canEdit": True,
            "canManageUsers": True,
        }

    def staff_profile(self):
        return {
            "user": "x03047",
            "displayName": "Staff User",
            "role": "staff",
            "canViewPortal": True,
            "canEditPortal": False,
            "canViewProduction": False,
            "canEditProduction": False,
            "canEdit": False,
            "canManageUsers": False,
        }

    def test_non_admin_proxy_role_is_ignored(self):
        with mock.patch.object(server, "load_roles", self.roles):
            profile = server.apply_proxy_role(self.staff_profile(), "admin")

        self.assertFalse(profile.get("isProxyLogin", False))
        self.assertEqual(profile["role"], "staff")
        self.assertFalse(profile["canManageUsers"])

    def test_admin_proxy_role_switches_effective_permissions(self):
        with mock.patch.object(server, "load_roles", self.roles):
            profile = server.apply_proxy_role(self.admin_profile(), "viewer")

        self.assertTrue(profile["isProxyLogin"])
        self.assertEqual(profile["actualUser"], "x02851")
        self.assertEqual(profile["actualDisplayName"], "Admin User")
        self.assertEqual(profile["role"], "viewer")
        self.assertEqual(profile["proxyRole"], "viewer")
        self.assertEqual(profile["proxyRoleLabel"], "Viewer")
        self.assertTrue(profile["canViewPortal"])
        self.assertFalse(profile["canEditPortal"])
        self.assertFalse(profile["canManageUsers"])

    def test_admin_proxy_to_non_admin_role_stays_read_only_even_if_role_has_edit_flags(self):
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "editor": server.normalize_role_record("editor", {
                "label": "Editor",
                "canViewPortal": False,
                "canEditPortal": True,
                "canViewProduction": False,
                "canEditProduction": True,
                "canManageUsers": True,
            }),
        }

        with mock.patch.object(server, "load_roles", lambda: roles):
            profile = server.apply_proxy_role(self.admin_profile(), "editor")

        self.assertTrue(profile["isProxyLogin"])
        self.assertEqual(profile["role"], "editor")
        self.assertTrue(profile["canViewPortal"])
        self.assertFalse(profile["canEditPortal"])
        self.assertTrue(profile["canViewProduction"])
        self.assertFalse(profile["canEditProduction"])
        self.assertFalse(profile["canEdit"])
        self.assertFalse(profile["canManageUsers"])

    def test_invalid_proxy_role_is_ignored(self):
        with mock.patch.object(server, "load_roles", self.roles):
            profile = server.apply_proxy_role(self.admin_profile(), "missing")

        self.assertFalse(profile.get("isProxyLogin", False))
        self.assertEqual(profile["role"], "admin")

    def test_proxy_role_data_permission_filters_portal_rows(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A", "URL": "http://a", "ログインID": "a"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B", "URL": "http://b", "ログインID": "b"},
        ]
        tags_json = {
            server.row_key(rows[0]): ["OneHR"],
            server.row_key(rows[1]): ["Other"],
        }

        with mock.patch.object(server, "load_roles", self.roles):
            profile = server.apply_proxy_role(self.admin_profile(), "viewer")
            visible = server.portal_rows_for_role(rows, tags_json, [], profile["role"], ["OneHR", "Other"])

        self.assertEqual(visible, [rows[0]])

    def test_proxy_role_data_permission_uses_or_within_category_and_and_between_categories(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A", "URL": "http://a", "ログインID": "a"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B", "URL": "http://b", "ログインID": "b"},
            {"組織コード": "3", "組織名": "C", "構築環境名": "C", "URL": "http://c", "ログインID": "c"},
            {"組織コード": "4", "組織名": "D", "構築環境名": "D", "URL": "http://d", "ログインID": "d"},
        ]
        tags_json = {
            server.row_key(rows[0]): ["UHR", "社内"],
            server.row_key(rows[1]): ["PHR", "受入"],
            server.row_key(rows[2]): ["UHR", "デモ"],
            server.row_key(rows[3]): ["Oracle", "社内"],
        }
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "scoped": server.normalize_role_record("scoped", {
                "canViewPortal": True,
                "dataTags": ["UHR", "PHR", "社内", "受入"],
            }),
        }
        categories = server.normalize_tag_categories_config({
            "categories": [
                {"id": "product", "label": "製品"},
                {"id": "environment", "label": "環境"},
            ],
            "assignments": {
                "UHR": "product",
                "PHR": "product",
                "社内": "environment",
                "受入": "environment",
                "デモ": "environment",
                "Oracle": "software",
            },
        }, ["UHR", "PHR", "社内", "受入", "デモ", "Oracle"])

        with mock.patch.object(server, "load_roles", lambda: roles), \
                mock.patch.object(server, "read_tag_categories_json", lambda known_tags=None: categories):
            visible = server.portal_rows_for_role(
                rows,
                tags_json,
                [],
                "scoped",
                ["UHR", "PHR", "社内", "受入", "デモ", "Oracle"],
            )

        self.assertEqual(visible, [rows[0], rows[1]])

    def test_role_data_permission_matches_organization_tags_but_returns_matching_rows(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A1", "URL": "http://a1", "ログインID": "a1"},
            {"組織コード": "1", "組織名": "A", "構築環境名": "A2", "URL": "http://a2", "ログインID": "a2"},
            {"組織コード": "1", "組織名": "A", "構築環境名": "A3", "URL": "http://a3", "ログインID": "a3"},
            {"組織コード": "1", "組織名": "A", "構築環境名": "A4", "URL": "http://a4", "ログインID": "a4"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B1", "URL": "http://b1", "ログインID": "b1"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B2", "URL": "http://b2", "ログインID": "b2"},
        ]
        tags_json = {
            server.row_key(rows[0]): ["UHR"],
            server.row_key(rows[1]): ["V6"],
            server.row_key(rows[2]): ["社内"],
            server.row_key(rows[3]): ["無関係"],
            server.row_key(rows[4]): ["UHR"],
            server.row_key(rows[5]): ["V6"],
        }
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "scoped": server.normalize_role_record("scoped", {
                "canViewPortal": True,
                "dataTags": ["UHR", "V6", "社内"],
            }),
        }
        categories = server.normalize_tag_categories_config({
            "categories": [
                {"id": "product", "label": "製品"},
                {"id": "version", "label": "版本"},
                {"id": "environment", "label": "環境"},
            ],
            "assignments": {
                "UHR": "product",
                "V6": "version",
                "社内": "environment",
                "無関係": "other",
            },
        }, ["UHR", "V6", "社内", "無関係"])

        with mock.patch.object(server, "load_roles", lambda: roles), \
                mock.patch.object(server, "read_tag_categories_json", lambda known_tags=None: categories):
            visible = server.portal_rows_for_role(
                rows,
                tags_json,
                [],
                "scoped",
                ["UHR", "V6", "社内", "無関係"],
            )

        self.assertEqual(visible, rows[:3])

    def test_admin_role_data_permission_still_returns_all_rows(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A1", "URL": "http://a1", "ログインID": "a1"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B1", "URL": "http://b1", "ログインID": "b1"},
        ]
        roles = {
            "admin": server.normalize_role_record("admin", {}),
        }

        with mock.patch.object(server, "load_roles", lambda: roles):
            visible = server.portal_rows_for_role(rows, {}, [], "admin", [])

        self.assertEqual(visible, rows)

    def test_role_with_all_data_tags_still_uses_data_filter(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A1", "URL": "http://a1", "ログインID": "a1"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B1", "URL": "http://b1", "ログインID": "b1"},
            {"組織コード": "3", "組織名": "C", "構築環境名": "C1", "URL": "http://c1", "ログインID": "c1"},
        ]
        tags_json = {
            server.row_key(rows[0]): ["UHR"],
            server.row_key(rows[1]): ["社内"],
            server.row_key(rows[2]): ["無関係"],
        }
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "watcher": server.normalize_role_record("watcher", {
                "canViewPortal": True,
                "dataTags": ["UHR", "社内", "無関係"],
            }),
        }
        known_tags = ["UHR", "社内", "無関係"]

        with mock.patch.object(server, "load_roles", lambda: roles):
            visible = server.portal_rows_for_role(rows, tags_json, [], "watcher", known_tags)
            filter_tags = server.portal_filter_tags_for_role("watcher", known_tags)
            active = server.role_uses_data_tag_filter("watcher", known_tags)

        self.assertEqual(visible, rows)
        self.assertEqual(filter_tags, known_tags)
        self.assertTrue(active)

    def test_role_with_partial_data_tags_keeps_scope_when_other_filters_change(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A1", "URL": "http://a1", "ログインID": "a1"},
            {"組織コード": "2", "組織名": "B", "構築環境名": "B1", "URL": "http://b1", "ログインID": "b1"},
            {"組織コード": "3", "組織名": "C", "構築環境名": "C1", "URL": "http://c1", "ログインID": "c1"},
        ]
        tags_json = {
            server.row_key(rows[0]): ["UHR", "社内"],
            server.row_key(rows[1]): ["PHR", "社内"],
            server.row_key(rows[2]): ["UHR", "デモ"],
        }
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "watcher": server.normalize_role_record("watcher", {
                "canViewPortal": True,
                "dataTags": ["UHR"],
            }),
        }

        with mock.patch.object(server, "load_roles", lambda: roles):
            scoped_rows = server.portal_rows_for_role(rows, tags_json, [], "watcher", ["UHR", "PHR", "社内", "デモ"])

        self.assertEqual(scoped_rows, [rows[0], rows[2]])
    def test_role_with_no_effective_data_tags_allows_initial_empty_tag_state(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A1", "URL": "http://a1", "ログインID": "a1"},
        ]
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "empty": server.normalize_role_record("empty", {
                "canViewPortal": True,
                "dataTags": [],
            }),
        }

        with mock.patch.object(server, "load_roles", lambda: roles):
            visible = server.portal_rows_for_role(rows, {}, [], "empty", [])
            active = server.role_uses_data_tag_filter("empty", [])

        self.assertEqual(visible, rows)
        self.assertFalse(active)

    def test_role_with_no_effective_data_tags_still_returns_no_rows(self):
        rows = [
            {"組織コード": "1", "組織名": "A", "構築環境名": "A1", "URL": "http://a1", "ログインID": "a1"},
        ]
        roles = {
            "admin": server.normalize_role_record("admin", {}),
            "empty": server.normalize_role_record("empty", {
                "canViewPortal": True,
                "dataTags": [],
            }),
        }

        with mock.patch.object(server, "load_roles", lambda: roles):
            visible = server.portal_rows_for_role(rows, {}, [], "empty", ["UHR"])

        self.assertEqual(visible, [])

    def test_proxy_role_filter_tags_expose_only_authorized_tags(self):
        with mock.patch.object(server, "load_roles", self.roles):
            profile = server.apply_proxy_role(self.admin_profile(), "viewer")
            filter_tags = server.portal_filter_tags_for_role(profile["role"], ["OneHR", "Other"])

        self.assertEqual(filter_tags, ["OneHR"])

    def test_proxy_role_marks_data_tag_filter_active(self):
        with mock.patch.object(server, "load_roles", self.roles):
            profile = server.apply_proxy_role(self.admin_profile(), "viewer")

            self.assertTrue(server.role_uses_data_tag_filter(profile["role"]))
            self.assertFalse(server.role_uses_data_tag_filter("admin"))


if __name__ == "__main__":
    unittest.main()



