# RHOAI Security Audit

Claude Code skill that orchestrates SAST tools and AI security skills to scan repositories, normalize findings, deduplicate across tools, and generate consolidated reports with trend tracking.

## Install

```bash
# Add marketplace and install
claude plugin marketplace add ugiordan/rhoai-security-audit
claude plugin install rhoai-security-audit
```

## Usage

```bash
# Full audit: SAST + AI skills + report + trends
/security-audit opendatahub-io/opendatahub-operator

# Scan multiple repos
/security-audit opendatahub-io/kserve opendatahub-io/odh-dashboard

# Scan repos from config file
/security-audit --config scan-config.yaml

# Generate report from existing scan data
/security-audit:report --full

# Show trends across runs
/security-audit:trends --last 10
```

## What it does

1. **Scans** repos with 15+ SAST tools (semgrep, trivy, gitleaks, kube-linter, etc.)
2. **Runs AI skills** (adversarial-reviewing, semantic-scan) for deep security analysis
3. **Normalizes** all tool outputs to a common finding format
4. **Deduplicates** findings across tools (same issue found by multiple tools = one finding)
5. **Generates reports**: executive report (critical/high only) or full report (all severities)
6. **Tracks trends** across runs so you can see improvement/regression over time

## Commands

| Command | Description |
|---------|-------------|
| `/security-audit <repos>` | Full scan + report + trends |
| `/security-audit:report` | Generate report from existing scan data |
| `/security-audit:trends` | Show trends across previous runs |

## Flags

| Flag | Description |
|------|-------------|
| `--config <file>` | YAML file with repos list |
| `--branch <name>` | Branch to scan (default: main) |
| `--output <dir>` | Output directory (default: ./output) |
| `--skip-sast` | Skip SAST tools (AI only) |
| `--skip-ai` | Skip AI skills (SAST only) |
| `--ai-prioritize` | AI-assisted finding ranking |
| `--full` | Include all severities in report |
| `--repo <name>` | Filter report/trends to specific repo |
| `--last <n>` | Show last N trend entries |

## Dependencies

For full functionality, install these skills:
- [adversarial-reviewing](https://github.com/ugiordan/adversarial-reviewing)
- [rhoai-semantic-scan](https://github.com/ugiordan/rhoai-semantic-scan)

SAST tools (semgrep, trivy, gitleaks, etc.) must be installed on the system.
