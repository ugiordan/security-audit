# Confidence Scoring

Every finding carries a confidence score between 0.0 and 1.0 that indicates how likely it is to be a real, exploitable issue. Confidence scores are computed differently depending on the finding's origin (SAST vs. AI) and triage status (corroborated vs. standalone).

## Confidence levels

| Level | Score range | Meaning | Visual |
|---|---|---|---|
| **HIGH** | 0.80 - 1.00 | Code-verified. The finding has strong evidence: exact code pattern match, verified credential, or corroboration between SAST and AI. | Green badge |
| **MEDIUM** | 0.60 - 0.79 | Plausible. The finding matches known vulnerability patterns but lacks full verification. May need manual review. | Yellow badge |
| **LOW** | < 0.60 | Speculative. The finding is based on heuristics or limited context. Higher chance of false positive. | Red badge |

## How confidence is computed

### SAST tool findings

Base confidence comes from the tool itself:

- **semgrep**: Uses rule confidence metadata. Custom rules with `confidence: HIGH` get 0.9, `MEDIUM` gets 0.7, `LOW` gets 0.5.
- **gitleaks / trufflehog**: Secret detection tools default to 0.85 (high precision).
- **trivy / grype / osv-scanner**: CVE findings default to 0.8 (sourced from advisory databases).
- **kube-linter / hadolint / shellcheck**: Lint findings default to 0.7 (pattern-based).
- **actionlint / zizmor**: CI/CD findings default to 0.75.
- **yamllint**: Config lint findings default to 0.6.

### AI skill findings

AI agents include confidence in their output:

- **adversarial-reviewing**: Each finding has `Confidence: High|Medium|Low`, mapped to 0.9, 0.7, 0.5 respectively. Three rounds of self-refinement and a challenge round filter out low-confidence findings.
- **semantic-scan**: Each finding has `**Confidence:** 0.XX` as a numeric value.

### Triage adjustments

After cross-correlation, confidence is adjusted:

```python
if status == "corroborated":
    confidence = min(base + 0.15, 1.0)
elif status == "ai-only":
    confidence = base  # unchanged
elif status == "sast-only":
    confidence = base  # unchanged
elif demoted:
    confidence = max(base - 0.20, 0.3)
```

!!! info "Corroboration is the strongest signal"
    When both a SAST tool and an AI agent independently identify the same issue in the same file, the finding gets a +0.15 confidence boost. This is the most reliable signal the pipeline produces: two fundamentally different analysis approaches agreeing on a vulnerability.

## Examples

| Finding | Base | Triage | Final | Level |
|---|---|---|---|---|
| Semgrep SQL injection + SEC agent confirmed | 0.85 | Corroborated (+0.15) | 1.00 | HIGH |
| AI-only: missing rate limiting | 0.70 | AI-only | 0.70 | MEDIUM |
| Trivy CVE in dependency | 0.80 | SAST-only | 0.80 | HIGH |
| Gitleaks secret in test/ dir | 0.85 | Demoted (-0.20) | 0.65 | MEDIUM |
| yamllint duplicate key in examples/ | 0.60 | Demoted (-0.20) | 0.40 | LOW |

## Display in reports

### HTML reports

Confidence appears as a colored badge in the card footer:

```html
<span class="confidence-badge high">0.95</span>
<span class="confidence-badge medium">0.72</span>
<span class="confidence-badge low">0.45</span>
```

### Markdown reports

Confidence is shown inline:

```
**Confidence:** 0.95 (HIGH)
```

### Word documents

Confidence is included in the finding detail table with color formatting matching the HTML badges.

## Filtering by confidence

In the HTML reports, you can mentally prioritize by looking at the badge color. The reports sort findings by severity first, then by confidence descending, so the most reliable findings appear first within each severity group.

The must-fix reports (`must-fix-report.html`, `must-fix-report.md`, `must-fix-report.docx`) already filter to critical and high severity, which tend to be the highest-confidence findings.
