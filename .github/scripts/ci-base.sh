#!/usr/bin/env bash
set -euo pipefail

if git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null; then
  printf '%s\n' "$BASE_SHA"
elif [[ "$REF_NAME" != "$DEFAULT_BRANCH" ]]; then
  git merge-base "origin/$DEFAULT_BRANCH" HEAD || true
fi
