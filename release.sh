#!/usr/bin/env bash
# Release a new version of the Nucleares HA integration.
# Usage: ./release.sh 1.2.0
#
# This script:
#   1. Updates the version in manifest.json
#   2. Commits the change
#   3. Creates and pushes a git tag
#   4. GitHub Actions then creates the release automatically
#      (HACS will detect it within a few minutes)

set -euo pipefail

MANIFEST="custom_components/nucleares/manifest.json"

if [ -z "${1-}" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 1.2.0"
    exit 1
fi

VERSION="$1"
TAG="v${VERSION}"

# Basic semver check
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: Version must be in semver format (e.g. 1.2.0)"
    exit 1
fi

# Make sure we're on master and up to date
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "master" ]; then
    echo "ERROR: Must be on master branch (currently on $BRANCH)"
    exit 1
fi

git pull --ff-only

# Check tag doesn't already exist
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "ERROR: Tag $TAG already exists"
    exit 1
fi

echo ""
echo " Releasing version $VERSION..."
echo ""

# Update manifest.json
python3 - <<PYEOF
import json, sys
with open("$MANIFEST") as f:
    data = json.load(f)
data["version"] = "$VERSION"
with open("$MANIFEST", "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(f" Updated manifest.json version → $VERSION")
PYEOF

# Commit and tag
git add "$MANIFEST"
git commit -m "Release $TAG"
git tag "$TAG"
git push origin master "$TAG"

echo ""
echo " Tag $TAG pushed."
echo " GitHub Actions will create the release automatically."
echo " HACS will detect it within a few minutes."
echo ""
echo " Release URL:"
echo " https://github.com/tyler919/nucleares-ha-integration/releases/tag/$TAG"
echo ""
