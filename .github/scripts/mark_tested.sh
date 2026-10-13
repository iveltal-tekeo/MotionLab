#!/bin/bash
# Move the branch "tested" (what the app's Update button installs) to this commit; with --tag also tag a new
# __version__ as v<version>. Used by .github/workflows/tests.yml after a passing run on main.
set -uo pipefail
# a failing command here leaves a public error note (job logs need admin rights)
trap 'echo "::error title=Mark as tested::line $LINENO failed: $BASH_COMMAND"' ERR
note() { echo "::error title=Mark as tested: $1::$(printf '%s' "$2" | tr '\n' ' ' | cut -c1-900)"; }
out=$(git fetch -q origin 2>&1) || { note "git fetch" "$out"; exit 1; }
head=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$head" origin/main; then
  echo "this commit is no longer on main - tested stays"; exit 0
fi
if git rev-parse -q --verify origin/tested >/dev/null && git merge-base --is-ancestor origin/tested origin/main \
   && ! git merge-base --is-ancestor origin/tested "$head"; then
  echo "tested is already further on - it stays"; exit 0
fi
for try in 1 2 3; do                       # a passing run must not stay unmarked over a network hiccup
  out=$(git push --force origin "$head:refs/heads/tested" 2>&1) && break
  [ "$try" = 3 ] && { note "git push tested" "$out"; exit 1; }
  sleep 20
done
echo "tested -> $head"
[ "${1:-}" = "--tag" ] || exit 0
v=$(sed -n 's/^__version__ = "\(.*\)".*/\1/p' tools/motionlab/__init__.py)
if [ -n "$v" ] && ! git ls-remote --exit-code --tags origin "refs/tags/v$v" >/dev/null; then
  git tag "v$v" "$head"
  out=$(git push origin "refs/tags/v$v" 2>&1) || { note "git push tag" "$out"; exit 1; }
  echo "tagged v$v"
fi
