# Architecture Context

The `--arch-context` flag provides architectural information to AI skills, significantly improving the quality and relevance of their findings. When agents know the system architecture, they can reason about trust boundaries, data flows, and component interactions instead of reviewing code in isolation.

## What it provides

Architecture context includes:

- **Component dependency graph**: Which components talk to each other
- **Trust boundary definitions**: Internal vs. external-facing components
- **API surface inventory**: Endpoints, authentication requirements, data types
- **Deployment topology**: How components are deployed (pods, services, operators)

## Usage

### Local path

If you have architecture-analyzer output on disk:

```bash
python3 pipeline.py org/repo --arch-context /tmp/arch-output
```

The path should point to a directory containing `component-architecture.json` and related files.

### GitHub repository

The pipeline can download architecture artifacts from a GitHub repository:

```bash
python3 pipeline.py org/repo --arch-context ugiordan/architecture-analyzer
```

This uses `gh run download` to fetch the latest artifact matching the target repository name. The lookup process:

1. Try exact match: `{prefix}-{org}-{repo}` (e.g., `odh-opendatahub-io-kube-auth-proxy`)
2. Try with `odh` and `rhoai` prefixes
3. Fallback: paginated search for any artifact ending in `-{repo-name}`
4. Prefer artifacts with `odh-` prefix when multiple matches exist

The downloaded artifact is stored at `<scan-dir>/raw/arch-context/`.

## How AI skills use it

### Adversarial-reviewing

Architecture context is passed as a `--context` argument:

```
--context architecture=/tmp/arch-output
```

Each specialist agent receives the architecture context alongside the repository code. This allows:

- **SEC agent**: Identifies trust boundaries that need authentication, external-facing APIs that need rate limiting
- **ARCH agent**: Validates that the code structure matches the intended architecture
- **CORR agent**: Checks that data flow assumptions in the architecture are correctly implemented

### Semantic-scan

The repo-analyst agent uses architecture context to build a more accurate inventory of the repository, which propagates to the security-scanner and post-scan agents.

## Impact on findings

Without architecture context, AI agents treat every component as equally important and can't distinguish between:

- Internal admin API vs. public-facing endpoint
- Test utility code vs. production operator logic
- Development convenience features vs. security-critical paths

With architecture context, false positives drop because agents understand:

- A hardcoded localhost URL in an internal health check is not a security finding
- Missing TLS on an internal-only gRPC connection behind a service mesh may be acceptable
- Privileged container access in an operator that manages node resources is expected

!!! info "Architecture context is optional"
    The pipeline runs fine without it. AI skills will still review the code, they just lack the broader system context. For repositories that are standalone tools or libraries, architecture context may not add much value. For operators and controllers that are part of a larger platform, it's highly recommended.

## Architecture-analyzer integration

The [architecture-analyzer](https://github.com/ugiordan/architecture-analyzer) is a separate tool that generates the context files. It analyzes a GitHub organization's repositories and produces:

```
component-architecture.json   # Dependency graph, API surfaces
deployment-topology.json       # K8s resources, operators, CRDs
trust-boundaries.json          # Internal/external classification
```

Run it against your organization, then point the security audit at the output:

```bash
# Generate architecture context (separate tool)
architecture-analyzer analyze opendatahub-io --output /tmp/arch-output

# Use it in a security audit
python3 pipeline.py opendatahub-io/kube-auth-proxy --arch-context /tmp/arch-output
```

Or set up a GitHub Actions workflow that publishes architecture artifacts and reference the repo:

```bash
python3 pipeline.py opendatahub-io/kube-auth-proxy --arch-context ugiordan/architecture-analyzer
```
