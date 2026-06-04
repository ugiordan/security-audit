---
name: security-audit
description: Runs 15 SAST tools and AI security skills against repositories, normalizes outputs, deduplicates findings, generates consolidated markdown + HTML reports with trend tracking. Use when asked to scan repos, generate security reports, check vulnerabilities, review security posture, or track security trends.
---

# Security Audit

This skill delegates to `pipeline.py`, a deterministic Python
orchestrator. Do not orchestrate steps yourself.

## How to run

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/pipeline.py $ARGUMENTS
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
| `--arch-context <path>` | Path to architecture-analyzer output for enriched AI review |

## Examples

```bash
# Full pipeline
python3 ${CLAUDE_SKILL_DIR}/scripts/pipeline.py opendatahub-io/agents-operator

# SAST only, no AI
python3 ${CLAUDE_SKILL_DIR}/scripts/pipeline.py opendatahub-io/kube-auth-proxy --skip-ai

# Force fresh AI review (ignore cache)
python3 ${CLAUDE_SKILL_DIR}/scripts/pipeline.py opendatahub-io/agents-operator --no-cache

# Regenerate reports from existing data
python3 ${CLAUDE_SKILL_DIR}/scripts/pipeline.py opendatahub-io/agents-operator --reports-only
```

## Rules

Do not orchestrate steps yourself. Do not add your own security
analysis. Do not invoke AI skills directly. Let pipeline.py handle
everything. If it fails, report the error to the user.
