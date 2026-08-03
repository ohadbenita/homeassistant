#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-master}"
RELOAD_AFTER_SYNC="${RELOAD_AFTER_SYNC:-0}"
LOCK_FILE="${LOCK_FILE:-.ha_git_sync.lock}"
STATUS_FILE="${STATUS_FILE:-www/github_sync_status.json}"

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*"
}

write_status() {
  local status="$1"
  local message="$2"
  local commit="${3:-}"
  local now

  now="$(date -Iseconds)"
  mkdir -p "$(dirname "$STATUS_FILE")"

  if command -v python3 >/dev/null 2>&1; then
    STATUS="$status" \
      MESSAGE="$message" \
      COMMIT="$commit" \
      UPDATED_AT="$now" \
      python3 - <<'PY' > "$STATUS_FILE"
import json
import os

print(json.dumps({
    "status": os.environ["STATUS"],
    "message": os.environ["MESSAGE"],
    "commit": os.environ["COMMIT"],
    "updated_at": os.environ["UPDATED_AT"],
}))
PY
    return
  fi

  printf '{"status":"%s","message":"%s","commit":"%s","updated_at":"%s"}\n' \
    "$status" "$message" "$commit" "$now" > "$STATUS_FILE"
}

run_ha_config_check() {
  local checkout_dir="$1"

  if [[ -n "${HA_CHECK_CMD:-}" ]]; then
    (cd "$checkout_dir" && eval "$HA_CHECK_CMD")
    return
  fi

  if command -v hass >/dev/null 2>&1; then
    hass --script check_config -c "$checkout_dir"
    return
  fi

  log "No candidate-checkout Home Assistant config checker found."
  log "Set HA_CHECK_CMD to a command that validates the current directory before enabling sync."
  return 1
}

reload_home_assistant() {
  if [[ "$RELOAD_AFTER_SYNC" != "1" ]]; then
    return
  fi

  if [[ -n "${HA_RELOAD_CMD:-}" ]]; then
    eval "$HA_RELOAD_CMD"
    return
  fi

  if command -v ha >/dev/null 2>&1; then
    ha core restart
    return
  fi

  log "Synced successfully, but no reload command is configured."
}

main() {
  if [[ -e "$LOCK_FILE" ]]; then
    log "Sync already running or stale lock exists: $LOCK_FILE"
    write_status "failed" "Sync already running or stale lock exists." "$(git rev-parse --short HEAD)"
    exit 1
  fi

  trap 'rm -f "$LOCK_FILE"; [[ -n "${WORKTREE_DIR:-}" ]] && rm -rf "$WORKTREE_DIR"' EXIT
  trap 'write_status "failed" "Sync failed unexpectedly." "$(git rev-parse --short HEAD 2>/dev/null || true)"' ERR
  printf '%s\n' "$$" > "$LOCK_FILE"
  write_status "running" "Fetching $REMOTE/$BRANCH." "$(git rev-parse --short HEAD)"

  if ! git diff --quiet || ! git diff --cached --quiet; then
    log "Working tree has local changes. Refusing to sync."
    git status --short
    write_status "skipped_dirty_tree" \
      "Working tree has local changes. Refusing to sync." \
      "$(git rev-parse --short HEAD)"
    exit 1
  fi

  log "Fetching $REMOTE/$BRANCH"
  git fetch "$REMOTE" "$BRANCH"

  local target="$REMOTE/$BRANCH"
  local current
  local upstream
  current="$(git rev-parse HEAD)"
  upstream="$(git rev-parse "$target")"

  if [[ "$current" == "$upstream" ]]; then
    log "Already up to date at $current"
    write_status "success" "Already up to date." "$(git rev-parse --short HEAD)"
    exit 0
  fi

  if ! git merge-base --is-ancestor HEAD "$target"; then
    log "Remote is not a fast-forward from local HEAD. Refusing to sync."
    write_status "failed" \
      "Remote is not a fast-forward from local HEAD. Refusing to sync." \
      "$(git rev-parse --short HEAD)"
    exit 1
  fi

  WORKTREE_DIR="$(mktemp -d /tmp/ha-sync-check.XXXXXX)"
  log "Validating $upstream in temporary checkout"
  git --work-tree="$WORKTREE_DIR" checkout -f "$target" -- .
  run_ha_config_check "$WORKTREE_DIR"

  log "Validation passed. Fast-forwarding to $upstream"
  git merge --ff-only "$target"
  reload_home_assistant
  write_status "success" "Synced successfully." "$(git rev-parse --short HEAD)"
  log "Sync complete at $(git rev-parse --short HEAD)"
}

main "$@"
