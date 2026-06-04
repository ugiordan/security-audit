# LLM-Agnostic Skill Framework: OpenCode Migration

**Date:** 2026-06-04
**Status:** Design
**Branch:** `feat/opencode-migration`

## Problem

The security-audit and adversarial-reviewing skills are locked to Claude Code's
proprietary skill system. Users cannot swap LLM providers without rewriting the
entire skill infrastructure. The skill format (SKILL.md with YAML frontmatter)
is identical between Claude Code and OpenCode, but the orchestration layer
(subprocess calls, plugin discovery, permissions) differs.

## Goals

1. Skills work in both Claude Code and OpenCode without modification
2. Users can swap LLM providers (Claude, GPT, Gemini, local models) via config
3. `pipeline.py` detects the active harness at runtime and adapts
4. No hook dependencies (already eliminated)
5. Backward compatible: existing Claude Code users aren't broken

## Non-Goals

- Rewriting skills in a new format
- Dropping Claude Code support
- Building a custom harness

## Design

### Harness Detection

`pipeline.py` detects the active harness at startup via environment variables
and binary availability:

```python
def detect_harness():
    if os.environ.get("CLAUDE_SKILL_DIR"):
        return "claude"
    if os.environ.get("OPENCODE_CONFIG") or shutil.which("opencode"):
        return "opencode"
    if shutil.which("claude"):
        return "claude"
    return "opencode"
```

### AI Skill Invocation

The subprocess call adapts based on harness:

```python
if harness == "claude":
    cmd = [
        "claude", "--add-dir", str(plugin_dir),
        "-p", prompt,
        "--allowedTools", "Bash,Read,Write,Grep,Glob,Skill,Agent",
        "--max-turns", "100",
    ]
elif harness == "opencode":
    cmd = [
        "opencode", "run",
        "--model", model,
        "--agent", "build",
        prompt,
    ]
```

Key differences:
- Claude Code: `claude -p "prompt"` with `--add-dir` for plugin discovery
- OpenCode: `opencode run "prompt"` with `--model` for provider selection

### Directory Structure

```
rhoai-security-audit/
  skills/
    security-audit/
      SKILL.md                  # works in both harnesses
      scripts/
        pipeline.py             # harness-agnostic orchestrator
        normalize.py
        dedup.py
        triage.py
        report_common.py
        report_standalone.py
        report_mustfix.py
        report_html.py
        report_docx.py
        report.py
        openshell-policy.yaml
        scan_container.sh
        install_tools.sh
        run_all.sh
        session_log.py
        trends.py
        tests/
          test_dedup.py
          test_triage.py
    adversarial-reviewing/      # symlink or copy from adversarial-reviewing repo
  opencode.json                 # OpenCode provider config
  .claude-plugin/               # Claude Code plugin manifest (backward compat)
    plugin.json
    marketplace.json
```

Both harnesses discover skills from the `skills/` directory. Claude Code uses
`--add-dir`, OpenCode uses config path in `opencode.json`.

### SKILL.md Format (Unchanged)

```yaml
---
name: security-audit
description: Runs SAST tools and AI skills, generates security reports.
---

# Security Audit

python3 ${CLAUDE_SKILL_DIR}/scripts/pipeline.py $ARGUMENTS
```

The `${CLAUDE_SKILL_DIR}` variable is set by Claude Code. OpenCode has no
equivalent variable. For OpenCode compatibility, the SKILL.md should use a
command that works in both:

```bash
python3 "$(dirname "$(find . -path '*/security-audit/scripts/pipeline.py' | head -1)")/pipeline.py" $ARGUMENTS
```

Or simpler: `pipeline.py` resolves its own location via
`Path(__file__).resolve().parent.parent` so it works regardless of how it's
invoked. The SKILL.md can fall back to discovering pipeline.py relative to
itself.

### Model Configuration

OpenCode config (`opencode.json`):

```json
{
  "model": "anthropic/claude-sonnet-4-6",
  "small_model": "anthropic/claude-haiku-4-5",
  "provider": {
    "anthropic": {}
  }
}
```

Users swap providers by changing `model`:
- `"openai/gpt-4o"` for GPT
- `"google/gemini-2.5-pro"` for Gemini
- `"ollama/llama3"` for local models

`pipeline.py` reads the model from:
1. `--model` CLI flag (highest priority)
2. `SECURITY_AUDIT_MODEL` env var
3. harness default (whatever the user configured)

### Permissions

Claude Code: `--allowedTools "Bash,Read,Write,Grep,Glob,Skill,Agent"`

OpenCode: permissions in `opencode.json`:
```json
{
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

`pipeline.py` passes `--dangerously-skip-permissions` for OpenCode headless
runs (same as Claude Code's `--allowedTools` pattern for non-interactive use).

### Adversarial-Reviewing Integration

The adversarial-reviewing skill uses Agent/Task tool for subagent dispatch.
Both harnesses support this:

- Claude Code: `Agent(subagent_type="review-specialist", prompt="...")`
- OpenCode: Task tool dispatches subagents based on agent definitions

The FSM orchestrator (`scripts/orchestrator/`) is pure Python and doesn't
depend on the harness. It writes dispatch.json, the hosting session reads it
and dispatches agents via whichever tool is available.

### Testing Strategy

1. **Unit tests**: existing test_dedup.py and test_triage.py (harness-independent)
2. **E2E test with Claude Code**: `claude -p "Skill(skill='security-audit', args='repo')""`
3. **E2E test with OpenCode**: `opencode run "Use skill security-audit on repo"`
4. **Comparison test**: run both on same repo, verify same SAST findings, similar AI findings
5. **Provider swap test**: run with OpenCode + different model, verify pipeline completes

### Migration Steps

1. Create `feat/opencode-migration` branch
2. Add `detect_harness()` to pipeline.py
3. Add OpenCode subprocess path (`opencode run`)
4. Create `opencode.json` with provider config
5. Add `--model` flag to pipeline.py
6. Test with Claude Code (regression)
7. Install OpenCode, test with OpenCode + Claude model
8. Test with OpenCode + different model (e.g., GPT)
9. Update SKILL.md to document both harnesses
10. Merge after all tests pass

### Risk Assessment

| Risk | Mitigation |
|------|-----------|
| OpenCode skill discovery differs | SKILL.md format is identical, only paths differ |
| Agent dispatch works differently | FSM orchestrator is Python, not harness-dependent |
| Provider-specific prompt differences | pipeline.py prompt is model-agnostic |
| OpenCode headless mode less mature | Fallback to Claude Code if OpenCode fails |
| Breaking existing Claude Code users | Dual support, no removals |

## Success Criteria

1. `/security-audit repo` works from both Claude Code and OpenCode sessions
2. `pipeline.py repo` works as a standalone script regardless of harness
3. User can swap model by changing one config line
4. All existing unit tests pass
5. E2E pipeline produces valid reports with both harnesses
