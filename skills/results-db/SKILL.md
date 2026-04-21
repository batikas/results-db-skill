---
name: results-db
description: Use when working on an empirical research paper and need to track, log, query, or decide what to do with regression results. Invoke when the user asks what results are significant, what goes in the paper vs appendix vs dropped, wants a results ledger or narrative, needs to log a new estimate, wants to update the status of a result, needs to see the full picture before writing a section, or wants to check pre-trend / Honest DiD status of any result. Works across any quantitative social-science or economics project. At the start of every empirical paper session, automatically run `status` and `show --in_paper tbd` without being asked.
---

# Results Database

A structured ledger for every regression estimate in a paper. One CSV per project. Query it to decide inclusion, generate the "story" narrative, and never forget a result again.

## Philosophy

Empirically heavy papers accumulate hundreds of estimates across specifications, estimators, heterogeneity splits, and robustness checks. Without a ledger:
- Results get forgotten between sessions
- The paper narrative drifts from the actual data
- Decisions about what to include are made informally and inconsistently
- Co-authors and referees find contradictions

The results DB is the single source of truth. Every time you run an analysis, log it. Every time you open a paper-writing session, start with `story` or `status`.

## Setup

Initialize a new project database (creates `results/results_database.csv`):
```bash
python ~/.claude/skills/results-db/scripts/results_db.py init --project /path/to/project
```

The DB file path defaults to `<project>/results/results_database.csv`. Pass `--db` to override.

## Schema

Each row is one estimate (one DV × one sample × one estimator):

| Column | Type | Description |
|---|---|---|
| `id` | int | Auto-incremented row ID |
| `section` | str | Paper section: `market` / `package` / `mechanism` / `robustness` / `heterogeneity` / `welfare` |
| `hypothesis` | str | Which hypothesis tested (e.g. `H1`, `H2a`, free text) |
| `estimator` | str | `C&S` / `TWFE` / `S&A` / `SDiD` / `OLS` / `ITS` / `RI` / `Honest DiD` etc. |
| `dv` | str | Outcome variable column name (machine-readable) |
| `dv_label` | str | Human-readable outcome label |
| `sample` | str | Sample description (`Full` / `DepQ4` / `Active` / `Data Science` etc.) |
| `att` | float | Point estimate (ATT or coefficient) |
| `se` | float | Standard error |
| `p` | float | p-value |
| `sig` | str | Stars: `***` / `**` / `*` / `n.s.` |
| `n` | int | Sample size |
| `ci_lo` | float | Lower 95% CI (optional) |
| `ci_hi` | float | Upper 95% CI (optional) |
| `in_paper` | str | `main` / `appendix` / `dropped` / `tbd` |
| `paper_version` | str | Which paper version (e.g. `JPE`, `MS IS`, `WP`) |
| `referee_round` | str | `original` / `R1` / `R2` etc. |
| `language` | str | Execution language: `Python` / `R` / `Stata` |
| `model_spec` | str | Model spec summary (e.g. `C&S DiD, pkg+month FE, HC1 SEs`) |
| `pre_trend_test` | str | Pre-trend / placebo test result (e.g. `RI p=0.000`, `event study F p=0.43`) |
| `pre_trend_pass` | str | `pass` / `fail` / `conditional` — did parallel trends hold? |
| `honest_did_m` | str | Honest DiD breakdown M value (e.g. `0.0000`, `0.025`) |
| `honest_did_pass` | str | `pass` / `fail` / `conditional` — did Honest DiD sensitivity hold? |
| `table_file` | str | Path to LaTeX table (relative to project root) |
| `figure_file` | str | Path to figure PDF (relative to project root) |
| `source_csv` | str | CSV file the estimate was read from |
| `notes` | str | Caveats — failed placebo, RI issues, small N, Honest DiD breakdown etc. |

## Commands

All commands accept `--project /path/to/project` (defaults to current directory) or `--db /explicit/path/to/db.csv`.

### Initialize
```bash
python ~/.claude/skills/results-db/scripts/results_db.py init --project .
```

### Show — filtered table of results
```bash
# All results
python ~/.claude/skills/results-db/scripts/results_db.py show --project .

# Filter by section and minimum significance
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --section mechanism --sig "*"

# What still needs a decision?
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --in_paper tbd

# Show only main-text results
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --in_paper main

# Show only Python-executed results
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --language Python

# Show results where parallel trends failed
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --pre_trend_pass fail
```

Supports: `--section`, `--sig` (minimum: `*`, `**`, `***`), `--in_paper`, `--estimator`, `--dv`, `--sample`, `--language`, `--pre_trend_pass`, `--honest_did_pass`, `--paper_version`, `--referee_round`

### Story — narrative summary of significant results
```bash
python ~/.claude/skills/results-db/scripts/results_db.py story --project .
python ~/.claude/skills/results-db/scripts/results_db.py story --project . --section package
python ~/.claude/skills/results-db/scripts/results_db.py story --project . --forest   # ASCII forest plot
```

Groups by section → hypothesis → outcome. Shows ATT, sig, in_paper status, language, and (when present) pre-trend test result and Honest DiD breakdown M. Good for sending to co-authors or starting a writing session.

### Status — what's decided vs pending
```bash
python ~/.claude/skills/results-db/scripts/results_db.py status --project .
```

Shows counts by `in_paper` value and by section. Quick health check before writing.

### Add — log a new result
```bash
python ~/.claude/skills/results-db/scripts/results_db.py add --project . \
  --section package --hypothesis H1 --estimator "C&S" \
  --dv delta_num_as_dep --dv_label "Δ Downstream (monthly flow)" \
  --sample DepQ4 --att 0.2194 --se 0.0789 --p 0.007 --sig "***" --n 24336 \
  --in_paper main \
  --language Python --model_spec "C&S DiD, pkg+month FE, HC1 SEs" \
  --pre_trend_test "RI p=0.000" --pre_trend_pass pass \
  --honest_did_m "0.025" --honest_did_pass pass \
  --table_file "results/tables/downstream_table_all_estimators_by_dep_quartile_py.tex" \
  --notes ""
```

All fields except `att`, `dv`, `sample` are optional but encouraged.

### Update — change in_paper status or notes
```bash
# By ID
python ~/.claude/skills/results-db/scripts/results_db.py update --project . --id 42 --in_paper appendix

# By DV + sample (updates all matching rows)
python ~/.claude/skills/results-db/scripts/results_db.py update --project . \
  --dv fork_hhi --sample Full --in_paper dropped \
  --pre_trend_pass fail \
  --notes "Placebo fails p=0.004, pre-trend non-parallel"

# Update Honest DiD result
python ~/.claude/skills/results-db/scripts/results_db.py update --project . \
  --id 17 --honest_did_m "0.031" --honest_did_pass conditional
```

All updatable: `in_paper`, `notes`, `section`, `hypothesis`, `paper_version`, `referee_round`, `language`, `model_spec`, `pre_trend_test`, `pre_trend_pass`, `honest_did_m`, `honest_did_pass`, `table_file`, `figure_file`

### Export — markdown or LaTeX summary table
```bash
python ~/.claude/skills/results-db/scripts/results_db.py export --project . --format md
python ~/.claude/skills/results-db/scripts/results_db.py export --project . --format latex --in_paper main
```

### Lint — integrity checks before submission
```bash
python ~/.claude/skills/results-db/scripts/results_db.py lint --project .
```

Checks for:
1. Red-flag phrases in notes for main-text results ("placebo fails", "RI p=1", "do not report", etc.)
2. sig/p mismatch (e.g., p=0.04 but sig="***")
3. Duplicate DV+sample+estimator in main text
4. Same DV+sample appears as both `main` and `dropped`
5. Main results missing both table_file and figure_file
6. table_file path not found on disk
7. Borderline p (0.05–0.10) in main without notes
8. **pre_trend_pass = fail in main text** — parallel trends violated
9. **honest_did_pass = fail in main text** — Honest DiD sensitivity failed
10. tbd count summary

### Compare — side-by-side estimator comparison
```bash
python ~/.claude/skills/results-db/scripts/results_db.py compare --project . --dv delta_num_as_dep
python ~/.claude/skills/results-db/scripts/results_db.py compare --project . --dv log_fork_count --sample DepQ4
```

Shows all estimators for a given DV × sample in a table. Useful for checking TWFE vs C&S agreement.

### Sync — detect new/changed results from CSV files
```bash
# See what's new without writing
python ~/.claude/skills/results-db/scripts/results_db.py sync --project . --source-dir results/tables/

# Apply new estimates to DB
python ~/.claude/skills/results-db/scripts/results_db.py sync --project . --source-dir results/tables/ --apply

# Also scan Stargazer .tex files
python ~/.claude/skills/results-db/scripts/results_db.py sync --project . --source-dir results/tables/ --include-tex
```

Auto-detects CSV format (generic, modelsummary, statsmodels) and Stargazer .tex. Reports new estimates not yet in DB and existing estimates where the value has changed.

### Check — verify DB vs source files
```bash
python ~/.claude/skills/results-db/scripts/results_db.py check --project .
```

For every row with a `source_csv`, re-reads the source and verifies the ATT still matches. Reports drift.

### History — show change log for a result
```bash
python ~/.claude/skills/results-db/scripts/results_db.py history --project . --id 42
python ~/.claude/skills/results-db/scripts/results_db.py history --project . --dv log_fork_count
```

Shows every field change ever made to a result (appended to `results_history.csv` by all `update` calls).

### Template — generate a starter populate script
```bash
python ~/.claude/skills/results-db/scripts/results_db.py template --project . --paper-name mypaper
```

Generates a `populate_mypaper.py` skeleton with the `r()` helper pre-configured.

## Session workflow

### At the start of every empirical writing session (run automatically)
```bash
python ~/.claude/skills/results-db/scripts/results_db.py status --project .
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --in_paper tbd
```

### After running new analysis
1. Read results from the output CSV
2. `add` each primary estimate (C&S or primary estimator) with `--language`, `--model_spec`, `--pre_trend_test`, `--pre_trend_pass`
3. `add` robustness variants with `--in_paper appendix`
4. Note any caveats in `--notes`; set `--pre_trend_pass fail` or `--honest_did_pass fail` when checks don't pass
5. Set `--in_paper tbd` until you decide

### Before submission
```bash
python ~/.claude/skills/results-db/scripts/results_db.py lint --project .
```

Fix all errors; review all warnings.

## Good habits
- **One row per estimate**, not per table. A table with 4 quartile splits = 4 rows.
- **Always fill `notes`** when anything is imperfect: small N, failed placebo, RI failure, borderline pre-trend.
- **Fill `pre_trend_test` and `pre_trend_pass`** for every DiD result. `pass` / `fail` / `conditional`.
- **Fill `honest_did_m` and `honest_did_pass`** whenever you run Rambachan & Roth sensitivity.
- **Fill `language` and `model_spec`** so co-authors can reproduce any result from the ledger alone.
- **Log null results too** (`in_paper dropped` or `appendix`). They matter for the story.
- **Track the primary estimator only** in main rows. Add robustness variants as separate rows.
- **Update after revision.** When results change, update the DB and check `history`.

## Reference: common section names

| section | what goes here |
|---|---|
| `market` | Market-level DiD (HHI, entropy, etc.) |
| `package` | Package-level DiD by dep/pop/age quartile |
| `mechanism` | Attention market, dep composition, community detection |
| `heterogeneity` | Category, company vs community, activity splits |
| `robustness` | Placebos, alt dates, RI, Honest DiD, PPML |
| `welfare` | Weitzman variety loss, ITS magnitudes |
| `replication` | Rust/Haskell, pooled 4-eco |

## Publishing this skill

See `references/publishing.md` for instructions on packaging and sharing this skill on GitHub.
