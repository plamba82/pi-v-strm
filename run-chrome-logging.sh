#!/usr/bin/env bash
# Replace /path/to/... with the path you found above.
CHROME_BIN="/path/to/Google Chrome for Testing"
if [ ! -x "$CHROME_BIN" ]; then
    echo "Set CHROME_BIN to the actual binary path found from previous step"
    exit 1
fi

# Run headful once with logging; this prints stdout/stderr and remote debugging listening port.
"$CHROME_BIN" \
    --remote-debugging-port=9222 \
    --enable-logging=stderr \
    --v=1 \
    --no-first-run \
    --disable-gpu \
    --no-sandbox 2>&1 | tee chrome_for_testing.log