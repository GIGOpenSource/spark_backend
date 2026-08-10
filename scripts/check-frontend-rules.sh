#!/usr/bin/env bash
# E-06: static checks for mobile_* frontend conventions
# - no CSS `gap:` in app vue/css (App compatibility; node_modules excluded)
# - no direct uni.request in pages/ (must go through utils/http)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MOBILE_DIRS=(
  "$ROOT/frontend/mobile_spark"
  "$ROOT/frontend/mobile_swipe"
  "$ROOT/frontend/mobile_matchup"
)

fail=0

echo "== check CSS gap: in mobile_* (pages/components/App) =="
for dir in "${MOBILE_DIRS[@]}"; do
  [ -d "$dir" ] || continue
  hits=""
  for sub in pages pagesA components App.vue uni.scss; do
    target="$dir/$sub"
    [ -e "$target" ] || continue
    part=$(rg -n --glob '*.{vue,css,scss,sass}' -e '(^|[^-])\bgap\s*:' "$target" 2>/dev/null || true)
    if [ -n "$part" ]; then
      hits="${hits}${part}"$'\n'
    fi
  done
  if [ -n "$(echo -n "$hits" | tr -d '[:space:]')" ]; then
    echo "FAIL gap found in $dir:"
    echo "$hits"
    fail=1
  else
    echo "OK $dir (no gap:)"
  fi
done

echo "== check uni.request in pages (not utils/http) =="
for dir in "${MOBILE_DIRS[@]}"; do
  [ -d "$dir" ] || continue
  hits=""
  for sub in pages pagesA; do
    target="$dir/$sub"
    [ -d "$target" ] || continue
    part=$(rg -n --glob '*.{vue,js}' -e '\buni\.request\s*\(' "$target" 2>/dev/null || true)
    if [ -n "$part" ]; then
      hits="${hits}${part}"$'\n'
    fi
  done
  if [ -n "$(echo -n "$hits" | tr -d '[:space:]')" ]; then
    echo "FAIL uni.request in pages of $dir:"
    echo "$hits"
    fail=1
  else
    echo "OK $dir pages (no uni.request)"
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "check-frontend-rules: FAILED (fix gaps / move requests into utils/http)"
  exit 1
fi
echo "check-frontend-rules: PASSED"
