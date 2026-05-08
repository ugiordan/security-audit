#!/usr/bin/env bash
# Host-side wrapper: runs SAST tools inside a container.
# Falls back to local tools if Docker/Podman is not available.
#
# Usage: scan_container.sh <org/repo> <branch> <results-dir>
set -euo pipefail

REPO="${1:?Usage: scan_container.sh <org/repo> <branch> <results-dir>}"
BRANCH="${2:-main}"
RESULTS_DIR="${3:?results-dir required}"
IMAGE="${SCANNER_IMAGE:-quay.io/ugiordan/security-audit-scanner:latest}"

RESULTS_DIR="$(mkdir -p "${RESULTS_DIR}" && cd "${RESULTS_DIR}" && pwd)"

# Detect container runtime
RUNTIME=""
if command -v docker &>/dev/null; then
  RUNTIME="docker"
elif command -v podman &>/dev/null; then
  RUNTIME="podman"
fi

if [ -n "${RUNTIME}" ]; then
  echo "Running SAST scan in container (${RUNTIME}, image: ${IMAGE})"
  ${RUNTIME} pull "${IMAGE}" 2>/dev/null || true
  ${RUNTIME} run --rm \
    -v "${RESULTS_DIR}:/results:z" \
    "${IMAGE}" \
    "${REPO}" "${BRANCH}" /results
  echo "Container scan complete. Results in ${RESULTS_DIR}"
else
  echo "WARNING: No container runtime (docker/podman) found."
  echo "Running with locally installed tools only. Some tools may be missing."
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  bash "${SCRIPT_DIR}/run_all.sh" "${REPO}" "${BRANCH}" "${RESULTS_DIR}"
fi
