# news_bot/utils/file_manager.py

import json
import os
from datetime import datetime
from ..core import config # For DEFAULT_OUTPUT_DIR

def save_data_to_json(data_to_save: list | dict, base_filename: str, timestamp_in_filename: bool = True) -> str | None:
    """
    Saves the given data (list or dict) to a JSON file in the configured output directory.

    Args:
        data_to_save: The Python list or dictionary to save as JSON.
        base_filename: The base name for the output file (e.g., "news_reports").
        timestamp_in_filename: If True, appends a YYYY-MM-DD timestamp to the filename.

    Returns:
        The full path to the saved file, or None if saving failed.
    """
    try:
        output_dir = config.DEFAULT_OUTPUT_DIR
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        filename = base_filename
        if timestamp_in_filename:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            filename = f"{base_filename}_{timestamp}.json"
        else:
            filename = f"{base_filename}.json"
        
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully saved data to {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving data to JSON file '{filename}': {e}")
        # import traceback
        # traceback.print_exc()
        return None

if __name__ == '__main__':
    # This is for testing the module directly
    print("Testing File Manager Module...")

    # Path adjustments for direct execution
    import sys
    if '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]) not in sys.path:
         sys.path.insert(0, '..'.join(os.path.abspath(__file__).split(os.sep)[:-2]))
    
    from news_bot.core import config # Re-import for DEFAULT_OUTPUT_DIR
    config.validate_config() # This is just to ensure config loads, not strictly needed for file_manager test

    test_data_list = [
        {"id": 1, "name": "Test Item 1", "details": {"key": "value1"}},
        {"id": 2, "name": "Test Item 2", "details": {"key": "value2", "notes": "一些中文测试"}}
    ]
    test_data_dict = {
        "report_date": datetime.now().isoformat(),
        "source": "Test Suite",
        "items": test_data_list
    }

    print("\n--- Test 1: Saving list with timestamp ---")
    saved_path1 = save_data_to_json(test_data_list, "test_list_output")
    if saved_path1:
        print(f"List saved to: {saved_path1}")
        # You can optionally verify by reading it back:
        # with open(saved_path1, 'r', encoding='utf-8') as f_read:
        #     loaded_data = json.load(f_read)
        #     print(f"Verified by reading: {loaded_data == test_data_list}")

    print("\n--- Test 2: Saving dictionary without timestamp ---")
    saved_path2 = save_data_to_json(test_data_dict, "test_dict_output", timestamp_in_filename=False)
    if saved_path2:
        print(f"Dictionary saved to: {saved_path2}")

    print("\n--- Test 3: Attempting to save with a problematic path (simulated by permissions, not truly testable here) ---")
    # To truly test error, you might try writing to a read-only location, but that's environment-dependent.
    # We can simulate an error by temporarily overriding config.DEFAULT_OUTPUT_DIR if needed for deeper tests,
    # or rely on unit tests with mocking.
    original_dir = config.DEFAULT_OUTPUT_DIR
    try:
        config.DEFAULT_OUTPUT_DIR = "/hopefully_non_writable_path_for_test/some_dir" # Unlikely to exist/be writable
        print(f"Attempting to save to a non-existent/non-writable path: {config.DEFAULT_OUTPUT_DIR}")
        saved_path_error = save_data_to_json(test_data_dict, "error_test")
        if not saved_path_error:
            print("Correctly failed to save to problematic path (as expected).")
        else:
            print(f"Unexpectedly saved to {saved_path_error} - check test setup.")
    except Exception as e_test:
        print(f"Caught exception during error test setup or save: {e_test}")
    finally:
        config.DEFAULT_OUTPUT_DIR = original_dir # Restore original config

    print("\nFile Manager Module testing complete.") 