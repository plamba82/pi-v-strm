import time
import logging
import subprocess
from typing import Tuple
import random

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


def type_like_human(text: str, target_selector: str) -> bool:
    """
    Type text character by character with human-like delays.

    Args:
        text: Text to type
        target_selector: CSS selector for the input element

    Returns:
        True if typing was successful, False otherwise
    """
    logger.info(f"Typing '{text}' character by character...")

    for char in text:
        # Escape special characters for JavaScript
        escaped_char = (
            char.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        )

        js_type_char = f"""
        (function() {{
            var input = document.querySelector('{target_selector}');
            if (!input) {{
                return 'Input not found';
            }}
            
            // Append character to current value
            input.value += '{escaped_char}';
            
            // Trigger input event
            var inputEvent = new Event('input', {{ bubbles: true }});
            input.dispatchEvent(inputEvent);
            
            return 'Typed: ' + '{escaped_char}';
        }})();
        """

        success, result = execute_javascript_in_chrome(js_type_char)
        if not success or "not found" in result:
            logger.error(f"Failed to type character: {char}")
            return False
            # fast typist delay: 40–140ms
            time.sleep(random.uniform(0.04, 0.14))
        # occasional micro pause like thinking
        if random.random() < 0.15:
            time.sleep(random.uniform(0.2, 0.6))
    logger.info(f"Finished typing: {text}")
    return True


def search_youtube(search_query: str, wait_for_results: bool = True) -> bool:
    """
    Search for a keyword in YouTube search box with human-like typing and wait for results to load.

    Args:
        search_query: The search term to enter in YouTube search box
        wait_for_results: Whether to wait for search results to load (default: True)

    Returns:
        True if search was successful, False otherwise
    """
    logger.info(f"Starting YouTube search for: '{search_query}'")

    # Step 1: Wait for page to be ready
    logger.info("Step 1: Checking if page is loaded...")
    js_check_ready = """
    (function() {
        return document.readyState === 'complete' ? 'ready' : 'loading';
    })();
    """

    success, result = execute_javascript_in_chrome(js_check_ready)
    if not success or result != "ready":
        logger.warning("Page not fully loaded, waiting 3 seconds...")
        time.sleep(3)

    # 1 second delay after action
    time.sleep(1)

    # Step 2: Find and focus the search box with multiple selector attempts
    logger.info("Step 2: Locating YouTube search box...")

    # Try multiple selectors with progressive waits
    selectors = [
        "input#search",
        'input[name="search_query"]',
        'input[aria-label*="Search"]',
        "ytd-searchbox input",
        "form#search-form input",
    ]

    max_attempts = 3
    search_box_found = False
    working_selector = None

    for attempt in range(max_attempts):
        for selector in selectors:
            js_find_searchbox = f"""
            (function() {{
                var searchBox = document.querySelector('{selector}');
                if (!searchBox) {{
                    return 'not_found';
                }}
                searchBox.focus();
                return 'found';
            }})();
            """

            success, result = execute_javascript_in_chrome(js_find_searchbox)
            if success and result == "found":
                logger.info(f"Search box located using selector: {selector}")
                search_box_found = True
                working_selector = selector
                break

        if search_box_found:
            break

        # Wait progressively longer between attempts
        wait_time = 2 * (attempt + 1)
        logger.warning(
            f"Search box not found (attempt {attempt + 1}/{max_attempts}), waiting {wait_time}s..."
        )
        time.sleep(wait_time)

    if not search_box_found:
        logger.error("Failed to locate YouTube search box after all attempts")
        return False

    # 1 second delay after action
    time.sleep(1)
    # CHANGE: Clear the search box before entering new text (prevents appending to previous searches)
    logger.info("Step 2.5: Clearing search box...")
    js_clear_searchbox = f"""
    (function() {{
        var searchBox = document.querySelector('{working_selector}');
        if (!searchBox) {{
            return 'Search box not found';
        }}
        
        // Clear the search box
        searchBox.value = '';
        
        // Trigger input event to notify YouTube of the change
        var inputEvent = new Event('input', {{ bubbles: true }});
        searchBox.dispatchEvent(inputEvent);
        
        return 'Search box cleared';
    }})();
    """

    success, result = execute_javascript_in_chrome(js_clear_searchbox)
    if not success or "not found" in result:
        logger.error(f"Failed to clear search box: {result}")
        return False

    logger.info(f"Search box cleared: {result}")
    time.sleep(0.5)
    # Step 3: Type search query character by character (human-like)
    logger.info(f"Step 3: Typing search query like a human: '{search_query}'")

    if not type_like_human(search_query, working_selector):
        logger.error("Failed to type search query")
        return False

    # 1 second delay after action
    time.sleep(1)

    # Step 4: Click search button with multiple selector attempts
    logger.info("Step 4: Clicking search button...")

    button_selectors = [
        "button#search-icon-legacy",
        'button[aria-label*="Search"]',
        "ytd-searchbox button",
        "form#search-form button",
    ]

    js_click_search = f"""
    (function() {{
        var selectors = {button_selectors};
        var searchButton = null;
        
        for (var i = 0; i < selectors.length; i++) {{
            searchButton = document.querySelector(selectors[i]);
            if (searchButton) break;
        }}
        
        if (!searchButton) {{
            return 'Search button not found';
        }}
        searchButton.click();
        return 'Search button clicked';
    }})();
    """

    success, result = execute_javascript_in_chrome(js_click_search)
    if not success or "not found" in result:
        logger.error("Failed to click search button")
        return False

    logger.info(f"Search initiated: {result}")

    # 1 second delay after action
    time.sleep(1)

    # Step 5: Wait for search results to load
    if wait_for_results:
        logger.info("Step 5: Waiting for search results to load...")

        max_wait_time = 15
        check_interval = 0.5
        elapsed_time = 0

        js_check_results = """
        (function() {
            var results = document.querySelectorAll('ytd-video-renderer, ytd-grid-video-renderer');
            if (results.length > 0) {
                return 'Results loaded: ' + results.length + ' videos found';
            }
            return 'No results yet';
        })();
        """

        while elapsed_time < max_wait_time:
            success, result = execute_javascript_in_chrome(js_check_results)

            if success and "Results loaded" in result:
                logger.info(f"Search results loaded: {result}")
                return True

            time.sleep(check_interval)
            elapsed_time += check_interval
            logger.debug(f"Waiting for results... ({elapsed_time}s elapsed)")

        logger.warning(f"Search results did not load within {max_wait_time} seconds")
        return False

    logger.info("Search completed (not waiting for results)")
    return True


def get_search_results_count() -> int:
    """
    Get the number of video results currently visible on the page.

    Returns:
        Number of video results, or -1 if unable to determine
    """
    js_count_results = """
    (function() {
        var results = document.querySelectorAll('ytd-video-renderer');
        return results.length.toString();
    })();
    """

    success, result = execute_javascript_in_chrome(js_count_results)
    if success and result.isdigit():
        count = int(result)
        logger.info(f"Found {count} video results on page")
        return count

    logger.error("Failed to count search results")
    return -1
