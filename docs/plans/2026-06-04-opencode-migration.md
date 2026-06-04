# OpenCode Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the security-audit skill LLM-agnostic by supporting both Claude Code and OpenCode, letting users swap providers via config.

**Architecture:** `pipeline.py` detects the active harness at startup and adapts subprocess calls. Skills use the same SKILL.md format (markdown + YAML frontmatter). OpenShell sandbox policy is generated dynamically per provider. MkDocs Material documentation site covers the full pipeline.

**Tech Stack:** Python 3, MkDocs Material, OpenShell, OpenCode CLI, pytest

**Design Spec:** `docs/specs/2026-06-04-opencode-migration-design.md`

---

### Task 1: Create Feature Branch

**Files:**
- None (git operation only)

- [ ] **Step 1: Create and switch to feature branch**

```bash
cd /Users/ugogiordano/workdir/rhoai/rhoai-security-audit
git checkout -b feat/opencode-migration
```

- [ ] **Step 2: Verify branch**

```bash
git branch --show-current
```

Expected: `feat/opencode-migration`

---

### Task 2: Add Harness Detection

**Files:**
- Modify: `rhoai-security-audit/skills/security-audit/scripts/pipeline.py`
- Create: `rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests for detect_harness()**

```python
# rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py
"""Tests for pipeline.py harness detection and model configuration."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_detect_harness_explicit_override_claude():
    with patch.dict(os.environ, {"SECURITY_AUDIT_HARNESS": "claude"}, clear=False):
        from pipeline import detect_harness
        assert detect_harness() == "claude"


def test_detect_harness_explicit_override_opencode():
    with patch.dict(os.environ, {"SECURITY_AUDIT_HARNESS": "opencode"}, clear=False):
        from pipeline import detect_harness
        assert detect_harness() == "opencode"


def test_detect_harness_claude_skill_dir():
    env = {"CLAUDE_SKILL_DIR": "/some/path"}
    with patch.dict(os.environ, env, clear=False):
        with patch.dict(os.environ, {"SECURITY_AUDIT_HARNESS": ""}, clear=False):
            from pipeline import detect_harness
            assert detect_harness() == "claude"


def test_detect_harness_prefers_claude_over_opencode():
    """When both binaries exist, Claude Code wins (backward compat)."""
    import shutil
    with patch.dict(os.environ, {"SECURITY_AUDIT_HARNESS": "", "CLAUDE_SKILL_DIR": ""}, clear=False):
        with patch.object(shutil, "which", side_effect=lambda x: "/usr/bin/claude" if x == "claude" else None):
            from pipeline import detect_harness
            assert detect_harness() == "claude"


def test_detect_harness_no_harness_exits():
    """When nothing is installed, fail loudly."""
    import shutil
    with patch.dict(os.environ, {"SECURITY_AUDIT_HARNESS": "", "CLAUDE_SKILL_DIR": ""}, clear=False):
        with patch.object(shutil, "which", return_value=None):
            import pytest
            from pipeline import detect_harness
            with pytest.raises(SystemExit):
                detect_harness()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/ugogiordano/workdir/rhoai/rhoai-security-audit
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py -v
```

Expected: FAIL (detect_harness not defined)

- [ ] **Step 3: Implement detect_harness()**

Add to `pipeline.py` after the imports section (around line 30):

```python
def detect_harness():
    """Detect whether running under Claude Code or OpenCode.

    Priority: explicit env var > CLAUDE_SKILL_DIR > claude binary > opencode binary.
    Claude Code preferred when both installed (backward compat).
    Fails loudly when nothing is available.
    """
    harness_override = os.environ.get("SECURITY_AUDIT_HARNESS", "").lower()
    if harness_override in ("claude", "opencode"):
        return harness_override

    if os.environ.get("CLAUDE_SKILL_DIR"):
        return "claude"

    if shutil.which("claude"):
        return "claude"

    if shutil.which("opencode"):
        return "opencode"

    log("No AI harness found. Install Claude Code or OpenCode.", level="ERROR")
    sys.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py -v
```

Expected: all 5 PASS

- [ ] **Step 5: Commit**

```bash
git add rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
       rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py
git commit -m "feat: add detect_harness() with backward-compatible priority

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Add Model Configuration Flag

**Files:**
- Modify: `rhoai-security-audit/skills/security-audit/scripts/pipeline.py`
- Modify: `rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py`

- [ ] **Step 1: Add --model flag to argparse**

In `pipeline.py` `main()`, add after the `--arch-context` argument:

```python
parser.add_argument("--model", default=None,
                    help="LLM model (e.g. anthropic/claude-sonnet-4-6, openai/gpt-4o)")
```

- [ ] **Step 2: Add model resolution logic**

Add function after `detect_harness()`:

```python
def resolve_model(args_model):
    """Resolve model from CLI flag, env var, or None (use harness default)."""
    if args_model:
        return args_model
    return os.environ.get("SECURITY_AUDIT_MODEL") or None
```

- [ ] **Step 3: Commit**

```bash
git add rhoai-security-audit/skills/security-audit/scripts/pipeline.py
git commit -m "feat: add --model flag and SECURITY_AUDIT_MODEL env var

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Add OpenCode Subprocess Path

**Files:**
- Modify: `rhoai-security-audit/skills/security-audit/scripts/pipeline.py`
- Modify: `rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py`

- [ ] **Step 1: Write test for command construction**

Add to `test_pipeline.py`:

```python
def test_build_claude_command():
    from pipeline import _build_ai_command
    cmd = _build_ai_command("claude", "test prompt", model=None)
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--allowedTools" in cmd


def test_build_opencode_command():
    from pipeline import _build_ai_command
    cmd = _build_ai_command("opencode", "test prompt", model="anthropic/claude-sonnet-4-6")
    assert cmd[0] == "opencode"
    assert "run" in cmd
    assert "--model" in cmd
    assert "anthropic/claude-sonnet-4-6" in cmd


def test_build_opencode_command_no_model():
    from pipeline import _build_ai_command
    cmd = _build_ai_command("opencode", "test prompt", model=None)
    assert "--model" not in cmd
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py -v -k "build"
```

- [ ] **Step 3: Extract command construction into _build_ai_command()**

Replace the inline command construction in `_invoke_ai_skill()` with:

```python
def _build_ai_command(harness, prompt, model=None):
    """Build the subprocess command for the detected harness."""
    if harness == "claude":
        plugin_dir = Path.home() / ".claude" / "plugins" / "cache"
        return [
            "claude",
            "--add-dir", str(plugin_dir),
            "-p", prompt,
            "--allowedTools", "Bash,Read,Write,Grep,Glob,Skill,Agent",
            "--max-turns", "100",
        ]
    elif harness == "opencode":
        cmd = ["opencode", "run"]
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["--max-turns", "100", prompt])
        return cmd
    else:
        raise ValueError(f"Unknown harness: {harness}")
```

Update `_invoke_ai_skill()` to call `_build_ai_command(harness, prompt, model)`.

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
       rhoai-security-audit/skills/security-audit/scripts/tests/test_pipeline.py
git commit -m "feat: add OpenCode subprocess path with --model support

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Dynamic OpenShell Policy Per Provider

**Files:**
- Modify: `rhoai-security-audit/skills/security-audit/scripts/pipeline.py`
- Modify: `rhoai-security-audit/skills/security-audit/scripts/openshell-policy.yaml` (becomes a template)
- Create: `rhoai-security-audit/skills/security-audit/scripts/tests/test_policy.py`

- [ ] **Step 1: Write test for policy generation**

```python
# rhoai-security-audit/skills/security-audit/scripts/tests/test_policy.py
"""Tests for dynamic OpenShell policy generation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_policy_anthropic():
    from pipeline import _generate_openshell_policy
    policy = _generate_openshell_policy("anthropic/claude-sonnet-4-6")
    assert "api.anthropic.com" in policy


def test_policy_openai():
    from pipeline import _generate_openshell_policy
    policy = _generate_openshell_policy("openai/gpt-4o")
    assert "api.openai.com" in policy


def test_policy_unknown_provider_uses_env():
    import os
    from unittest.mock import patch
    from pipeline import _generate_openshell_policy
    with patch.dict(os.environ, {"SECURITY_AUDIT_PROVIDER_HOST": "my-api.example.com"}):
        policy = _generate_openshell_policy("custom/model")
        assert "my-api.example.com" in policy


def test_policy_unknown_provider_no_env_raises():
    import os
    import pytest
    from unittest.mock import patch
    from pipeline import _generate_openshell_policy
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            _generate_openshell_policy("custom/model")
```

- [ ] **Step 2: Implement _generate_openshell_policy()**

```python
PROVIDER_ENDPOINTS = {
    "anthropic": "api.anthropic.com",
    "openai": "api.openai.com",
    "google": "generativelanguage.googleapis.com",
}

OPENSHELL_POLICY_TEMPLATE = """version: 1
filesystem_policy:
  include_workdir: true
  read_only:
    - /usr
    - /lib
    - /proc
    - /dev/urandom
    - /etc
  read_write:
    - /tmp
    - /dev/null
network_policies:
  llm_api:
    name: llm-api
    endpoints:
      - host: {provider_host}
        port: 443
        protocol: rest
        enforcement: enforce
        access: full
        request_body_credential_rewrite: true
    binaries:
      - path: /usr/local/bin/claude
      - path: /usr/local/bin/opencode
      - path: /usr/bin/node
      - path: /usr/bin/curl
"""


def _generate_openshell_policy(model):
    """Generate OpenShell network policy for the model's provider."""
    if not model:
        return OPENSHELL_POLICY_TEMPLATE.format(provider_host="api.anthropic.com")

    provider = model.split("/")[0] if "/" in model else model
    host = PROVIDER_ENDPOINTS.get(provider)

    if not host:
        host = os.environ.get("SECURITY_AUDIT_PROVIDER_HOST")
        if not host:
            known = ", ".join(PROVIDER_ENDPOINTS.keys())
            log(f"Unknown provider '{provider}'. Set SECURITY_AUDIT_PROVIDER_HOST "
                f"or use a known provider ({known}).", level="ERROR")
            sys.exit(1)

    return OPENSHELL_POLICY_TEMPLATE.format(provider_host=host)
```

- [ ] **Step 3: Update _run_in_openshell() to use dynamic policy**

```python
def _run_in_openshell(cmd, name, model=None):
    """Run command inside an OpenShell sandbox with dynamic network policy."""
    import tempfile
    policy_content = _generate_openshell_policy(model)
    policy_fd, policy_path = tempfile.mkstemp(suffix=".yaml", prefix="openshell-policy-")
    try:
        os.write(policy_fd, policy_content.encode())
        os.close(policy_fd)

        sandbox_name = f"security-audit-{name}-{int(time.time())}"
        sandbox_cmd = [
            "openshell", "sandbox", "create",
            "--name", sandbox_name,
            "--no-keep",
            "--auto-providers",
            "--policy", policy_path,
            "--",
        ] + cmd

        result = run(sandbox_cmd, check=False, timeout=3600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"  {name} timed out (1h), deleting sandbox", level="WARN")
        subprocess.run(["openshell", "sandbox", "delete", sandbox_name],
                       capture_output=True, text=True, timeout=30)
        return False
    finally:
        os.unlink(policy_path)
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/test_policy.py -v
```

- [ ] **Step 5: Commit**

```bash
git add rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
       rhoai-security-audit/skills/security-audit/scripts/tests/test_policy.py
git commit -m "feat: dynamic OpenShell policy per LLM provider

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Update SKILL.md for Portable Invocation

**Files:**
- Modify: `rhoai-security-audit/skills/security-audit/SKILL.md`

- [ ] **Step 1: Update SKILL.md**

```yaml
---
name: security-audit
description: Runs SAST tools and AI skills, generates security reports. Works with Claude Code and OpenCode.
---

# Security Audit

This skill delegates to `pipeline.py`, a deterministic Python
orchestrator. Do not orchestrate steps yourself.

## How to run

```bash
python3 ${CLAUDE_SKILL_DIR:-.}/scripts/pipeline.py $ARGUMENTS
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
| `--arch-context <path>` | Path or GitHub repo for architecture context |
| `--model <model>` | LLM model (e.g. openai/gpt-4o). Default: harness config |

## Rules

Do not orchestrate steps yourself. Do not add your own security
analysis. Do not invoke AI skills directly. Let pipeline.py handle
everything. If it fails, report the error to the user.
```

- [ ] **Step 2: Commit**

```bash
git add rhoai-security-audit/skills/security-audit/SKILL.md
git commit -m "feat: portable SKILL.md with --model flag, works in both harnesses

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Create opencode.json

**Files:**
- Create: `rhoai-security-audit/opencode.json`

- [ ] **Step 1: Create OpenCode config**

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

- [ ] **Step 2: Commit**

```bash
git add rhoai-security-audit/opencode.json
git commit -m "feat: add opencode.json for OpenCode provider config

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Wire Everything Together in main()

**Files:**
- Modify: `rhoai-security-audit/skills/security-audit/scripts/pipeline.py`

- [ ] **Step 1: Update main() to use detect_harness() and resolve_model()**

In `main()`, after repo validation:

```python
    harness = detect_harness()
    model = resolve_model(args.model)
    log(f"Harness: {harness}")
    if model:
        log(f"Model: {model}")
```

Pass `harness` and `model` through to `step_ai_skills()` and `_invoke_ai_skill()`.

- [ ] **Step 2: Update step_ai_skills() signature**

```python
def step_ai_skills(repo, output_dir, session_file, sandbox=True, no_cache=False,
                   arch_context=None, harness="claude", model=None):
```

Pass `harness` and `model` to `_invoke_ai_skill()`.

- [ ] **Step 3: Update _invoke_ai_skill() to use _build_ai_command()**

Replace the hardcoded claude command with:

```python
    cmd = _build_ai_command(harness, prompt, model)
```

Pass `model` to `_run_in_openshell()`.

- [ ] **Step 4: Run full test suite**

```bash
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: E2E test with Claude Code (regression)**

```bash
cd /Users/ugogiordano/workdir/rhoai/rhoai-security-audit
python3 rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
  opendatahub-io/kube-auth-proxy --skip-ai
```

Expected: 140+ findings, 7 reports, no errors

- [ ] **Step 6: Commit**

```bash
git add rhoai-security-audit/skills/security-audit/scripts/pipeline.py
git commit -m "feat: wire detect_harness() and --model through full pipeline

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Install OpenCode and E2E Test

**Files:**
- None (testing only)

- [ ] **Step 1: Install OpenCode**

```bash
curl -fsSL https://opencode.ai/install | bash
```

- [ ] **Step 2: Configure OpenCode with Anthropic API key**

```bash
# Set up provider (OpenCode should detect ANTHROPIC_API_KEY or prompt)
opencode --version
```

- [ ] **Step 3: E2E test with OpenCode**

```bash
SECURITY_AUDIT_HARNESS=opencode python3 \
  rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
  opendatahub-io/kube-auth-proxy --skip-ai --no-sandbox
```

Expected: same SAST findings as Claude Code run

- [ ] **Step 4: Compare outputs**

Verify both runs produce the same SAST finding count and report files.

---

### Task 10: MkDocs Documentation Site

**Files:**
- Create: `site/mkdocs.yml`
- Create: `site/docs/index.md`
- Create: `site/docs/getting-started/installation.md`
- Create: `site/docs/getting-started/quickstart.md`
- Create: `site/docs/pipeline/overview.md`
- Create: `site/docs/pipeline/sast-tools.md`
- Create: `site/docs/pipeline/ai-skills.md`
- Create: `site/docs/pipeline/triage.md`
- Create: `site/docs/reports/formats.md`
- Create: `site/docs/reports/card-format.md`
- Create: `site/docs/reports/confidence-scoring.md`
- Create: `site/docs/configuration/opencode.md`
- Create: `site/docs/configuration/sandboxing.md`
- Create: `site/docs/configuration/arch-context.md`
- Create: `site/requirements.txt`
- Create: `.github/workflows/docs.yml`

- [ ] **Step 1: Create mkdocs.yml using adversarial-reviewing template**

```yaml
# site/mkdocs.yml
site_name: "RHOAI Security Audit"
site_url: https://ugiordan.github.io/rhoai-security-audit/
repo_url: https://github.com/ugiordan/rhoai-security-audit
repo_name: ugiordan/rhoai-security-audit

copyright: Copyright &copy; Red Hat, Inc.

theme:
  name: material
  language: en
  icon:
    repo: fontawesome/brands/github
    logo: material/shield-lock
  font:
    text: Red Hat Text
    code: Red Hat Mono
  palette:
    - scheme: default
      primary: black
      toggle:
        icon: material/brightness-4
        name: Switch to dark mode
    - scheme: slate
      primary: black
      toggle:
        icon: material/brightness-7
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.top
    - navigation.indexes
    - navigation.path
    - navigation.expand
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.tabs.link
    - toc.follow

plugins:
  - search
  - glightbox

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.tasklist:
      custom_checkbox: true

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/quickstart.md
  - Pipeline:
    - Overview: pipeline/overview.md
    - SAST Tools: pipeline/sast-tools.md
    - AI Skills: pipeline/ai-skills.md
    - Triage System: pipeline/triage.md
  - Reports:
    - Report Formats: reports/formats.md
    - Card Format: reports/card-format.md
    - Confidence Scoring: reports/confidence-scoring.md
  - Configuration:
    - OpenCode Setup: configuration/opencode.md
    - Sandboxing: configuration/sandboxing.md
    - Architecture Context: configuration/arch-context.md
```

- [ ] **Step 2: Create requirements.txt**

```
# site/requirements.txt
mkdocs-material>=9.5
mkdocs-glightbox>=0.4
```

- [ ] **Step 3: Create index.md**

Write the homepage with architecture overview, pipeline diagram (mermaid), feature highlights, and quick links. Include the CONFIDENTIAL banner pattern.

- [ ] **Step 4: Create all documentation pages**

Each page covers one topic with code examples, screenshots (where applicable), and configuration reference. Use admonitions for warnings, tips, and important notes. Use glightbox for image zoom (+/- fullscreen).

- [ ] **Step 5: Create GitHub Actions workflow for docs**

```yaml
# .github/workflows/docs.yml
name: Deploy Docs
on:
  push:
    branches: [main]
    paths: ['site/**']
permissions:
  contents: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r site/requirements.txt
      - run: cd site && mkdocs gh-deploy --force
```

- [ ] **Step 6: Build and test locally**

```bash
cd site && pip install -r requirements.txt && mkdocs serve
```

Open http://localhost:8000 and verify all pages render correctly.

- [ ] **Step 7: Commit**

```bash
git add site/ .github/workflows/docs.yml
git commit -m "docs: MkDocs Material documentation site

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Final E2E Validation and Merge

**Files:**
- None (testing and git operations)

- [ ] **Step 1: Run all unit tests**

```bash
python3 -m pytest rhoai-security-audit/skills/security-audit/scripts/tests/ -v
```

Expected: all tests PASS

- [ ] **Step 2: E2E test with Claude Code (full pipeline)**

```bash
python3 rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
  opendatahub-io/kube-auth-proxy --skip-ai
```

- [ ] **Step 3: E2E test with OpenCode (if installed)**

```bash
SECURITY_AUDIT_HARNESS=opencode python3 \
  rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
  opendatahub-io/kube-auth-proxy --skip-ai --no-sandbox
```

- [ ] **Step 4: Build docs**

```bash
cd site && mkdocs build --strict
```

- [ ] **Step 5: Merge to main**

```bash
git checkout main
git merge feat/opencode-migration --no-ff -m "feat: LLM-agnostic skill framework with OpenCode support

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Sync plugin cache**

```bash
# Copy updated files to plugin cache for immediate use
cp rhoai-security-audit/skills/security-audit/scripts/pipeline.py \
   ~/.claude/plugins/cache/ugiordan-rhoai-security-audit/rhoai-security-audit/1.2.0/skills/security-audit/scripts/
cp rhoai-security-audit/skills/security-audit/SKILL.md \
   ~/.claude/plugins/cache/ugiordan-rhoai-security-audit/rhoai-security-audit/1.2.0/skills/security-audit/
```
