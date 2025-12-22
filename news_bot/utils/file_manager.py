# news_bot/utils/file_manager.py

import json
import os
import logging
from datetime import datetime
from ..core import config

# Setup logging
logger = logging.getLogger('file_manager')

def save_data_to_json(data_to_save: list | dict, base_filename: str, timestamp_in_filename: bool = True) -> str | None:
    """
    Saves data to a JSON file in the configured output directory.
    """
    logger.info(f"[SAVE] Saving data to JSON: base_filename={base_filename}, timestamp={timestamp_in_filename}")
    logger.debug(f"[SAVE] Data type: {type(data_to_save)}, items: {len(data_to_save) if isinstance(data_to_save, list) else 'N/A'}")
    
    try:
        output_dir = config.DEFAULT_OUTPUT_DIR
        logger.debug(f"[SAVE] Output directory: {output_dir}")
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                logger.info(f"[SAVE] Created output directory: {output_dir}")
                print(f"Info: Created output directory: {output_dir}")
            except OSError as e_mkdir:
                logger.error(f"[SAVE] Failed to create output directory: {e_mkdir}")
                print(f"Error: Could not create output directory {output_dir}. {e_mkdir}")
                return None

        filename = base_filename
        if timestamp_in_filename:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S") 
            filename = f"{base_filename}_{timestamp}.json"
        else:
            filename = f"{base_filename}.json"
        
        filepath = os.path.join(output_dir, filename)
        logger.info(f"[SAVE] Writing to: {filepath}")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        # Verify file was written
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"[SAVE] ✅ Successfully saved: {filepath} ({file_size} bytes)")
        else:
            logger.error(f"[SAVE] File was not created: {filepath}")
        
        print(f"Successfully saved data to {filepath}")
        return filepath
    except Exception as e:
        # Catching the filename might be an issue if it's not defined due to an earlier error (e.g. makedirs failed)
        final_filename_for_error = filename if 'filename' in locals() else base_filename
        logger.error(f"[SAVE] Error saving to '{final_filename_for_error}': {e}")
        import traceback
        logger.error(f"[SAVE] Traceback: {traceback.format_exc()}")
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