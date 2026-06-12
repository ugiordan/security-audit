# Quick Start

## Run your first scan

### Using Claude Code

```bash
claude "/security-audit opendatahub-io/kube-auth-proxy"
```

### Using OpenCode + Vertex AI

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project
export VERTEX_LOCATION=us-east5
export SECURITY_AUDIT_HARNESS=opencode
/security-audit opendatahub-io/kube-auth-proxy \
  --model google-vertex-anthropic/claude-opus-4-6@default
```

See [OpenCode Setup](../configuration/opencode.md) for provider configuration.

### Using pipeline.py directly

```bash
python3 skills/security-audit/scripts/pipeline.py opendatahub-io/kube-auth-proxy --no-sandbox
```

!!! note "First run takes longer"
    The first scan downloads SAST tool databases (trivy, grype, osv-scanner) and clones the target repository. Subsequent runs use cached databases.

## What happens

The pipeline runs through six steps:

1. **Init**: Creates the output directory and session log
2. **SAST scan**: Clones the repo into a container, runs 15+ tools
3. **AI skills**: Spawns adversarial-reviewing and semantic-scan agents (in parallel with SAST)
4. **Normalize + dedup + triage**: Converts all tool outputs to a common schema, removes duplicates, cross-correlates SAST and AI findings
5. **Reports**: Generates all 7 report formats
6. **Finalize**: Updates trend data and closes the session log

Console output looks like:

```
[14:22:01] [INFO] Security audit: opendatahub-io/kube-auth-proxy
[14:22:01] [INFO] Output: ~/.security-audit/output/kube-auth-proxy/2026-06-04-142201
[14:22:01] [INFO] Sandbox: enabled
[14:22:01] [INFO] Container runtime: podman
[14:22:01] [INFO] Step 1: Init (opendatahub-io/kube-auth-proxy -> ~/.security-audit/output/kube-auth-proxy/2026-06-04-142201)
[14:22:01] [INFO] Step 2: SAST scan + AI skills (parallel)
[14:22:01] [INFO] Step 2: SAST scan
[14:22:01] [INFO] Step 3: AI skills
...
[14:28:33] [INFO] Step 4: Normalize, deduplicate, triage
[14:28:33] [INFO]   47 triaged findings
[14:28:33] [INFO] Step 5: Generate reports
[14:28:34] [INFO]   executive-report.md OK
[14:28:34] [INFO]   must-fix-report.md OK
[14:28:35] [INFO]   security-report.html OK
[14:28:35] [INFO]   must-fix-report.html OK
[14:28:36] [INFO]   MkDocs site OK
[14:28:36] [INFO]   security-report.docx OK
[14:28:36] [INFO]   must-fix-report.docx OK
[14:28:36] [INFO] Step 6: Finalize
[14:28:36] [INFO] Results: 47 findings
[14:28:36] [INFO]   Severity: {'high': 12, 'medium': 18, 'low': 14, 'info': 3}
[14:28:36] [INFO]   Triage: {'sast-only': 30, 'ai-only': 9, 'corroborated': 8}
[14:28:36] [INFO] Reports in: ~/.security-audit/output/kube-auth-proxy/2026-06-04-142201/
[14:28:36] [INFO] Pipeline complete
```

## Output directory structure

```
~/.security-audit/output/kube-auth-proxy/2026-06-04-142201/
  raw/                          # Raw tool outputs
    semgrep.json
    gitleaks.json
    trivy.json
    ...
    adversarial-reviewing/      # AI skill outputs
      REPORT.md
      SEC-findings.md
      ...
    semantic-scan/
      security-report.md
      repo-analysis.md
  normalized-findings.json      # All findings in common schema
  deduplicated-findings.json    # After dedup
  triaged-findings.json         # After cross-correlation + triage
  executive-report.md           # Full markdown report
  must-fix-report.md            # Critical + high only
  security-report.html          # Self-contained HTML report
  must-fix-report.html          # Must-fix HTML report
  security-report.docx          # Word document (full)
  must-fix-report.docx          # Word document (must-fix)
  report-site/                  # MkDocs static site
  scan-metadata.json            # Scan metadata
  session-log.json              # Pipeline execution log
```

## Opening reports

### HTML reports

Open directly in a browser:

```bash
open ~/.security-audit/output/kube-auth-proxy/2026-06-04-142201/security-report.html
```

The HTML reports are completely self-contained (all CSS and JS inlined). They include:

- Stat cards and donut chart at the top
- Filter chips for severity, source, and triage status
- Finding cards with code snippets and GitHub file links
- Collapsible dependency CVE section

### Word reports

Open with any .docx-compatible application:

```bash
open ~/.security-audit/output/kube-auth-proxy/2026-06-04-142201/security-report.docx
```

### MkDocs site

Serve locally:

```bash
cd ~/.security-audit/output/kube-auth-proxy/2026-06-04-142201/report-site
python3 -m http.server 8000
```

## Common flags

| Flag | What it does |
|---|---|
| `--skip-ai` | SAST only, skip AI skills (faster, lower coverage) |
| `--no-sandbox` | Run AI skills without OpenShell isolation |
| `--no-cache` | Clear AI skill caches, force fresh review |
| `--branch <name>` | Scan a specific branch (default: main) |
| `--arch-context <path>` | Provide architecture-analyzer output for richer AI context |
| `--model <model>` | LLM model, e.g. `openai/gpt-4o` or `anthropic/claude-sonnet-4-6` |
| `--reports-only` | Regenerate reports from existing scan data |
| `--scan-dir <path>` | Specify scan directory for `--reports-only` |
