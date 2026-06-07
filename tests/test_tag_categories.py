import unittest
import tempfile
from pathlib import Path
from unittest import mock

import server


class TagCategoryNormalizationTest(unittest.TestCase):
    def test_missing_config_uses_other(self):
        config = server.normalize_tag_categories_config(None, ["UHR"])

        self.assertEqual(config["categories"], [{
            "id": "other",
            "label": "其他",
            "protected": True,
        }])
        self.assertEqual(config["assignments"], {"UHR": "other"})
        self.assertEqual(config["skins"]["other"]["UHR"]["bg"], "#f0fdf4")
        self.assertEqual(config["activeSkinCategory"], "other")

    def test_other_is_fixed_last_and_protected(self):
        config = server.normalize_tag_categories_config({
            "categories": [
                {"id": "other", "label": "renamed", "protected": False},
                {"id": "product", "label": "Product", "protected": True},
            ],
            "assignments": {"UHR": "product"},
        })

        self.assertEqual([category["id"] for category in config["categories"]], ["product", "other"])
        self.assertEqual(config["categories"][-1]["label"], "其他")
        self.assertTrue(config["categories"][-1]["protected"])

    def test_deleted_category_assignments_move_to_other(self):
        config = server.normalize_tag_categories_config({
            "categories": [{"id": "product", "label": "Product"}],
            "assignments": {
                "UHR": "deleted",
                "PHR": "product",
            },
        })

        self.assertEqual(config["assignments"], {
            "UHR": "other",
            "PHR": "product",
        })

    def test_invalid_assignment_is_cleaned(self):
        config = server.normalize_tag_categories_config({
            "categories": [{"id": "product", "label": "Product"}],
            "assignments": {
                "": "product",
                "UHR": "bad value",
            },
        }, ["Oracle"])

        self.assertEqual(config["assignments"], {
            "UHR": "other",
            "Oracle": "other",
        })

    def test_skin_is_category_scoped_and_requires_complete_colors(self):
        config = server.normalize_tag_categories_config({
            "categories": [{"id": "product", "label": "Product"}],
            "activeSkinCategory": "product",
            "assignments": {"UHR": "product", "PHR": "product"},
            "skins": {
                "product": {
                    "UHR": {"bg": "#ABCDEF", "border": "#123456", "accent": "#fedcba"},
                    "PHR": {"bg": "#ffffff"},
                },
                "deleted": {
                    "UPDS-V6": {"bg": "#ffffff", "border": "#eeeeee", "accent": "#111111"},
                },
            },
        }, ["UHR", "PHR", "UPDS-V6"])

        self.assertEqual(config["skins"]["product"]["UHR"], {
            "bg": "#abcdef",
            "border": "#123456",
            "accent": "#fedcba",
        })
        self.assertEqual(config["activeSkinCategory"], "product")
        self.assertEqual(config["skins"]["product"]["PHR"]["bg"], "#eff6ff")
        self.assertEqual(config["skins"]["other"]["UPDS-V6"]["bg"], "#f8fafc")
        self.assertNotIn("deleted", config["skins"])

    def test_invalid_active_skin_category_falls_back_to_other(self):
        config = server.normalize_tag_categories_config({
            "categories": [{"id": "product", "label": "Product"}],
            "activeSkinCategory": "deleted",
        }, ["UHR"])

        self.assertEqual(config["activeSkinCategory"], "other")


class TagStoreCompatibilityTest(unittest.TestCase):
    def test_read_tags_json_returns_dict_when_file_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tags_path = Path(temp_dir) / "tags.json"
            tags_path.write_text('{"row": ["UHR"]}', encoding="utf-8")
            with mock.patch.object(server, "BASE_DIR", Path(temp_dir)):
                tags = server.read_tags_json()

        self.assertEqual(tags, {"row": ["UHR"]})

    def test_tags_for_row_accepts_legacy_array_and_record_object(self):
        row = {
            "組織コード": "TOK",
            "組織名": "東京",
            "構築環境名": "PHR",
            "URL": "http://example.test/login",
            "ログインID": "user",
        }
        key = server.row_key(row)

        self.assertEqual(server.tags_for_row(row, {key: ["UHR", ""]}), ["UHR"])
        self.assertEqual(server.tags_for_row(row, {key: {"tags": ["PHR", "  "]}}), ["PHR"])


class RoleDataPermissionTest(unittest.TestCase):
    def test_auto_tags_include_environment_group_and_product_system(self):
        row = {
            "環境グループ": "UHR-V6",
            "構築環境名": "U-PDS V7-TS2課-社内",
            "URL": "http://example.test/login",
            "DBタイプ": "PostgreSQL",
            "DBバージョン": "16",
        }

        tags = server.auto_tags_for_row(row, [])

        self.assertIn("UHR-V6", tags)
        self.assertIn("UHR", tags)
        self.assertIn("UPDS-V7", tags)
        self.assertNotIn("UPDSV7", tags)

    def test_filter_tag_is_migrated_to_data_tags(self):
        role = server.normalize_role_record("legacy", {"dataTags": "", "filterTag": "OneHR"})

        self.assertEqual(role["dataTags"], ["OneHR"])
        self.assertEqual(role["filterTag"], "OneHR")

    def test_deleted_tag_does_not_match_rows(self):
        row = {
            "組織コード": "TOK",
            "組織名": "東京",
            "構築環境名": "PHR",
            "URL": "http://example.test/login",
            "ログインID": "user",
        }
        role = {"dataTags": ["DeletedTag"], "filterTag": "DeletedTag"}

        self.assertEqual(server.effective_role_data_tags(role, ["OneHR"]), [])

    def test_role_data_permission_matches_manual_and_auto_tags(self):
        row = {
            "組織コード": "TOK",
            "組織名": "東京",
            "構築環境名": "PHR",
            "URL": "http://example.test/login",
            "ログインID": "user",
            "DBタイプ": "PostgreSQL",
            "DBバージョン": "16",
        }
        key = server.row_key(row)

        self.assertIn("OneHR", server.all_tags_for_row(row, {key: ["OneHR"]}, []))
        self.assertIn("PostgreSQL 16", server.all_tags_for_row(row, {key: []}, []))


class EnvironmentGroupConfigTest(unittest.TestCase):
    def test_env_group_config_preserves_explicit_groups_without_forcing_default(self):
        config = server.normalize_env_groups_config({
            "0408": ["UHR-V6", "", "PHR-V7", "UHR-V6"],
        })

        record = config["records"]["0408"]

        self.assertEqual(record["groups"], ["UHR-V6", "PHR-V7"])
        self.assertEqual(record["code"], "0408")

    def test_env_group_config_adds_default_when_group_list_is_empty(self):
        config = server.normalize_env_groups_config({
            "0408": [],
        })

        self.assertEqual(config["records"]["0408"]["groups"], ["デフォルト"])

    def test_env_group_config_accepts_record_shape(self):
        config = server.normalize_env_groups_config({
            "records": {
                "name:OneHR": {
                    "code": "",
                    "name": "OneHR",
                    "groups": ["UPDS-V7"],
                }
            }
        })

        record = config["records"]["name:OneHR"]

        self.assertEqual(record["groups"], ["UPDS-V7"])
        self.assertEqual(record["name"], "OneHR")

    def test_filter_env_groups_keeps_visible_organizations_only(self):
        config = server.normalize_env_groups_config({
            "0408": ["UHR-V6"],
            "0528": ["PHR-V7"],
        })
        rows = [{"組織コード": "0408", "組織名": "筑波大学"}]

        filtered = server.filter_env_groups_for_rows(config, rows)

        self.assertEqual(list(filtered["records"].keys()), ["0408"])

    def test_empty_environment_group_is_default_auto_tag(self):
        row = {"環境グループ": "", "構築環境名": "PHR", "URL": ""}

        tags = server.auto_tags_for_row(row, [])

        self.assertIn("デフォルト", tags)


if __name__ == "__main__":
    unittest.main()
