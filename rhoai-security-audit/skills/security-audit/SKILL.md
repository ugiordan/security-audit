---
name: security-audit
description: Runs SAST tools and AI skills, generates security reports. Works with Claude Code and OpenCode.
---

# Security Audit

This skill delegates to `pipeline.py`, a deterministic Python
orchestrator. Do not orchestrate steps yourself.

## How to run

```bash
python3 ${CLAUDE_SKILL_DIR:-.}/scripts/pipeline.py $ARGUMENTS
```

The script handles everything: SAST scan, AI skills, triage, and
all report formats. Present the results to the user when it completes.

## Flags

| Flag | Effect |
|------|--------|
| `--skip-ai` | Skip AI skills, SAST only |
| `--no-cache` | Clear AI skill caches, force fresh review |
| `--no-sandbox` | Run AI skills without container isolation |
| `--reports-only` | Regenerate reports from existing scan data |
| `--scan-dir <path>` | Specify scan directory for `--reports-only` |
| `--branch <name>` | Branch to scan (default: main) |
| `--arch-context <path>` | Path or GitHub repo for architecture context |
| `--model <model>` | LLM model (e.g. openai/gpt-4o). Default: harness config |

## Rules

Do not orchestrate steps yourself. Do not add your own security
analysis. Do not invoke AI skills directly. Let pipeline.py handle
everything. If it fails, report the error to the user.
