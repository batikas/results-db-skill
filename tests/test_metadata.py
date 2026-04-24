import json
import unittest
from pathlib import Path


class MetadataConsistencyTest(unittest.TestCase):
    def test_release_versions_match(self):
        root = Path(__file__).resolve().parents[1]
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        citation = (root / "CITATION.cff").read_text(encoding="utf-8").splitlines()

        top_version = next(line.split(":", 1)[1].strip() for line in citation if line.startswith("version:"))
        preferred_version = None
        in_preferred = False
        for line in citation:
            if line.startswith("preferred-citation:"):
                in_preferred = True
                continue
            if in_preferred and line.startswith("  version:"):
                preferred_version = line.split(":", 1)[1].strip()
                break

        self.assertEqual(plugin["version"], version)
        self.assertEqual(marketplace["metadata"]["version"], version)
        self.assertEqual(marketplace["plugins"][0]["version"], version)
        self.assertEqual(marketplace["plugins"][0]["name"], plugin["name"])
        self.assertEqual(top_version, version)
        self.assertEqual(preferred_version, version)


if __name__ == "__main__":
    unittest.main()
