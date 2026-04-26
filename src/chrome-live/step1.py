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


# CHANGE: Modified to accept lock and profile_index for synchronized typing
def type_like_human(
    text: str, target_selector: str, lock=None, profile_index=0
) -> bool:
    logger.info(f"Typing '{text}' character by character...")

    # CHANGE: Acquire lock and switch to this profile's window before typing
    if lock:
        logger.info(f"[Profile-{profile_index + 1}] 🔒 Waiting for typing lock...")
        lock.acquire()
        logger.info(f"[Profile-{profile_index + 1}] ✅ Acquired typing lock")

        # CHANGE: Switch focus to this profile's Chrome window
        from main import switch_to_profile

        switch_to_profile(profile_index)
        time.sleep(0.5)  # Allow window switch to complete

    try:
        for char in text:
            escaped_char = (
                char.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            )
            js_type_char = f"""
            (function() {{
                var input = document.querySelector('{target_selector}');
                if (!input) {{
                    return 'Input not found';
                }}
                input.value += '{escaped_char}';
                var inputEvent = new Event('input', {{ bubbles: true }});
                input.dispatchEvent(inputEvent);
                return 'Typed: ' + '{escaped_char}';
            }})();
            """
            success, result = execute_javascript_in_chrome(js_type_char)
            if not success or "not found" in result:
                logger.error(f"Failed to type character: {char}")
                return False
            time.sleep(random.uniform(0.04, 0.14))
            if random.random() < 0.15:
                time.sleep(random.uniform(0.2, 0.6))
        logger.info(f"Finished typing: {text}")
        return True
    finally:
        # CHANGE: Release lock after typing completes
        if lock:
            lock.release()
            logger.info(f"[Profile-{profile_index + 1}] 🔓 Released typing lock")


# CHANGE: New wrapper function that accepts lock and profile_index
def search_and_click_first_channel_with_lock(
    lock=None, profile_index=0, search_term="@bhaktisangeetplus channel"
):
    """
    1. Focuses YouTube search box, types the search term as a human, submits.
    2. Waits for search results to load.
    3. Finds the first channel result and clicks it (using the provided DOM structure).
    """
    logger.info(f"Searching for: {search_term}")

    selectors = [
        "input#search",
        'input[name="search_query"]',
        'input[aria-label*="Search"]',
        "ytd-searchbox input",
        "form#search-form input",
    ]
    search_box_found = False
    working_selector = None
    for selector in selectors:
        js_focus = f"""
        (function() {{
            var el = document.querySelector('{selector}');
            if (!el) return 'not_found';
            el.focus();
            el.value = '';
            var inputEvent = new Event('input', {{ bubbles: true }});
            el.dispatchEvent(inputEvent);
            return 'found';
        }})();
        """
        success, result = execute_javascript_in_chrome(js_focus)
        if success and result == "found":
            working_selector = selector
            search_box_found = True
            break
    if not search_box_found:
        logger.error("Could not find YouTube search box.")
        return False
    time.sleep(0.5)

    # CHANGE: Pass lock and profile_index to type_like_human
    if not type_like_human(search_term, working_selector, lock, profile_index):
        logger.error("Failed to type search term.")
        return False
    time.sleep(0.5)

    js_press_enter = f"""
    (function() {{
        var el = document.querySelector('{working_selector}');
        if (!el) return 'Input not found';
        var event = new KeyboardEvent('keydown', {{
            bubbles: true,
            cancelable: true,
            key: 'Enter',
            code: 'Enter',
            which: 13,
            keyCode: 13
        }});
        el.dispatchEvent(event);
        return 'Enter pressed';
    }})();
    """
    execute_javascript_in_chrome(js_press_enter)
    logger.info("Submitted search.")
    time.sleep(2)

    max_wait = 10
    waited = 0
    found = False
    while waited < max_wait:
        js_check = """
        (function() {
            var channel = document.querySelector('ytd-channel-renderer');
            return channel ? 'found' : 'not_found';
        })();
        """
        success, result = execute_javascript_in_chrome(js_check)
        if success and result == "found":
            found = True
            break
        time.sleep(1)
        waited += 1
    if not found:
        logger.error("Channel search result not found.")
        return False

    js_click_channel = """
    (function() {
        var channel = document.querySelector('ytd-channel-renderer');
        if (!channel) return 'Channel not found';
        var link = channel.querySelector('a.channel-link[href^="/@BhaktiSangeetPlus"]')
            || channel.querySelector('a#main-link[href^="/@BhaktiSangeetPlus"]');
        if (!link) return 'Channel link not found';
        link.scrollIntoView({behavior: 'smooth', block: 'center'});
        link.click();
        return 'Channel link clicked';
    })();
    """
    success, result = execute_javascript_in_chrome(js_click_channel)
    if success and "clicked" in result:
        logger.info("Clicked first channel search result.")
        return True
    else:
        logger.error(f"Failed to click channel: {result}")
        return False


# CHANGE: Keep original function for backward compatibility
def search_and_click_first_channel(search_term="@bhaktisangeetplus channel"):
    return search_and_click_first_channel_with_lock(None, 0, search_term)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    search_and_click_first_channel()
