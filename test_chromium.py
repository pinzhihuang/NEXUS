#!/usr/bin/env python3
"""
Quick test script to verify Chromium detection
Run this before deploying to Railway to test the detection logic
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_chromium_detection():
    """Test if Chromium can be detected"""
    print("=" * 70)
    print("🔍 Chromium Detection Test")
    print("=" * 70)
    
    # Import after path is set
    from news_bot.processing.image_generator import _guess_chrome_path
    
    print("\n1. Checking environment variables...")
    for key in ("PUPPETEER_EXECUTABLE_PATH", "PYPPETEER_EXECUTABLE_PATH", "CHROME_PATH"):
        val = os.environ.get(key)
        if val:
            print(f"   ✅ {key} = {val}")
        else:
            print(f"   ⚠️  {key} not set")
    
    print("\n2. Running _guess_chrome_path()...")
    print("-" * 70)
    chrome_path = _guess_chrome_path()
    print("-" * 70)
    
    if chrome_path:
        print(f"\n✅ SUCCESS: Found Chromium at: {chrome_path}")
        
        # Try to run it
        print("\n3. Testing Chromium execution...")
        try:
            import subprocess
            result = subprocess.run(
                [chrome_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"   ✅ {result.stdout.strip()}")
            else:
                print(f"   ❌ Exit code: {result.returncode}")
                print(f"   Stderr: {result.stderr}")
        except Exception as e:
            print(f"   ❌ Error running Chromium: {e}")
    else:
        print("\n❌ FAILED: Could not find Chromium")
        print("\nSuggestions:")
        print("   • Install Chromium: apt-get install chromium-browser (Linux)")
        print("   • Install Chrome: https://www.google.com/chrome/ (Windows/Mac)")
        print("   • Set PUPPETEER_EXECUTABLE_PATH env var manually")
    
    print("\n" + "=" * 70)
    return chrome_path is not None

if __name__ == "__main__":
    success = test_chromium_detection()
    sys.exit(0 if success else 1)

