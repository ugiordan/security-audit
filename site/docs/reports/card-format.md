# Card Format

Every finding in the HTML reports is rendered as a card with consistent visual structure. Cards are designed for fast triage: severity is visible at a glance, key metadata is front-and-center, and details expand on demand.

## Card anatomy

```
┌─────────────────────────────────────────────────────┐
│ ▌ CRITICAL   CORR   semgrep                         │
│   SEM-003: Hardcoded JWT signing key                │
│   pkg/auth/token.go:87 ↗                            │
│                                                     │
│   Description                                       │
│   JWT signing key is hardcoded as a string constant  │
│   in the source code, allowing any attacker with    │
│   source access to forge valid tokens.              │
│                                                     │
│   Impact                                            │
│   Complete authentication bypass. Attacker can      │
│   create tokens for any user.                       │
│                                                     │
│   ┌─────────────────────────────────────────┐       │
│   │ var signingKey = "my-secret-key-123"    │       │
│   └─────────────────────────────────────────┘       │
│                                                     │
│   ▶ Remediation                                     │
│     Load signing key from environment variable or   │
│     secrets manager. Rotate the compromised key.    │
│                                                     │
│   Confidence: 0.95                                  │
└─────────────────────────────────────────────────────┘
```

## Visual elements

### Severity chip

A colored badge in the top-left corner of each card. The card's left border also uses the severity color.

| Severity | Color | Hex |
|---|---|---|
| Critical | Red | `#dc3545` |
| High | Orange | `#fd7e14` |
| Medium | Yellow | `#ffc107` |
| Low | Cyan | `#17a2b8` |
| Info | Gray | `#6c757d` |

### Triage badge

Appears next to the severity chip when the finding has a triage status:

| Badge | Color | Meaning |
|---|---|---|
| `CORR` | Green (`#16a34a`) | Corroborated: found by both SAST and AI |
| `AI` | Blue (`#2563eb`) | AI-only: found by AI agent, no SAST match |
| (none) | | SAST-only: standard tool finding |

Hovering over the badge shows a tooltip with the full description.

### Source chip

Shows which tool or AI skill produced the finding:

| Source | Color |
|---|---|
| adversarial-review | Blue (`#2563eb`) |
| semantic-scan | Purple (`#7c3aed`) |
| SAST tools | Default gray |

### GitHub file link

The file path and line number link directly to the file on GitHub:

```
https://github.com/<org>/<repo>/blob/<branch>/<file>#L<line>
```

If the commit SHA is available (from `commit-info.json`), the link uses the commit hash instead of the branch name for a permanent permalink.

## Card sections

### Description

The primary finding description from the tool or AI agent. Truncated to 500 characters in the card view for readability.

### Impact

When available (mainly from AI findings), describes the business or security impact of the vulnerability.

### Evidence / Code snippet

Syntax-highlighted code block showing the vulnerable code. Pulled from the tool's output or extracted by the AI agent.

### Remediation (collapsible)

Expandable section with fix recommendations. Collapsed by default to keep the card compact during initial triage.

### Confidence badge

Displayed as a colored badge in the card footer:

| Level | Range | Badge color |
|---|---|---|
| HIGH | 0.80+ | Green |
| MEDIUM | 0.60 - 0.79 | Yellow |
| LOW | < 0.60 | Red |

## Filtering

The HTML report header includes filter chips that toggle finding visibility:

- **By severity**: Click `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` to show/hide
- **By source**: Filter to specific tools or AI skills
- **By triage status**: Show only corroborated, AI-only, or SAST-only findings

Filters are applied client-side using JavaScript. Multiple filters can be combined (AND logic within a category, OR logic across categories).

## Category labels

Findings are grouped by category in some report views:

| Category key | Display label |
|---|---|
| `secrets` | Secrets |
| `sca` | CVEs / SCA |
| `k8s` | Kubernetes |
| `config` | Configuration |
| `cicd` | CI/CD |
| `injection` | Injection |
| `ai-review` | AI Review |
| `other` | SAST |
