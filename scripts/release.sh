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
import sys
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

PYPROJECT_FILE = Path(sys.argv[1])
PYTHON_VERSION = "3.12"
TARGET_EXTRA = {"standard"}
TARGET_SYS_PLATFORM = sys.platform
HTTP_TIMEOUT = 10

text = PYPROJECT_FILE.read_text()
match = re.search(r'dependencies\s*=\s*\[(.*?)\n\]', text, re.S)
if not match:
    raise SystemExit("Unable to find dependencies in pyproject.toml")
block = re.sub(r'^\s*#.*$', '', match.group(1), flags=re.M)
requirements = ast.literal_eval("[" + block + "]")

OPS = [">=", "<=", "!=", "==", "~=", ">", "<"]
PRE_RELEASE_RE = re.compile(r"[A-Za-z]")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def split_version(version: str):
    version = version.replace("-", ".")
    version = re.sub(r"(?i)(a|b|rc|post|dev)", lambda m: "." + m.group(1).lower() + ".", version)
    parts = re.split(r"[^0-9A-Za-z]+", version)
    normalized = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            normalized.append((0, int(part)))
        else:
            normalized.append((1, part.lower()))
    return tuple(normalized)


def is_prerelease(version: str) -> bool:
    return bool(PRE_RELEASE_RE.search(version))


class MarkerParser:
    def __init__(self, text: str):
        self.tokens = self.tokenize(text)
        self.index = 0

    def tokenize(self, text: str):
        tokens = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch.isspace():
                i += 1
                continue
            if text.startswith("and", i) and self._boundary(text, i, 3):
                tokens.append(("AND", "and"))
                i += 3
                continue
            if text.startswith("or", i) and self._boundary(text, i, 2):
                tokens.append(("OR", "or"))
                i += 2
                continue
            if text.startswith("not", i) and self._boundary(text, i, 3):
                tokens.append(("NOT", "not"))
                i += 3
                continue
            if ch in "()":
                tokens.append((ch, ch))
                i += 1
                continue
            if text.startswith("==", i) or text.startswith("!=", i) or text.startswith(">=", i) or text.startswith("<=", i):
                tokens.append(("OP", text[i:i+2]))
                i += 2
                continue
            if ch in "<>":
                tokens.append(("OP", ch))
                i += 1
                continue
            if ch in {'"', "'"}:
                quote = ch
                i += 1
                start = i
                while i < len(text) and text[i] != quote:
                    i += 1
                if i >= len(text):
                    raise SystemExit(f"Unterminated string in marker: {text}")
                tokens.append(("STRING", text[start:i]))
                i += 1
                continue
            start = i
            while i < len(text) and re.match(r"[A-Za-z0-9_.-]", text[i]):
                i += 1
            if start == i:
                raise SystemExit(f"Unexpected marker token near: {text[i:]}")
            tokens.append(("IDENT", text[start:i]))
        return tokens

    def _boundary(self, text, start, size):
        before = start == 0 or not re.match(r"[A-Za-z0-9_]", text[start - 1])
        after_index = start + size
        after = after_index >= len(text) or not re.match(r"[A-Za-z0-9_]", text[after_index])
        return before and after

    def current(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def eat(self, kind=None, value=None):
        token = self.current()
        if token is None:
            raise SystemExit("Unexpected end of marker")
        if kind is not None and token[0] != kind:
            raise SystemExit(f"Expected {kind}, got {token}")
        if value is not None and token[1] != value:
            raise SystemExit(f"Expected {value}, got {token}")
        self.index += 1
        return token

    def parse(self):
        expr = self.parse_or()
        if self.current() is not None:
            raise SystemExit(f"Unexpected token in marker: {self.current()}")
        return expr

    def parse_or(self):
        node = self.parse_and()
        while self.current() and self.current()[0] == "OR":
            self.eat("OR")
            node = ("or", node, self.parse_and())
        return node

    def parse_and(self):
        node = self.parse_not()
        while self.current() and self.current()[0] == "AND":
            self.eat("AND")
            node = ("and", node, self.parse_not())
        return node

    def parse_not(self):
        if self.current() and self.current()[0] == "NOT":
            self.eat("NOT")
            return ("not", self.parse_not())
        return self.parse_atom()

    def parse_atom(self):
        token = self.current()
        if token and token[0] == "(":
            self.eat("(")
            node = self.parse_or()
            self.eat(")")
            return node
        ident = self.eat("IDENT")[1]
        op = self.eat("OP")[1]
        value = self.eat("STRING")[1]
        return ("cmp", ident, op, value)


def eval_marker(node, extra_context=None):
    extra_context = extra_context or set()
    kind = node[0]
    if kind == "or":
        return eval_marker(node[1], extra_context) or eval_marker(node[2], extra_context)
    if kind == "and":
        return eval_marker(node[1], extra_context) and eval_marker(node[2], extra_context)
    if kind == "not":
        return not eval_marker(node[1], extra_context)
    _, ident, op, value = node
    ident = ident.replace(".", "_")
    if ident == "extra":
        left = extra_context
        return compare_extra(left, op, value)
    if ident == "python_version":
        left = PYTHON_VERSION
    elif ident == "sys_platform":
        left = TARGET_SYS_PLATFORM
    else:
        return True
    return compare_value(left, op, value)


def compare_extra(values, op, value):
    if op == "==":
        return value in values
    if op == "!=":
        return value not in values
    return False


def compare_value(left, op, right):
    if op in {"==", "!="}:
        result = left == right
        return result if op == "==" else not result
    left_key = split_version(left)
    right_key = split_version(right)
    if op == ">=":
        return left_key >= right_key
    if op == "<=":
        return left_key <= right_key
    if op == ">":
        return left_key > right_key
    if op == "<":
        return left_key < right_key
    if op == "~=":
        parts = right.split(".")
        if len(parts) == 1:
            upper = str(int(parts[0]) + 1)
        else:
            prefix = parts[:-1]
            prefix[-1] = str(int(prefix[-1]) + 1)
            upper = ".".join(prefix)
        return left_key >= right_key and left_key < split_version(upper)
    return True


def parse_requirement(raw: str):
    raw = raw.strip()
    marker = None
    if ";" in raw:
        raw, marker = [part.strip() for part in raw.split(";", 1)]
    extras = set()
    if "[" in raw and "]" in raw:
        name_part, rest = raw.split("[", 1)
        extras_text, remainder = rest.split("]", 1)
        extras = {item.strip() for item in extras_text.split(",") if item.strip()}
        raw = name_part + remainder
    name = raw
    specifiers = []
    selected_op = None
    spec_text = ""
    match = re.match(r'^([A-Za-z0-9_.-]+)(.*)$', raw)
    if not match:
        raise SystemExit(f"Unable to parse requirement: {raw}")
    name = match.group(1).strip()
    spec_text = match.group(2).strip()
    for op in OPS:
        if spec_text.startswith(op):
            selected_op = op
            break
    else:
        name = raw.strip()
    specifiers = []
    if selected_op and spec_text.startswith(selected_op):
        spec_text = spec_text[len(selected_op):]
    if spec_text:
        pieces = [piece.strip() for piece in spec_text.split(',') if piece.strip()]
        if pieces:
            first_piece = pieces[0]
            specifiers.append((selected_op, first_piece.strip()))
        for piece in pieces[1:]:
            for candidate in OPS:
                if piece.startswith(candidate):
                    specifiers.append((candidate, piece[len(candidate):].strip()))
                    break
    marker_ast = MarkerParser(marker).parse() if marker else None
    return {
        'name': normalize_name(name),
        'extras': extras,
        'specifiers': specifiers,
        'marker': marker_ast,
        'raw': raw,
    }


def merge_specifiers(existing, incoming):
    merged = list(existing)
    for item in incoming:
        if item not in merged:
            merged.append(item)
    return merged


def version_satisfies(version, specifiers):
    if is_prerelease(version):
        return False
    for op, expected in specifiers:
        if not compare_value(version, op, expected):
            return False
    return True


@lru_cache(maxsize=None)
def fetch_package(name: str):
    encoded = urllib.parse.quote(name, safe="")
    url = f"https://pypi.org/pypi/{encoded}/json"
    print(f"PROCESS {name}", file=sys.stderr)
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
            return json.load(resp)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise SystemExit(f"Failed to fetch PyPI metadata for {name}: {url}: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"Unexpected error while fetching PyPI metadata for {name}: {url}: {exc}") from exc


def choose_release(name: str, specifiers):
    data = fetch_package(name)
    releases = data.get('releases', {})
    candidates = []
    for version, files in releases.items():
        if not version_satisfies(version, specifiers):
            continue
        sdist = next((item for item in files if item.get('packagetype') == 'sdist'), None)
        if not sdist:
            continue
        candidates.append((split_version(version), version, sdist))
    if not candidates:
        raise SystemExit(f"No stable sdist release found for {name} matching {specifiers}")
    candidates.sort()
    _, version, sdist = candidates[-1]
    return version, sdist


def evaluate_marker(marker_ast, extras):
    if marker_ast is None:
        return True
    return eval_marker(marker_ast, extras)


constraints = {}
selected_versions = {}
resource_entries = {}
queue = []

for requirement in requirements:
    parsed = parse_requirement(requirement)
    name = parsed['name']
    entry = constraints.setdefault(name, {'specifiers': [], 'extras': set()})
    entry['specifiers'] = merge_specifiers(entry['specifiers'], parsed['specifiers'])
    entry['extras'].update(parsed['extras'])
    queue.append(name)

processed = set()
while queue:
    name = queue.pop(0)
    entry = constraints[name]
    version, sdist = choose_release(name, entry['specifiers'])
    previous_version = selected_versions.get(name)
    selected_versions[name] = version
    resource_entries[name] = {
        'version': version,
        'url': sdist['url'],
        'sha256': sdist['digests']['sha256'],
    }
    if name in processed and previous_version == version:
        continue
    processed.add(name)
    package = fetch_package(name)
    requires_dist = package['info'].get('requires_dist') or []
    active_extras = set(entry['extras'])
    for raw_req in requires_dist:
        parsed = parse_requirement(raw_req)
        if not evaluate_marker(parsed['marker'], active_extras):
            continue
        dep_name = parsed['name']
        dep_entry = constraints.setdefault(dep_name, {'specifiers': [], 'extras': set()})
        before = (tuple(dep_entry['specifiers']), tuple(sorted(dep_entry['extras'])))
        dep_entry['specifiers'] = merge_specifiers(dep_entry['specifiers'], parsed['specifiers'])
        dep_entry['extras'].update(parsed['extras'])
        after = (tuple(dep_entry['specifiers']), tuple(sorted(dep_entry['extras'])))
        if before != after or dep_name not in processed:
            queue.append(dep_name)

names = sorted(resource_entries)
print('# BEGIN PYTHON RESOURCES')
for name in names:
    entry = resource_entries[name]
    print(f'  resource "{name}" do')
    print(f'    url "{entry["url"]}"')
    print(f'    sha256 "{entry["sha256"]}"')
    print('  end')
    print()
print('# END PYTHON RESOURCES')
print(f'# RESOURCE COUNT: {len(names)}', file=sys.stderr)
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
    rf'{re.escape(resource_start)}\n.*?\n{re.escape(resource_end)}',
    re.S,
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
