#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
DRY_RUN=false
CHECK_ONLY=false
UNLINK=false
CHECK_FAILURE=false

usage() {
  cat <<'EOF'
Usage: ./sync.sh [--dry-run] [--check] [--unlink]

  --dry-run  Show changes without applying them
  --check    Check managed links without changing them
  --unlink   Remove only links that point into this repository
EOF
}

case "${1:-}" in
  "") ;;
  --dry-run) DRY_RUN=true ;;
  --check) CHECK_ONLY=true ;;
  --unlink) UNLINK=true ;;
  --help|-h) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

if [[ "$CHECK_ONLY" == true || "$UNLINK" == true ]]; then
  DRY_RUN=false
fi

declare -a MANAGED=()

ensure_dir() {
  local dir=$1
  [[ "$UNLINK" == true ]] && return 0
  if [[ "$DRY_RUN" == true || "$CHECK_ONLY" == true ]]; then
    printf 'would create directory: %s\n' "$dir"
  else
    mkdir -p "$dir"
  fi
}

link_item() {
  local source=$1 destination=$2
  MANAGED+=("$destination")

  if [[ -L "$destination" ]]; then
    local target
    target=$(readlink "$destination")
    if [[ "$target" == "$source" ]]; then
      printf 'ok: %s\n' "$destination"
      return 0
    fi
    printf 'conflict: symlink exists at %s -> %s\n' "$destination" "$target" >&2
    return 1
  fi

  if [[ -e "$destination" ]]; then
    printf 'conflict: real path exists at %s\n' "$destination" >&2
    return 1
  fi

  if [[ "$CHECK_ONLY" == true ]]; then
    printf 'missing: %s\n' "$destination"
    CHECK_FAILURE=true
  elif [[ "$UNLINK" == true ]]; then
    printf 'absent: %s\n' "$destination"
  elif [[ "$DRY_RUN" == true ]]; then
    printf 'link: %s -> %s\n' "$destination" "$source"
  else
    ln -s "$source" "$destination"
    printf 'linked: %s -> %s\n' "$destination" "$source"
  fi
}

unlink_item() {
  local destination=$1
  if [[ -L "$destination" ]] && [[ "$(readlink "$destination")" == "$ROOT_DIR"/* ]]; then
    rm "$destination"
    printf 'unlinked: %s\n' "$destination"
  fi
}

link_group() {
  local source_dir=$1 target_dir=$2
  [[ -d "$source_dir" ]] || return 0
  ensure_dir "$target_dir"
  local item name
  for item in "$source_dir"/*; do
    [[ -e "$item" || -L "$item" ]] || continue
    name=$(basename "$item")
    [[ "$name" == ".gitkeep" ]] && continue
    if [[ "$UNLINK" == true ]]; then
      unlink_item "$target_dir/$name"
    else
      link_item "$item" "$target_dir/$name"
    fi
  done
}

link_file() {
  local source=$1 target=$2
  ensure_dir "$(dirname "$target")"
  if [[ "$UNLINK" == true ]]; then
    unlink_item "$target"
  else
    link_item "$source" "$target"
  fi
}

HOME_DIR=${HOME:?HOME must be set}

link_group "$ROOT_DIR/skills" "$HOME_DIR/.agents/skills"
link_group "$ROOT_DIR/skills" "$HOME_DIR/.claude/skills"
link_group "$ROOT_DIR/skills" "$HOME_DIR/.config/opencode/skills"
link_group "$ROOT_DIR/skills" "$HOME_DIR/.hermes/skills"
link_group "$ROOT_DIR/agents" "$HOME_DIR/.config/opencode/agents"
link_group "$ROOT_DIR/agents" "$HOME_DIR/.claude/agents"
link_group "$ROOT_DIR/commands" "$HOME_DIR/.config/opencode/commands"
link_group "$ROOT_DIR/commands" "$HOME_DIR/.claude/commands"
link_group "$ROOT_DIR/commands" "$HOME_DIR/.codex/prompts"
link_group "$ROOT_DIR/adapters/opencode/plugins" "$HOME_DIR/.config/opencode/plugins"

link_file "$ROOT_DIR/rules/global.md" "$HOME_DIR/.config/opencode/AGENTS.md"
link_file "$ROOT_DIR/rules/global.md" "$HOME_DIR/.codex/AGENTS.md"
link_file "$ROOT_DIR/rules/global.md" "$HOME_DIR/.claude/CLAUDE.md"

if [[ "$CHECK_ONLY" == true ]]; then
  printf 'check complete\n'
elif [[ "$DRY_RUN" == true ]]; then
  printf 'dry run complete\n'
elif [[ "$UNLINK" == true ]]; then
  printf 'unlink complete\n'
else
  chmod +x "$ROOT_DIR"/hooks/*.sh "$ROOT_DIR"/sync.sh
  printf 'sync complete\n'
fi

if [[ "$CHECK_ONLY" == true && "$CHECK_FAILURE" == true ]]; then
  exit 1
fi
