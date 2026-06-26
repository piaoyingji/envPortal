import unittest

import server


class LegacyProductionCompatibilityTest(unittest.TestCase):
    def production_row(self):
        return {
            "組織名": "森林整備センター",
            "構築環境名": "UHR",
            "使用VPN": "社内サーバー",
            "VPN IP": "192.168.20.232",
            "VPNユーザー名": "NS0141\\NS0141",
            "VPNパスワード": "vpn-pass",
            "踏み台IP": "10.132.4.4",
            "踏み台ユーザー名": "administrator",
            "踏み台パスワード": "bastion-pass",
            "AP IP": "10.148.0.142",
            "APユーザー名": "ap-user",
            "APパスワード": "ap-pass",
            "DB IP": "10.148.0.143",
            "DBユーザー名": "db-user",
            "DBパスワード": "db-pass",
        }

    def test_legacy_production_csv_is_converted_to_portal_records(self):
        data_rows, rdp_rows = server.merge_legacy_production_records([], [], [self.production_row()])

        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0]["組織名"], "森林整備センター")
        self.assertEqual(data_rows[0]["構築環境名"], "UHR")
        self.assertEqual(data_rows[0]["環境グループ"], server.DEFAULT_ENV_GROUP)
        self.assertEqual(data_rows[0]["環境種別"], "本番")
        self.assertEqual(data_rows[0]["用途"], "生産")
        self.assertEqual(data_rows[0]["URL"], "10.148.0.142")
        self.assertEqual(data_rows[0]["ログインID"], "ap-user")
        self.assertEqual(data_rows[0]["ログインパスワード"], "ap-pass")
        self.assertEqual(data_rows[0]["DB名"], "10.148.0.143")
        self.assertEqual(data_rows[0]["DBユーザー名"], "db-user")
        self.assertEqual(data_rows[0]["DBパスワード"], "db-pass")

        names = {row["サーバ名"] for row in rdp_rows}
        self.assertEqual(names, {"VPN", "踏み台", "AP", "DB"})
        self.assertIn("10.148.0.142", {row["接続先(IP:Port)"] for row in rdp_rows})

    def test_existing_unified_production_record_is_not_duplicated(self):
        existing = {
            "組織コード": "",
            "組織名": "森林整備センター",
            "環境グループ": "本番",
            "環境種別": "本番",
            "用途": "生産",
            "構築環境名": "UHR",
            "URL": "10.148.0.142",
            "ログインID": "",
            "ログインパスワード": "",
            "DBタイプ": "",
            "DBバージョン": "",
            "DB名": "",
            "DBユーザー名": "",
            "DBパスワード": "",
        }

        data_rows, _ = server.merge_legacy_production_records([existing], [], [self.production_row()])

        self.assertEqual(len(data_rows), 1)
        self.assertIs(data_rows[0], existing)

    def test_view_permission_filter_keeps_production_records_on_production_permission(self):
        production = server.legacy_production_data_row(self.production_row())
        portal = {
            "組織名": "筑波大学",
            "構築環境名": "UHR",
            "環境種別": "社内",
            "用途": "テスト",
        }

        production_only = server.portal_rows_for_view_permissions(
            [production, portal],
            {"canViewPortal": False, "canViewProduction": True},
        )
        portal_only = server.portal_rows_for_view_permissions(
            [production, portal],
            {"canViewPortal": True, "canViewProduction": False},
        )

        self.assertEqual(production_only, [production])
        self.assertEqual(portal_only, [portal])

    def test_view_permission_filter_treats_both_permissions_as_superset(self):
        production = server.legacy_production_data_row(self.production_row())
        portal = {
            "組織名": "筑波大学",
            "構築環境名": "UHR",
            "環境種別": "社内",
            "用途": "テスト",
        }

        rows = server.portal_rows_for_view_permissions(
            [production, portal],
            {"canViewPortal": True, "canViewProduction": True},
        )

        self.assertEqual(rows, [production, portal])


if __name__ == "__main__":
    unittest.main()
