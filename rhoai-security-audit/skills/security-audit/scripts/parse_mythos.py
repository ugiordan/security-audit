#!/usr/bin/env python3
"""Parse Mythos security audit markdown reports into normalized finding schema.

Reads Mythos-format markdown files (FIND-NNN blocks with CVSS, ASVS, files,
exploit scenarios, remediation) and outputs our normalized JSON schema so
report generators can produce HTML/DOCX/MkDocs reports.

Usage:
    python3 parse_mythos.py <mythos-dir> -o <output-dir>
    python3 parse_mythos.py <mythos-dir> --reports  # generate all report formats
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
    "info": "info",
}


def parse_executive_summary(text):
    """Extract metadata from the executive summary table."""
    meta = {}
    table_match = re.search(
        r'\| Field \| Value \|\n\|.*\|\n((?:\|.*\|\n)+)', text
    )
    if table_match:
        for row in table_match.group(1).strip().split("\n"):
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if len(cells) == 2:
                key = cells[0].lower().replace(" ", "_")
                meta[key] = cells[1]

    repo_match = re.search(r'Repository.*?(https://github\.com/[\w\-/]+)', text)
    if repo_match:
        url = repo_match.group(1)
        meta["repo"] = "/".join(url.rstrip("/").split("/")[-2:])

    date_match = re.search(r'Date.*?(\d{4}-\d{2}-\d{2})', text)
    if date_match:
        meta["date"] = date_match.group(1)

    commit_match = re.search(r'`(\w{8,40})`', meta.get("audited_ref", ""))
    if commit_match:
        meta["commit"] = commit_match.group(1)

    return meta


def parse_finding(fid, body, component, repo):
    """Parse a single FIND-NNN block into normalized schema."""
    f = {
        "id": f"{component.upper()[:4]}-{fid}",
        "mythos_id": fid,
        "source": "mythos",
        "origin": "mythos",
        "category": "ai-review",
        "detected_by": ["mythos"],
    }

    # Title (first line: "— Title text")
    title_match = re.match(r'\s*—\s*(.+?)(?:\n|$)', body)
    f["title"] = title_match.group(1).strip() if title_match else fid

    # CVSS score (multiple formats)
    cvss_patterns = [
        # Format 1: **CVSS v3.1**: **9.6** (AV:N/...) — **Critical**
        r'\*\*CVSS.*?(\d+\.\d+)\*?\*?\s*\(([^)]+)\).*?—\s*\*\*(\w+)\*\*',
        # Format 2: table row: | **CVSS v3.1** | 7.3 — `AV:N/...` |
        r'CVSS.*?\|\s*(\d+\.\d+)\s*[-—]\s*`([^`]+)`',
        # Format 3: table row: | **CVSS v3.1** | 8.8 (High) `AV:N/...` |
        r'CVSS.*?\|\s*(\d+\.\d+)\s*\(\w+\)\s*`([^`]+)`',
        # Format 4: bullet: - **CVSS v3.1:** 7.6 `AV:N/...`
        r'\*\*CVSS.*?:\*\*\s*(\d+\.\d+)\s*`([^`]+)`',
    ]
    cvss_found = False
    for pattern in cvss_patterns:
        cvss_match = re.search(pattern, body)
        if cvss_match:
            f["cvss_score"] = float(cvss_match.group(1))
            f["cvss_vector"] = cvss_match.group(2)
            cvss_found = True
            break

    # Severity (multiple formats)
    sev_patterns = [
        # Format 1: — **Critical** (end of CVSS line or table cell)
        r'—\s*\*\*(\w+)\*\*',
        # Format 2: table row: | **Severity** | **High** |
        r'\*\*Severity\*\*\s*\|\s*\*\*(\w+)\*\*',
        # Format 3: inline: **Severity: High** or **Severity:** High
        r'\*\*Severity[:\s]+(\w+)\*\*',
        r'\*\*Severity:\*\*\s*(\w+)',
        # Format 4: CVSS line ending with severity word in bold
        r'CVSS.*\*\*(\w+)\*\*\s*\|?\s*$',
        # Format 5: CVSS score followed by (High) in parens
        r'CVSS.*?\d+\.\d+\s*\((\w+)\)',
        # Format 6: — inherited / N/A patterns
        r'CVSS.*?—\s*(\w+)',
    ]
    sev_found = False
    for pattern in sev_patterns:
        sev_match = re.search(pattern, body, re.MULTILINE)
        if sev_match:
            f["severity"] = SEVERITY_MAP.get(sev_match.group(1).lower(), "medium")
            sev_found = True
            break
    if not sev_found:
        f["severity"] = "medium"

    # Files (from bullet list or table rows)
    file_refs = re.findall(r'`([^`]+\.\w+(?::\d+[-–]\d+)?)`', body)
    source_files = [fr for fr in file_refs
                    if ("/" in fr or fr.endswith((".go", ".py", ".sh", ".yaml", ".yml", ".json", ".js", ".ts")))
                    and not fr.startswith("http")
                    and not fr.startswith("$")
                    and "==" not in fr]
    f["file"] = source_files[0].split(":")[0] if source_files else ""
    f["files"] = source_files

    # Line numbers from first file
    line_match = re.search(r':(\d+)[-–](\d+)', source_files[0]) if source_files else None
    f["line_start"] = int(line_match.group(1)) if line_match else 0
    f["line_end"] = int(line_match.group(2)) if line_match else 0

    # Frameworks
    frameworks = re.findall(
        r'(ASVS\s+V[\d.]+(?:\.\d+)?|CWE-\d+|K\d{2}|CIS\s+[\d.]+)', body
    )
    f["frameworks"] = frameworks
    f["rule_id"] = fid

    # Description
    desc_match = re.search(
        r'\*\*Description\*\*\n\n(.+?)(?=\n\*\*(?:Exploit|Remediation|Impact)|---|\Z)',
        body, re.DOTALL
    )
    f["description"] = desc_match.group(1).strip()[:2000] if desc_match else ""

    # Exploit scenario
    exploit_match = re.search(
        r'\*\*Exploit scenario\*\*\n\n(.+?)(?=\n\*\*Remediation|---|\Z)',
        body, re.DOTALL
    )
    f["exploit"] = exploit_match.group(1).strip()[:1500] if exploit_match else ""

    # Remediation
    remed_match = re.search(
        r'\*\*Remediation\*\*\n\n(.+?)(?=\n---|\n### FIND-|\Z)',
        body, re.DOTALL
    )
    f["recommendation"] = remed_match.group(1).strip()[:1500] if remed_match else ""

    # Code snippet (first code block in description or exploit)
    snippet_match = re.search(r'```\w*\n(.+?)```', body, re.DOTALL)
    f["snippet"] = snippet_match.group(1).strip()[:800] if snippet_match else ""

    # Confidence (Mythos findings are manual audit quality)
    f["confidence"] = 0.95
    f["triage"] = {"status": "mythos-audit"}

    return f


def parse_report(filepath):
    """Parse a single Mythos markdown report into findings list + metadata."""
    text = Path(filepath).read_text()
    component = Path(filepath).parent.name

    meta = parse_executive_summary(text)
    meta["component"] = component

    # Split on FIND-NNN headings
    parts = re.split(r'\n### (FIND-\d+)', text)
    findings = []
    for i in range(1, len(parts), 2):
        fid = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        f = parse_finding(fid, body, component, meta.get("repo", ""))
        f["component"] = component
        findings.append(f)

    return findings, meta


def parse_mythos_dir(mythos_dir):
    """Parse all Mythos reports in a directory tree."""
    base = Path(mythos_dir)
    all_findings = []
    all_meta = []

    for md in sorted(base.rglob("*-security-audit.md")):
        findings, meta = parse_report(md)
        all_findings.extend(findings)
        all_meta.append(meta)

    # Deduplicate IDs (prefix with component)
    seen = set()
    for f in all_findings:
        while f["id"] in seen:
            num = int(re.search(r'\d+$', f["id"]).group())
            prefix = re.sub(r'\d+$', '', f["id"])
            f["id"] = f"{prefix}{num + 1}"
        seen.add(f["id"])

    return all_findings, all_meta


def generate_scan_metadata(all_meta):
    """Generate scan-metadata.json from parsed metadata."""
    repos = [m.get("repo", "") for m in all_meta if m.get("repo")]
    dates = [m.get("date", "") for m in all_meta if m.get("date")]
    return {
        "repo": repos[0] if len(set(repos)) == 1 else "multi-repo",
        "date": max(dates) if dates else "",
        "branch": "main",
        "commit": "",
        "source": "mythos",
        "components": [m.get("component", "") for m in all_meta],
    }


def main():
    parser = argparse.ArgumentParser(description="Parse Mythos security audit reports")
    parser.add_argument("mythos_dir", help="Directory containing Mythos markdown reports")
    parser.add_argument("-o", "--output", default=None, help="Output directory")
    parser.add_argument("--reports", action="store_true", help="Generate all report formats")
    parser.add_argument("--json", action="store_true", help="Output normalized JSON only")
    args = parser.parse_args()

    findings, meta_list = parse_mythos_dir(args.mythos_dir)

    if not findings:
        print("No findings found.", file=sys.stderr)
        sys.exit(1)

    sev_counts = Counter(f["severity"] for f in findings)
    print(f"Parsed {len(findings)} findings from {len(meta_list)} reports")
    print(f"Severity: {dict(sev_counts)}")

    output_dir = Path(args.output) if args.output else Path(args.mythos_dir) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write normalized findings
    findings_path = output_dir / "triaged-findings.json"
    findings_path.write_text(json.dumps(findings, indent=2))
    print(f"Findings: {findings_path}")

    # Write scan metadata
    scan_meta = generate_scan_metadata(meta_list)
    meta_path = output_dir / "scan-metadata.json"
    meta_path.write_text(json.dumps(scan_meta, indent=2))

    if args.json:
        return

    if args.reports:
        scripts_dir = Path(__file__).parent
        import subprocess

        report_cmds = [
            (["python3", str(scripts_dir / "report.py"), str(output_dir)],
             "executive-report.md"),
            (["python3", str(scripts_dir / "report_mustfix.py"), str(output_dir)],
             "must-fix-report.md"),
            (["python3", str(scripts_dir / "report_standalone.py"), str(output_dir)],
             "security-report.html"),
            (["python3", str(scripts_dir / "report_mustfix.py"), str(output_dir), "--html"],
             "must-fix-report.html"),
            (["python3", str(scripts_dir / "report_html.py"), str(output_dir)],
             "MkDocs site"),
            (["python3", str(scripts_dir / "report_docx.py"), str(output_dir)],
             "security-report.docx"),
            (["python3", str(scripts_dir / "report_docx.py"), str(output_dir), "--must-fix"],
             "must-fix-report.docx"),
        ]

        for cmd, name in report_cmds:
            try:
                if name.endswith(".md") or name.endswith(".html"):
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0 and result.stdout:
                        out_path = output_dir / name
                        out_path.write_text(result.stdout)
                        print(f"  {name} OK")
                    else:
                        print(f"  {name} FAILED: {result.stderr[:100]}")
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        print(f"  {name} OK")
                    else:
                        print(f"  {name} FAILED: {result.stderr[:100]}")
            except Exception as e:
                print(f"  {name} ERROR: {e}")

    print(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
