#!/usr/bin/env python3
"""Render Mythos security audit markdown reports as a single tabbed HTML file.

Preserves original findings content (CVSS, ASVS, exploit scenarios, remediation
code blocks). Adds: tabbed navigation per component, severity summary dashboard,
dark theme, search, collapsible sections.

Usage:
    python3 render_mythos.py <mythos-dir> -o report.html
    python3 render_mythos.py <mythos-dir>  # outputs to <mythos-dir>/mythos-report.html
"""
import argparse
import re
import sys
from html import escape
from pathlib import Path


SEV_COLORS = {
    "critical": "#dc3545",
    "high": "#fd7e14",
    "medium": "#ffc107",
    "low": "#17a2b8",
    "informational": "#6c757d",
    "info": "#6c757d",
}

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4, "info": 5}


def parse_severity_counts(text):
    """Extract severity counts from executive summary."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for sev in counts:
        label = "Informational" if sev == "info" else sev.title()
        m = re.search(rf'(\d+)\s+{label}', text[:3000], re.IGNORECASE)
        if m:
            counts[sev] = int(m.group(1))
    # Also try table format: | **Critical** | 1 |
    for row in re.findall(r'\|\s*\*\*(\w+)\*\*\s*\|\s*(\d+)\s*\|', text[:3000]):
        sev = row[0].lower()
        if sev == "informational":
            sev = "info"
        if sev in counts:
            counts[sev] = int(row[1])
    return counts


def md_to_html(md_text):
    """Convert markdown to HTML, preserving code blocks and tables."""
    lines = md_text.split("\n")
    html_parts = []
    in_code = False
    code_lang = ""
    code_lines = []
    in_table = False
    table_lines = []

    for line in lines:
        # Code blocks
        if line.startswith("```"):
            if in_code:
                code = escape("\n".join(code_lines))
                html_parts.append(
                    f'<pre class="code-block"><code class="{code_lang}">{code}</code></pre>'
                )
                code_lines = []
                in_code = False
            else:
                if in_table:
                    html_parts.append(render_table(table_lines))
                    table_lines = []
                    in_table = False
                code_lang = line[3:].strip()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        # Tables
        if line.strip().startswith("|") and "|" in line[1:]:
            if not in_table:
                in_table = True
            table_lines.append(line)
            continue
        elif in_table:
            html_parts.append(render_table(table_lines))
            table_lines = []
            in_table = False

        # Skip horizontal rules
        if line.strip() == "---":
            continue

        # Headings (only h4+ inside findings, h1-h3 handled by structure)
        if line.startswith("####"):
            text = format_inline(line.lstrip("#").strip())
            html_parts.append(f"<h4>{text}</h4>")
            continue

        # Bold section headers: **Description**, **Exploit scenario**, etc.
        if re.match(r'^\*\*\w', line) and line.strip().endswith("**"):
            text = line.strip().strip("*")
            html_parts.append(f'<h4 class="section-header">{escape(text)}</h4>')
            continue
        if re.match(r'^\*\*\w.*\*\*$', line.strip()):
            text = line.strip().strip("*").rstrip(".")
            html_parts.append(f'<h4 class="section-header">{escape(text)}</h4>')
            continue

        # Bullet lists
        if re.match(r'^[-*]\s', line.strip()):
            text = format_inline(line.strip().lstrip("-* "))
            html_parts.append(f"<li>{text}</li>")
            continue
        if re.match(r'^\d+\.\s', line.strip()):
            text = format_inline(re.sub(r'^\d+\.\s*', '', line.strip()))
            html_parts.append(f"<li>{text}</li>")
            continue

        # Empty lines
        if not line.strip():
            html_parts.append("")
            continue

        # Regular paragraphs
        html_parts.append(f"<p>{format_inline(line)}</p>")

    if in_table:
        html_parts.append(render_table(table_lines))
    if in_code:
        code = escape("\n".join(code_lines))
        html_parts.append(f'<pre class="code-block"><code>{code}</code></pre>')

    return "\n".join(html_parts)


def render_table(lines):
    """Render markdown table as HTML."""
    if len(lines) < 2:
        return ""
    rows = []
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells:
            continue
        if i == 1 and all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        tag = "th" if i == 0 else "td"
        row = "".join(f"<{tag}>{format_inline(c)}</{tag}>" for c in cells)
        rows.append(f"<tr>{row}</tr>")
    if not rows:
        return ""
    return f'<table class="finding-table">{"".join(rows)}</table>'


def format_inline(text):
    """Format inline markdown: bold, italic, code, links."""
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def parse_component(filepath):
    """Parse a single Mythos report into structured data."""
    text = Path(filepath).read_text()
    component = Path(filepath).parent.name

    # Executive summary (everything before first FIND)
    first_find = re.search(r'\n### FIND-', text)
    exec_summary = text[:first_find.start()] if first_find else text[:2000]

    # Severity counts
    sev_counts = parse_severity_counts(text)
    total = sum(sev_counts.values())

    # Extract repo info
    repo_match = re.search(r'Repository.*?(https://github\.com/[\w\-/]+)', text)
    repo = repo_match.group(1) if repo_match else ""

    # Split into findings
    parts = re.split(r'\n### (FIND-\d+)', text)
    findings = []
    for i in range(1, len(parts), 2):
        fid = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""

        title_match = re.match(r'\s*—\s*(.+?)(?:\n|$)', body)
        title = title_match.group(1).strip() if title_match else fid

        # Severity from multiple formats
        severity = "medium"
        for pattern in [
            r'—\s*\*\*(\w+)\*\*',
            r'\*\*Severity\*\*\s*\|\s*\*\*(\w+)\*\*',
            r'\*\*Severity:\*\*\s*(\w+)',
            r'CVSS.*?\d+\.\d+\s*\((\w+)\)',
        ]:
            m = re.search(pattern, body, re.MULTILINE)
            if m:
                s = m.group(1).lower()
                if s in SEV_COLORS:
                    severity = s
                    break

        # CVSS
        cvss_match = re.search(r'(\d+\.\d+)', body[:500])
        cvss = cvss_match.group(1) if cvss_match else ""

        # Render body as HTML (skip the title line)
        body_without_title = re.sub(r'^[^\n]*\n', '', body, count=1)
        body_html = md_to_html(body_without_title)

        findings.append({
            "id": fid,
            "title": title,
            "severity": severity,
            "cvss": cvss,
            "html": body_html,
        })

    return {
        "name": component,
        "repo": repo,
        "sev_counts": sev_counts,
        "total": total,
        "findings": findings,
        "exec_summary_html": md_to_html(exec_summary),
    }


def generate_report(mythos_dir, output_path):
    """Generate single tabbed HTML report from all Mythos reports."""
    base = Path(mythos_dir)
    reports = sorted(base.rglob("*-security-audit.md"))

    if not reports:
        print("No Mythos reports found.", file=sys.stderr)
        sys.exit(1)

    # Parse all components
    components = []
    for rpath in reports:
        comp = parse_component(rpath)
        components.append(comp)

    # Sort: components with findings first (by severity), then empty ones
    components.sort(key=lambda c: (
        -c["sev_counts"]["critical"],
        -c["sev_counts"]["high"],
        -c["sev_counts"]["medium"],
        -c["total"],
    ))

    # Global summary
    total_findings = sum(c["total"] for c in components)
    total_critical = sum(c["sev_counts"]["critical"] for c in components)
    total_high = sum(c["sev_counts"]["high"] for c in components)
    total_medium = sum(c["sev_counts"]["medium"] for c in components)
    total_low = sum(c["sev_counts"]["low"] for c in components)
    total_info = sum(c["sev_counts"]["info"] for c in components)
    comps_with_findings = sum(1 for c in components if c["total"] > 0)

    # Read README if present
    readme_path = base / "README.md"
    readme_html = ""
    if readme_path.exists():
        readme_html = md_to_html(readme_path.read_text())

    # Build tab buttons
    tab_buttons = ['<button class="tab-btn active" onclick="showTab(\'overview\')">Overview</button>']
    for c in components:
        if c["total"] == 0:
            continue
        sev_badge = ""
        if c["sev_counts"]["critical"] > 0:
            sev_badge = f'<span class="tab-badge crit">{c["sev_counts"]["critical"]}C</span>'
        elif c["sev_counts"]["high"] > 0:
            sev_badge = f'<span class="tab-badge high">{c["sev_counts"]["high"]}H</span>'
        tab_buttons.append(
            f'<button class="tab-btn" onclick="showTab(\'{c["name"]}\')">'
            f'{escape(c["name"])} {sev_badge}</button>'
        )

    # Build tab content
    tab_contents = []

    # Overview tab
    overview = f'''<div id="tab-overview" class="tab-content active">
    <div class="banner">CONFIDENTIAL — This report may contain undisclosed security findings. Do not share outside authorized personnel.</div>
    <h1>RHOAI Security Audit</h1>
    <div class="stat-row">
        <div class="stat-card" style="border-left:3px solid {SEV_COLORS["critical"]}"><div class="stat-count" style="color:{SEV_COLORS["critical"]}">{total_critical}</div><div class="stat-label">Critical</div></div>
        <div class="stat-card" style="border-left:3px solid {SEV_COLORS["high"]}"><div class="stat-count" style="color:{SEV_COLORS["high"]}">{total_high}</div><div class="stat-label">High</div></div>
        <div class="stat-card" style="border-left:3px solid {SEV_COLORS["medium"]}"><div class="stat-count" style="color:{SEV_COLORS["medium"]}">{total_medium}</div><div class="stat-label">Medium</div></div>
        <div class="stat-card" style="border-left:3px solid {SEV_COLORS["low"]}"><div class="stat-count" style="color:{SEV_COLORS["low"]}">{total_low}</div><div class="stat-label">Low</div></div>
        <div class="stat-card" style="border-left:3px solid {SEV_COLORS["info"]}"><div class="stat-count" style="color:{SEV_COLORS["info"]}">{total_info}</div><div class="stat-label">Info</div></div>
        <div class="stat-card"><div class="stat-count">{total_findings}</div><div class="stat-label">Total</div></div>
    </div>
    <p class="meta">{comps_with_findings} components with findings out of {len(components)} scanned</p>
    {readme_html}
</div>'''
    tab_contents.append(overview)

    # Component tabs
    for c in components:
        if c["total"] == 0:
            continue

        findings_html = ""
        for f in c["findings"]:
            sev = f["severity"]
            color = SEV_COLORS.get(sev, "#6c757d")
            cvss_badge = f'<span class="cvss-badge">CVSS {f["cvss"]}</span>' if f["cvss"] else ""
            sev_chip = f'<span class="chip" style="background:{color}">{sev.upper()}</span>'

            findings_html += f'''<div class="finding-card" style="border-left-color:{color}">
    <div class="finding-header" onclick="this.parentElement.classList.toggle('expanded')">
        {sev_chip} {cvss_badge}
        <span class="finding-id">{f["id"]}</span>
        <span class="finding-title">{escape(f["title"][:120])}</span>
        <span class="expand-icon">&#9660;</span>
    </div>
    <div class="finding-body">{f["html"]}</div>
</div>\n'''

        sev_summary = " · ".join(
            f'<span style="color:{SEV_COLORS.get(s, "#ccc")}">{c["sev_counts"][s]} {s.title()}</span>'
            for s in ["critical", "high", "medium", "low", "info"]
            if c["sev_counts"][s] > 0
        )

        tab_contents.append(f'''<div id="tab-{c["name"]}" class="tab-content">
    <h2>{escape(c["name"])}</h2>
    <p class="meta">{sev_summary} · {c["total"]} findings</p>
    {c["exec_summary_html"]}
    <h3>Findings</h3>
    {findings_html}
</div>''')

    # Assemble HTML
    html = f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RHOAI Security Audit - Mythos</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font:14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0d1117; color:#c9d1d9; }}
a {{ color:#58a6ff; text-decoration:none; }}
h1 {{ font-size:22px; color:#f0f6fc; margin:16px 0 8px; }}
h2 {{ font-size:18px; color:#f0f6fc; margin:16px 0 8px; }}
h3 {{ font-size:15px; color:#f0f6fc; margin:16px 0 8px; border-bottom:1px solid #21262d; padding-bottom:6px; }}
h4 {{ font-size:13px; color:#e6edf3; margin:10px 0 4px; }}
.section-header {{ color:#8b949e; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; margin:14px 0 6px; }}
p {{ margin:4px 0; }}
li {{ margin:2px 0 2px 20px; }}
code {{ background:#161b22; padding:1px 5px; border-radius:3px; font-size:12px; color:#e6edf3; }}
.code-block {{ background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:10px 12px; font-size:12px; overflow-x:auto; margin:8px 0; color:#e6edf3; white-space:pre; }}
.banner {{ background:#dc354520; border:1px solid #dc3545; border-radius:6px; padding:8px 14px; margin:16px 24px; font-size:12px; color:#f0f6fc; text-align:center; }}
.banner strong {{ color:#dc3545; }}
.meta {{ color:#8b949e; font-size:12px; margin:4px 0 12px; }}

/* Tabs */
.tab-bar {{ display:flex; flex-wrap:wrap; gap:2px; padding:8px 16px; background:#161b22; border-bottom:1px solid #21262d; position:sticky; top:0; z-index:10; overflow-x:auto; }}
.tab-btn {{ background:none; border:none; color:#8b949e; padding:6px 12px; font-size:12px; cursor:pointer; border-radius:4px 4px 0 0; white-space:nowrap; }}
.tab-btn:hover {{ background:#21262d; color:#c9d1d9; }}
.tab-btn.active {{ background:#0d1117; color:#f0f6fc; border-bottom:2px solid #58a6ff; }}
.tab-badge {{ font-size:9px; padding:1px 4px; border-radius:6px; color:#fff; margin-left:3px; }}
.tab-badge.crit {{ background:#dc3545; }}
.tab-badge.high {{ background:#fd7e14; }}
.tab-content {{ display:none; padding:16px 24px; max-width:1100px; margin:0 auto; }}
.tab-content.active {{ display:block; }}

/* Stats */
.stat-row {{ display:flex; gap:10px; margin:12px 0; flex-wrap:wrap; }}
.stat-card {{ background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px 16px; text-align:center; }}
.stat-count {{ font-size:24px; font-weight:700; }}
.stat-label {{ font-size:10px; text-transform:uppercase; color:#8b949e; }}

/* Findings */
.finding-card {{ background:#161b22; border:1px solid #30363d; border-left:3px solid #6c757d; border-radius:6px; margin:6px 0; overflow:hidden; }}
.finding-header {{ display:flex; align-items:center; gap:6px; padding:10px 14px; cursor:pointer; flex-wrap:wrap; }}
.finding-header:hover {{ background:#1c2128; }}
.finding-id {{ color:#8b949e; font-size:11px; font-weight:600; }}
.finding-title {{ color:#f0f6fc; font-size:13px; flex:1; }}
.expand-icon {{ color:#8b949e; font-size:10px; transition:transform 0.2s; }}
.finding-card.expanded .expand-icon {{ transform:rotate(180deg); }}
.finding-body {{ display:none; padding:0 14px 14px; font-size:12px; border-top:1px solid #21262d; }}
.finding-card.expanded .finding-body {{ display:block; }}
.chip {{ display:inline-block; padding:1px 7px; border-radius:10px; font-size:10px; font-weight:600; color:#fff; }}
.cvss-badge {{ font-size:10px; color:#8b949e; background:#21262d; padding:1px 6px; border-radius:4px; }}

/* Tables */
.finding-table {{ width:100%; border-collapse:collapse; font-size:12px; margin:8px 0; }}
.finding-table th {{ background:#0d1117; padding:5px 8px; text-align:left; border-bottom:1px solid #30363d; color:#8b949e; font-weight:600; font-size:10px; }}
.finding-table td {{ padding:4px 8px; border-bottom:1px solid #161b22; }}
.finding-table tr:hover {{ background:#1c2128; }}
</style>
</head><body>

<div class="tab-bar">
{"".join(tab_buttons)}
</div>

{"".join(tab_contents)}

<script>
function showTab(name) {{
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.target.classList.add('active');
}}
</script>
</body></html>'''

    Path(output_path).write_text(html)
    print(f"Report: {output_path} ({len(html) // 1024}KB)")
    print(f"Components: {len(components)} ({comps_with_findings} with findings)")
    print(f"Findings: {total_findings}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mythos_dir")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    output = args.output or str(Path(args.mythos_dir) / "mythos-report.html")
    generate_report(args.mythos_dir, output)


if __name__ == "__main__":
    main()
