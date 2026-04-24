import logging
import subprocess
from typing import Tuple
import time
import random

logger = logging.getLogger(__name__)


def execute_applescript(script: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            logger.error(f"AppleScript error: {result.stderr}")
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error("AppleScript execution timed out")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Failed to execute AppleScript: {e}")
        return False, str(e)


def execute_javascript_in_chrome(js_code: str) -> Tuple[bool, str]:
    escaped_js = js_code.replace("\\", "\\\\").replace('"', '\\"')
    script = f"""
    tell application "Google Chrome"
        tell active tab of front window
            execute javascript "{escaped_js}"
        end tell
    end tell
    """
    return execute_applescript(script)


def click_channel_avatar_and_wait():
    """
    Click on the channel avatar icon and wait for the channel page to render.
    Targets the specific DOM structure with ytSpecAvatarShapeAvatarSizeGiant class.
    """
    logger.info("Looking for channel avatar icon...")

    # Step 1: Find and click the channel avatar
    js_click_avatar = """
    (function() {
        // Look for the specific avatar container
        var avatarContainer = document.querySelector('.ytSpecAvatarShapeAvatarSizeGiant');
        if (!avatarContainer) {
            return 'Avatar container not found';
        }
        
        // Try to find a clickable parent element (link or button)
        var clickableElement = avatarContainer.closest('a') || avatarContainer.closest('button') || avatarContainer;
        
        if (!clickableElement) {
            return 'No clickable element found';
        }
        
        // Scroll into view and click
        clickableElement.scrollIntoView({behavior: 'smooth', block: 'center'});
        clickableElement.click();
        
        return 'Channel avatar clicked';
    })();
    """

    success, result = execute_javascript_in_chrome(js_click_avatar)
    if not success or "not found" in result:
        logger.error(f"Failed to click channel avatar: {result}")
        return False

    logger.info("Channel avatar clicked successfully")

    # Step 2: Wait for navigation and page load
    time.sleep(3)  # Allow navigation to start

    # Step 3: Wait for channel page to fully render
    max_wait = 15
    waited = 0
    page_loaded = False

    while waited < max_wait:
        js_check_page = """
        (function() {
            // Check for channel page indicators
            var channelHeader = document.querySelector('#channel-header') || 
                               document.querySelector('ytd-c4-tabbed-header-renderer') ||
                               document.querySelector('[role="banner"]');
            
            var channelContent = document.querySelector('#contents') ||
                                document.querySelector('ytd-section-list-renderer') ||
                                document.querySelector('#tabsContent');
            
            if (channelHeader && channelContent) {
                return 'channel_page_loaded';
            }
            
            return 'still_loading';
        })();
        """

        success, result = execute_javascript_in_chrome(js_check_page)
        if success and result == "channel_page_loaded":
            page_loaded = True
            break

        time.sleep(1)
        waited += 1

    if page_loaded:
        logger.info("Channel page loaded successfully")
        return True
    else:
        logger.error("Channel page failed to load within timeout")
        return False


# Example usage (for direct test/run)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    click_channel_avatar_and_wait()
