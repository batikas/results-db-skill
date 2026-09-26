"""p is stored empty when not supplied; update --p works; lint skips no_p= rows."""
import csv, os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "skills", "results-db", "scripts", "results_db.py")

def run(db, *args):
    return subprocess.run([sys.executable, CLI, "--db", db, *args], capture_output=True, text=True)

def rows(db):
    with open(db, newline="") as fh:
        return list(csv.DictReader(fh))

class TestPHandling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.db = os.path.join(self.tmp, "results_database.csv")
        run(self.db, "init")

    def test_add_without_p_stores_empty(self):
        r = run(self.db, "add", "--section", "s", "--dv", "y", "--sample", "Full", "--att", "0.1", "--in_paper", "tbd", "--notes", "no_p=breakdown value")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rows(self.db)[0]["p"], "")

    def test_add_with_p_zero_keeps_zero(self):
        run(self.db, "add", "--section", "s", "--dv", "y", "--sample", "Full", "--att", "0.1", "--p", "0.0", "--in_paper", "tbd")
        self.assertEqual(float(rows(self.db)[0]["p"]), 0.0)

    def test_update_p_and_sig(self):
        run(self.db, "add", "--section", "s", "--dv", "y", "--sample", "Full", "--att", "0.1", "--in_paper", "tbd")
        rid = rows(self.db)[0]["id"]
        r = run(self.db, "update", "--id", rid, "--p", "0.04", "--sig", "*")
        self.assertEqual(r.returncode, 0, r.stderr)
        row = rows(self.db)[0]; self.assertEqual(float(row["p"]), 0.04); self.assertEqual(row["sig"], "*")

    def test_lint_skips_no_p_rows(self):
        run(self.db, "add", "--section", "s", "--dv", "y", "--sample", "Full", "--att", "0.1", "--sig", "n.s.", "--in_paper", "appendix", "--notes", "no_p=placebo-in-space rank has no p")
        r = run(self.db, "lint")
        self.assertNotIn("sig=", r.stdout); self.assertNotIn("ERROR", r.stdout)

if __name__ == "__main__":
    unittest.main()
