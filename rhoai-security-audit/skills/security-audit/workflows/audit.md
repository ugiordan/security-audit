# Audit Workflow

Full security scan: SAST tools + AI skills + normalize + dedup + report.

## Checklist

```
Audit Progress:
- [ ] Step 1: Parse input and init session log
- [ ] Step 2: Clone repo
- [ ] Step 3: Run SAST tools
- [ ] Step 4: Run AI skills (adversarial-reviewing)
- [ ] Step 5: Normalize outputs
- [ ] Step 6: Deduplicate findings
- [ ] Step 7: Save results
- [ ] Step 8: Generate report
- [ ] Step 9: Update trends
- [ ] Step 10: Finalize session log
```

## Step 1: Parse input and init session log

Accept repos as:
- Space-separated args: `opendatahub-io/kserve opendatahub-io/odh-dashboard`
- Config file: `--config scan-config.yaml` (YAML with `repos:` list)

Parse flags. Set defaults for missing flags.

Create the output directory and initialize the session log:

```bash
DATE=$(date -u +%Y-%m-%d)
OUTPUT_DIR="output/${REPO_SHORT}/${DATE}"
mkdir -p "${OUTPUT_DIR}/raw"

python3 ${CLAUDE_SKILL_DIR}/scripts/session_log.py init \
  --repo "${REPO}" --output-dir "${OUTPUT_DIR}"
```

Save the `session_file` path from the JSON output. Log every step below.

To log a step:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/session_log.py step \
  --session-file "${SESSION_FILE}" \
  --name "Step name" --status ok \
  --detail "What happened" \
  --reasoning "Why this approach was chosen" \
  --duration <seconds>
```

## Step 2: Clone repo

```bash
WORKDIR=$(mktemp -d)
git clone --depth 1 --branch "${BRANCH:-main}" \
  "https://github.com/${REPO}.git" "$WORKDIR/repo"
COMMIT_SHA=$(git -C "$WORKDIR/repo" rev-parse HEAD)
```

Log the step with commit SHA in detail.

## Step 3: Run SAST tools

Run each available tool against the cloned repo. For each tool, capture
output to `${OUTPUT_DIR}/raw/<tool>-report.json` (or `.sarif`).

Tools to run (skip any not installed):
- `semgrep scan --config auto --json`
- `gitleaks detect --source <repo> --report-format json`
- `shellcheck -f json` (on .sh files)
- `hadolint -f sarif` (on Dockerfiles)
- `trivy fs --format json --scanners vuln`
- `kube-linter lint --format json` (on config/ dir)
- `trufflehog filesystem <repo> --json`
- `govulncheck -format json ./...` (if go.mod exists)
- `grype dir:<repo> -o json`
- `osv-scanner --json <repo>`
- `gosec -fmt json ./...` (if go.mod exists)

Log the step with tool count and total findings in detail.

Skip if `--skip-sast` flag is set. Log as skipped.

## Step 4: Run AI skills

Invoke installed AI skills against the cloned repo. Each skill runs
as a separate agent dispatch.

### adversarial-reviewing

If the `adversarial-reviewing` plugin is installed, invoke it:

```
Skill(skill="adversarial-reviewing:adversarial-reviewing", args="<repo-path>")
```

After it completes, copy its outputs from the adversarial-reviewing
cache directory to `${OUTPUT_DIR}/raw/adversarial-reviewing/`.

Log the agent dispatch:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/session_log.py agent \
  --session-file "${SESSION_FILE}" \
  --name "adversarial-reviewing" --phase "full-review" \
  --output-file "${OUTPUT_DIR}/raw/adversarial-reviewing/output.md" \
  --model "<model-used>" --duration <seconds> \
  --findings-count <count>
```

### semantic-scan (if available)

If the `rhoai-semantic-scan` plugin is installed, invoke it similarly.

**Important**: Log every agent dispatch, including the model used,
duration, and any reasoning the agent provided. This creates a full
audit trail of what the AI "thought" at each step.

Skip if `--skip-ai` flag is set. Log as skipped.

## Step 5: Normalize outputs

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/normalize.py" "${OUTPUT_DIR}/raw" \
  > "${OUTPUT_DIR}/normalized-findings.json"
```

Log the step with finding counts per tool.

## Step 6: Deduplicate findings

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/dedup.py" \
  "${OUTPUT_DIR}/normalized-findings.json" \
  > "${OUTPUT_DIR}/deduplicated-findings.json"
```

Log with raw vs deduped counts.

## Step 7: Save metadata

```bash
python3 -c "
import json
data = {
    'date': '${DATE}',
    'repo': '${REPO}',
    'branch': '${BRANCH}',
    'commit': '${COMMIT_SHA}',
    'tools_run': [<list of tools that ran>],
    'ai_skills_run': [<list of AI skills that ran>],
    'findings': {
        'critical': <count>, 'high': <count>,
        'medium': <count>, 'low': <count>, 'info': <count>,
        'total_raw': <raw_count>, 'total_deduped': <dedup_count>
    }
}
json.dump(data, open('${OUTPUT_DIR}/scan-metadata.json', 'w'), indent=2)
"
```

## Step 8: Generate report

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/report.py" "${OUTPUT_DIR}" \
  > "${OUTPUT_DIR}/executive-report.md"
```

If `--ai-prioritize` flag is set, review the critical/high findings
and rank by actual exploitability before generating the report.
Log your reasoning for each prioritization decision.

Present the executive report to the user.

## Step 9: Update trends

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/trends.py" \
  --add "${OUTPUT_DIR}/scan-metadata.json" \
  --trends-file "output/security-trends.json"
```

Show the trends table to the user.

## Step 10: Finalize session log

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/session_log.py finalize \
  --session-file "${SESSION_FILE}"
```

This writes `session-log.json` (structured) and
`session-transcript.md` (human-readable) to the output directory.
The transcript includes all step timings, reasoning, and AI agent
dispatch details with prompt/output previews.

## Cleanup

```bash
rm -rf "$WORKDIR"
```
