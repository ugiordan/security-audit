#!/usr/bin/env bash
# Host-side wrapper: runs SAST tools inside a container using scan-repo.sh
# with all the tuned configs from rhoai-security-scanner.
#
# Usage: scan_container.sh <org/repo> <branch> <results-dir>
set -euo pipefail

REPO="${1:?Usage: scan_container.sh <org/repo> <branch> <results-dir>}"
BRANCH="${2:-main}"
RESULTS_DIR="${3:?results-dir required}"
IMAGE="${SCANNER_IMAGE:-quay.io/ugiordan/security-audit-scanner:latest}"
REPO_SHORT="${REPO##*/}"

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

  # scan-repo.sh usage: scan-repo.sh <org/repo> <results-base-dir>
  # It clones the repo internally and writes to <results-base>/<repo-short>/
  #
  # We mount a temp dir as /results. scan-repo.sh writes to
  # /results/<repo-short>/. After the container exits, we move
  # the contents to RESULTS_DIR.
  MOUNT_DIR="$(mktemp -d)"

  ${RUNTIME} run --rm \
    -v "${MOUNT_DIR}:/results:z" \
    -w /scanner \
    "${IMAGE}" \
    "${REPO}" /results

  # Move results from <repo-short>/ subdir to RESULTS_DIR
  if [ -d "${MOUNT_DIR}/${REPO_SHORT}" ]; then
    cp -R "${MOUNT_DIR}/${REPO_SHORT}/"* "${RESULTS_DIR}/" 2>/dev/null || true
    rm -rf "${MOUNT_DIR}"
    echo "Container scan complete. Results in ${RESULTS_DIR}"
  else
    echo "WARNING: Expected ${MOUNT_DIR}/${REPO_SHORT}/ but not found"
    ls "${MOUNT_DIR}/" 2>/dev/null
    rm -rf "${MOUNT_DIR}"
  fi
else
  echo "WARNING: No container runtime (docker/podman) found."
  echo "Running with locally installed tools only. Some tools may be missing."
  echo "Install docker or podman for full 15-tool coverage."
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  bash "${SCRIPT_DIR}/run_all.sh" "${REPO}" "${BRANCH}" "${RESULTS_DIR}"
fi
