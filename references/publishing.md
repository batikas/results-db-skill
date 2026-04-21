# Publishing the results-db Skill

## GitHub Repository Structure

For publishing as a standalone skill on GitHub:

```
results-db-skill/
├── README.md                   # Overview, installation, usage
├── .gitignore                  # Exclude generated DB files and caches
├── LICENSE                     # MIT
├── CITATION.cff                # Machine-readable citation metadata
├── RELEASE_CHECKLIST.md        # Step-by-step release flow
├── scripts/
│   └── package_skill.py        # Repo-local packaging helper
├── Makefile                    # Common local commands
├── examples/
│   ├── README.md
│   ├── example_estimates.csv
│   └── example_results_database.csv
├── tests/
│   └── test_package_skill.py
├── .claude-plugin/
│   └── plugin.json             # Plugin metadata for Claude Code marketplace
├── .github/
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── workflows/
│       ├── ci.yml              # Syntax and markdown checks
│       └── release.yml         # Tagged GitHub release creation
├── skills/
│   └── results-db/
│       ├── SKILL.md            # Main skill file
│       └── scripts/
│           ├── results_db.py   # CLI helper
│           └── populate_example.py
└── references/
    └── publishing.md
```

## plugin.json

```json
{
  "name": "results-db",
  "description": "Structured results ledger for empirical research papers",
  "author": {
    "name": "Michail Batikas",
    "email": "mpatikas@gmail.com"
  },
  "version": "1.0.0",
  "homepage": "https://github.com/batikas/results-db-skill"
}
```

## Installation for others

```bash
claude plugin install github:batikas/results-db-skill
```

## Publishing to agentskills.io

1. Create account at agentskills.io
2. Package from the repo root: `python scripts/package_skill.py --repo-root .`
3. Upload the generated `.skill` file from `dist/results-db-skill-v<VERSION>.skill`

## README content outline

- What it solves (forgetting results, narrative drift)
- Installation
- Quick start (init + add + story)
- Full command reference
- Schema reference  
- Example: populating from existing CSV outputs
- Design philosophy (one row per estimate, log nulls too)
