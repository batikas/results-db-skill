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
$DB story --section main_results --prose

# 5. Before submission
$DB lint
```

---

## How Claude Uses This Skill

Claude reads the skill description and invokes it automatically when you are working on an empirical paper. You do not need to ask for it explicitly.

**At the start of every empirical paper session** Claude will automatically run `status` and `show --in_paper tbd` without being asked.

**Querying results**
- *"What results do we have for the mechanism section?"*
- *"What's still tbd?"*
- *"Which results are going in the main text?"*
- *"What did we find for the forks DV?"*
- *"Is the IV result significant?"*
- *"Show me what's in the appendix"*
- *"What do we have for the full sample?"*
- *"Which results use the C&S estimator?"*
- *"What's the ATT for the top-quartile subsample?"*
- *"Are there any null results we logged?"*
- *"What did we drop and why?"*

**Pre-trends and validation**
- *"Did the parallel trends pass for the treated group?"*
- *"Which results failed the Honest DiD check?"*
- *"Did RI pass for the main outcome?"*
- *"Which main-text results have a pre-trend failure?"*
- *"Do any main results have honest_did_pass = fail?"*
- *"What's the Honest DiD breakdown M for the mechanism result?"*
- *"Which estimates need a placebo test before submission?"*

**Narrative and writing**
- *"Give me the story of the main findings"*
- *"Write the robustness paragraph"*
- *"What's the narrative for the mechanism results?"*
- *"I'm writing the results section — what do we have?"*
- *"Summarize what went in the paper for each hypothesis"*
- *"Write the paragraph for the referee response on robustness"*
- *"Give me a forest plot of the main results"*
- *"What's the referee-ready summary of our findings?"*

**Logging and updating**
- *"Log the new IV result"*
- *"Add the PPML robustness check result"*
- *"We just ran the RI test — update the main row"*
- *"Mark the HHI result as appendix"*
- *"Drop the Gini result — placebo failed"*
- *"Log this as conditional — pre-trend is borderline"*
- *"The new spec changed the ATT — update row 17"*

**Referee and revision**
- *"The referee asked about randomization inference"*
- *"The referee wants more robustness — what do we have in the DB?"*
- *"What changed between the original submission and R1?"*
- *"Find all results relevant to the referee's comment about parallel trends"*
- *"Generate the referee response document"*

**Quality control**
- *"Run the integrity checks before we submit"*
- *"Is anything broken in the results DB?"*
- *"Are there any sig/p mismatches?"*
- *"Are there duplicates in the main text?"*

**Overview and hypothesis coverage**
- *"Give me the big picture before I start writing"*
- *"What's the coverage of our hypotheses?"*
- *"Which hypotheses don't have a main result yet?"*
- *"Are H1 and H2 both covered in the main text?"*

---

## Schema

One row per estimate — one DV × one sample × one estimator.

### Core fields

| Field | Values | Description |
|---|---|---|
| `id` | integer | Auto-incremented row ID |
| `section` | `intro` `main` `mechanism` `heterogeneity` `robustness` `welfare` `appendix` or any label | Paper section |
| `hypothesis` | `H1` `H2a` free text | Which hypothesis this tests |
| `estimator` | `C&S` `TWFE` `IV` `OLS` `ITS` `RI` `Honest DiD` … | Estimator used |
| `dv` | string | Outcome variable (machine-readable column name) |
| `dv_label` | string | Human-readable outcome label for display |
| `sample` | `Full` `Treated` `Control` `Q4` `Subgroup A` … | Sample / subgroup |
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
| `paper_version` | `QJE` `ReStat` `WP` … | Which paper version (if submitting to multiple journals) |
| `referee_round` | `original` `R1` `R2` … | Revision round when this was logged |

### Model metadata

| Field | Example | Description |
|---|---|---|
| `language` | `Python` `R` `Stata` | Execution language |
| `model_spec` | `TWFE, unit+time FE, clustered SE` | Full model specification |

### Validation fields

| Field | Values | Description |
|---|---|---|
| `pre_trend_test` | `F p=0.43` `RI p=0.12` `event study clean` | Pre-trend / placebo test result |
| `pre_trend_pass` | `pass` `fail` `conditional` | Did parallel trends hold? |
| `honest_did_m` | `0.025` `0.0000` | Rambachan & Roth breakdown M |
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

# Only R-executed results
python3 results_db.py show --project . --language R
```

**Filters:** `--section` `--in_paper` `--estimator` `--dv` `--sample` `--sig` `--language` `--pre_trend_pass` `--honest_did_pass` `--paper_version` `--referee_round`

---

### `add` — Log a new estimate

```bash
python3 results_db.py add --project . \
  --section main \
  --hypothesis H1 \
  --estimator "TWFE" \
  --dv log_outcome \
  --dv_label "Log Outcome" \
  --sample "Treated Q4" \
  --att 0.142 --se 0.031 --p 0.000 --n 8450 \
  --in_paper main \
  --language R \
  --model_spec "TWFE, unit+year FE, clustered SE" \
  --pre_trend_test "F p=0.61" \
  --pre_trend_pass pass \
  --honest_did_m "0.018" \
  --honest_did_pass pass \
  --table_file "results/tables/main_table.tex" \
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
  --dv log_outcome --sample "Control" \
  --in_paper dropped \
  --pre_trend_pass fail \
  --notes "Placebo test fails p=0.008, pre-trend non-parallel"

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
python3 results_db.py story --project . --section main --audience referee
```

**Internal format** groups by section → hypothesis → outcome, shows ATT, sig, placement, language, pre-trend result, and Honest DiD breakdown M.

**`--prose`** renders each section as a LaTeX paragraph with inline ATT percentages, estimator, and N. Starting point for writing — add framing around it.

**`--audience referee`** writes:
```
Consistent with H1, \textit{Log Outcome} (among Treated Q4 firms) increases
by 14.2\%*** (TWFE, $N=8{,}450$, $p<0.01$). Randomization inference confirms
this result (RI p=0.000). We find no significant effect on Log Input.
```

---

### `status` — Placement overview

```bash
python3 results_db.py status --project .
```

Sample output:
```
Results Database — 54 total estimates

By placement:
  main        18  ██████████████████
  appendix    22  ██████████████████████
  tbd          6  ██████
  dropped      8  ████████

By section:
  main_results         14
  heterogeneity        12
  mechanism             9
  robustness            7
  welfare               4

Hypothesis coverage matrix:
  Hypothesis             main  appendix   tbd  dropped
  ─────────────────────────────────────────────────────
  H1                        6        10     ·        3
  H2                        4         5     ·        2
  H_mechanism               4         4     4  ⚠  ← unresolved
  H_subgroup                4         3     2  ⚠  ← unresolved
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
python3 results_db.py compare --project . --dv log_outcome
python3 results_db.py compare --project . --dv log_outcome --sample "Treated Q4"
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
  --comment "Please clarify whether parallel trends hold for the treatment group"

# From a text file
python3 results_db.py referee --project . --file comments/referee2.txt
```

Scores every DB entry by keyword overlap with the comment and returns a ranked checklist:

```
Score  ID   DV             Sample      In Paper   Notes
4      12   Log Outcome    Treated Q4  main       pre-trend F p=0.43
3       8   Log Outcome    Full        appendix
3      31   Log Input      Full        dropped    RI p=1.0 — do not report
```

Then follow up with:
```bash
python3 results_db.py update --id 12 --referee_round R1 \
  --notes "Added event study figure as Figure A2"
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
python3 results_db.py history --project . --dv log_outcome
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
python3 results_db.py status --project .        # orientation
python3 results_db.py show --in_paper tbd        # make pending decisions
python3 results_db.py story --section main       # read what you have
```

### After running a new analysis

```bash
# Option A: add manually
python3 results_db.py add --project . \
  --section robustness --estimator TWFE \
  --dv log_outcome --sample Full \
  --att 0.138 --se 0.029 --p 0.000 --n 12400 \
  --in_paper appendix \
  --pre_trend_test "F p=0.52" --pre_trend_pass pass \
  --model_spec "TWFE, unit+year FE, clustered SE"

# Option B: auto-detect from output CSV
python3 results_db.py sync --project . --source-dir results/tables/ --apply
```

### Before submission

```bash
python3 results_db.py lint --project .                          # fix all issues
python3 results_db.py story --audience referee --section main   # read as a referee would
python3 results_db.py export --format referee-response > appendix.md
```

### During revision (R1 response)

```bash
# Find what the referee is asking about
python3 results_db.py referee --project . --file comments/referee1.txt

# Update affected results
python3 results_db.py update --id 12 --referee_round R1 \
  --notes "Added event study; pre-trend F p=0.61 confirmed"

# See everything that changed
python3 results_db.py diff --project . --round-b R1
```

---

## Good Habits

**One row per estimate, not per table.** A table with 4 subgroup splits = 4 rows. A table with 3 estimators = 3 rows.

**Log null results.** A null result with `in_paper=dropped` is data. It tells you what you tried and why you didn't report it.

**Fill `notes` for anything imperfect.** Small N, failed placebo, RI failure, borderline pre-trend, marginal p-value. If you have a caveat in your head when you log a result, write it in `notes`.

**Fill `pre_trend_pass` for every DiD result.** `pass` / `fail` / `conditional`. The lint check will catch any `fail` that ended up in main text.

**Fill `honest_did_m` and `honest_did_pass` after every Rambachan & Roth run.** M = 0 means the result is not robust to any deviation; M > 0 gives you a quantified robustness margin to report.

**Fill `language` and `model_spec`.** Any result in the DB should be self-contained — someone should be able to reproduce it from the DB entry alone without reading the code.

**Write a populate script, not `add` one-by-one.** For papers with 20+ results, write `populate_mypaper.py` once. When results change (re-run, revision), update the script and re-run it.

**Update after revision.** When results change, update the DB with `--referee_round R1`. Then use `diff` to see exactly what changed for your response letter.

---

## Project Structure

```
your-paper/
├── results/
│   ├── results_database.csv    ← the ledger (commit this to git)
│   ├── results_history.csv     ← change log (commit this too)
│   └── tables/                 ← LaTeX tables and CSV outputs from analysis
└── code/
    └── populate_mypaper.py     ← script that rebuilds the DB from scratch
```

Add `.gitignore` exceptions for the database files:
```gitignore
*.csv
!results/results_database.csv
!results/results_history.csv
```

---

## CI Lint Gate

Add a GitHub Actions workflow to fail the build whenever a result with a red-flag note or failed pre-trend is accidentally promoted to main text:

```yaml
# .github/workflows/lint.yml
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
