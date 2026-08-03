#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-master}"
RELOAD_AFTER_SYNC="${RELOAD_AFTER_SYNC:-0}"
LOCK_FILE="${LOCK_FILE:-.ha_git_sync.lock}"

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*"
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
    exit 1
  fi

  trap 'rm -f "$LOCK_FILE"; [[ -n "${WORKTREE_DIR:-}" ]] && rm -rf "$WORKTREE_DIR"' EXIT
  printf '%s\n' "$$" > "$LOCK_FILE"

  if ! git diff --quiet || ! git diff --cached --quiet; then
    log "Working tree has local changes. Refusing to sync."
    git status --short
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
    exit 0
  fi

  if ! git merge-base --is-ancestor HEAD "$target"; then
    log "Remote is not a fast-forward from local HEAD. Refusing to sync."
    exit 1
  fi

  WORKTREE_DIR="$(mktemp -d /tmp/ha-sync-check.XXXXXX)"
  log "Validating $upstream in temporary checkout"
  git --work-tree="$WORKTREE_DIR" checkout -f "$target" -- .
  run_ha_config_check "$WORKTREE_DIR"

  log "Validation passed. Fast-forwarding to $upstream"
  git merge --ff-only "$target"
  reload_home_assistant
  log "Sync complete at $(git rev-parse --short HEAD)"
}

main "$@"
