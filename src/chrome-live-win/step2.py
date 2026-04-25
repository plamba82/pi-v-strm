import logging
import time
import pyautogui

logger = logging.getLogger(__name__)


# CHANGE: Configuration for absolute coordinates (adjust these for your screen)
AVATAR_COORDINATES = {
    # CHANGE: Default coordinates for 1920x1080 screen
    # Adjust these values based on where the live avatar appears on YOUR screen
    "x": 435,  # Horizontal position in pixels from left edge1320   
    "y": 400,  # Vertical position in pixels from top edge 695
}


def click_channel_avatar_and_wait():
    """
    Click on the live channel avatar using absolute screen coordinates.
    No image recognition or OCR - just direct coordinate clicking.
    """
    logger.info("Looking for live channel avatar using absolute coordinates...")

    try:
        # CHANGE: Step 1 - Wait for search results page to stabilize
        logger.info("Waiting for search results to load...")
        time.sleep(3)

        # CHANGE: Step 2 - Get configured coordinates
        avatar_x = AVATAR_COORDINATES["x"]
        avatar_y = AVATAR_COORDINATES["y"]
        
        logger.info(f"Using absolute coordinates: ({avatar_x}, {avatar_y})")

        # CHANGE: Step 3 - Move mouse to position and click
        logger.info(f"Moving mouse to avatar position...")
        pyautogui.moveTo(avatar_x, avatar_y, duration=0.5)
        time.sleep(0.3)
        
        logger.info(f"Clicking avatar at ({avatar_x}, {avatar_y})")
        pyautogui.click()
        
        logger.info("Avatar clicked successfully")

        # CHANGE: Step 4 - Wait for navigation to live stream page
        time.sleep(3)
        logger.info("Waiting for live stream page to load...")
        time.sleep(5)

        logger.info("Live stream page loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to click live avatar: {e}")
        return False


# CHANGE: Helper function to find the correct coordinates interactively
def find_avatar_coordinates():
    """
    Interactive helper to find the correct avatar coordinates for your screen.
    Run this once to determine the coordinates, then update AVATAR_COORDINATES.
    """
    print("\n" + "="*60)
    print("AVATAR COORDINATE FINDER")
    print("="*60)
    print("\nInstructions:")
    print("1. Navigate to YouTube search results showing a LIVE channel")
    print("2. Move your mouse EXACTLY over the live avatar (red ring)")
    print("3. Press ENTER when positioned correctly")
    print("\nWaiting for you to position the mouse...")
    
    input()
    
    # CHANGE: Get current mouse position
    x, y = pyautogui.position()
    
    print("\n" + "="*60)
    print(f"✅ Avatar coordinates found: ({x}, {y})")
    print("="*60)
    print("\nUpdate your step2.py file with these values:")
    print(f'\nAVATAR_COORDINATES = {{')
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
def click_avatar_by_percentage(x_percent=0.15, y_percent=0.30):
    """
    Click avatar using percentage of screen dimensions.
    More portable across different screen resolutions.
    
    Args:
        x_percent: Horizontal position as percentage of screen width (0.0 to 1.0)
        y_percent: Vertical position as percentage of screen height (0.0 to 1.0)
    """
    try:
        # CHANGE: Get scre  en dimensions
        screen_width, screen_height = pyautogui.size()
        
        # CHANGE: Calculate absolute coordinates from percentages
        avatar_x = int(screen_width * x_percent)
        avatar_y = int(screen_height * y_percent)
        
        logger.info(f"Screen size: {screen_width}x{screen_height}")
        logger.info(f"Calculated coordinates: ({avatar_x}, {avatar_y}) from {x_percent*100}%, {y_percent*100}%")
        
        # CHANGE: Click at calculated position
        pyautogui.moveTo(avatar_x, avatar_y, duration=0.5)
        time.sleep(0.3)
        pyautogui.click()
        
        logger.info("Avatar clicked successfully using percentage-based coordinates")
        return True
        
    except Exception as e:
        logger.error(f"Failed to click avatar: {e}")
        return False


# Example usage (for direct test/run)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # CHANGE: Uncomment to find coordinates interactively
    # find_avatar_coordinates()
    
    # CHANGE: Test the configured coordinates
    click_channel_avatar_and_wait()