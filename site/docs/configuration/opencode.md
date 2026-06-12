# OpenCode Setup

The pipeline supports both Claude Code and OpenCode as AI harnesses.

## Installation

```bash
npm i -g opencode-ai@latest
```

Or via Homebrew:

```bash
brew install anomalyco/tap/opencode
```

## Harness detection

The pipeline auto-detects the available harness:

1. `SECURITY_AUDIT_HARNESS` env var (explicit override)
2. `CLAUDE_SKILL_DIR` env var (implies Claude Code)
3. `claude` binary on PATH
4. `opencode` binary on PATH

Claude Code is preferred when both are installed. To force OpenCode:

```bash
export SECURITY_AUDIT_HARNESS=opencode
```

## OpenCode configuration

OpenCode reads its provider config from `~/.config/opencode/config.json`. Create this file to enable your provider:

### Google Vertex AI (Claude via Vertex)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "google-vertex": {}
  }
}
```

Required env vars:

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export VERTEX_LOCATION=us-east5
```

Auth: `gcloud auth application-default login`

### Anthropic (direct)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "anthropic": {}
  }
}
```

Requires `ANTHROPIC_API_KEY` in environment.

## Model names

Model format varies by provider:

| Provider | Model ID example |
|---|---|
| `google-vertex-anthropic` | `google-vertex-anthropic/claude-opus-4-6@default` |
| `google-vertex` | `google-vertex/gemini-2.5-pro` |
| `anthropic` | `anthropic/claude-sonnet-4-6` |
| `openai` | `openai/gpt-4o` |

!!! important "Vertex AI Claude models"
    Claude models on Vertex AI use the `google-vertex-anthropic` provider, not `google-vertex`. The `google-vertex` provider is for Gemini models only.

## Running with OpenCode + Vertex AI

Full example:

```bash
export GOOGLE_CLOUD_PROJECT=itpc-gcp-ai-eng-claude
export VERTEX_LOCATION=us-east5
export SECURITY_AUDIT_HARNESS=opencode

# Without sandbox
/security-audit opendatahub-io/batch-gateway \
  --model google-vertex-anthropic/claude-opus-4-6@default \
  --no-sandbox

# With sandbox (OpenShell required)
/security-audit opendatahub-io/batch-gateway \
  --model google-vertex-anthropic/claude-opus-4-6@default
```

## CLI model override

The `--model` flag overrides the default:

```bash
python3 pipeline.py org/repo --model google-vertex-anthropic/claude-opus-4-6@default
```

Or via env var:

```bash
export SECURITY_AUDIT_MODEL=google-vertex-anthropic/claude-opus-4-6@default
```

Priority: `--model` flag > `SECURITY_AUDIT_MODEL` env var > harness default.

## Agent dispatch

The adversarial-reviewing FSM dispatches individual review agents (SEC, PERF, QUAL, CORR, ARCH). These agents always use Claude Code for dispatch because it handles headless file I/O reliably. The harness choice (`opencode` vs `claude`) affects the semantic-scan skill and harness detection, not the FSM agent subprocess.

## Provider endpoints for sandbox

The pipeline maps providers to API endpoints for the OpenShell network policy:

| Provider prefix | API endpoint |
|---|---|
| `anthropic` | `api.anthropic.com` |
| `openai` | `api.openai.com` |
| `google` | `generativelanguage.googleapis.com` |
| `google-vertex` | `us-east5-aiplatform.googleapis.com` |
| `google-vertex-anthropic` | `us-east5-aiplatform.googleapis.com` |

For custom providers:

```bash
export SECURITY_AUDIT_PROVIDER_HOST=my-llm-proxy.internal.company.com
```

## Environment variables

| Variable | Purpose |
|---|---|
| `SECURITY_AUDIT_HARNESS` | Force `claude` or `opencode` harness |
| `SECURITY_AUDIT_MODEL` | Default model (overridden by `--model`) |
| `SECURITY_AUDIT_PROVIDER_HOST` | Custom API endpoint for unknown providers |
| `GOOGLE_CLOUD_PROJECT` | GCP project for Vertex AI |
| `VERTEX_LOCATION` | Vertex AI region (e.g., `us-east5`) |
| `ANTHROPIC_API_KEY` | Anthropic API key (direct provider) |
