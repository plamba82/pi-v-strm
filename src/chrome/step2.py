import time
import logging
import subprocess
from typing import Tuple

# Configure logger for this module
logger = logging.getLogger(__name__)


def execute_applescript(script: str) -> Tuple[bool, str]:
    """
    Execute an AppleScript and return the result.

    Args:
        script: AppleScript code to execute

    Returns:
        Tuple of (success: bool, output: str)
    """
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
    """
    Execute JavaScript in the active Chrome tab.

    Args:
        js_code: JavaScript code to execute

    Returns:
        Tuple of (success: bool, result: str)
    """
    # Escape quotes in JavaScript code for AppleScript
    escaped_js = js_code.replace("\\", "\\\\").replace('"', '\\"')

    script = f"""
    tell application "Google Chrome"
        tell active tab of front window
            execute javascript "{escaped_js}"
        end tell
    end tell
    """

    success, output = execute_applescript(script)
    if success:
        logger.info(f"JavaScript executed successfully. Result: {output[:100]}")
    else:
        logger.error(f"JavaScript execution failed: {output}")
    return success, output


def click_like_button() -> bool:
    """
    Click the like button on the currently playing Short.
    Waits for the button to be visible before clicking.

    Returns:
        True if like button was clicked successfully, False otherwise
    """
    logger.info("Step 4: Waiting for like button to be visible...")

    # Wait for like button to be visible before clicking
    max_wait_time = 10  # Wait up to 10 seconds for button to appear
    check_interval = 0.5
    elapsed_time = 0

    js_wait_for_button = """
    (function() {
        // Try multiple selector strategies
        var likeButton = null;
        
        // Strategy 1: Find by aria-label containing "Like this video"
        var buttons = document.querySelectorAll('button[aria-label*="Like this video"]');
        if (buttons.length > 0) {
            likeButton = buttons[0];
        }
        
        // Strategy 2: Find by class combination
        if (!likeButton) {
            var classButtons = document.querySelectorAll('button.ytSpecButtonShapeNextHost.ytSpecButtonShapeNextTonal.ytSpecButtonShapeNextIconButton');
            for (var i = 0; i < classButtons.length; i++) {
                var ariaLabel = classButtons[i].getAttribute('aria-label');
                if (ariaLabel && ariaLabel.toLowerCase().includes('like')) {
                    likeButton = classButtons[i];
                    break;
                }
            }
        }
        
        // Strategy 3: Find by SVG path (thumbs up icon)
        if (!likeButton) {
            var svgPaths = document.querySelectorAll('button svg path[d*="M9.221"]');
            if (svgPaths.length > 0) {
                var svgButton = svgPaths[0].closest('button');
                if (svgButton) {
                    likeButton = svgButton;
                }
            }
        }
        
        if (!likeButton) {
            return 'not_found';
        }
        
        // Check if button is visible in viewport
        var rect = likeButton.getBoundingClientRect();
        var isVisible = rect.top >= 0 && 
                       rect.left >= 0 && 
                       rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && 
                       rect.right <= (window.innerWidth || document.documentElement.clientWidth) &&
                       window.getComputedStyle(likeButton).visibility !== 'hidden' &&
                       window.getComputedStyle(likeButton).display !== 'none';
        
        if (!isVisible) {
            return 'not_visible';
        }
        
        return 'visible';
    })();
    """

    # Poll until button is visible
    while elapsed_time < max_wait_time:
        success, result = execute_javascript_in_chrome(js_wait_for_button)

        if success and result == "visible":
            logger.info("Like button is visible, proceeding to click")
            break

        if result == "not_found":
            logger.debug(f"Like button not found yet ({elapsed_time}s elapsed)")
        elif result == "not_visible":
            logger.debug(
                f"Like button found but not visible yet ({elapsed_time}s elapsed)"
            )

        time.sleep(check_interval)
        elapsed_time += check_interval

    if elapsed_time >= max_wait_time:
        logger.error("Like button did not become visible within timeout")
        return False

    # CHANGE: Click the button and verify state change in separate executions (no Promise)
    js_click_like = """
    (function() {
        // Try multiple selector strategies
        var likeButton = null;
        
        // Strategy 1: Find by aria-label containing "Like this video"
        var buttons = document.querySelectorAll('button[aria-label*="Like this video"]');
        if (buttons.length > 0) {
            likeButton = buttons[0];
            console.log('Found like button using aria-label');
        }
        
        // Strategy 2: Find by class combination
        if (!likeButton) {
            var classButtons = document.querySelectorAll('button.ytSpecButtonShapeNextHost.ytSpecButtonShapeNextTonal.ytSpecButtonShapeNextIconButton');
            for (var i = 0; i < classButtons.length; i++) {
                var ariaLabel = classButtons[i].getAttribute('aria-label');
                if (ariaLabel && ariaLabel.toLowerCase().includes('like')) {
                    likeButton = classButtons[i];
                    console.log('Found like button using class combination');
                    break;
                }
            }
        }
        
        // Strategy 3: Find by SVG path (thumbs up icon)
        if (!likeButton) {
            var svgPaths = document.querySelectorAll('button svg path[d*="M9.221"]');
            if (svgPaths.length > 0) {
                var svgButton = svgPaths[0].closest('button');
                if (svgButton) {
                    likeButton = svgButton;
                    console.log('Found like button using SVG path');
                }
            }
        }
        
        if (!likeButton) {
            return 'Like button not found';
        }
        
        // Check if already liked (aria-pressed="true")
        var isPressed = likeButton.getAttribute('aria-pressed');
        if (isPressed === 'true') {
            return 'Video already liked';
        }
        
        // Try multiple click strategies to ensure the click registers
        var clickSuccess = false;
        
        // Method 1: Standard click
        try {
            likeButton.click();
            clickSuccess = true;
            console.log('Standard click executed');
        } catch (e) {
            console.log('Standard click failed: ' + e.message);
        }
        
        // Method 2: Dispatch click event (handles shadow DOM and event listeners)
        if (!clickSuccess) {
            try {
                var clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                likeButton.dispatchEvent(clickEvent);
                clickSuccess = true;
                console.log('Event dispatch click executed');
            } catch (e) {
                console.log('Event dispatch failed: ' + e.message);
            }
        }
        
        // Method 3: Coordinate-based click (simulates actual user click)
        if (!clickSuccess) {
            try {
                var rect = likeButton.getBoundingClientRect();
                var x = rect.left + rect.width / 2;
                var y = rect.top + rect.height / 2;
                
                var mousedownEvent = new MouseEvent('mousedown', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y
                });
                var mouseupEvent = new MouseEvent('mouseup', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y
                });
                
                likeButton.dispatchEvent(mousedownEvent);
                likeButton.dispatchEvent(mouseupEvent);
                likeButton.click();
                clickSuccess = true;
                console.log('Coordinate-based click executed');
            } catch (e) {
                console.log('Coordinate click failed: ' + e.message);
            }
        }
        
        if (!clickSuccess) {
            return 'All click methods failed';
        }
        
        // CHANGE: Return synchronously instead of using Promise
        return 'Click executed';
    })();
    """

    success, result = execute_javascript_in_chrome(js_click_like)
    if not success or "not found" in result or "failed" in result:
        logger.error(f"Failed to click like button: {result}")
        return False

    logger.info(f"Like button clicked: {result}")

    # CHANGE: Wait for UI to update, then verify state change in a separate call
    time.sleep(1)

    # CHANGE: Verify the button state changed (separate JavaScript execution)
    js_verify_state = """
    (function() {
        var buttons = document.querySelectorAll('button[aria-label*="Like this video"]');
        if (buttons.length > 0) {
            var isPressed = buttons[0].getAttribute('aria-pressed');
            if (isPressed === 'true') {
                return 'Like button state changed to pressed';
            } else {
                return 'Like button state did not change (aria-pressed=' + isPressed + ')';
            }
        }
        return 'Like button not found for verification';
    })();
    """

    success, verify_result = execute_javascript_in_chrome(js_verify_state)
    if success:
        logger.info(f"Verification: {verify_result}")
    else:
        logger.warning("Could not verify like button state change")

    # 1 second delay after action
    time.sleep(1)

    return True


def find_and_click_first_short() -> bool:
    """
    Find the Shorts grid section and click on the first Short.
    Targets the ytGridShelfViewModelGridShelfRow structure.

    Returns:
        True if successful, False otherwise
    """
    logger.info("Step 1: Looking for Shorts grid section...")

    # Wait for search results to fully load
    time.sleep(2)

    # CHANGE: Updated to select the SECOND grid row instead of the first
    js_find_shorts_grid = """
    (function() {
        // Find ALL grid shelf rows containing Shorts
        var gridRows = document.querySelectorAll('.ytGridShelfViewModelGridShelfRow.ytd-item-section-renderer');
        
        // CHANGE: Check if at least 2 grid rows exist
        if (gridRows.length < 2) {
            // Fallback: try finding by the grid item class
            var gridItems = document.querySelectorAll('.ytGridShelfViewModelGridShelfItem');
            if (gridItems.length >= 2 && gridItems[1].parentElement) {
                var gridRow = gridItems[1].parentElement;
                gridRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return 'found';
            }
            return 'not_found';
        }
        
        // CHANGE: Select the SECOND grid row (index 1)
        var gridRow = gridRows[1];
        
        // Scroll into view
        gridRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return 'found';
    })();
    """

    max_attempts = 3
    shorts_found = False

    for attempt in range(max_attempts):
        success, result = execute_javascript_in_chrome(js_find_shorts_grid)
        if success and result == "found":
            logger.info("Shorts grid section found (second row)")
            shorts_found = True
            break

        wait_time = 2 * (attempt + 1)
        logger.warning(
            f"Shorts grid not found (attempt {attempt + 1}/{max_attempts}), waiting {wait_time}s..."
        )
        time.sleep(wait_time)

    if not shorts_found:
        logger.error("Failed to locate Shorts grid section after all attempts")
        return False

    # 1 second delay after scrolling
    time.sleep(1)

    # Step 2: Click on the first Short from the grid
    logger.info("Step 2: Clicking on the first Short from grid...")

    # CHANGE: Updated to target the SECOND grid row
    js_click_first_short = """
    (function() {
        // Find ALL grid rows
        var gridRows = document.querySelectorAll('.ytGridShelfViewModelGridShelfRow.ytd-item-section-renderer');
        
        var gridRow = null;
        
        // CHANGE: Select the SECOND grid row if it exists
        if (gridRows.length >= 2) {
            gridRow = gridRows[1];
        } else {
            // Fallback: try finding by the grid item class
            var gridItems = document.querySelectorAll('.ytGridShelfViewModelGridShelfItem');
            if (gridItems.length >= 2 && gridItems[1].parentElement) {
                gridRow = gridItems[1].parentElement;
            }
        }
        
        if (!gridRow) {
            return 'Grid row not found';
        }
        
        // Find the first grid item within the SECOND row
        var firstGridItem = gridRow.querySelector('.ytGridShelfViewModelGridShelfItem:first-of-type');
        
        if (!firstGridItem) {
            return 'First grid item not found';
        }
        
        // Find the clickable link within the first item
        var firstShortLink = firstGridItem.querySelector('ytm-shorts-lockup-view-model-v2 a.shortsLockupViewModelHostEndpoint[href^="/shorts/"]') ||
                            firstGridItem.querySelector('ytm-shorts-lockup-view-model a.shortsLockupViewModelHostEndpoint[href^="/shorts/"]') ||
                            firstGridItem.querySelector('a[href^="/shorts/"]');
        
        if (!firstShortLink) {
            return 'First Short link not found in grid item';
        }
        
        // Get the Short URL for logging
        var shortUrl = firstShortLink.href;
        
        // Click the link
        firstShortLink.click();
        
        return 'Clicked first Short from grid: ' + shortUrl;
    })();
    """

    success, result = execute_javascript_in_chrome(js_click_first_short)
    if not success or "not found" in result:
        logger.error("Failed to click first Short from grid")
        return False

    logger.info(f"First Short clicked: {result}")

    # 1 second delay after click
    time.sleep(1)

    # Step 3: Wait for Short page to load (just URL change, not full video load)
    logger.info("Step 3: Waiting for Short page to load...")

    max_wait_time = 10
    check_interval = 0.5
    elapsed_time = 0

    js_check_short_loaded = """
    (function() {
        // Check if we're on a Shorts page
        var isShorts = window.location.pathname.includes('/shorts/');
        if (!isShorts) {
            return 'Not on Shorts page yet';
        }
        
        // Only check if video player exists, not if it's fully loaded
        var videoPlayer = document.querySelector('video.html5-main-video') || 
                         document.querySelector('video');
        if (!videoPlayer) {
            return 'Video player not found';
        }
        
        return 'Short page loaded';
    })();
    """

    while elapsed_time < max_wait_time:
        success, result = execute_javascript_in_chrome(js_check_short_loaded)

        if success and "Short page loaded" in result:
            logger.info(f"Short page loaded successfully: {result}")

            # Click like button after Short page loads (not after video loads)
            click_like_button()

            return True

        time.sleep(check_interval)
        elapsed_time += check_interval
        logger.debug(
            f"Waiting for Short page to load... ({elapsed_time}s elapsed) - Status: {result}"
        )

    logger.warning(f"Short page did not load within {max_wait_time} seconds")
    return False


def get_short_info() -> dict:
    """
    Get information about the currently playing Short.
    Works for both desktop and mobile YouTube.

    Returns:
        Dictionary with Short info (title, duration, etc.) or empty dict if failed
    """
    js_get_info = """
    (function() {
        var info = {};
        
        // Get video element
        var video = document.querySelector('video.html5-main-video') || 
                   document.querySelector('video');
        if (video) {
            info.duration = video.duration;
            info.currentTime = video.currentTime;
            info.paused = video.paused;
        }
        
        // Get title (try both desktop and mobile selectors)
        var titleElement = document.querySelector('h2.title yt-formatted-string') ||
                          document.querySelector('h1.shortsLockupViewModelHostMetadataTitle') ||
                          document.querySelector('.shortsLockupViewModelHostMetadataTitle span');
        if (titleElement) {
            info.title = titleElement.textContent;
        }
        
        // Get Short URL
        info.url = window.location.href;
        
        return JSON.stringify(info);
    })();
    """

    success, result = execute_javascript_in_chrome(js_get_info)
    if success:
        try:
            import json

            info = json.loads(result)
            logger.info(f"Short info: {info}")
            return info
        except:
            logger.error("Failed to parse Short info")
            return {}

    logger.error("Failed to get Short info")
    return {}
