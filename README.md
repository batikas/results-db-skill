# results-db — Results Ledger Skill for Claude Code

A Claude Code skill that maintains a structured database of regression results for empirical research papers. Never forget a result between sessions, always know what goes in the paper vs the appendix, and generate a narrative summary of your findings on demand.

## The Problem

Empirically heavy papers accumulate hundreds of estimates — across specifications, estimators, heterogeneity splits, and robustness checks. Without a ledger:
- Results get forgotten between sessions
- The paper narrative drifts from the actual data
- Decisions about inclusion are made informally and inconsistently
- Co-authors and referees find contradictions

## Installation

```bash
claude plugin install github:mbatikas/results-db-skill
```

Or manually: copy `skills/results-db/` to `~/.claude/skills/results-db/`.

## Quick Start

```bash
# 1. Initialize a database in your project
python ~/.claude/skills/results-db/scripts/results_db.py init --project /path/to/project

# 2. Add results (or write a populate script — see examples/)
python ~/.claude/skills/results-db/scripts/results_db.py add --project . \
  --section package --hypothesis H1 --estimator "C&S" \
  --dv delta_downstream --dv_label "Δ Downstream Deps" \
  --sample DepQ4 --att 0.219 --se 0.079 --p 0.007 --n 24336 \
  --in_paper main --notes ""

# 3. Get the story
python ~/.claude/skills/results-db/scripts/results_db.py story --project .

# 4. Check placement status
python ~/.claude/skills/results-db/scripts/results_db.py status --project .

# 5. See what still needs a decision
python ~/.claude/skills/results-db/scripts/results_db.py show --project . --in_paper tbd
```

## Commands

| Command | Description |
|---|---|
| `init` | Create empty `results/results_database.csv` |
| `show` | Filtered table with `--section`, `--sig`, `--in_paper`, `--estimator`, `--dv`, `--sample` |
| `add` | Log a new estimate |
| `update` | Change `in_paper` status or notes (by `--id` or `--dv --sample`) |
| `story` | Narrative summary grouped by section → hypothesis → DV |
| `status` | Count by placement and section |
| `export` | Output as `md`, `latex`, or `csv` |

## Schema (v2.0)

One row per estimate:

| Field | Description |
|---|---|
| `section` | `market` / `package` / `mechanism` / `heterogeneity` / `robustness` / `welfare` / `replication` |
| `hypothesis` | `H1`, `H2a`, or free text |
| `estimator` | `C&S` / `TWFE` / `S&A` / `OLS` / `ITS` / `RI` / `Honest DiD` etc. |
| `dv` / `dv_label` | Machine-readable / human-readable outcome |
| `sample` | `Full` / `DepQ4` / `Active` / `Data Science` etc. |
| `att` / `se` / `p` / `sig` | Estimate, SE, p-value, significance stars |
| `n` | Sample size |
| `in_paper` | `main` / `appendix` / `dropped` / `tbd` |
| `paper_version` | Which paper version: `JPE`, `MS IS`, `WP` etc. |
| `referee_round` | `original` / `R1` / `R2` |
| `language` | Execution language: `Python` / `R` / `Stata` |
| `model_spec` | Model spec summary (e.g. `C&S DiD, pkg+month FE, HC1 SEs`) |
| `pre_trend_test` | Pre-trend / placebo test result (e.g. `RI p=0.000`) |
| `pre_trend_pass` | `pass` / `fail` / `conditional` — did parallel trends hold? |
| `honest_did_m` | Honest DiD breakdown M (e.g. `0.0000`, `0.025`) |
| `honest_did_pass` | `pass` / `fail` / `conditional` — did Honest DiD sensitivity hold? |
| `table_file` / `figure_file` | Relative paths to LaTeX table and figure |
| `source_csv` | CSV file the estimate was read from |
| `notes` | Caveats: failed placebo, RI issues, small N, etc. |

## Commands (v2.0)

| Command | Description |
|---|---|
| `init` | Create empty `results/results_database.csv` |
| `show` | Filtered table with `--section`, `--sig`, `--in_paper`, `--estimator`, `--dv`, `--sample`, `--language`, `--pre_trend_pass`, `--honest_did_pass` |
| `add` | Log a new estimate (all schema fields supported) |
| `update` | Change any field by `--id` or `--dv --sample` (all changes logged to history) |
| `story` | Narrative summary grouped by section → hypothesis → DV; `--forest` for ASCII plot |
| `status` | Count by placement and section |
| `export` | Output as `md`, `latex`, or `csv` |
| `sync` | Scan CSV/tex files, detect new/changed estimates vs DB |
| `check` | Verify DB values match source CSV files |
| `compare` | Side-by-side estimator view for same DV × sample |
| `lint` | 10 integrity checks incl. pre-trend failures, Honest DiD failures, sig/p mismatch |
| `history` | Show change log for a result |
| `template` | Generate starter populate script |

## Good Habits

- **One row per estimate** — not per table. A table with 4 quartile splits = 4 rows.
- **Log null results too** — they matter for the story. Mark them `dropped` or `appendix`.
- **Fill `notes`** whenever anything is imperfect: small N, failed placebo, RI failure, borderline pre-trend.
- **Fill `pre_trend_test` and `pre_trend_pass`** for every DiD result.
- **Fill `honest_did_m` and `honest_did_pass`** whenever you run Rambachan & Roth.
- **Fill `language` and `model_spec`** so any result is self-contained.
- **Write a populate script** (see `examples/populate_example.py`) rather than adding results one-by-one.
- **Update after revision** — when results change, update the DB and check `history`.

## How Claude Uses This Skill

When you ask Claude to:
- "What results do we have for the mechanism section?"
- "What's still not decided for placement?"
- "Give me the story of the package-level findings"
- "Log the new dep composition results"

Claude will invoke this skill, run the appropriate command via Bash, and interpret the output for you.

## License

MIT
