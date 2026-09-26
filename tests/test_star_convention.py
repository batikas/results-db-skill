"""Stars follow the + * ** *** ladder (p<.10, .05, .01, .001), and update --p "" clears a stored p."""
import csv, os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CLI = os.path.join(ROOT, "skills", "results-db", "scripts", "results_db.py")
sys.path.insert(0, os.path.dirname(CLI)); import results_db
def run(db, *a): return subprocess.run([sys.executable, CLI, "--db", db, *a], capture_output=True, text=True)
def rows(db):
    with open(db, newline="") as fh: return list(csv.DictReader(fh))
class TestStars(unittest.TestCase):
    def test_ladder(self):
        f = results_db.sig_from_p
        self.assertEqual((f(0.0005), f(0.005), f(0.03), f(0.07), f(0.2)), ("***", "**", "*", "+", "n.s."))
    def test_update_p_empty_clears(self):
        tmp = tempfile.mkdtemp(); db = os.path.join(tmp, "results_database.csv"); run(db, "init")
        run(db, "add", "--section", "s", "--dv", "y", "--sample", "Full", "--att", "0.1", "--p", "0.03", "--in_paper", "tbd")
        rid = rows(db)[0]["id"]; r = run(db, "update", "--id", rid, "--p", "", "--notes", "no_p=cleared")
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(rows(db)[0]["p"], "")
        self.assertNotIn("ERROR", run(db, "lint").stdout)
if __name__ == "__main__": unittest.main()
