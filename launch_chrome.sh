#!/bin/bash
# Launch Chrome with remote debugging for XDigest

echo "Launching Chrome with remote debugging..."
echo "After Chrome opens, go to x.com and log in manually."
echo ""

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-xdigest" \
  > /dev/null 2>&1 &

echo "Chrome launched!"
echo "Chrome profile: $HOME/chrome-xdigest"
echo "Debug port: 9222"
echo ""
echo "Next steps:"
echo "1. Log into X in the Chrome window"
echo "2. Run: python main.py --use-chrome"
