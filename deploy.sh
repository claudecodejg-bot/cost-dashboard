#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"
PROJECT_NAME="${CLOUDFLARE_PROJECT_NAME:-}"
USE_MOCK_DATA="${USE_MOCK_DATA:-0}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if ! command -v wrangler >/dev/null 2>&1; then
  echo "wrangler is required. Install it with: npm install -g wrangler" >&2
  exit 1
fi

if [[ -z "$PROJECT_NAME" ]]; then
  echo "Set CLOUDFLARE_PROJECT_NAME before deploying." >&2
  echo "Example: CLOUDFLARE_PROJECT_NAME=weber-cost-dashboard ./deploy.sh" >&2
  exit 1
fi

mkdir -p "$DIST_DIR"

if [[ "$USE_MOCK_DATA" == "1" ]]; then
  python3 "$ROOT_DIR/generate-dashboard.py" --mock --output "$DIST_DIR/index.html"
else
  python3 "$ROOT_DIR/generate-dashboard.py" --output "$DIST_DIR/index.html"
fi

wrangler pages deploy "$DIST_DIR" --project-name "$PROJECT_NAME" --branch main

echo
echo "Public URL: https://${PROJECT_NAME}.pages.dev"

