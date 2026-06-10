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


if __name__ == "__main__":
    unittest.main()
