import time
import logging
import subprocess
import random
from typing import Tuple

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
    success, output = execute_applescript(script)
    if success:
        logger.info(f"JavaScript executed successfully. Result: {output[:100]}")
    else:
        logger.error(f"JavaScript execution failed: {output}")
    return success, output


def type_like_human_comment(
    text: str, selector: str = 'div#contenteditable-root[contenteditable="true"]'
) -> bool:
    """
    Types text character by character into a contenteditable element with human-like delays.
    Uses JS to append to .textContent and dispatches input events.
    """
    logger.info(f"Typing comment as human: '{text}'")
    for idx, char in enumerate(text):
        # Escape for JS string
        escaped_char = (
            char.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        )
        js_type_char = f"""
        (function() {{
            var el = document.querySelector('{selector}');
            if (!el) return 'Input not found';
            el.textContent += '{escaped_char}';
            var inputEvent = new Event('input', {{ bubbles: true }});
            el.dispatchEvent(inputEvent);
            return 'Typed: {escaped_char}';
        }})();
        """
        success, result = execute_javascript_in_chrome(js_type_char)
        if not success or "not found" in result:
            logger.error(f"Failed to type character: {char}")
            return False
        # Human-like delay
        time.sleep(random.uniform(0.04, 0.14))
        if random.random() < 0.15:
            time.sleep(random.uniform(0.2, 0.6))
    logger.info("Finished typing comment as human.")
    return True


def click_comment_button_and_add_comment(
    comment_text: str = "Great video! Thanks for sharing.",
) -> bool:
    logger.info("Step 5: Waiting 1 second before clicking comment button...")
    time.sleep(1)

    # Step 1: Click the comment button (unchanged)
    js_click_comment = """
    (function() {
        var commentButton = null;
        var buttons = document.querySelectorAll('button[aria-label]');
        for (var i = 0; i < buttons.length; i++) {
            var label = buttons[i].getAttribute('aria-label');
            if (label && label.toLowerCase().includes('comment')) {
                commentButton = buttons[i];
                break;
            }
        }
        if (!commentButton) return 'Comment button not found';
        var rect = commentButton.getBoundingClientRect();
        var isVisible = rect.top >= 0 && rect.left >= 0 && rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && rect.right <= (window.innerWidth || document.documentElement.clientWidth) && window.getComputedStyle(commentButton).visibility !== 'hidden' && window.getComputedStyle(commentButton).display !== 'none';
        if (!isVisible) return 'Comment button not visible';
        try { commentButton.click(); } catch (e) { return 'Click failed'; }
        return 'Comment button clicked';
    })();
    """
    success, result = execute_javascript_in_chrome(js_click_comment)
    if (
        not success
        or "not found" in result
        or "failed" in result
        or "not visible" in result
    ):
        logger.error(f"Failed to click comment button: {result}")
        return False
    logger.info(f"Comment button clicked: {result}")

    logger.info("Waiting 2 seconds for comment popup to render...")
    time.sleep(2)

    # Step 2: Tab to comment input
    logger.info(
        "Step 5.2: Using Tab key (3 times) to navigate to comment input field..."
    )
    tab_script = """
    tell application "Google Chrome"
        activate
        tell application "System Events"
            keystroke tab
            delay 0.3
            keystroke tab
            delay 0.3
            keystroke tab
            delay 0.5
        end tell
    end tell
    """
    success, result = execute_applescript(tab_script)
    if not success:
        logger.error("Failed to press Tab key 3 times")
        return False
    logger.info("Tab key pressed 3 times to focus comment input")
    time.sleep(0.5)

    # Step 3: Human-like typing using JS (supports emoji, Unicode)
    if not type_like_human_comment(comment_text):
        logger.error("Failed to type comment as human")
        return False

    # Wait 1 second for YouTube to show the submit button
    time.sleep(1)

    # Step 4: Click the submit "Comment" button (unchanged)
    js_click_submit = """
    (function() {
        var submitButton = null;
        var buttons = document.querySelectorAll('button[aria-label="Comment"]');
        for (var i = 0; i < buttons.length; i++) {
            var classList = buttons[i].classList;
            if (classList.contains('ytSpecButtonShapeNextFilled') || classList.contains('ytSpecButtonShapeNextCallToAction')) {
                submitButton = buttons[i];
                break;
            }
        }
        if (!submitButton) return 'Submit button not found';
        var isDisabled = submitButton.getAttribute('aria-disabled');
        if (isDisabled === 'true') return 'Submit button is disabled';
        try { submitButton.click(); } catch (e) { return 'Click failed'; }
        return 'Submit button clicked';
    })();
    """
    success, result = execute_javascript_in_chrome(js_click_submit)
    if (
        not success
        or "not found" in result
        or "failed" in result
        or "disabled" in result
    ):
        logger.error(f"Failed to click submit button: {result}")
        return False
    logger.info(f"Submit button clicked: {result}")

    # Step 5: Verify comment popup closed (unchanged)
    logger.info("Step 5.5: Verifying comment submission...")
    time.sleep(1)
    js_verify_submission = """
    (function() {
        var commentBox = document.querySelector('div#contenteditable-root[contenteditable="true"]');
        if (!commentBox) return 'Comment popup closed - submission likely successful';
        var rect = commentBox.getBoundingClientRect();
        var isVisible = rect.top >= 0 && rect.left >= 0 && rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && rect.right <= (window.innerWidth || document.documentElement.clientWidth) && window.getComputedStyle(commentBox).visibility !== 'hidden' && window.getComputedStyle(commentBox).display !== 'none';
        if (!isVisible) return 'Comment popup hidden - submission likely successful';
        return 'Comment popup still visible - submission may have failed';
    })();
    """
    success, verify_result = execute_javascript_in_chrome(js_verify_submission)
    if success:
        logger.info(f"Verification: {verify_result}")
    else:
        logger.warning("Could not verify comment submission")
    time.sleep(1)
    return True
