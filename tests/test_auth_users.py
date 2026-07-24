import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import server


class ForcedAdminUsersTest(unittest.TestCase):
    def roles(self):
        return {
            "admin": server.normalize_role_record("admin", {}),
            "staff": server.normalize_role_record("staff", {}),
        }

    def test_forced_admin_user_is_created_as_admin(self):
        users = {}

        def save(next_users):
            users.clear()
            users.update(next_users)

        with mock.patch.object(server, "load_users", lambda: dict(users)), \
                mock.patch.object(server, "save_users", save), \
                mock.patch.object(server, "load_roles", self.roles), \
                mock.patch.object(server, "FORCED_ADMIN_USERS", "x02851"):
            profile = server.user_profile_for("x02851", is_initial_admin=False)

        self.assertEqual(profile["role"], "admin")
        self.assertTrue(profile["canManageUsers"])
        self.assertEqual(users["x02851"]["role"], "admin")

    def test_forced_admin_user_existing_staff_record_is_corrected(self):
        users = {
            "x02851": {
                "user": "x02851",
                "displayName": "x02851",
                "role": "staff",
            }
        }

        def save(next_users):
            users.clear()
            users.update(next_users)

        with mock.patch.object(server, "load_users", lambda: dict(users)), \
                mock.patch.object(server, "save_users", save), \
                mock.patch.object(server, "load_roles", self.roles), \
                mock.patch.object(server, "FORCED_ADMIN_USERS", "x02851"):
            profile = server.user_profile_for("TOKYO\\X02851", is_initial_admin=False)

        self.assertEqual(profile["role"], "admin")
        self.assertTrue(profile["canManageUsers"])
        self.assertEqual(users["x02851"]["role"], "admin")


class MachineAccountUsersTest(unittest.TestCase):
    def roles(self):
        return {
            "admin": server.normalize_role_record("admin", {}),
            "staff": server.normalize_role_record("staff", {}),
        }

    def test_machine_account_is_not_auto_registered(self):
        users = {}

        def save(next_users):
            users.clear()
            users.update(next_users)

        with mock.patch.object(server, "load_users", lambda: dict(users)), \
                mock.patch.object(server, "save_users", save), \
                mock.patch.object(server, "load_roles", self.roles):
            profile = server.user_profile_for("WIN-BG8F1P9AMB0$", client_ip="127.0.0.1")

        self.assertEqual(profile["user"], "win-bg8f1p9amb0$")
        self.assertFalse(profile["canViewPortal"])
        self.assertFalse(profile["canManageUsers"])
        self.assertEqual(users, {})

    def test_machine_accounts_are_excluded_from_human_user_payload(self):
        users = {
            "x02851": {"user": "x02851", "role": "admin"},
            "win-bg8f1p9amb0$": {"user": "win-bg8f1p9amb0$", "role": "staff"},
        }

        filtered = server.human_users(users)

        self.assertIn("x02851", filtered)
        self.assertNotIn("win-bg8f1p9amb0$", filtered)


class OneOpsSsoBridgeTest(unittest.TestCase):
    def test_domain_proxy_uses_upn_when_ad_mail_is_empty(self):
        source = (
            Path(server.BASE_DIR)
            / "tools"
            / "domain-proxy"
            / "Program.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("PropertiesToLoad.Add('userPrincipalName')", source)
        self.assertIn("email = if ($mail) { $mail } else { $userPrincipalName }", source)
        self.assertIn('Email = ReadJsonString(root, "email")', source)

    def test_first_domain_visit_persists_ad_profile_fields(self):
        users = {}
        metadata = {
            "displayName": "孫 少宣",
            "email": "sun.shaoxuan@onehr.jp",
            "department": "技術部",
            "title": "担当",
        }

        def save(next_users):
            users.clear()
            users.update(next_users)

        with mock.patch.object(server, "load_users", lambda: dict(users)), \
                mock.patch.object(server, "save_users", save), \
                mock.patch.object(server, "load_roles", lambda: {
                    "staff": server.normalize_role_record("staff", {}),
                }), \
                mock.patch.object(server, "FORCED_ADMIN_USERS", ""):
            profile = server.user_profile_for(
                "ONEHR\\x02851",
                client_ip="192.168.20.100",
                metadata=metadata,
            )

        self.assertEqual(profile["displayName"], "孫 少宣")
        self.assertEqual(profile["email"], "sun.shaoxuan@onehr.jp")
        self.assertEqual(profile["department"], "技術部")
        self.assertEqual(profile["title"], "担当")
        self.assertEqual(users["x02851"]["email"], "sun.shaoxuan@onehr.jp")

    def test_bridge_posts_only_signed_token_and_safe_return_path(self):
        page = server.oneops_sso_form(
            {
                "ok": True,
                "user": "ONEHR\\x02851",
                "displayName": "孫 少宣",
                "email": "sun.shaoxuan@onehr.jp",
                "authToken": "signed-token",
            },
            "/environments",
        )

        self.assertIn('method="post"', page)
        self.assertIn('value="signed-token"', page)
        self.assertIn('value="/environments"', page)
        self.assertNotIn("孫 少宣", page)
        self.assertNotIn("sun.shaoxuan@onehr.jp", page)

    def test_bridge_rejects_machine_accounts_and_missing_tokens(self):
        with self.assertRaises(ValueError):
            server.oneops_sso_form(
                {"ok": True, "user": "SERVER$", "authToken": "signed-token"},
                "/",
            )
        with self.assertRaises(ValueError):
            server.oneops_sso_form({"ok": True, "user": "x02851"}, "/")

    def test_bridge_rejects_external_return_paths(self):
        page = server.oneops_sso_form(
            {"ok": True, "user": "x02851", "authToken": "signed-token"},
            "//outside.example/path",
        )

        self.assertIn('name="returnTo" value="/"', page)


class RolePermissionNormalizationTest(unittest.TestCase):
    def test_non_admin_edit_flags_become_read_only_view_permissions(self):
        role = server.normalize_role_record("import_staff", {
            "label": "Import",
            "canViewPortal": False,
            "canEditPortal": True,
            "canViewProduction": False,
            "canEditProduction": True,
            "canEdit": True,
            "canManageUsers": True,
            "dataTags": ["OneHR"],
        })

        self.assertTrue(role["canViewPortal"])
        self.assertFalse(role["canEditPortal"])
        self.assertTrue(role["canViewProduction"])
        self.assertFalse(role["canEditProduction"])
        self.assertFalse(role["canEdit"])
        self.assertFalse(role["canManageUsers"])
        self.assertEqual(role["dataTags"], ["OneHR"])

    def test_save_roles_strips_non_admin_edit_and_management_flags(self):
        with TemporaryDirectory() as tmp:
            roles_path = Path(tmp) / "roles.json"
            with mock.patch.object(server, "ROLES_PATH", roles_path):
                server.save_roles({
                    "admin": server.normalize_role_record("admin", {}),
                    "editor": {
                        "key": "editor",
                        "label": "Editor",
                        "canViewPortal": False,
                        "canEditPortal": True,
                        "canViewProduction": False,
                        "canEditProduction": True,
                        "canManageUsers": True,
                        "dataTags": ["UHR"],
                    },
                })
                loaded = server.load_json_file(roles_path, {})

        editor = loaded["editor"]
        self.assertTrue(editor["canViewPortal"])
        self.assertFalse(editor["canEditPortal"])
        self.assertTrue(editor["canViewProduction"])
        self.assertFalse(editor["canEditProduction"])
        self.assertFalse(editor["canEdit"])
        self.assertFalse(editor["canManageUsers"])
        self.assertEqual(editor["dataTags"], ["UHR"])


class UsersFileRecoveryTest(unittest.TestCase):
    def test_load_json_file_recovers_from_latest_valid_backup(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            users_path = base_dir / "users.json"
            users_path.write_text("{invalid json", encoding="utf-8")
            older = base_dir / "users.json.bak_old"
            older.write_text('{"x00001": {"user": "x00001", "role": "staff"}}', encoding="utf-8")
            newer = base_dir / "users.json.bak_new"
            newer.write_text('{"x02851": {"user": "x02851", "role": "admin"}}', encoding="utf-8")
            os.utime(older, (1000, 1000))
            os.utime(newer, (2000, 2000))

            with mock.patch.object(server, "BASE_DIR", base_dir):
                loaded = server.load_json_file(users_path, {})

        self.assertEqual(sorted(loaded), ["x02851"])
        self.assertEqual(loaded["x02851"]["role"], "admin")

    def test_load_users_recovers_and_filters_machine_accounts(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            users_path = base_dir / "users.json"
            users_path.write_text("{invalid json", encoding="utf-8")
            backup = base_dir / "users.json.bak_valid"
            backup.write_text(
                '{"x02851": {"user": "x02851", "role": "admin"}, '
                '"win-bg8f1p9amb0$": {"user": "win-bg8f1p9amb0$", "role": "staff"}}',
                encoding="utf-8",
            )

            with mock.patch.object(server, "BASE_DIR", base_dir), \
                    mock.patch.object(server, "USERS_PATH", users_path):
                loaded = server.load_users()

        self.assertEqual(sorted(loaded), ["x02851"])

    def test_save_users_filters_machine_accounts(self):
        with TemporaryDirectory() as tmp:
            users_path = Path(tmp) / "users.json"
            users = {
                "x02851": {"user": "x02851", "role": "admin"},
                "win-bg8f1p9amb0$": {"user": "win-bg8f1p9amb0$", "role": "staff"},
            }

            with mock.patch.object(server, "USERS_PATH", users_path):
                server.save_users(users)
                loaded = server.load_users()

        self.assertEqual(sorted(loaded), ["x02851"])

    def test_write_json_file_creates_backup_and_replaces_atomically(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            path = base_dir / "roles.json"
            path.write_text('{"staff": {"key": "staff"}}\n', encoding="utf-8")

            with mock.patch.object(server, "BASE_DIR", base_dir):
                server.write_json_file(path, {"admin": {"key": "admin"}})
                loaded = server.load_json_file(path, {})
                backups = list(base_dir.glob("roles.json.bak_autosave_*"))

        self.assertEqual(sorted(loaded), ["admin"])
        self.assertEqual(len(backups), 1)

    def test_write_csv_records_creates_backup_and_replaces_atomically(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            path = base_dir / "data.csv"
            path.write_text("name\nold\n", encoding="utf-8-sig")

            with mock.patch.object(server, "BASE_DIR", base_dir):
                server.write_csv_records("data.csv", ["name"], [{"name": "new"}])
                loaded = server.read_csv_records("data.csv", ["name"])
                backups = list(base_dir.glob("data.csv.bak_autosave_*"))

        self.assertEqual(loaded, [{"name": "new"}])
        self.assertEqual(len(backups), 1)

    def test_count_csv_text_rows_rejects_missing_header_fields(self):
        with self.assertRaises(ValueError):
            server.count_csv_text_rows("name\nold\n", ["name", "url"])

    def test_count_csv_text_rows_counts_empty_and_non_empty_payloads(self):
        self.assertEqual(server.count_csv_text_rows("name,url\n", ["name", "url"]), 0)
        self.assertEqual(server.count_csv_text_rows("name,url\na,http://a\n", ["name", "url"]), 1)


if __name__ == "__main__":
    unittest.main()
