import unittest
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


if __name__ == "__main__":
    unittest.main()
