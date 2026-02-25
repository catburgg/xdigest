#!/bin/bash

# XDigest Scheduler Uninstallation Script

set -e

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/com.xdigest.scheduler.plist"

echo "=== XDigest Scheduler Uninstallation ==="
echo ""

# Unload the service
if launchctl list | grep -q "com.xdigest.scheduler"; then
    echo "Stopping scheduler..."
    launchctl unload "$INSTALLED_PLIST"
    echo "✓ Scheduler stopped"
else
    echo "Scheduler is not running"
fi

# Remove plist file
if [ -f "$INSTALLED_PLIST" ]; then
    echo "Removing configuration..."
    rm "$INSTALLED_PLIST"
    echo "✓ Configuration removed"
else
    echo "Configuration file not found"
fi

echo ""
echo "✓ Scheduler uninstalled successfully!"
echo ""
