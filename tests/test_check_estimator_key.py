"""check must compare a ledger row to the source row with the SAME estimator when the source names one."""
import csv, os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CLI = os.path.join(ROOT, "skills", "results-db", "scripts", "results_db.py")
def run(db, *a, cwd=None): return subprocess.run([sys.executable, CLI, "--db", db, *a], capture_output=True, text=True, cwd=cwd)
class TestCheckEstimatorKey(unittest.TestCase):
    def test_cs_row_not_compared_to_twfe_source(self):
        tmp = tempfile.mkdtemp(); db = os.path.join(tmp, "results_database.csv"); src = os.path.join(tmp, "src.csv"); run(db, "init")
        with open(src, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["outcome", "sample", "block", "att", "se", "p"])
            w.writerow(["delta", "Q4", "twfe_pooled", "-0.181", "0.292", "0.563"]); w.writerow(["delta", "Q4", "callaway_santanna", "-0.093", "0.027", "0.0004"])
        run(db, "add", "--section", "s", "--estimator", "callaway_santanna", "--dv", "delta", "--sample", "Q4", "--att", "-0.093", "--se", "0.027", "--p", "0.0004", "--in_paper", "tbd", "--source_csv", src)
        out = run(db, "check", cwd=tmp).stdout
        self.assertIn("Mismatches: 0", out, out); self.assertIn("OK:         1", out, out)
    def test_source_without_estimator_still_matches(self):
        tmp = tempfile.mkdtemp(); db = os.path.join(tmp, "results_database.csv"); src = os.path.join(tmp, "src.csv"); run(db, "init")
        with open(src, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["dv", "sample", "att", "se", "p"]); w.writerow(["y", "Full", "0.5", "0.1", "0.01"])
        run(db, "add", "--section", "s", "--estimator", "C&S", "--dv", "y", "--sample", "Full", "--att", "0.5", "--in_paper", "tbd", "--source_csv", src)
        self.assertIn("OK:         1", run(db, "check", cwd=tmp).stdout)
if __name__ == "__main__": unittest.main()
