# results-db — Results Ledger Skill for Claude Code

A Claude Code skill that maintains a structured CSV ledger of every regression estimate in an empirical paper. It tracks what goes in the paper, what goes in the appendix, what was dropped and why, whether parallel trends held, and whether Honest DiD sensitivity passed — across sessions, across co-authors, and across revision rounds.

---

## The Problem

Empirically heavy papers accumulate hundreds of estimates across specifications, estimators, heterogeneity splits, and robustness checks. Without a ledger:

- Results get forgotten between working sessions
- The paper narrative drifts from what the data actually show
- Decisions about inclusion are made informally and inconsistently
- Co-authors and referees find contradictions you can't explain
- Referee rounds scramble everything and you can't see what changed

---

## Installation

**Via Claude Code plugin manager:**
```bash
claude plugin install github:batikas/results-db-skill
```

**Manually:**
```bash
cp -r skills/results-db/ ~/.claude/skills/results-db/
```

**Requirements:** Python 3.8+, no dependencies beyond the standard library.

---

## Quick Start

```bash
DB="python3 ~/.claude/skills/results-db/scripts/results_db.py --project /path/to/project"

# 1. Initialize
$DB init

# 2. Populate (write a populate script — see examples/)
python3 populate_mypaper.py --project /path/to/project

# 3. Orient yourself
$DB status
$DB show --in_paper tbd

# 4. Read the story
$DB story
$DB story --section package --prose

# 5. Before submission
$DB lint
```

---

## How Claude Uses This Skill

Claude reads the skill description and invokes this automatically when you are working on an empirical paper. You do not need to ask for it explicitly. Trigger phrases include:

- *"What results do we have for the mechanism section?"*
- *"What's still tbd?"*
- *"Give me the story of the package-level findings"*
- *"Log the new eigenvector centrality result"*
- *"Did the parallel trends pass for forks?"*
- *"Write the robustness paragraph"*
- *"The referee asked about randomization inference"*

At the start of every empirical paper session Claude will automatically run `status` and `show --in_paper tbd` without being asked.

---

## Schema

One row per estimate — one DV × one sample × one estimator.

### Core fields

| Field | Values | Description |
|---|---|---|
| `id` | integer | Auto-incremented row ID |
| `section` | `market` `package` `mechanism` `heterogeneity` `robustness` `welfare` `replication` | Paper section |
| `hypothesis` | `H1` `H2a` free text | Which hypothesis this tests |
| `estimator` | `C&S` `TWFE` `S&A` `SDiD` `OLS` `ITS` `RI` `Honest DiD` | Estimator used |
| `dv` | string | Outcome variable (machine-readable column name) |
| `dv_label` | string | Human-readable outcome label for display |
| `sample` | `Full` `DepQ4` `Active` `Data Science` … | Sample / subgroup |
| `att` | float | Point estimate (ATT or coefficient) |
| `se` | float | Standard error |
| `p` | float | p-value |
| `sig` | `***` `**` `*` `n.s.` | Significance stars |
| `n` | integer | Observations |
| `ci_lo` / `ci_hi` | float | 95% confidence interval (optional) |

### Placement fields

| Field | Values | Description |
|---|---|---|
| `in_paper` | `main` `appendix` `dropped` `tbd` | Where this result goes |
| `paper_version` | `JPE` `MS IS` `WP` … | Which paper version (if submitting to multiple journals) |
| `referee_round` | `original` `R1` `R2` … | Revision round when this was logged |

### Model metadata

| Field | Example | Description |
|---|---|---|
| `language` | `Python` `R` `Stata` | Execution language |
| `model_spec` | `C&S DiD, pkg+month FE, HC1 SEs` | Full model specification |

### Validation fields

| Field | Values | Description |
|---|---|---|
| `pre_trend_test` | `RI p=0.000` `event study F p=0.43` | Pre-trend / placebo test result |
| `pre_trend_pass` | `pass` `fail` `conditional` | Did parallel trends hold? |
| `honest_did_m` | `0.0000` `0.025` | Rambachan & Roth breakdown M |
| `honest_did_pass` | `pass` `fail` `conditional` | Did Honest DiD sensitivity hold? |

### File references

| Field | Description |
|---|---|
| `table_file` | Path to LaTeX table (relative to project root) |
| `figure_file` | Path to figure PDF (relative to project root) |
| `source_csv` | CSV file the estimate was read from |
| `notes` | Caveats — failed placebo, small N, RI failure, Honest DiD breakdown |

---

## Commands

All commands take `--project /path/to/project` (default: current directory) or `--db /explicit/path.csv`.

---

### `init` — Create empty database

```bash
python3 results_db.py init --project .
```

Creates `results/results_database.csv` with all column headers. Run once per paper.

---

### `show` — Filtered table of results

```bash
# All results
python3 results_db.py show --project .

# Filter by section
python3 results_db.py show --project . --section mechanism

# What still needs a placement decision?
python3 results_db.py show --project . --in_paper tbd

# Only significant main-text results
python3 results_db.py show --project . --in_paper main --sig "**"

# Results where parallel trends failed
python3 results_db.py show --project . --pre_trend_pass fail

# Only Python-executed results
python3 results_db.py show --project . --language Python
```

**Filters:** `--section` `--in_paper` `--estimator` `--dv` `--sample` `--sig` `--language` `--pre_trend_pass` `--honest_did_pass` `--paper_version` `--referee_round`

---

### `add` — Log a new estimate

```bash
python3 results_db.py add --project . \
  --section package \
  --hypothesis H1 \
  --estimator "C&S" \
  --dv delta_num_as_dep \
  --dv_label "Δ Downstream (monthly flow)" \
  --sample DepQ4 \
  --att 0.2194 --se 0.0789 --p 0.007 --n 24336 \
  --in_paper main \
  --language Python \
  --model_spec "C&S DiD, pkg+month FE, HC1 SEs" \
  --pre_trend_test "RI p=0.000" \
  --pre_trend_pass pass \
  --honest_did_m "0.025" \
  --honest_did_pass pass \
  --table_file "results/tables/downstream_table.tex" \
  --notes ""
```

Only `--dv`, `--sample`, and `--att` are required. All other fields are optional but encouraged.

> **Tip:** For papers with many results, write a `populate_mypaper.py` script instead of calling `add` one by one. See `examples/populate_example.py`.

---

### `update` — Change any field

```bash
# By ID
python3 results_db.py update --project . --id 42 --in_paper appendix

# By DV + sample (updates all matching rows)
python3 results_db.py update --project . \
  --dv fork_hhi --sample Full \
  --in_paper dropped \
  --pre_trend_pass fail \
  --notes "Placebo fails p=0.004, pre-trend non-parallel"

# Mark a result as revised after R1
python3 results_db.py update --project . \
  --id 17 \
  --referee_round R1 \
  --honest_did_m "0.031" \
  --honest_did_pass conditional
```

All changes are appended to `results_history.csv` automatically. Updatable fields: `in_paper` `notes` `section` `hypothesis` `paper_version` `referee_round` `language` `model_spec` `pre_trend_test` `pre_trend_pass` `honest_did_m` `honest_did_pass` `table_file` `figure_file`

---

### `story` — Narrative summary

```bash
# Internal format (bullet list with validation flags)
python3 results_db.py story --project .

# Filter to one section
python3 results_db.py story --project . --section mechanism

# With ASCII forest plot
python3 results_db.py story --project . --forest

# LaTeX-ready draft paragraphs
python3 results_db.py story --project . --prose

# Referee-response framing ("Consistent with H1, we find...")
python3 results_db.py story --project . --audience referee

# Combine: referee framing for one section
python3 results_db.py story --project . --section package --audience referee
```

**Internal format** groups by section → hypothesis → outcome, shows ATT, sig, placement, language, pre-trend result, and Honest DiD breakdown M.

**`--prose`** renders each section as a LaTeX paragraph with inline ATT percentages, estimator, and N. Starting point for writing — add "Consistent with H1..." framing around it.

**`--audience referee`** writes:
```
Consistent with H1, \textit{Δ Downstream (flow)} increases by 21.9\%***
(C&S, $N=23{,}660$, $p<0.01$). Randomization inference confirms this result
(RI p=0.000). We do not find significant effects on Upstream Deps (log).
```

---

### `status` — Placement overview

```bash
python3 results_db.py status --project .
```

Output:
```
Results Database — 77 total estimates

By placement:
  main        31  ███████████████████████████████
  appendix    31  ███████████████████████████████
  tbd          5  █████
  dropped     10  ██████████

By section:
  package              24
  heterogeneity        17
  ...

Hypothesis coverage matrix:
  Hypothesis             main  appendix   tbd  dropped
  ─────────────────────────────────────────────────────
  H_package                 9        24     ·        5
  H_mechanism               4         2     3  ⚠  ← tbd
  H_org                     ·         ·     2  ⚠  ← tbd
```

The hypothesis matrix shows at a glance which hypotheses have zero main-text results or unresolved placements.

---

### `lint` — Integrity checks before submission

```bash
python3 results_db.py lint --project .

# Exit nonzero on any warning (for Makefile / pre-commit hooks)
python3 results_db.py lint --project . --strict
```

Checks:
1. Red-flag phrases in notes for main-text results (`"RI p=1"`, `"placebo fails"`, `"do not report"`, …)
2. sig/p mismatch (e.g., p=0.04 but sig=`***`)
3. Duplicate DV+sample+estimator in main text
4. Same DV+sample appears as both `main` and `dropped`
5. Main results missing both `table_file` and `figure_file`
6. `table_file` path not found on disk
7. Borderline p (0.05–0.10) in main text without notes
8. `pre_trend_pass = fail` in main text
9. `honest_did_pass = fail` in main text
10. Count of `tbd` results still needing a decision

**Makefile integration:**
```makefile
lint:
    python3 ~/.claude/skills/results-db/scripts/results_db.py lint --strict --project .
```

**Pre-commit hook** (`.git/hooks/pre-commit`):
```bash
#!/bin/sh
python3 ~/.claude/skills/results-db/scripts/results_db.py lint --strict --project .
```

---

### `export` — Output in different formats

```bash
# Markdown table
python3 results_db.py export --project . --format md

# LaTeX tabular
python3 results_db.py export --project . --format latex --in_paper main

# Raw CSV
python3 results_db.py export --project . --format csv

# Full referee response document (Markdown, paste into response letter)
python3 results_db.py export --project . --format referee-response > response_appendix.md
```

**`--format referee-response`** generates a structured Markdown document containing:
- Main results table by section
- Randomization inference summary
- Honest DiD summary
- Appendix results summary (count + significant ones)
- Model specifications referenced

All filters (`--section`, `--in_paper`, `--estimator`, etc.) work with every format.

---

### `compare` — Side-by-side estimator comparison

```bash
python3 results_db.py compare --project . --dv delta_num_as_dep
python3 results_db.py compare --project . --dv log_fork_count --sample DepQ4
```

Shows all estimators for a given DV × sample in one table. Use to verify TWFE vs C&S agreement, or to decide which estimator to put in main text.

---

### `sync` — Auto-detect new results from CSV files

```bash
# Preview what's new without writing
python3 results_db.py sync --project . --source-dir results/tables/

# Add new estimates to DB as tbd
python3 results_db.py sync --project . --source-dir results/tables/ --apply

# Also scan Stargazer .tex files
python3 results_db.py sync --project . --source-dir results/tables/ --apply --include-tex
```

Scans a directory for CSV and (optionally) LaTeX table files. Auto-detects format: generic CSV, R `modelsummary` tidy output, Python `statsmodels` summary, and Stargazer LaTeX. Reports estimates that are new or whose ATT has changed vs the DB.

---

### `check` — Verify DB vs source files

```bash
python3 results_db.py check --project .
```

For every row with a `source_csv` field, re-reads the source and verifies the ATT still matches. Reports drift — useful after re-running analysis to catch results that changed.

---

### `referee` — Match a referee comment to DB entries

```bash
# Inline comment
python3 results_db.py referee --project . \
  --comment "Please clarify whether the parallel trends assumption holds for the fork results"

# From a text file
python3 results_db.py referee --project . --file comments/referee2.txt
```

Scores every DB entry by keyword overlap with the comment and returns a ranked checklist:

```
Score  ID   DV                      Sample   In Paper   Notes
4      28   Forks (log)             Full     main       RI p=0.000 — cleanest result
3      22   Downstream Deps (stock) DepQ4    main       RI p=1.0...
```

Then follow up with:
```bash
python3 results_db.py update --id 28 --referee_round R1 --notes "Added RI table as Table A7"
```

---

### `diff` — What changed between revision rounds

```bash
# Show all changes ever logged
python3 results_db.py diff --project .

# Filter by round
python3 results_db.py diff --project . --round-a original --round-b R1
```

Reads `results_history.csv` and shows every field change grouped by result, highlighting changes to `sig`, `in_paper`, `pre_trend_pass`, and `honest_did_pass`.

---

### `history` — Change log for one result

```bash
python3 results_db.py history --project . --id 42
python3 results_db.py history --project . --dv log_fork_count
```

Shows the full audit trail for a specific result — every field that was ever changed, when, and what it changed from/to.

---

### `watch` — Auto-ingest on analysis run

```bash
python3 results_db.py watch --project . --source-dir results/tables/ --interval 30
```

Polls `--source-dir` every `--interval` seconds (default 30). When a CSV changes, runs the fuzzy parser and ingests any new estimates as `in_paper=tbd`. Run this in a background terminal while you're running analyses, and new results appear in the DB automatically.

Stop with `Ctrl-C`.

---

### `template` — Generate a populate script

```bash
python3 results_db.py template --project . --paper-name mypaper
```

Generates `populate_mypaper.py` with the `r()` helper pre-configured. Edit the rows, then run:
```bash
python3 populate_mypaper.py --project /path/to/project
```

---

## Workflow Patterns

### Starting a writing session

```bash
python3 results_db.py status --project .       # orientation
python3 results_db.py show --in_paper tbd       # make pending decisions
python3 results_db.py story --section package   # read what you have
```

### After running a new analysis

```bash
# Option A: add manually
python3 results_db.py add --project . \
  --section robustness --estimator TWFE \
  --dv log_fork_count --sample Full \
  --att 0.024 --se 0.007 --p 0.001 --n 97272 \
  --in_paper appendix \
  --pre_trend_test "RI p=0.000" --pre_trend_pass pass \
  --model_spec "TWFE, pkg+month FE, HC1 SEs"

# Option B: auto-detect from output CSV
python3 results_db.py sync --project . --source-dir results/tables/ --apply
```

### Before submission

```bash
python3 results_db.py lint --project .                          # fix all issues
python3 results_db.py story --audience referee --section package  # read it as a referee
python3 results_db.py export --format referee-response > appendix.md
```

### During revision (R1 response)

```bash
# Find what the referee is asking about
python3 results_db.py referee --project . --file comments/referee1.txt

# Update affected results
python3 results_db.py update --id 22 --referee_round R1 \
  --notes "Added RI robustness table; RI p=0.000"

# See everything that changed
python3 results_db.py diff --project . --round-b R1
```

---

## Good Habits

**One row per estimate, not per table.** A table with 4 quartile splits = 4 rows. A table with 3 estimators = 3 rows.

**Log null results.** A null result with `in_paper=dropped` is data. It tells you what you tried and why you didn't report it. Future-you and co-authors will thank you.

**Fill `notes` for anything imperfect.** Small N, failed placebo, RI failure, borderline pre-trend, marginal p-value. If you have a caveat in your head when you log a result, put it in `notes`.

**Fill `pre_trend_pass` for every DiD result.** `pass` / `fail` / `conditional`. The lint check will catch any `fail` that ended up in main text.

**Fill `honest_did_m` and `honest_did_pass` after every Rambachan & Roth run.** M = 0 means the result is not robust to any deviation; M > 0 means you have a quantified robustness margin.

**Fill `language` and `model_spec`.** Any result in the DB should be self-contained — someone should be able to reproduce it from the DB entry alone without reading the code.

**Write a populate script, not `add` one-by-one.** For papers with 20+ results, write `populate_mypaper.py` once. When results change (re-run, revision), update the script and re-run it. The DB is always reconstructed from source.

**Update after revision.** When a referee forces a re-run and results change, update the DB. Use `--referee_round R1`. Then `diff` to see exactly what changed for your response letter.

---

## Project Structure

```
your-paper/
├── results/
│   ├── results_database.csv    ← the ledger (commit this to git)
│   ├── results_history.csv     ← change log (commit this too)
│   └── tables/                 ← LaTeX tables and CSV outputs
└── code/
    └── populate_mypaper.py     ← script that rebuilds the DB from scratch
```

Add to `.gitignore` exception for the database:
```
*.csv
!results/results_database.csv
!results/results_history.csv
```

---

## CI Lint Gate

Add a GitHub Actions workflow (`.github/workflows/lint.yml`) to fail the build whenever a result with a red-flag note or failed pre-trend is accidentally promoted to main text:

```yaml
name: Results DB Lint
on:
  push:
    paths: ['results/results_database.csv']
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: |
          curl -sSL https://raw.githubusercontent.com/batikas/results-db-skill/main/skills/results-db/scripts/results_db.py \
            -o results_db.py
          python3 results_db.py lint --strict --project .
```

---

## License

MIT
