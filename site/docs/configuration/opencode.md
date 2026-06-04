# OpenCode Setup

The pipeline supports both Claude Code and OpenCode as AI harnesses. This page covers OpenCode-specific configuration.

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

## opencode.json reference

The repository ships with an `opencode.json` at `rhoai-security-audit/opencode.json`:

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

### Key fields

| Field | Description |
|---|---|
| `model` | Primary model for AI skills. Format: `provider/model-name`. |
| `small_model` | Smaller model for lightweight tasks. |
| `provider` | Provider configuration. Empty `{}` means use default env vars for auth. |
| `permission` | Tool permissions. All set to `allow` because the pipeline needs full access to run scans. |

## Switching providers

### Anthropic (default)

```json
{
  "model": "anthropic/claude-sonnet-4-6",
  "provider": {
    "anthropic": {}
  }
}
```

Requires `ANTHROPIC_API_KEY` in environment.

### OpenAI

```json
{
  "model": "openai/gpt-4o",
  "provider": {
    "openai": {}
  }
}
```

Requires `OPENAI_API_KEY` in environment.

### Google

```json
{
  "model": "google/gemini-2.5-pro",
  "provider": {
    "google": {}
  }
}
```

Requires `GOOGLE_API_KEY` in environment.

## CLI model override

The `--model` flag overrides whatever is configured in `opencode.json`:

```bash
python3 pipeline.py org/repo --model openai/gpt-4o
```

You can also use the `SECURITY_AUDIT_MODEL` env var:

```bash
export SECURITY_AUDIT_MODEL=openai/gpt-4o
python3 pipeline.py org/repo
```

Priority: `--model` flag > `SECURITY_AUDIT_MODEL` env var > `opencode.json` config.

## Provider endpoints

The pipeline maps providers to API endpoints for the OpenShell network policy:

| Provider prefix | API endpoint |
|---|---|
| `anthropic` | `api.anthropic.com` |
| `openai` | `api.openai.com` |
| `google` | `generativelanguage.googleapis.com` |

For custom or self-hosted providers, set:

```bash
export SECURITY_AUDIT_PROVIDER_HOST=my-llm-proxy.internal.company.com
```

## AI command construction

When the pipeline invokes an AI skill under OpenCode, it builds this command:

```bash
opencode run --model <model> --max-turns 100 "<prompt>"
```

Under Claude Code:

```bash
claude --add-dir <plugin-dir> -p "<prompt>" \
  --allowedTools Bash,Read,Write,Grep,Glob,Skill,Agent \
  --max-turns 100
```

Both commands get wrapped in an OpenShell sandbox when sandboxing is enabled.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECURITY_AUDIT_HARNESS` | Force `claude` or `opencode` harness |
| `SECURITY_AUDIT_MODEL` | Default model (overridden by `--model`) |
| `SECURITY_AUDIT_PROVIDER_HOST` | Custom API endpoint for unknown providers |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google API key |
