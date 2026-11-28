#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-origin}"
REMOTE_URL="${REMOTE_URL:-https://github.com/ohadbenita/homeassistant.git}"
BRANCH="${BRANCH:-master}"
RELOAD_AFTER_SYNC="${RELOAD_AFTER_SYNC:-0}"
LOCK_FILE="${LOCK_FILE:-.ha_git_sync.lock}"
STATUS_FILE="${STATUS_FILE:-github_sync_status.json}"
export GIT_CONFIG_GLOBAL="${GIT_CONFIG_GLOBAL:-$PWD/.gitconfig}"

git() {
  command git -c safe.directory="$(pwd)" "$@"
}

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*"
}

write_status() {
  local status="$1"
  local message="$2"
  local commit="${3:-}"
  local now
  local commit_message

  if [[ -n "$commit" ]]; then
    commit_message="$(git log -1 --format=%s "$commit" 2>/dev/null || true)"
    [[ -z "$commit_message" ]] || message="$message Commit: $commit_message"
  fi

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

current_commit() {
  git rev-parse --short HEAD 2>/dev/null || true
}

ensure_git_repo() {
  git config --global --add safe.directory "$(pwd)"

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "Initializing git repository in $(pwd)"
    git init
  fi

  if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
    log "Adding git remote $REMOTE"
    git remote add "$REMOTE" "$REMOTE_URL"
  fi
}

handle_error() {
  local failed_command="$1"

  write_status \
    "failed" \
    "Sync failed while running: $failed_command" \
    "$(current_commit)"
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

migrate_public_files() {
  python3 - <<'PY'
from pathlib import Path
import shutil

config = Path.cwd()
www = config / "www"

def move_tree(source, destination):
    if not source.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            move_tree(item, target)
        elif target.exists():
            if not item.is_file() or not target.is_file() or item.read_bytes() != target.read_bytes():
                raise FileExistsError(f"Refusing to overwrite {target}")
            item.unlink()
        else:
            shutil.move(str(item), str(target))
    source.rmdir()

private = config / "snapshots"
private.mkdir(exist_ok=True)
move_tree(www / "snapshots", private)
move_tree(www / "camera_captures", private / "camera_captures")
move_tree(www / "home_assistant_upgrade", config / "home_assistant_upgrade")

old_status = www / "github_sync_status.json"
new_status = config / "github_sync_status.json"
if old_status.exists():
    if new_status.exists():
        # The sync script has already written the current status to this private path.
        old_status.unlink()
    else:
        shutil.move(str(old_status), str(new_status))
PY
}

main() {
  local last_command=""

  if [[ -e "$LOCK_FILE" ]]; then
    log "Sync already running or stale lock exists: $LOCK_FILE"
    write_status "failed" "Sync already running or stale lock exists." "$(current_commit)"
    exit 1
  fi

  trap 'rm -f "$LOCK_FILE"; [[ -n "${WORKTREE_DIR:-}" ]] && rm -rf "$WORKTREE_DIR"' EXIT
  trap 'last_command=$BASH_COMMAND; handle_error "$last_command"' ERR
  printf '%s\n' "$$" > "$LOCK_FILE"
  ensure_git_repo
  write_status "running" "Fetching $REMOTE/$BRANCH." "$(current_commit)"

  log "Fetching $REMOTE/$BRANCH"
  git fetch "$REMOTE" "$BRANCH"

  local target="$REMOTE/$BRANCH"
  local current
  local upstream
  current="$(git rev-parse HEAD 2>/dev/null || true)"
  upstream="$(git rev-parse "$target")"

  if [[ "$current" == "$upstream" ]]; then
    log "Already up to date at $current"
    git reset --hard "$target"
    migrate_public_files
    write_status "success" "Already up to date." "$(current_commit)"
    exit 0
  fi

  if [[ -n "$current" ]] && (! git diff --quiet || ! git diff --cached --quiet); then
    log "Working tree has local changes. Saving patch before sync."
    git status --short
    mkdir -p backups
    git diff > "backups/git-sync-$(date +%Y%m%d-%H%M%S).patch"
  fi

  if [[ -n "$current" ]] && ! git merge-base --is-ancestor HEAD "$target"; then
    log "Remote is not a fast-forward from local HEAD. Refusing to sync."
    write_status "failed" \
      "Remote is not a fast-forward from local HEAD. Refusing to sync." \
      "$(current_commit)"
    exit 1
  fi

  WORKTREE_DIR="$(mktemp -d /tmp/ha-sync-check.XXXXXX)"
  log "Validating $upstream in temporary checkout"
  git --work-tree="$WORKTREE_DIR" checkout -f "$target" -- .
  run_ha_config_check "$WORKTREE_DIR"

  log "Validation passed. Resetting to $upstream"
  git reset --hard "$target"

  log "Moving existing www files to private storage"
  migrate_public_files

  reload_home_assistant
  write_status "success" "Synced successfully." "$(current_commit)"
  log "Sync complete at $(current_commit)"
}

main "$@"
