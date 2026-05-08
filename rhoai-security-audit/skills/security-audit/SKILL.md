---
name: security-audit
description: Runs SAST tools and AI security skills against repositories, normalizes outputs, deduplicates findings across tools, and generates consolidated reports with trend tracking. Use when asked to scan repos, generate security reports, review security posture, or track security trends.
---

# Security Audit

Full security analysis: SAST tools + AI skills, normalized findings,
cross-tool deduplication, consolidated reports, trend tracking.

## Usage

```
/rhoai-security-audit:security-audit opendatahub-io/opendatahub-operator
/rhoai-security-audit:security-audit opendatahub-io/kserve opendatahub-io/odh-dashboard
/rhoai-security-audit:security-audit --config scan-config.yaml
```

Pass `report` or `trends` as first arg to skip scanning:
```
/rhoai-security-audit:security-audit report --full
/rhoai-security-audit:security-audit trends --last 10
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--config <file>` | - | YAML file with `repos:` list |
| `--branch <name>` | main | Branch to scan |
| `--output <dir>` | ./output | Output directory |
| `--skip-sast` | false | Skip SAST tools (AI only) |
| `--skip-ai` | false | Skip AI skills (SAST only) |
| `--ai-prioritize` | false | AI-assisted finding ranking |
| `--full` | false | Include all severities in report |
| `--repo <name>` | all | Filter report/trends to specific repo |
| `--last <n>` | 10 | Show last N trend entries |

## Intent Detection

Determine what the user wants from their request:

- "scan", "audit", "analyze", "check security" -> full audit (see [workflows/audit.md](workflows/audit.md))
- "report", "summary", "findings" (no scan) -> report only (see [workflows/report.md](workflows/report.md))
- "trends", "history", "over time", "track" -> trends only (see [workflows/trends.md](workflows/trends.md))
- Ambiguous or "do everything" -> chain: audit, then report, then trends

## Output Structure

```
output/
  <repo-name>/
    <YYYY-MM-DD>/
      raw/                          # Raw tool outputs (JSON/SARIF)
      normalized-findings.json
      deduplicated-findings.json
      scan-metadata.json
      executive-report.md
    <YYYY-MM-DD>-2/                 # Counter if date dir exists
  security-trends.json              # Accumulated across all runs
```

## Scripts

All deterministic work uses bundled Python scripts. Run via:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/normalize.py <results-dir>
python3 ${CLAUDE_SKILL_DIR}/scripts/dedup.py <normalized.json>
python3 ${CLAUDE_SKILL_DIR}/scripts/report.py <output-dir> [--full]
python3 ${CLAUDE_SKILL_DIR}/scripts/trends.py --show --trends-file <file>
```

## Tools

**SAST** (via scan-repo.sh): semgrep, gitleaks, trufflehog, kube-linter,
hadolint, actionlint, zizmor, shellcheck, trivy, grype, govulncheck,
pip-audit, osv-scanner, gosec, yamllint

**AI Skills** (native invocation): adversarial-reviewing, semantic-scan

## Normalization

All tool outputs are normalized to a common format.
See [reference/finding-schema.md](reference/finding-schema.md).

## Deduplication

Findings from multiple tools pointing to the same issue are merged.
See [reference/dedup-rules.md](reference/dedup-rules.md).
