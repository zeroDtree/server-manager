#!/usr/bin/env bash

# @help-begin
# Pull one repo in a nested submodule chain and record its commit in each
# parent up to the top superproject.
#
# At each parent the script fast-forwards from origin. If that update already
# records the checked-out submodule commit, the parent is left unchanged.
# If the checkout is ahead of the recorded pointer, it commits that pointer
# and pushes the parent branch.
#
# Usage:
#   ./update-submodule-chain.sh [start-dir]
#
# start-dir is the repository that already contains the new commits. It must
# have a clean tracked worktree. The default is the current directory.
#
# Example:
#   ./utils/update-submodule-chain.sh server-agent/account-provisioner/isolation/shell_script
#
# Each repository uses origin and the branch currently checked out there.
# @help-end

# @help-options-begin
#   -h, --help              show help
# @help-options-end

set -euo pipefail

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

start_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    --) shift; break ;;
    -*) echo "Unknown option: $1" >&2; usage ;;
    *)
      [[ -z "$start_dir" ]] || { echo "Unexpected argument: $1" >&2; usage; }
      start_dir="$1"
      shift
      ;;
  esac
done

[[ -n "$start_dir" ]] || start_dir="."

die() {
  echo "error: $*" >&2
  exit 1
}

canon_dir() {
  (cd "$1" && pwd -P)
}

branch_name() {
  local branch
  branch="$(git -C "$1" rev-parse --abbrev-ref HEAD)"
  [[ "$branch" != "HEAD" ]] || die "detached HEAD: $1"
  printf '%s\n' "$branch"
}

require_clean_tracked() {
  local dir="$1" line path mode
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    path="${line:3}"
    mode="$(git -C "$dir" ls-files -s -- "$path" | awk '{print $1}')"
    if [[ "$mode" == "160000" ]]; then
      die "$dir has an updated submodule ($path). Start from that repository instead."
    fi
    die "tracked changes in $dir ($path). Commit or stash them first."
  done < <(git -C "$dir" status --porcelain --untracked-files=no)
}

require_clean_except() {
  local dir="$1" allowed="$2" line path
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    path="${line:3}"
    [[ "$path" == "$allowed" ]] || die "tracked changes besides $allowed in $dir: $path"
  done < <(git -C "$dir" status --porcelain --untracked-files=no)
}

sync_branch() {
  local dir="$1" branch remote_ref local_sha remote_sha
  branch="$(branch_name "$dir")"
  remote_ref="origin/$branch"

  git -C "$dir" fetch origin "$branch"
  git -C "$dir" rev-parse --verify "$remote_ref" >/dev/null 2>&1 \
    || die "missing $remote_ref after fetch ($dir)"

  local_sha="$(git -C "$dir" rev-parse HEAD)"
  remote_sha="$(git -C "$dir" rev-parse "$remote_ref")"
  if [[ "$local_sha" == "$remote_sha" ]]; then
    echo "$dir ($branch): matches $remote_ref"
    return 0
  fi

  if git -C "$dir" merge-base --is-ancestor "$local_sha" "$remote_sha"; then
    echo "$dir ($branch): fast-forward to $remote_ref"
    git -C "$dir" merge --ff-only "$remote_ref"
  elif git -C "$dir" merge-base --is-ancestor "$remote_sha" "$local_sha"; then
    echo "$dir ($branch): push existing commits"
    git -C "$dir" push origin "$branch"
  else
    die "$dir ($branch) diverged from $remote_ref"
  fi
}

bump_pointer() {
  local parent="$1" child="$2" rel mode recorded checked branch
  rel="${child#"$parent"/}"
  [[ "$rel" != "$child" ]] || die "cannot locate $child inside $parent"

  sync_branch "$parent"

  mode="$(git -C "$parent" ls-tree HEAD -- "$rel" | awk '{print $1}')"
  [[ "$mode" == "160000" ]] || die "$rel is not a submodule of $parent"

  require_clean_except "$parent" "$rel"
  require_clean_tracked "$child"

  recorded="$(git -C "$parent" rev-parse "HEAD:$rel")"
  checked="$(git -C "$child" rev-parse HEAD)"
  if [[ "$recorded" == "$checked" ]]; then
    echo "$parent: $rel already at ${checked:0:12}"
    return 0
  fi

  git -C "$child" cat-file -e "${recorded}^{commit}" 2>/dev/null \
    || die "$parent records $rel ${recorded:0:12}, which is not in $child"

  if git -C "$child" merge-base --is-ancestor "$recorded" "$checked"; then
    branch="$(branch_name "$parent")"
    echo "$parent: record $rel ${recorded:0:12} -> ${checked:0:12}"
    git -C "$parent" add -- "$rel"
    git -C "$parent" commit -m "update submodule"
    git -C "$parent" push origin "$branch"
    return 0
  fi

  if git -C "$child" merge-base --is-ancestor "$checked" "$recorded"; then
    die "$parent records a newer $rel (${recorded:0:12}); checkout is ${checked:0:12}"
  fi
  die "$rel diverged in $parent (recorded ${recorded:0:12}, checkout ${checked:0:12})"
}

start_dir="$(canon_dir "$start_dir")"
start_dir="$(canon_dir "$(git -C "$start_dir" rev-parse --show-toplevel)")"

require_clean_tracked "$start_dir"
sync_branch "$start_dir"

current="$start_dir"
while true; do
  parent="$(git -C "$current" rev-parse --show-superproject-working-tree 2>/dev/null || true)"
  [[ -n "$parent" ]] || break
  parent="$(canon_dir "$parent")"
  bump_pointer "$parent" "$current"
  current="$parent"
done

echo "done: $start_dir"