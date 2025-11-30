#!/usr/bin/env python3
"""
Test script to verify image generation works in threads (like Flask request handlers)

This tests the fix for "signal only works in main thread" error by:
1. Using asyncio.new_event_loop() instead of asyncio.run()
2. Disabling pyppeteer signal handlers (handleSIGINT/TERM/HUP=False)
"""
import threading
import sys
from pathlib import Path

def test_image_generation_in_thread():
    """Test that image generation works when called from a thread"""
    from news_bot.processing.image_generator import generate_image_from_article
    
    test_output = Path("test_output")
    test_output.mkdir(exist_ok=True)
    
    output_path = test_output / "test_thread_image.png"
    
    try:
        print(f"Testing image generation in thread: {threading.current_thread().name}")
        
        result = generate_image_from_article(
            title="测试标题 Test Title",
            content="这是一段测试内容。\n\nThis is test content for verifying that image generation works in threads.",
            output_path=str(output_path),
            page_width=540,
            device_scale=2,  # Lower scale for faster testing
        )
        
        if Path(result).exists():
            print(f"✅ SUCCESS: Image generated at {result}")
            print(f"   File size: {Path(result).stat().st_size} bytes")
            return True
        else:
            print(f"❌ FAILED: Image file not created at {result}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("Testing Image Generation in Thread (Flask scenario)")
    print("=" * 70)
    print()
    
    # Test 1: Main thread
    print("Test 1: Running in main thread...")
    success_main = test_image_generation_in_thread()
    print()
    
    # Test 2: Worker thread (simulates Flask request handler)
    print("Test 2: Running in worker thread (simulates Flask)...")
    success_thread = False
    
    def thread_target():
        nonlocal success_thread
        success_thread = test_image_generation_in_thread()
    
    worker = threading.Thread(target=thread_target, name="WorkerThread-1")
    worker.start()
    worker.join()
    print()
    
    # Summary
    print("=" * 70)
    print("Test Results:")
    print(f"  Main thread:   {'✅ PASS' if success_main else '❌ FAIL'}")
    print(f"  Worker thread: {'✅ PASS' if success_thread else '❌ FAIL'}")
    print("=" * 70)
    
    if success_main and success_thread:
        print("\n🎉 All tests passed! Image generation works in threads.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

