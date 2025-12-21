#!/bin/bash
# Railway build verification script
# This runs during the build phase to verify Chromium installation

echo "=================================================="
echo "🔍 RAILWAY BUILD VERIFICATION"
echo "=================================================="

echo ""
echo "1. Current working directory:"
pwd

echo ""
echo "2. Build system detection:"
if [ -d "/nix/store" ]; then
    echo "   ✅ /nix/store EXISTS - Using Nixpacks"
    echo "   Listing /nix/store (first 20 entries):"
    ls -la /nix/store/ 2>/dev/null | head -20
else
    echo "   ❌ /nix/store DOES NOT EXIST - Using Docker or other builder"
fi

echo ""
echo "3. Checking for Chromium in various locations:"

# Check standard apt locations
for path in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome; do
    if [ -f "$path" ]; then
        echo "   ✅ Found: $path"
        $path --version 2>&1 | head -1 || echo "      (--version failed)"
    else
        echo "   ❌ Not found: $path"
    fi
done

# Check Nix store
echo ""
echo "4. Searching Nix store for chromium:"
if [ -d "/nix/store" ]; then
    find /nix/store -name chromium -type f 2>/dev/null | head -5 || echo "   find command failed or no results"
else
    echo "   Skipped - /nix/store doesn't exist"
fi

# Check which command
echo ""
echo "5. Checking 'which' command:"
which chromium 2>/dev/null && echo "   ✅ which chromium: $(which chromium)" || echo "   ❌ which chromium: not found"
which chromium-browser 2>/dev/null && echo "   ✅ which chromium-browser: $(which chromium-browser)" || echo "   ❌ which chromium-browser: not found"

echo ""
echo "6. Environment PATH:"
echo "   $PATH"

echo ""
echo "7. Checking nixpacks.toml existence:"
if [ -f "nixpacks.toml" ]; then
    echo "   ✅ nixpacks.toml exists"
    echo "   Contents:"
    cat nixpacks.toml | head -20
else
    echo "   ❌ nixpacks.toml NOT FOUND"
fi

echo ""
echo "8. Checking Dockerfile existence:"
if [ -f "Dockerfile" ]; then
    echo "   ⚠️  Dockerfile EXISTS - Railway might use this instead of nixpacks!"
    ls -la Dockerfile
else
    echo "   ✅ Dockerfile does not exist - should use nixpacks.toml"
fi

echo ""
echo "=================================================="
echo "✅ Build verification complete"
echo "=================================================="

