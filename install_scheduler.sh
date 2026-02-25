#!/bin/bash

# XDigest Scheduler Installation Script
# This script sets up automatic email delivery at 7 AM and 7 PM daily

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_FILE="$SCRIPT_DIR/com.xdigest.scheduler.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/com.xdigest.scheduler.plist"
LOG_DIR="$SCRIPT_DIR/logs"

echo "=== XDigest Scheduler Installation ==="
echo ""

# Create logs directory
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating logs directory..."
    mkdir -p "$LOG_DIR"
fi

# Create LaunchAgents directory if it doesn't exist
if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
    echo "Creating LaunchAgents directory..."
    mkdir -p "$LAUNCH_AGENTS_DIR"
fi

# Unload existing service if running
if launchctl list | grep -q "com.xdigest.scheduler"; then
    echo "Stopping existing scheduler..."
    launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
fi

# Copy plist file
echo "Installing scheduler configuration..."
cp "$PLIST_FILE" "$INSTALLED_PLIST"

# Load the service
echo "Starting scheduler..."
launchctl load "$INSTALLED_PLIST"

echo ""
echo "✓ Scheduler installed successfully!"
echo ""
echo "Schedule:"
echo "  - Every day at 7:00 AM"
echo "  - Every day at 7:00 PM (19:00)"
echo ""
echo "Logs location:"
echo "  - Output: $LOG_DIR/scheduler.log"
echo "  - Errors: $LOG_DIR/scheduler.error.log"
echo ""
echo "Useful commands:"
echo "  - Check status: launchctl list | grep xdigest"
echo "  - View logs: tail -f $LOG_DIR/scheduler.log"
echo "  - Uninstall: ./uninstall_scheduler.sh"
echo ""
