#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/release.sh [options]

Options:
  --dry-run           Run preflight checks and print the plan without publishing.
  --skip-build        Skip ./scripts/build-release.sh.
  --notes <text>      Release notes text passed to gh release create.
  --help              Show this help.
EOF
}

DRY_RUN=0
SKIP_BUILD=0
RELEASE_NOTES=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    --notes)
      [ $# -ge 2 ] || { usage; exit 2; }
      RELEASE_NOTES="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TAP_DIR="$(cd "$ROOT_DIR/.." && pwd)/homebrew-tap"
PYPROJECT_FILE="$ROOT_DIR/pyproject.toml"
FORMULA_FILE="$TAP_DIR/Formula/bookkeeping-tool.rb"
REPO="lastarla/bookkeeping-tool"
CURRENT_BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
MACOS_ARM64_ARTIFACT_NAME=""
MACOS_ARM64_ARTIFACT_FILE=""

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
  if git -C "$repo_dir" rev-parse "$tag" >/dev/null 2>&1; then
    fail "Tag already exists locally: $tag"
  fi
  if git -C "$repo_dir" ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1; then
    fail "Tag already exists on origin: $tag"
  fi
}

artifact_name_from_version() {
  local version="$1"
  printf 'bookkeeping-tool-darwin-arm64-v%s.tar.gz' "$version"
}

update_formula() {
  local version="$1"
  local artifact_name="$2"
  local artifact_sha="$3"
  python3 - <<'PY' "$FORMULA_FILE" "$version" "$artifact_name" "$artifact_sha"
import pathlib
import re
import sys

formula = pathlib.Path(sys.argv[1])
version = sys.argv[2]
artifact_name = sys.argv[3]
artifact_sha = sys.argv[4]
text = formula.read_text()
new_text = f'''class BookkeepingTool < Formula
  desc "Local bookkeeping data import and normalization tool"
  homepage "https://github.com/lastarla/bookkeeping-tool"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/lastarla/bookkeeping-tool/releases/download/v{version}/{artifact_name}"
      sha256 "{artifact_sha}"
    end

    on_intel do
      odie "bookkeeping-tool Homebrew formula currently provides only a macOS arm64 release artifact"
    end
  end

  on_linux do
    odie "bookkeeping-tool Homebrew formula is currently macOS-only"
  end

  def install
    bin.install "bookkeeping"
  end

  def post_install
    chmod 0755, "#{{bin}}/bookkeeping"
  end

  test do
    assert_match "bookkeeping 本地记账工具 CLI", shell_output("#{{bin}}/bookkeeping --help")
  end
end
'''
if new_text == text:
    raise SystemExit("Formula did not change; aborting")
formula.write_text(new_text)
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

VERSION="$(version_from_pyproject)"
TAG="v$VERSION"
MACOS_ARM64_ARTIFACT_NAME="$(artifact_name_from_version "$VERSION")"
MACOS_ARM64_ARTIFACT_FILE="$ROOT_DIR/dist/$MACOS_ARM64_ARTIFACT_NAME"
TAP_BRANCH="$(git -C "$TAP_DIR" branch --show-current)"

[ -n "$TAP_BRANCH" ] || fail "Could not determine homebrew-tap current branch"

echo "==> Releasing version $VERSION from branch $CURRENT_BRANCH"
echo "==> Tag: $TAG"
echo "==> Artifact: $MACOS_ARM64_ARTIFACT_NAME"
echo "==> Tap repo: $TAP_DIR ($TAP_BRANCH)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "==> Dry run: no changes will be published"
  echo "==> Dry run note: skipping repo cleanliness, auth, and remote tag checks"
  exit 0
fi

echo "==> Checking git repositories"
ensure_git_repo "$ROOT_DIR"
ensure_git_repo "$TAP_DIR"

echo "==> Checking working tree cleanliness"
ensure_clean_repo "$ROOT_DIR" "bookkeeping-tool"
ensure_clean_repo "$TAP_DIR" "homebrew-tap"

echo "==> Checking GitHub auth"
gh auth status >/dev/null 2>&1 || fail "gh auth status failed; run 'gh auth login' first"

echo "==> Checking tag availability"
ensure_tag_absent "$ROOT_DIR" "$TAG"
if [ "$SKIP_BUILD" -eq 0 ]; then
  echo "==> Building release artifacts"
  "$ROOT_DIR/scripts/build-release.sh"
else
  echo "==> Skipping build step"
fi

[ -f "$MACOS_ARM64_ARTIFACT_FILE" ] || fail "Missing release artifact: $MACOS_ARM64_ARTIFACT_FILE"
MACOS_ARM64_SHA256="$(shasum -a 256 "$MACOS_ARM64_ARTIFACT_FILE" | awk '{print $1}')"
echo "==> Artifact sha256: $MACOS_ARM64_SHA256"

echo "==> Pushing $CURRENT_BRANCH"
git -C "$ROOT_DIR" push origin "$CURRENT_BRANCH"

echo "==> Creating and pushing tag $TAG"
git -C "$ROOT_DIR" tag "$TAG"
git -C "$ROOT_DIR" push origin "$TAG"

echo "==> Creating GitHub release"
gh release create "$TAG" \
  --repo "$REPO" \
  --title "$TAG" \
  --notes "$RELEASE_NOTES" \
  "$MACOS_ARM64_ARTIFACT_FILE"

echo "==> Updating Homebrew formula"
update_formula "$VERSION" "$MACOS_ARM64_ARTIFACT_NAME" "$MACOS_ARM64_SHA256"

git -C "$TAP_DIR" add Formula/bookkeeping-tool.rb
git -C "$TAP_DIR" commit -m "$(cat <<EOF
Update bookkeeping-tool formula to $TAG.

Point the Homebrew formula at the published $TAG single-binary release tarball and refresh its sha256.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git -C "$TAP_DIR" push origin "$TAP_BRANCH"

echo "==> Done"
echo "Version: $VERSION"
echo "Tag: $TAG"
echo "Release: https://github.com/lastarla/bookkeeping-tool/releases/tag/$TAG"
echo "Artifact: $MACOS_ARM64_ARTIFACT_NAME"
echo "Formula SHA256: $MACOS_ARM64_SHA256"
