import unittest
from pathlib import Path


class FrontendStaticBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_html = Path("index.html").read_text(encoding="utf-8")

    def test_environment_rendering_uses_product_display_order(self):
        self.assertIn("function environmentDisplayRank(row)", self.index_html)
        self.assertIn("function sortEnvironmentsByDisplayOrder(envs)", self.index_html)
        self.assertIn("sortEnvironmentsByDisplayOrder(envs).forEach((env, index)", self.index_html)
        self.assertIn("sortEnvironmentsByDisplayOrder(envs).forEach(env =>", self.index_html)
        self.assertIn("const orderedEnvs = sortEnvironmentsByDisplayOrder(envs);", self.index_html)

    def test_inline_expand_uses_sorted_environment_order(self):
        sorted_lookup = "sortEnvironmentsByDisplayOrder(getFilteredData().filter"
        self.assertGreaterEqual(self.index_html.count(sorted_lookup), 2)


if __name__ == "__main__":
    unittest.main()
