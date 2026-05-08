# RHOAI Security Audit

Claude Code plugin that orchestrates 15+ SAST tools and AI security skills to scan repositories, normalize findings, deduplicate across tools, and generate consolidated reports with trend tracking. Every run produces a full session transcript logging model reasoning at each step.

## Install

```bash
# Add marketplace
claude
/plugin marketplace add ugiordan/rhoai-security-audit
/plugin install rhoai-security-audit@ugiordan-rhoai-security-audit
```

Or test locally without installing:
```bash
claude --plugin-dir ./rhoai-security-audit
```

## Usage

```bash
# Full audit: SAST + AI skills + report + trends
/rhoai-security-audit:security-audit opendatahub-io/opendatahub-operator

# Scan multiple repos
/rhoai-security-audit:security-audit opendatahub-io/kserve opendatahub-io/odh-dashboard

# Scan repos from config file
/rhoai-security-audit:security-audit --config scan-config.yaml

# SAST only (skip AI skills)
/rhoai-security-audit:security-audit opendatahub-io/kube-auth-proxy --skip-ai

# AI only (skip SAST tools)
/rhoai-security-audit:security-audit opendatahub-io/kube-auth-proxy --skip-sast

# Generate report from existing scan data
/rhoai-security-audit:security-audit report --full

# Show trends across runs
/rhoai-security-audit:security-audit trends --last 10
```

## What it does

1. **Scans** repos with 15+ SAST tools (semgrep, trivy, gitleaks, kube-linter, grype, govulncheck, etc.)
2. **Runs AI skills** (adversarial-reviewing, semantic-scan) for deep security analysis
3. **Normalizes** all tool outputs to a common finding format
4. **Deduplicates** findings across tools (same issue found by multiple tools = one finding)
5. **Generates reports**: executive report (critical/high only) or full report (all severities)
6. **Tracks trends** across runs so you can see improvement/regression over time
7. **Logs everything**: full session transcript with model reasoning, agent dispatches, timing

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

## Output

Each scan run produces a dated directory:

```
output/
  kube-auth-proxy/
    2026-05-08/
      raw/                          # Raw tool outputs (JSON/SARIF per tool)
        adversarial-reviewing/      # AI agent outputs
      normalized-findings.json      # All findings in common format
      deduplicated-findings.json    # After cross-tool dedup
      scan-metadata.json            # Date, branch, commit, tool list, counts
      executive-report.md           # Report (critical + high findings)
      session-log.json              # Structured audit trail
      session-transcript.md         # Human-readable model reasoning log
  security-trends.json              # Accumulated across all runs
```

## Session Logging

Every audit run logs model reasoning at each pipeline step, similar to
adversarial-reviewing's telemetry. The `session-transcript.md` captures:

- What tools ran and their output counts
- What AI agents were dispatched (model, prompt, output preview)
- Reasoning for prioritization decisions
- Timing for each step
- Error details when tools fail

## SAST Tools

| Tool | Category | What it checks |
|------|----------|----------------|
| semgrep | SAST | Code patterns, secrets, injection |
| gitleaks | Secrets | Hardcoded credentials in code |
| trufflehog | Secrets | Verified credential detection |
| trivy | SCA | Go/Python/JS dependency CVEs |
| grype | SCA | Dependency vulnerability scanning |
| govulncheck | SCA | Go-specific vulnerability scanning |
| osv-scanner | SCA | OSV database vulnerability lookup |
| pip-audit | SCA | Python dependency audit |
| gosec | SAST | Go security static analysis |
| kube-linter | K8s | Kubernetes manifest best practices |
| hadolint | Config | Dockerfile linting |
| shellcheck | Config | Shell script analysis |
| actionlint | CI/CD | GitHub Actions workflow linting |
| zizmor | CI/CD | GitHub Actions security analysis |
| yamllint | Config | YAML syntax validation |

## AI Skills

| Skill | What it does |
|-------|-------------|
| [adversarial-reviewing](https://github.com/ugiordan/adversarial-reviewing) | Multi-agent review: 5 specialists (security, correctness, performance, quality, architecture) + red team + devil's advocate debate |
| [rhoai-semantic-scan](https://github.com/ugiordan/rhoai-semantic-scan) | 3-agent semantic security analysis (from Matthew Stratto's scanner) |

AI skills must be installed separately as Claude Code plugins.

## Dependencies

SAST tools must be installed on the system. The skill gracefully skips
tools that aren't available and reports which tools ran in the session log.

## Plugin Structure

```
rhoai-security-audit/
  .claude-plugin/
    plugin.json                     # Plugin manifest
  skills/
    security-audit/
      SKILL.md                      # Main skill entry point
      workflows/                    # Detailed step-by-step guides
        audit.md                    # Full scan workflow
        report.md                   # Report-only workflow
        trends.md                   # Trends-only workflow
      reference/
        finding-schema.md           # Normalized finding format
        dedup-rules.md              # Deduplication logic
      scripts/
        normalize.py                # Tool output normalization (13 parsers)
        dedup.py                    # Cross-tool deduplication
        report.py                   # Markdown report generation
        trends.py                   # Trend tracking
        session_log.py              # Session logging and transcript
```
