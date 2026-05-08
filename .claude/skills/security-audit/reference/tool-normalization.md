# Tool Output Normalization

Maps each tool's output to the common finding schema.

## Semgrep
File: `semgrep.json`, Format: JSON
Fields: `results[].check_id` -> rule_id, `path` -> file, `start.line` -> line_start, `extra.severity` -> severity, `extra.message` -> description

## Trivy
File: `trivy.json`, Format: JSON
Fields: `Results[].Vulnerabilities[].VulnerabilityID` -> rule_id, `Severity` -> severity, `PkgName` -> title prefix

## Grype
File: `grype.json`, Format: JSON
Fields: `matches[].vulnerability.id` -> rule_id, `severity` -> severity, `artifact.name` -> title prefix

## Gitleaks
File: `gitleaks.json`, Format: JSON array
Fields: `File` -> file, `StartLine` -> line_start, `Description` -> title, `RuleID` -> rule_id. Severity always "high".

## Kube-linter
File: `kube-linter.json`, Format: JSON
Fields: `Reports[].Check` -> rule_id, `Diagnostic.Message` -> description. Severity always "medium".

## SARIF tools (hadolint, zizmor)
Files: `hadolint.sarif`, `zizmor.sarif`
Fields: `runs[0].results[].ruleId` -> rule_id, `level` -> severity, `message.text` -> description

## ShellCheck
File: `shellcheck.json`, Format: JSON array
Fields: `code` -> rule_id (prefix SC), `level` -> severity, `message` -> description

## Gosec
File: `gosec.json`, Format: JSON
Fields: `Issues[].rule_id` -> rule_id, `severity` -> severity, `details` -> description
