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
