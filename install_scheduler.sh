#!/bin/bash
# XDigest Scheduler Installation Script
# Installs launchd job to run XDigest at 7 AM and 7 PM daily

set -e

echo "==================================="
echo "XDigest Scheduler Installation"
echo "==================================="
echo ""

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"

# Get Python path from current environment
PYTHON_PATH=$(which python)
if [ -z "$PYTHON_PATH" ]; then
    echo "Error: Python not found. Please activate your conda environment first:"
    echo "  conda activate xdigest"
    exit 1
fi

echo "Using Python: $PYTHON_PATH"
echo "Project directory: $PROJECT_DIR"
echo ""

# Create a temporary plist with correct paths
PLIST_TEMPLATE="$PROJECT_DIR/scheduler/com.xdigest.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.xdigest.plist"

if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "Error: Template plist not found at $PLIST_TEMPLATE"
    exit 1
fi

# Replace paths in plist
echo "Creating launchd plist with your paths..."
sed -e "s|/opt/miniconda3/envs/xdigest/bin/python|$PYTHON_PATH|g" \
    -e "s|/Users/catburg/xdigest|$PROJECT_DIR|g" \
    -e "s|/Users/catburg/Library/Logs|$HOME/Library/Logs|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

echo "✓ Created plist at $PLIST_DEST"
echo ""

# Load the launchd job
echo "Loading launchd job..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "✓ Launchd job loaded"
echo ""

# Verify
if launchctl list | grep -q "com.xdigest"; then
    echo "✓ Installation successful!"
    echo ""
    echo "XDigest will now run automatically at:"
    echo "  - 7:00 AM daily"
    echo "  - 7:00 PM daily"
    echo ""
    echo "Logs will be written to:"
    echo "  - $HOME/Library/Logs/xdigest.log"
    echo "  - $HOME/Library/Logs/xdigest.error.log"
    echo ""
    echo "To uninstall:"
    echo "  launchctl unload $PLIST_DEST"
    echo "  rm $PLIST_DEST"
else
    echo "✗ Installation failed. Check the error messages above."
    exit 1
fi
