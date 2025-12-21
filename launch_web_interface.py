#!/usr/bin/env python3
"""
Demo launcher for Project NEXUS Web Interface
This script starts the Flask server with helpful output
"""

import os
import sys
import webbrowser
import time
from threading import Timer

def check_requirements():
    """Check if all requirements are met"""
    issues = []
    
    # Check Flask
    try:
        import flask
        print(f"✅ Flask {flask.__version__} is installed")
    except ImportError:
        issues.append("Flask is not installed. Run: pip install Flask")
    
    # Check .env file
    if not os.path.exists('.env'):
        print("⚠️  .env file not found (news collection will fail without API key)")
    else:
        print("✅ .env file found")
    
    # Check templates
    if not os.path.exists('templates/index.html'):
        issues.append("templates/index.html not found")
    else:
        print("✅ templates/index.html found")
    
    # Check app.py
    if not os.path.exists('app.py'):
        issues.append("app.py not found")
    else:
        print("✅ app.py found")
    
    return issues

def open_browser():
    """Open browser after a short delay"""
    url = "http://127.0.0.1:5000"
    print(f"\n🌐 Opening browser to {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"   Please open {url} manually")

def main():
    print("=" * 70)
    print("🚀 Project NEXUS - Web Interface Launcher")
    print("=" * 70)
    print()
    
    # Check requirements
    print("📋 Checking requirements...")
    issues = check_requirements()
    
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\nPlease fix these issues before starting.")
        sys.exit(1)
    
    print("\n✅ All checks passed!")
    print()
    print("=" * 70)
    print("Starting Flask web server...")
    print("=" * 70)
    print()
    print("📊 Dashboard: http://127.0.0.1:5000")
    print("📁 Reports:   news_reports/")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    # Open browser after 2 seconds
    Timer(2.0, open_browser).start()
    
    # Start Flask app
    try:
        from app import app
        app.run(debug=True, threaded=True, port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTry running directly: python app.py")
        sys.exit(1)

if __name__ == '__main__':
    main()

