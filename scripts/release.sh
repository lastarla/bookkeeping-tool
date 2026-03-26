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
RESOURCE_START="# BEGIN PYTHON RESOURCES"
RESOURCE_END="# END PYTHON RESOURCES"

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

generate_resource_block() {
  python3 - <<'PY' "$PYPROJECT_FILE"
import ast
import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

PYPROJECT_FILE = Path(sys.argv[1])
HTTP_TIMEOUT = 10
HTTP_RETRIES = 3

text = PYPROJECT_FILE.read_text()
match = re.search(r'dependencies\s*=\s*\[(.*?)\n\]', text, re.S)
if not match:
    raise SystemExit("Unable to find dependencies in pyproject.toml")
block = re.sub(r'^\s*#.*$', '', match.group(1), flags=re.M)
requirements = ast.literal_eval("[" + block + "]")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@lru_cache(maxsize=None)
def fetch_json(url: str, label: str):
    last_error = None
    for attempt in range(1, HTTP_RETRIES + 1):
        print(f"FETCH {label} (attempt {attempt}/{HTTP_RETRIES})", file=sys.stderr)
        try:
            with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"Failed to fetch PyPI metadata for {label}: {url}: {exc}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error = exc
            if attempt == HTTP_RETRIES:
                break
            time.sleep(attempt)
        except Exception as exc:
            raise SystemExit(f"Unexpected error while fetching PyPI metadata for {label}: {url}: {exc}") from exc
    raise SystemExit(f"Failed to fetch PyPI metadata for {label}: {url}: {last_error}")


def resolve_versions(requirements_list):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        requirements_file = tmpdir_path / "requirements.txt"
        report_file = tmpdir_path / "report.json"
        requirements_file.write_text("\n".join(requirements_list) + "\n")
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--quiet",
            "--report",
            str(report_file),
            "-r",
            str(requirements_file),
        ]
        print("RESOLVE dependencies with pip", file=sys.stderr)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip() or "pip dependency resolution failed"
            raise SystemExit(f"Failed to resolve Python dependencies: {details}")
        report = json.loads(report_file.read_text())
    versions = {}
    for item in report.get("install", []):
        metadata = item.get("metadata") or {}
        name = metadata.get("name")
        version = metadata.get("version")
        if name and version:
            versions[normalize_name(name)] = version
    if not versions:
        raise SystemExit("pip did not resolve any Python dependencies")
    return versions


def fetch_release(name: str, version: str):
    encoded_name = urllib.parse.quote(name, safe="")
    encoded_version = urllib.parse.quote(version, safe="")
    url = f"https://pypi.org/pypi/{encoded_name}/{encoded_version}/json"
    data = fetch_json(url, f"{name}=={version}")
    urls = data.get("urls") or []
    sdist = next((item for item in urls if item.get("packagetype") == "sdist"), None)
    if sdist is None:
        releases = data.get("releases", {})
        sdist = next((item for item in releases.get(version, []) if item.get("packagetype") == "sdist"), None)
    if sdist is None:
        raise SystemExit(f"No sdist release found for {name}=={version}")
    return sdist["url"], sdist["digests"]["sha256"]


selected_versions = resolve_versions(requirements)
resource_entries = {}
for name, version in sorted(selected_versions.items()):
    resource_url, resource_sha = fetch_release(name, version)
    resource_entries[name] = {
        "version": version,
        "url": resource_url,
        "sha256": resource_sha,
    }

print('# BEGIN PYTHON RESOURCES')
for name in sorted(resource_entries):
    entry = resource_entries[name]
    print(f'  resource "{name}" do')
    print(f'    url "{entry["url"]}"')
    print(f'    sha256 "{entry["sha256"]}"')
    print('  end')
    print()
print('# END PYTHON RESOURCES')
print(f'# RESOURCE COUNT: {len(resource_entries)}', file=sys.stderr)
PY
}

update_formula() {
  local version="$1"
  local sha="$2"
  local resource_block="$3"
  python3 - <<'PY' "$FORMULA_FILE" "$version" "$sha" "$resource_block" "$RESOURCE_START" "$RESOURCE_END"
import pathlib
import re
import sys

formula = pathlib.Path(sys.argv[1])
version = sys.argv[2]
sha = sys.argv[3]
resource_block = pathlib.Path(sys.argv[4]).read_text().rstrip() + "\n"
resource_start = sys.argv[5]
resource_end = sys.argv[6]
text = formula.read_text()

updated = re.sub(
    r'url "https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/v[^"]+\.tar\.gz"',
    f'url "https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/v{version}.tar.gz"',
    text,
    count=1,
)
updated = re.sub(
    r'(url "https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/v[^"]+\.tar\.gz"\n\s*sha256 ")[0-9a-f]{64}(")',
    rf'\g<1>{sha}\2',
    updated,
    count=1,
)
pattern = re.compile(
    rf'^[ \t]*{re.escape(resource_start)}\n.*?^[ \t]*{re.escape(resource_end)}',
    re.S | re.M,
)
if not pattern.search(updated):
    raise SystemExit("Formula resource block markers not found")
updated = pattern.sub(resource_block.rstrip(), updated, count=1)
updated += "\n" if not updated.endswith("\n") else ""
if updated == text:
    raise SystemExit("Formula did not change; aborting")
formula.write_text(updated)
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
ARCHIVE_URL="https://github.com/lastarla/bookkeeping-tool/archive/refs/tags/$TAG.tar.gz"
ARCHIVE_FILE="/tmp/bookkeeping-tool-$TAG.tar.gz"
RESOURCE_FILE="/tmp/bookkeeping-tool-$TAG-resources.rb"
RESOURCE_STDERR_FILE="/tmp/bookkeeping-tool-$TAG-resources.stderr"
TAP_BRANCH="$(git -C "$TAP_DIR" branch --show-current)"

[ -n "$TAP_BRANCH" ] || fail "Could not determine homebrew-tap current branch"

echo "==> Releasing version $VERSION from branch $CURRENT_BRANCH"
echo "==> Tag: $TAG"
echo "==> Archive URL: $ARCHIVE_URL"
echo "==> Tap repo: $TAP_DIR ($TAP_BRANCH)"

echo "==> Generating Python resources"
if ! generate_resource_block >"$RESOURCE_FILE" 2>"$RESOURCE_STDERR_FILE"; then
  echo "Error: failed to generate Python resources" >&2
  if [ -f "$RESOURCE_STDERR_FILE" ]; then
    cat "$RESOURCE_STDERR_FILE" >&2
  fi
  exit 1
fi
RESOURCE_COUNT="$(python3 - <<'PY' "$RESOURCE_STDERR_FILE"
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text()
match = re.search(r'RESOURCE COUNT: (\d+)', text)
print(match.group(1) if match else 'unknown')
PY
)"
echo "==> Resource count: $RESOURCE_COUNT"

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

echo "==> Pushing $CURRENT_BRANCH"
git -C "$ROOT_DIR" push origin "$CURRENT_BRANCH"

echo "==> Creating and pushing tag $TAG"
git -C "$ROOT_DIR" tag "$TAG"
git -C "$ROOT_DIR" push origin "$TAG"

echo "==> Creating GitHub release"
gh release create "$TAG" \
  --repo "$REPO" \
  --title "$TAG" \
  --notes "$RELEASE_NOTES"

echo "==> Downloading release tarball"
curl -L "$ARCHIVE_URL" -o "$ARCHIVE_FILE"
SHA256="$(shasum -a 256 "$ARCHIVE_FILE" | awk '{print $1}')"

echo "==> Updating Homebrew formula"
update_formula "$VERSION" "$SHA256" "$RESOURCE_FILE"

git -C "$TAP_DIR" add Formula/bookkeeping-tool.rb
git -C "$TAP_DIR" commit -m "$(cat <<EOF
Update bookkeeping-tool formula to $TAG.

Point the Homebrew formula at the published $TAG release tarball, refresh its sha256, and regenerate Python resources.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git -C "$TAP_DIR" push origin "$TAP_BRANCH"

echo "==> Done"
echo "Version: $VERSION"
echo "Tag: $TAG"
echo "Release: https://github.com/lastarla/bookkeeping-tool/releases/tag/$TAG"
echo "Formula SHA256: $SHA256"
echo "Resource count: $RESOURCE_COUNT"
