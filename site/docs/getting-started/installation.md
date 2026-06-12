# Installation

## Prerequisites

- **Python 3.10+** with `pip` or `uv`
- **Git** for cloning target repositories
- **Podman or Docker** for running SAST tools in a container
- **Go 1.21+** (optional, for `govulncheck` and `gosec`)

## Install the skill

### Claude Code

Install as a plugin:

```bash
claude plugin install ugiordan/rhoai-security-audit
```

The skill registers as `/security-audit` and is available immediately.

### OpenCode

Clone the repository and configure `opencode.json`:

```bash
git clone https://github.com/ugiordan/rhoai-security-audit.git
cd rhoai-security-audit
```

The repository includes an `opencode.json` at `rhoai-security-audit/opencode.json`:

```json
{
  "model": "anthropic/claude-sonnet-4-6",
  "small_model": "anthropic/claude-haiku-4-5",
  "provider": {
    "anthropic": {}
  },
  "permission": {
    "bash": "allow",
    "read": "allow",
    "edit": "allow",
    "glob": "allow",
    "grep": "allow",
    "skill": "allow",
    "task": "allow"
  }
}
```

See [OpenCode Setup](../configuration/opencode.md) for provider configuration details.

## Install SAST tools

The pipeline needs the SAST tools available on PATH. The `install_tools.sh` script downloads pinned versions to a local cache directory (no system modification):

```bash
source skills/security-audit/scripts/install_tools.sh
```

This installs to `~/.cache/security-audit-tools/` and updates PATH for the current shell session. Tools are cached between runs, so subsequent invocations skip already-installed binaries.

### What gets installed

| Tool | Method | Version |
|---|---|---|
| semgrep | pip (venv) | latest |
| gitleaks | binary | 8.30.0 |
| trufflehog | binary | 3.92.3 |
| shellcheck | binary | 0.10.0 |
| hadolint | binary | 2.14.0 |
| trivy | binary | 0.70.0 |
| grype | binary | 0.112.0 |
| kube-linter | binary | 0.8.3 |
| actionlint | binary | 1.7.8 |
| osv-scanner | binary | 2.3.8 |
| zizmor | pip (venv) | latest |
| yamllint | pip (venv) | latest |
| pip-audit | pip (venv) | latest |
| govulncheck | `go install` | 1.1.4 |
| gosec | `go install` | 2.22.4 |

!!! info "Go tools are optional"
    `govulncheck` and `gosec` are only installed if Go is already on PATH. The pipeline runs without them, you just lose Go-specific analysis.

## OpenShell setup (sandboxing)

AI skills run inside an OpenShell sandbox by default. Install OpenShell:

```bash
# Using uv (preferred)
uv tool install -U openshell

# Or using pip
pip3 install openshell
```

Start the gateway:

```bash
brew services start openshell
```

Verify connectivity:

```bash
openshell status
# Should output: Connected
```

!!! tip "Running without sandbox"
    Use `--no-sandbox` to skip OpenShell isolation. This is fine for local development but not recommended for automated pipelines.

## Container runtime

The SAST scan step runs tools inside a container using the scanner image. The pipeline auto-detects `podman` or `docker`:

```bash
# Verify your container runtime
podman --version   # or: docker --version
```

The scanner container is built from `rhoai-security-audit/Dockerfile.scanner` and includes all 15 SAST tools pre-installed.
