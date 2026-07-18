#!/bin/bash
# RK3 SessionStart hook — provisions a fresh Claude Code on the web container:
#   1. Python 3.12+ venv at .venv/ with requirements.txt installed
#   2. source PDFs synced from S3 (opt-in via env vars; see below)
#   3. app/ui node_modules
#   4. venv bin on PATH + project root on PYTHONPATH for the session
#
# Runs SYNCHRONOUSLY so deps are guaranteed present before the agent acts.
# Idempotent and non-interactive: safe to re-run; cached container state makes
# repeat runs fast.
#
# S3 PDF sync (set these in the environment's variable/secret settings, NOT here):
#   RK3_PDF_S3_URI          e.g. s3://my-bucket/rk3/sources/  (prefix mirroring
#                           the sources/<folder>/ layout; only *.pdf is pulled)
#   AWS_ACCESS_KEY_ID       AWS credentials with read access to that bucket
#   AWS_SECRET_ACCESS_KEY
#   AWS_DEFAULT_REGION      (optional) bucket region
# If RK3_PDF_S3_URI is unset the sync is skipped and everything else still runs.
set -euo pipefail

# Only provision the ephemeral web container; a local dev machine is set up by hand.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT"

log() { echo "[session-start] $*" >&2; }

# --- 1. Python venv (needs 3.12+ for PEP 701 f-strings in rk3/eval.py) ------
PYBIN=""
for cand in python3.12 python3.13 python3.14; do
  if command -v "$cand" >/dev/null 2>&1; then PYBIN="$cand"; break; fi
done
if [ -z "$PYBIN" ]; then
  log "ERROR: no python3.12+ found; RK3 requires Python 3.12 or newer."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  log "creating venv with $PYBIN"
  "$PYBIN" -m venv .venv
fi
log "installing Python requirements"
.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

# --- 2. Source PDFs from S3 (opt-in) ---------------------------------------
if [ -n "${RK3_PDF_S3_URI:-}" ]; then
  if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    log "WARN: RK3_PDF_S3_URI set but AWS credentials missing; skipping PDF sync."
  else
    if [ ! -x ".venv/bin/aws" ]; then
      log "installing awscli into venv"
      .venv/bin/pip install "awscli>=1.32,<2" -q
    fi
    log "syncing PDFs from $RK3_PDF_S3_URI -> sources/"
    # additive (no --delete): never touch the committed .config/.ops/.landing
    # sidecars; only pull *.pdf that aren't already present.
    .venv/bin/aws s3 sync "$RK3_PDF_S3_URI" sources/ \
      --exclude "*" --include "*.pdf" --no-progress
    # the bucket is flat, but the pipeline needs sources/<folder>/<name>.pdf
    # (slug = <folder>--<name>). Move each synced PDF into the folder whose
    # committed sidecars already claim its stem.
    .venv/bin/python -m tools.place_sources --apply
  fi
else
  log "RK3_PDF_S3_URI unset; skipping PDF sync (conversion/tests need PDFs)."
fi

# --- 3. Web UI dependencies -------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  log "installing app/ui node modules"
  ( cd app/ui && npm install --no-audit --no-fund --silent )
else
  log "WARN: npm not found; skipping UI dependency install."
fi

# --- 4. Session environment -------------------------------------------------
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$ROOT/.venv/bin:\$PATH\""
    echo "export PYTHONPATH=\"$ROOT\""
  } >> "$CLAUDE_ENV_FILE"
fi

log "provisioning complete"
