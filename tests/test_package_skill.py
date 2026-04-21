import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.package_skill import main, should_exclude


class PackageSkillTest(unittest.TestCase):
    def test_should_exclude_paths(self):
        self.assertTrue(should_exclude(Path(".git/config")))
        self.assertTrue(should_exclude(Path("dist/output.skill")))
        self.assertTrue(should_exclude(Path("foo/__pycache__/bar.pyc")))
        self.assertFalse(should_exclude(Path("README.md")))

    def test_package_contains_core_files(self):
        repo_root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "skill.skill"
            old_argv = sys.argv
            sys.argv = ["package_skill.py", "--repo-root", str(repo_root), "--output", str(out)]
            try:
                self.assertEqual(main(), 0)
            finally:
                sys.argv = old_argv

            with ZipFile(out) as zf:
                names = set(zf.namelist())
                self.assertIn("README.md", names)
                self.assertIn(".github/workflows/ci.yml", names)
                self.assertIn("skills/results-db/SKILL.md", names)


if __name__ == "__main__":
    unittest.main()
