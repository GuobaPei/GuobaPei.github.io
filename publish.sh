#!/bin/bash
# Commit and push the homepage, then wait until the change is actually live.
# Usage: ./publish.sh "add NeurIPS paper"
set -uo pipefail
cd "$(dirname "$0")" || exit 1

MSG="${1:-update}"

if [ -z "$(git status --porcelain)" ]; then
  echo "nothing to publish — working tree is clean"
  exit 0
fi

# every referenced local image must exist, or the page ships with a broken card
missing=0
for f in $(grep -oE '(figs|logos)/[A-Za-z0-9_.-]+\.(webp|png|jpg)|src="me\.webp"' index.html \
           | sed 's/src="//;s/"//' | sort -u); do
  [ -f "$f" ] || { echo "MISSING asset referenced by index.html: $f"; missing=1; }
done
[ "$missing" -eq 0 ] || { echo "refusing to publish with broken image references"; exit 1; }

git add -A
git -c user.name="pei2333" -c user.email="1826502980@qq.com" commit -q -m "$MSG" || exit 1
echo "committed: $(git log --oneline -1)"

# GitHub over this connection is flaky; retry rather than fail
for i in 1 2 3 4 5 6; do
  if GIT_TERMINAL_PROMPT=0 git push -q origin main 2>/dev/null; then
    echo "pushed"
    break
  fi
  echo "push failed, retry $i"
  sleep 5
  [ "$i" -eq 6 ] && { echo "could not push after 6 tries — run ./publish.sh again"; exit 1; }
done

echo -n "waiting for Pages to redeploy"
LOCAL_HASH=$(shasum -a 256 index.html | cut -c1-16)
for i in $(seq 1 40); do
  LIVE=$(curl -sSL --http1.1 -m 45 "https://guobapei.github.io/" 2>/dev/null \
         | shasum -a 256 | cut -c1-16)
  if [ "$LIVE" = "$LOCAL_HASH" ]; then
    echo " done"
    echo "live and byte-identical to local: https://guobapei.github.io/"
    exit 0
  fi
  echo -n "."
  sleep 6
done
echo
echo "pushed, but the live page still differs after 4 minutes."
echo "Usually just a slow deploy — check https://guobapei.github.io/ in a moment."
