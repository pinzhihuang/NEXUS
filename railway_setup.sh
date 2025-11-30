#!/bin/bash
# Railway setup script - finds and exports Chromium path

echo "🔍 Railway Chromium Setup"
echo "=========================="

# Try to find Chromium
CHROMIUM_PATH=""

# Method 1: Check which command
if command -v chromium &> /dev/null; then
    CHROMIUM_PATH=$(which chromium)
    echo "✅ Found via 'which chromium': $CHROMIUM_PATH"
elif command -v chromium-browser &> /dev/null; then
    CHROMIUM_PATH=$(which chromium-browser)
    echo "✅ Found via 'which chromium-browser': $CHROMIUM_PATH"
fi

# Method 2: Check Nix store (Railway/Nixpacks)
if [ -z "$CHROMIUM_PATH" ]; then
    NIX_CHROMIUM=$(find /nix/store -name chromium -type f -executable 2>/dev/null | grep "/bin/chromium" | head -n 1)
    if [ -n "$NIX_CHROMIUM" ]; then
        CHROMIUM_PATH="$NIX_CHROMIUM"
        echo "✅ Found in Nix store: $CHROMIUM_PATH"
    fi
fi

# Method 3: Check standard locations
if [ -z "$CHROMIUM_PATH" ]; then
    for path in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome; do
        if [ -f "$path" ]; then
            CHROMIUM_PATH="$path"
            echo "✅ Found at standard location: $CHROMIUM_PATH"
            break
        fi
    done
fi

# Export if found
if [ -n "$CHROMIUM_PATH" ]; then
    export PUPPETEER_EXECUTABLE_PATH="$CHROMIUM_PATH"
    echo "✅ Exported PUPPETEER_EXECUTABLE_PATH=$CHROMIUM_PATH"
    
    # Test if it works
    if $CHROMIUM_PATH --version &> /dev/null; then
        VERSION=$($CHROMIUM_PATH --version)
        echo "✅ Chromium is working: $VERSION"
    else
        echo "⚠️  WARNING: Chromium found but --version failed"
    fi
else
    echo "❌ ERROR: Chromium not found!"
    echo "Available executables in PATH:"
    echo "$PATH" | tr ':' '\n' | while read dir; do
        if [ -d "$dir" ]; then
            ls -la "$dir" 2>/dev/null | grep -i chrom || true
        fi
    done
fi

echo "=========================="

