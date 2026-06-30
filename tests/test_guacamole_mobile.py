import unittest
from urllib.parse import parse_qs, urlparse

import server


class GuacamoleMobileConnectionTest(unittest.TestCase):
    def test_quickconnect_uri_uses_dynamic_resize(self):
        uri = server.build_guacamole_uri("192.168.20.10:3389", "user", "pass")
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        self.assertEqual(params.get("resize-method"), ["display-update"])
        self.assertEqual(params.get("enable-wallpaper"), ["false"])


if __name__ == "__main__":
    unittest.main()
