#!/bin/bash
# Updates app.kubernetes.io/version labels in all k8s manifests
# from the VERSION file at the repository root.
#
# Usage: ./set-version.sh [version]
#   If no version argument is given, reads from ../VERSION

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "$1" ]; then
    VERSION="$1"
elif [ -f "$REPO_ROOT/VERSION" ]; then
    VERSION="$(cat "$REPO_ROOT/VERSION" | tr -d '[:space:]')"
else
    echo "ERROR: VERSION file not found at $REPO_ROOT/VERSION and no version argument provided."
    exit 1
fi

echo "Setting Kubernetes manifest versions to: $VERSION"

# Update all YAML files in k8s/ (including enterprise/ subdirectory)
find "$SCRIPT_DIR" -name '*.yaml' -o -name '*.yml' | while read -r file; do
    if grep -q 'app.kubernetes.io/version:' "$file" 2>/dev/null; then
        sed -i "s|app.kubernetes.io/version: \"[^\"]*\"|app.kubernetes.io/version: \"${VERSION}\"|g" "$file"
        echo "  Updated: $(basename "$file")"
    fi
done

echo "Done. All manifests updated to version $VERSION."
