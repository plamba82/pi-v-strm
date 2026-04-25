import logging
import time
import random

# CHANGE: Import pyautogui for keyboard/mouse automation on Windows
import pyautogui

logger = logging.getLogger(__name__)

# CHANGE: Configuration for absolute coordinates (adjust these for your screen)
CHANNEL_RESULT_COORDINATES = {
    # CHANGE: Default coordinates for 1920x1080 screen
    # Adjust these values based on where the first channel result appears on YOUR screen
    "x": 625,  # Horizontal position in pixels from left edge
    "y": 210,  # Vertical position in pixels from top edge
}


# CHANGE: Modified to use pyautogui for typing instead of AppleScript
def type_like_human(text: str, lock=None, profile_index=0) -> bool:
    logger.info(f"Typing '{text}' character by character...")

    # CHANGE: Acquire lock only during typing operation
    if lock:
        logger.info(f"[Profile-{profile_index + 1}] 🔒 Waiting for typing lock...")
        lock.acquire()
        logger.info(f"[Profile-{profile_index + 1}] ✅ Acquired typing lock")

    try:
        # CHANGE: Use pyautogui to type each character
        for char in text:
            pyautogui.write(char, interval=random.uniform(0.04, 0.14))
            
            # CHANGE: Random pauses for human-like typing
            if random.random() < 0.15:
                time.sleep(random.uniform(0.2, 0.6))
                
        logger.info(f"Finished typing: {text}")
        return True
    except Exception as e:
        logger.error(f"Failed to type text: {e}")
        return False
    finally:
        # CHANGE: Release lock immediately after typing completes
        if lock:
            lock.release()
            logger.info(f"[Profile-{profile_index + 1}] 🔓 Released typing lock")


# CHANGE: New wrapper function that uses absolute coordinates for Step 5
def search_and_click_first_channel_with_lock(
    lock=None, profile_index=0, search_term="@bhaktisangeetplus channel"
):
    """
    1. Focuses YouTube search box, types the search term as a human, submits.
    2. Waits for search results to load.
    3. Clicks the first channel result using absolute screen coordinates.
    """
    logger.info(f"Searching for: {search_term}")

    try:
        # CHANGE: Step 1 - Click on search box using keyboard shortcut
        # YouTube search shortcut: / key
        pyautogui.press('/')
        time.sleep(0.5) 
        
        # CHANGE: Step 2 - Type search term with lock (ONLY typing is locked)
        if not type_like_human(search_term, lock, profile_index):
            logger.error("Failed to type search term.")
            return False
        time.sleep(0.5)

        # CHANGE: Step 3 - Submit search by pressing Enter
        pyautogui.press('enter')
        logger.info("Submitted search.")
        time.sleep(3)

        # CHANGE: Step 4 - Wait for search results to load
        logger.info("Waiting for search results to load...")
        time.sleep(5)

        # CHANGE: Step 5 - Use absolute coordinates to click first channel result
        channel_x = CHANNEL_RESULT_COORDINATES["x"]
        channel_y = CHANNEL_RESULT_COORDINATES["y"]
        
        logger.info(f"Using absolute coordinates: ({channel_x}, {channel_y})")
        
        # CHANGE: Move mouse to position and click
        logger.info(f"Moving mouse to channel result position...")
        pyautogui.moveTo(channel_x, channel_y, duration=0.5)
        time.sleep(0.3)
        
        logger.info(f"Clicking channel result at ({channel_x}, {channel_y})")
        pyautogui.click()
        
        logger.info("Clicked first channel search result.")
        time.sleep(2)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in search and click: {e}")
        return False


# CHANGE: Helper function to find the correct coordinates interactively
def find_channel_result_coordinates():
    """
    Interactive helper to find the correct channel result coordinates for your screen.
    Run this once to determine the coordinates, then update CHANNEL_RESULT_COORDINATES.
    """
    print("\n" + "="*60)
    print("CHANNEL RESULT COORDINATE FINDER")
    print("="*60)
    print("\nInstructions:")
    print("1. Navigate to YouTube search results showing the target channel")
    print("2. Move your mouse EXACTLY over the first channel result (avatar or name)")
    print("3. Press ENTER when positioned correctly")
    print("\nWaiting for you to position the mouse...")
    
    input()
    
    # CHANGE: Get current mouse position
    x, y = pyautogui.position()
    
    print("\n" + "="*60)
    print(f"✅ Channel result coordinates found: ({x}, {y})")
    print("="*60)
    print("\nUpdate your step1.py file with these values:")
    print(f'\nCHANNEL_RESULT_COORDINATES = {{')
    print(f'    "x": {x},')
    print(f'    "y": {y},')
    print(f'}}')
    print("\n" + "="*60)
    
    # CHANGE: Verify by clicking
    verify = input("\nDo you want to test-click this position? (y/n): ")
    if verify.lower() == 'y':
        print(f"Moving to ({x}, {y}) and clicking in 3 seconds...")
        time.sleep(3)
        pyautogui.click(x, y)
        print("✅ Test click executed")
    
    return x, y


# CHANGE: Alternative function with percentage-based coordinates (more portable)
def click_channel_by_percentage(x_percent=0.22, y_percent=0.32):
    """
    Click channel result using percentage of screen dimensions.
    More portable across different screen resolutions.
    
    Args:
        x_percent: Horizontal position as percentage of screen width (0.0 to 1.0)
        y_percent: Vertical position as percentage of screen height (0.0 to 1.0)
    """
    try:
        # CHANGE: Get screen dimensions
        screen_width, screen_height = pyautogui.size()
        
        # CHANGE: Calculate absolute coordinates from percentages
        channel_x = int(screen_width * x_percent)
        channel_y = int(screen_height * y_percent)
        
        logger.info(f"Screen size: {screen_width}x{screen_height}")
        logger.info(f"Calculated coordinates: ({channel_x}, {channel_y}) from {x_percent*100}%, {y_percent*100}%")
        
        # CHANGE: Click at calculated position
        pyautogui.moveTo(channel_x, channel_y, duration=0.5)
        time.sleep(0.3)
        pyautogui.click()
        
        logger.info("Channel result clicked successfully using percentage-based coordinates")
        return True
        
    except Exception as e:
        logger.error(f"Failed to click channel result: {e}")
        return False


# CHANGE: Keep original function for backward compatibility
def search_and_click_first_channel(search_term="@bhaktisangeetplus channel"):
    return search_and_click_first_channel_with_lock(None, 0, search_term)


# Example usage (for direct test/run)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # CHANGE: Uncomment to find coordinates interactively
    # find_channel_result_coordinates()
    
    # CHANGE: Test the configured coordinates
    search_and_click_first_channel()