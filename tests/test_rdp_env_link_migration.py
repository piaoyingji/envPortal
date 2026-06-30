import unittest

import server


def env_row(org="Org", name="EnvA", url="http://10.0.0.10:8080/login", db="10.0.0.20:5432/app"):
    return {
        "組織名": org,
        "構築環境名": name,
        "URL": url,
        "DB名": db,
    }


def rdp_row(org="Org", env="", name="AP", target="10.0.0.10:3389"):
    return {
        "組織名": org,
        "構築環境名": env,
        "サーバ名": name,
        "接続タイプ": "RDP",
        "RDPユーザー名": "user",
        "RDPパスワード": "pass",
        "接続先(IP:Port)": target,
    }


class RdpEnvLinkMigrationTest(unittest.TestCase):
    def test_unique_url_host_fills_environment_name(self):
        rows, report = server.upgrade_rdp_env_links(
            [env_row()],
            [rdp_row(target="10.0.0.10:3389")],
        )

        self.assertEqual(rows[0]["構築環境名"], "EnvA")
        self.assertEqual(report["updatedRows"], 1)
        self.assertEqual(report["dirtyRows"], 0)

    def test_unique_db_host_fills_environment_name_even_when_port_differs(self):
        rows, report = server.upgrade_rdp_env_links(
            [env_row()],
            [rdp_row(name="DB", target="10.0.0.20:3389")],
        )

        self.assertEqual(rows[0]["構築環境名"], "EnvA")
        self.assertEqual(report["updatedRows"], 1)
        self.assertEqual(report["dirtyRows"], 0)

    def test_orphan_rdp_is_reported_without_assignment(self):
        rows, report = server.upgrade_rdp_env_links(
            [env_row()],
            [rdp_row(target="10.0.0.99:3389")],
        )

        self.assertEqual(rows[0]["構築環境名"], "")
        self.assertEqual(report["updatedRows"], 0)
        self.assertEqual(report["dirtyRows"], 1)
        self.assertEqual(report["dirty"][0]["reason"], "orphan-rdp")

    def test_ambiguous_parent_is_reported_without_assignment(self):
        rows, report = server.upgrade_rdp_env_links(
            [
                env_row(name="EnvA", url="http://10.0.0.10:8080/a"),
                env_row(name="EnvB", url="http://10.0.0.10:9090/b"),
            ],
            [rdp_row(target="10.0.0.10:3389")],
        )

        self.assertEqual(rows[0]["構築環境名"], "")
        self.assertEqual(report["dirtyRows"], 1)
        self.assertEqual(report["dirty"][0]["reason"], "ambiguous-parent")
        self.assertEqual({item["env"] for item in report["dirty"][0]["candidates"]}, {"EnvA", "EnvB"})

    def test_existing_invalid_parent_is_reported_dirty(self):
        rows, report = server.upgrade_rdp_env_links(
            [env_row(name="EnvA")],
            [rdp_row(env="MissingEnv")],
        )

        self.assertEqual(rows[0]["構築環境名"], "MissingEnv")
        self.assertEqual(report["updatedRows"], 0)
        self.assertEqual(report["dirtyRows"], 1)
        self.assertEqual(report["dirty"][0]["reason"], "missing-parent")


if __name__ == "__main__":
    unittest.main()
