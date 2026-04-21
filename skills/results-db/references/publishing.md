# Publishing the results-db Skill

## GitHub Repository Structure

For publishing as a standalone skill on GitHub:

```
results-db-skill/
├── README.md                   # Overview, installation, usage
├── LICENSE                     # MIT
├── .claude-plugin/
│   └── plugin.json             # Plugin metadata for Claude Code marketplace
├── skills/
│   └── results-db/
│       ├── SKILL.md            # Main skill file
│       └── scripts/
│           └── results_db.py   # CLI helper
└── examples/
    └── populate_example.py     # Example population script
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
  "homepage": "https://github.com/mbatikas/results-db-skill"
}
```

## Installation for others

```bash
claude plugin install github:mbatikas/results-db-skill
```

## Publishing to agentskills.io

1. Create account at agentskills.io
2. Package: `python -m scripts.package_skill ~/.claude/skills/results-db`
3. Upload the `.skill` file

## README content outline

- What it solves (forgetting results, narrative drift)
- Installation
- Quick start (init + add + story)
- Full command reference
- Schema reference  
- Example: populating from existing CSV outputs
- Design philosophy (one row per estimate, log nulls too)
