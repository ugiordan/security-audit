# SAST Tools

The pipeline runs 15+ static analysis tools, each targeting a specific class of vulnerability. All tool outputs are normalized to a [common finding schema](#normalized-schema) before triage.

## Tool inventory

| Tool | ID Prefix | Category | What it detects |
|---|---|---|---|
| **semgrep** | `SEM` | Code analysis | Injection flaws, insecure patterns, custom rules per language |
| **gitleaks** | `GLK` | Secrets | Hardcoded API keys, tokens, passwords in source and git history |
| **trufflehog** | `THG` | Secrets | High-entropy strings, verified credentials across 700+ detectors |
| **trivy** | `TRV` | SCA / Config | CVEs in dependencies, container image vulnerabilities, IaC misconfigs |
| **grype** | `GRP` | SCA | Vulnerability matching against SBOM, OS packages, language deps |
| **osv-scanner** | `OSV` | SCA | Known vulnerabilities via the OSV database (Google's unified vuln DB) |
| **kube-linter** | `KBL` | Kubernetes | K8s manifest misconfigurations: missing resource limits, privileged pods, missing network policies |
| **hadolint** | `HDL` | Containers | Dockerfile best practices: `RUN` as root, missing `USER`, `COPY --chown` |
| **shellcheck** | `SHC` | Shell scripts | Bash/sh bugs: unquoted variables, word splitting, deprecated syntax |
| **actionlint** | `ACT` | CI/CD | GitHub Actions workflow errors: invalid expressions, missing permissions, unsafe `${{ }}` interpolation |
| **zizmor** | `ZIZ` | CI/CD | GitHub Actions security: unpinned actions, command injection via inputs, artifact poisoning |
| **govulncheck** | `GVC` | Go security | Reachable vulnerabilities in Go dependencies (call graph analysis) |
| **gosec** | `GSC` | Go security | Go source code security: SQL injection, hardcoded credentials, unsafe crypto |
| **yamllint** | `YML` | Config | YAML syntax and style: duplicate keys, incorrect indentation, truthy values |
| **pip-audit** | `PIP` | SCA (Python) | Known vulnerabilities in Python dependencies via PyPI advisory DB |

!!! note "Language-conditional tools"
    `govulncheck` and `gosec` only run if Go is installed. `pip-audit` only runs if Python dependencies are detected. The pipeline adapts to whatever is available.

## How tools are run

Each tool is executed by `run_all.sh` inside the scanner container with a 10-minute timeout:

```bash
run_tool "semgrep" \
  "semgrep scan --config auto --json -o ${RESULTS_DIR}/semgrep.json ${WORKDIR}" \
  "${RESULTS_DIR}/semgrep.json" \
  '{"results":[]}'
```

If a tool fails or times out, it's logged but doesn't block the pipeline. The `empty_default` parameter ensures downstream scripts always have valid JSON to process.

## Tool outputs

Raw outputs are written to `<scan-dir>/raw/` in each tool's native JSON format:

```
raw/
  semgrep.json          # Semgrep SARIF-like results
  gitleaks.json         # Gitleaks findings array
  trufflehog.json       # TruffleHog results
  trivy.json            # Trivy JSON report
  grype.json            # Grype matches
  osv-scanner.json      # OSV scanner results
  kube-linter.json      # KubeLinter reports
  hadolint.json         # Hadolint warnings
  shellcheck.json       # ShellCheck findings
  actionlint.json       # Actionlint errors
  zizmor.json           # Zizmor findings
  govulncheck.json      # Govulncheck vulns
  gosec.json            # Gosec issues
  yamllint.json         # Yamllint problems
  pip-audit.json        # pip-audit advisories
  security-summary.json # Aggregate counts
  commit-info.json      # Scanned commit SHA + branch
```

## Normalized schema

After running, `normalize.py` converts each tool's output to a common format:

```json
{
  "id": "SEM-001",
  "source": "semgrep",
  "severity": "high",
  "category": "injection",
  "file": "pkg/handler/auth.go",
  "line_start": 42,
  "line_end": 55,
  "title": "SQL injection via string concatenation",
  "description": "User input concatenated into SQL query without parameterization",
  "confidence": 0.85,
  "rule_id": "go.lang.security.audit.sqli.string-concat",
  "detected_by": ["semgrep"],
  "recommendation": ""
}
```

### Severity mapping

Tools use different severity labels. The normalizer maps them to five levels:

| Normalized | Tool labels that map here |
|---|---|
| `critical` | CRITICAL, ERROR |
| `high` | HIGH, WARNING, warning |
| `medium` | MEDIUM |
| `low` | LOW |
| `info` | INFO, NOTE, style |

### Categories

Each finding is classified into one of ten categories:

| Category | Description |
|---|---|
| `injection` | SQL, command, template, header injection |
| `auth` | Authentication, authorization, session, RBAC |
| `crypto` | Weak algorithms, hardcoded keys, TLS bypass |
| `config` | Misconfigurations, debug mode, insecure defaults |
| `secrets` | Hardcoded credentials, exposed tokens |
| `k8s` | Kubernetes/container security (SCC, network policies, RBAC) |
| `cicd` | CI/CD pipeline security (actions, workflows) |
| `sca` | Vulnerable dependencies (CVEs) |
| `data-exposure` | Sensitive data in logs, errors, responses |
| `other` | Anything not fitting the above categories |

### ID prefixes

Every finding gets a stable ID composed of a tool prefix and a sequence number:

| Prefix | Tool |
|---|---|
| `SEM` | semgrep |
| `GLK` | gitleaks |
| `THG` | trufflehog |
| `TRV` | trivy |
| `GRP` | grype |
| `KBL` | kube-linter |
| `HDL` | hadolint |
| `ACT` | actionlint |
| `ZIZ` | zizmor |
| `GVC` | govulncheck |
| `SHC` | shellcheck |
| `GSC` | gosec |
| `PIP` | pip-audit |
| `OSV` | osv-scanner |
| `YML` | yamllint |
| `ADV` | adversarial-reviewing |
| `SSC` | semantic-scan |
