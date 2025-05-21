# news_bot/utils/file_manager.py

import json
import os
from datetime import datetime
from ..core import config

def save_data_to_json(data_to_save: list | dict, base_filename: str, timestamp_in_filename: bool = True) -> str | None:
    """
    Saves data to a JSON file in the configured output directory.
    """
    try:
        output_dir = config.DEFAULT_OUTPUT_DIR
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Info: Created output directory: {output_dir}")
            except OSError as e_mkdir:
                print(f"Error: Could not create output directory {output_dir}. {e_mkdir}")
                return None

        filename = base_filename
        if timestamp_in_filename:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S") 
            filename = f"{base_filename}_{timestamp}.json"
        else:
            filename = f"{base_filename}.json"
        
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2) # Changed indent to 2 for slightly less verbose files
        
        print(f"Successfully saved data to {filepath}")
        return filepath
    except Exception as e:
        # Catching the filename might be an issue if it's not defined due to an earlier error (e.g. makedirs failed)
        final_filename_for_error = filename if 'filename' in locals() else base_filename
        print(f"Error saving data to JSON file '{final_filename_for_error}': {e}")
        return None

if __name__ == '__main__':
    print("Testing File Manager Module...")
    import sys
    PROJECT_ROOT_FOR_TEST = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT_FOR_TEST not in sys.path:
         sys.path.insert(0, PROJECT_ROOT_FOR_TEST)
    
    from news_bot.core import config 
    # No need to validate_config() here as file_manager is independent of API keys for basic saving

    test_data_list = [
        {"id": 1, "name": "Test Item 1", "details": {"key": "value1"}},
        {"id": 2, "name": "Test Item 2", "details": {"key": "value2", "notes": "一些中文测试"}}
    ]

    print("\n--- Test 1: Saving list with timestamp ---")
    save_data_to_json(test_data_list, "test_output_list")

    print("\n--- Test 2: Saving dict without timestamp ---")
    save_data_to_json({"data": test_data_list, "count": len(test_data_list)}, "test_output_dict", timestamp_in_filename=False)

    print("\nFile Manager Module testing complete.") 