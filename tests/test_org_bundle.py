import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import server


class OrganizationBundleUpdateTest(unittest.TestCase):
    def write_portal_files(self, base_dir, rows=None):
        rows = rows or [{
            "組織コード": "0408",
            "組織名": "筑波大学",
            "環境グループ": "UHR",
            "構築環境名": "本番",
            "URL": "http://example/login",
            "ログインID": "user",
        }]
        with mock.patch.object(server, "BASE_DIR", base_dir):
            server.write_csv_records("data.csv", server.PORTAL_CSV_FIELDS, rows)
            server.write_csv_records("rdp.csv", server.RDP_CSV_FIELDS, [{
                "組織名": "筑波大学",
                "サーバ名": "AP/DB共用",
                "接続タイプ": "RDP",
                "RDPユーザー名": "rdp",
                "RDPパスワード": "pass",
                "接続先(IP:Port)": "10.0.0.1:3389",
            }])

    def run_update(self, base_dir, before_org, after_org):
        with mock.patch.object(server, "BASE_DIR", base_dir), \
                mock.patch.object(server, "ENV_GROUPS_PATH", base_dir / "env_groups.json"):
            return server.update_org_bundle_files(before_org, after_org)

    def test_updates_only_organization_code_and_moves_related_keys(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            self.write_portal_files(base_dir)
            (base_dir / "tags.json").write_text(json.dumps({
                "0408||筑波大学||本番||http://example/login||user": ["A"]
            }, ensure_ascii=False), encoding="utf-8-sig")
            (base_dir / "env_groups.json").write_text(json.dumps({
                "records": {
                    "0408": {
                        "key": "0408",
                        "code": "0408",
                        "name": "筑波大学",
                        "groups": ["UHR"],
                    }
                }
            }, ensure_ascii=False), encoding="utf-8-sig")

            data_rows, _, tags_json, env_groups, changed_count = self.run_update(
                base_dir,
                {"key": "0408", "code": "0408", "name": "筑波大学"},
                {"key": "9999", "code": "9999", "name": "筑波大学"},
            )

        self.assertEqual(changed_count, 1)
        self.assertEqual(data_rows[0]["組織コード"], "9999")
        self.assertIn("9999||筑波大学||本番||http://example/login||user", tags_json)
        self.assertNotIn("0408||筑波大学||本番||http://example/login||user", tags_json)
        self.assertIn("9999", env_groups["records"])
        self.assertNotIn("0408", env_groups["records"])

    def test_updates_code_and_name_for_data_rdp_tags_and_env_groups(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            self.write_portal_files(base_dir)
            (base_dir / "tags.json").write_text(json.dumps({
                "0408||筑波大学||本番||http://example/login||user": ["A"]
            }, ensure_ascii=False), encoding="utf-8-sig")
            (base_dir / "env_groups.json").write_text(json.dumps({
                "records": {"0408": {"key": "0408", "code": "0408", "name": "筑波大学", "groups": ["UHR"]}}
            }, ensure_ascii=False), encoding="utf-8-sig")

            data_rows, rdp_rows, tags_json, env_groups, changed_count = self.run_update(
                base_dir,
                {"key": "0408", "code": "0408", "name": "筑波大学"},
                {"key": "9999", "code": "9999", "name": "東京大学"},
            )

        self.assertEqual(changed_count, 1)
        self.assertEqual(data_rows[0]["組織コード"], "9999")
        self.assertEqual(data_rows[0]["組織名"], "東京大学")
        self.assertEqual(rdp_rows[0]["組織名"], "東京大学")
        self.assertEqual(rdp_rows[0]["サーバ名"], "AP/DB共用")
        self.assertIn("9999||東京大学||本番||http://example/login||user", tags_json)
        self.assertEqual(env_groups["records"]["9999"]["name"], "東京大学")

    def test_rejects_existing_target_organization_code_without_writing(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            self.write_portal_files(base_dir, rows=[
                {"組織コード": "0408", "組織名": "筑波大学", "構築環境名": "本番"},
                {"組織コード": "9999", "組織名": "東京大学", "構築環境名": "検証"},
            ])
            (base_dir / "tags.json").write_text("{}", encoding="utf-8-sig")
            (base_dir / "env_groups.json").write_text("{}", encoding="utf-8-sig")
            before_text = (base_dir / "data.csv").read_text(encoding="utf-8-sig")

            with self.assertRaisesRegex(ValueError, "target organization code already exists"):
                self.run_update(
                    base_dir,
                    {"key": "0408", "code": "0408", "name": "筑波大学"},
                    {"key": "9999", "code": "9999", "name": "筑波大学"},
                )

            after_text = (base_dir / "data.csv").read_text(encoding="utf-8-sig")

        self.assertEqual(after_text, before_text)

    def test_missing_runtime_json_files_are_created(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            self.write_portal_files(base_dir)

            _, _, tags_json, env_groups, changed_count = self.run_update(
                base_dir,
                {"key": "0408", "code": "0408", "name": "筑波大学"},
                {"key": "9999", "code": "9999", "name": "筑波大学"},
            )
            tags_exists = (base_dir / "tags.json").exists()
            env_groups_exists = (base_dir / "env_groups.json").exists()

        self.assertEqual(changed_count, 1)
        self.assertEqual(tags_json, {})
        self.assertIn("9999", env_groups["records"])
        self.assertTrue(tags_exists)
        self.assertTrue(env_groups_exists)

    def test_invalid_runtime_json_returns_clear_error(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            self.write_portal_files(base_dir)
            (base_dir / "tags.json").write_text("{invalid", encoding="utf-8-sig")
            (base_dir / "env_groups.json").write_text("{}", encoding="utf-8-sig")

            with self.assertRaisesRegex(ValueError, "invalid tags.json"):
                self.run_update(
                    base_dir,
                    {"key": "0408", "code": "0408", "name": "筑波大学"},
                    {"key": "9999", "code": "9999", "name": "筑波大学"},
                )


if __name__ == "__main__":
    unittest.main()
