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
