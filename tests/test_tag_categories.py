import unittest

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


class TagStoreCompatibilityTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
