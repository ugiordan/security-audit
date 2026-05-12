#!/usr/bin/env bash
# Run SAST scan with all tools + tuned configs from rhoai-security-scanner.
# Downloads missing tool binaries and scan-repo.sh on first run.
# No container, no system modification.
#
# Usage: scan_container.sh <org/repo> <branch> <results-dir>
set -euo pipefail

REPO="${1:?Usage: scan_container.sh <org/repo> <branch> <results-dir>}"
BRANCH="${2:-main}"
RESULTS_DIR="${3:?results-dir required}"
REPO_SHORT="${REPO##*/}"

RESULTS_DIR="$(mkdir -p "${RESULTS_DIR}" && cd "${RESULTS_DIR}" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install missing tools + clone scanner repo (cached between runs)
# Save and clear positional args so install_tools.sh doesn't inherit them
_SAVED_ARGS=("$@")
set --
source "${SCRIPT_DIR}/install_tools.sh"
set -- "${_SAVED_ARGS[@]}"

# Use scan-repo.sh from the scanner repo (has all tuned configs and exclusions)
SCAN_SCRIPT="${SCANNER_REPO_DIR}/scripts/scan-repo.sh"

if [ -f "${SCAN_SCRIPT}" ]; then
  MOUNT_DIR="$(mktemp -d)"
  bash "${SCAN_SCRIPT}" "${REPO}" "${MOUNT_DIR}"
  if [ -d "${MOUNT_DIR}/${REPO_SHORT}" ]; then
    cp -R "${MOUNT_DIR}/${REPO_SHORT}/"* "${RESULTS_DIR}/" 2>/dev/null || true
  fi
  rm -rf "${MOUNT_DIR}"
else
  echo "WARNING: scan-repo.sh not found. Running with default configs (no tuning)."
  bash "${SCRIPT_DIR}/run_all.sh" "${REPO}" "${BRANCH}" "${RESULTS_DIR}"
fi

echo "Scan complete. Results in ${RESULTS_DIR}"
