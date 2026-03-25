#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TAP_DIR="$(cd "$ROOT_DIR/.." && pwd)/homebrew-tap"
PYPROJECT_FILE="$ROOT_DIR/pyproject.toml"
FORMULA_FILE="$TAP_DIR/Formula/bookkeeping-tool.rb"
REPO="lastarla/bookkeeping-tool"
CURRENT_BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
ALLOWED_ROOT_FILES=("README.md" "scripts/release.sh")

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

ensure_git_repo() {
  git -C "$1" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Not a git repository: $1"
}

ensure_release_ready_root_repo() {
  local status path allowed
  while IFS= read -r status_line; do
    [ -n "$status_line" ] || continue
    path="${status_line:3}"
    allowed=0
    for allowed_path in "${ALLOWED_ROOT_FILES[@]}"; do
      if [ "$path" = "$allowed_path" ]; then
        allowed=1
        break
      fi
    done
    [ "$allowed" -eq 1 ] || fail "bookkeeping-tool has unrelated uncommitted change: $path"
  done < <(git -C "$ROOT_DIR" status --porcelain)

  git -C "$ROOT_DIR" diff --quiet --cached -- README.md scripts/release.sh || true
  git -C "$ROOT_DIR" diff --quiet -- README.md scripts/release.sh || true

  for required_path in "${ALLOWED_ROOT_FILES[@]}"; do
    git -C "$ROOT_DIR" diff --quiet -- "$required_path" && git -C "$ROOT_DIR" diff --cached --quiet -- "$required_path" && continue
    return 0
  done

  fail "No releasable changes found in bookkeeping-tool"
}

ensure_clean_repo() {
  local repo_dir="$1"
  local repo_name="$2"
  local status
  status="$(git -C "$repo_dir" status --porcelain)"
  [ -z "$status" ] || fail "$repo_name has uncommitted changes:\n$status"
}

version_from_pyproject() {
  python3 - <<'PY' "$PYPROJECT_FILE"
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
if not match:
    raise SystemExit("Unable to find version in pyproject.toml")
print(match.group(1))
PY
}

ensure_tag_absent() {
  local repo_dir="$1"
  local tag="$2"
  git -C "$repo_dir" rev-parse "$tag" >/dev/null 2>&1 && fail "Tag already exists locally: $tag"
  git -C "$repo_dir" ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1 && fail "Tag already exists on origin: $tag"
}

update_formula() {
  local version="$1"
  local sha="$2"
  python3 - <<'PY' "$FORMULA_FILE" "$version" "$sha"
import pathlib
import re
import sys
formula = pathlib.Path(sys.argv[1])
version = sys.argv[2]
sha = sys.argv[3]
text = formula.read_text()
text = re.sub(
    r'url "https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/v[^"]+\.tar\.gz"',
    f'url "https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/v{version}.tar.gz"',
    text,
)
text = re.sub(r'sha256 "[0-9a-f]{64}"', f'sha256 "{sha}"', text)
formula.write_text(text)
PY
}

require_command git
require_command gh
require_command curl
require_command shasum
require_command python3

[ -f "$PYPROJECT_FILE" ] || fail "Missing pyproject.toml: $PYPROJECT_FILE"
[ -d "$TAP_DIR" ] || fail "Missing homebrew-tap repo: $TAP_DIR"
[ -f "$FORMULA_FILE" ] || fail "Missing formula file: $FORMULA_FILE"
[ -n "$CURRENT_BRANCH" ] || fail "Could not determine current git branch"

ensure_git_repo "$ROOT_DIR"
ensure_git_repo "$TAP_DIR"
ensure_release_ready_root_repo
ensure_clean_repo "$TAP_DIR" "homebrew-tap"

gh auth status >/dev/null 2>&1 || fail "gh auth status failed; run 'gh auth login' first"

VERSION="$(version_from_pyproject)"
TAG="v$VERSION"
ARCHIVE_URL="https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/$TAG.tar.gz"
ARCHIVE_FILE="/tmp/bookkeeping-tool-$TAG.tar.gz"

ensure_tag_absent "$ROOT_DIR" "$TAG"

echo "==> Committing release changes"
git -C "$ROOT_DIR" add README.md scripts/release.sh
git -C "$ROOT_DIR" commit -m "$(cat <<EOF
Add local release automation.

Document the local release flow and add a script that creates a GitHub release and updates the Homebrew tap.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"

echo "==> Building release artifacts"
"$ROOT_DIR/scripts/build-release.sh"

echo "==> Pushing $CURRENT_BRANCH"
git -C "$ROOT_DIR" push origin "$CURRENT_BRANCH"

echo "==> Creating and pushing tag $TAG"
git -C "$ROOT_DIR" tag "$TAG"
git -C "$ROOT_DIR" push origin "$TAG"

echo "==> Creating GitHub release"
gh release create "$TAG" \
  --repo "$REPO" \
  --title "$TAG" \
  --notes "Release $TAG"

echo "==> Downloading release tarball"
curl -L "$ARCHIVE_URL" -o "$ARCHIVE_FILE"
SHA256="$(shasum -a 256 "$ARCHIVE_FILE" | awk '{print $1}')"

echo "==> Updating Homebrew formula"
update_formula "$VERSION" "$SHA256"

git -C "$TAP_DIR" add Formula/bookkeeping-tool.rb
git -C "$TAP_DIR" commit -m "$(cat <<EOF
Update bookkeeping-tool formula to $TAG.

Point the Homebrew formula at the published $TAG release tarball and refresh its sha256.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git -C "$TAP_DIR" push origin "$(git -C "$TAP_DIR" branch --show-current)"

echo "==> Done"
echo "Version: $VERSION"
echo "Tag: $TAG"
echo "Release: https://github.com/lastarla/bookkeeping-tool/releases/tag/$TAG"
echo "Formula SHA256: $SHA256"
