---
name: results-db
description: Use when working on an empirical research paper and need to track, log, query, or decide what to do with regression results. Invoke when the user asks what results are significant, what goes in the paper vs appendix vs dropped, wants a results ledger or narrative, needs to log a new estimate, wants to update the status of a result, or needs to see the full picture before writing a section. Works across any quantitative social-science or economics project.
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
| `estimator` | str | `C&S` / `TWFE` / `S&A` / `SDiD` / `OLS` / `ITS` / `RI` etc. |
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
| `table_file` | str | Path to LaTeX table (relative to project root) |
| `figure_file` | str | Path to figure PDF (relative to project root) |
| `notes` | str | Caveats — failed placebo, RI issues, small N, etc. |

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
```

Supports: `--section`, `--sig` (minimum: `*`, `**`, `***`), `--in_paper`, `--estimator`, `--dv`, `--sample`

### Story — narrative summary of significant results
```bash
python ~/.claude/skills/results-db/scripts/results_db.py story --project .
python ~/.claude/skills/results-db/scripts/results_db.py story --project . --section package
```

Groups by section → hypothesis → outcome. Shows ATT, sig, and in_paper status. Good for sending to co-authors or starting a writing session.

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
  --notes "Placebo fails p=0.004, pre-trend non-parallel"
```

### Export — markdown or LaTeX summary table
```bash
python ~/.claude/skills/results-db/scripts/results_db.py export --project . --format md
python ~/.claude/skills/results-db/scripts/results_db.py export --project . --format latex --in_paper main
```

## Workflow

### Starting a writing session
1. `story` → read the narrative; check it matches what you remember
2. `status` → see how many results are still `tbd`
3. `show --in_paper tbd` → make placement decisions
4. Write the section, pulling numbers from the DB

### After running a new analysis
1. Read results from the output CSV
2. `add` each primary estimate (C&S or primary estimator)
3. `add` robustness variants with `--in_paper appendix`
4. Note any caveats in `--notes`
5. Set `--in_paper tbd` until you decide

### Good habits
- **One row per estimate**, not per table. A table with 4 quartile splits = 4 rows.
- **Always fill `notes`** when anything is imperfect: small N, failed placebo, RI failure, borderline pre-trend.
- **Log null results too** (`in_paper dropped` or `appendix`). They matter for the story.
- **Track the primary estimator only** in main rows. Add robustness variants as separate rows with `in_paper = appendix`.
- **Update after revision.** When a referee asks you to re-run something and results change, update the DB.

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

See `references/publishing.md` for instructions on packaging and sharing this skill on GitHub or agentskills.io.
