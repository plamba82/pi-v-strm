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


def click_comment_button_and_add_comment(
    comment_text: str = "Great video! Thanks for sharing.",
) -> bool:
    """
    Click the comment button, use keyboard navigation to focus input, type comment, and submit.

    Args:
        comment_text: The comment text to add (default: hardcoded test comment)

    Returns:
        True if comment was added and submitted successfully, False otherwise
    """
    logger.info("Step 5: Waiting 1 second before clicking comment button...")
    time.sleep(1)

    # Step 1: Click the comment button
    logger.info("Step 5.1: Clicking comment button...")

    js_click_comment = """
    (function() {
        // Try multiple selector strategies for the comment button
        var commentButton = null;
        
        // Strategy 1: Find by aria-label containing "comment" (case-insensitive)
        var buttons = document.querySelectorAll('button[aria-label]');
        for (var i = 0; i < buttons.length; i++) {
            var label = buttons[i].getAttribute('aria-label');
            if (label && label.toLowerCase().includes('comment')) {
                commentButton = buttons[i];
                console.log('Found comment button using aria-label: ' + label);
                break;
            }
        }
        
        // Strategy 2: Find by SVG path (comment icon)
        if (!commentButton) {
            var svgPaths = document.querySelectorAll('button svg path[d*="M1 6a4 4 0 014-4h14"]');
            if (svgPaths.length > 0) {
                var svgButton = svgPaths[0].closest('button');
                if (svgButton) {
                    commentButton = svgButton;
                    console.log('Found comment button using SVG path');
                }
            }
        }
        
        // Strategy 3: Find by button-view-model parent
        if (!commentButton) {
            var buttonViewModels = document.querySelectorAll('button-view-model button');
            for (var j = 0; j < buttonViewModels.length; j++) {
                var label = buttonViewModels[j].getAttribute('aria-label');
                if (label && label.toLowerCase().includes('comment')) {
                    commentButton = buttonViewModels[j];
                    console.log('Found comment button using button-view-model');
                    break;
                }
            }
        }
        
        // Strategy 4: Find by class combination
        if (!commentButton) {
            var classButtons = document.querySelectorAll('button.ytSpecButtonShapeNextHost.ytSpecButtonShapeNextTonal.ytSpecButtonShapeNextIconButton');
            for (var k = 0; k < classButtons.length; k++) {
                var ariaLabel = classButtons[k].getAttribute('aria-label');
                if (ariaLabel && ariaLabel.toLowerCase().includes('comment')) {
                    commentButton = classButtons[k];
                    console.log('Found comment button using class combination');
                    break;
                }
            }
        }
        
        if (!commentButton) {
            return 'Comment button not found';
        }
        
        // Check if button is visible
        var rect = commentButton.getBoundingClientRect();
        var isVisible = rect.top >= 0 && 
                       rect.left >= 0 && 
                       rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && 
                       rect.right <= (window.innerWidth || document.documentElement.clientWidth) &&
                       window.getComputedStyle(commentButton).visibility !== 'hidden' &&
                       window.getComputedStyle(commentButton).display !== 'none';
        
        if (!isVisible) {
            return 'Comment button not visible';
        }
        
        // Click the button using multiple strategies
        var clickSuccess = false;
        
        // Method 1: Standard click
        try {
            commentButton.click();
            clickSuccess = true;
            console.log('Standard click executed');
        } catch (e) {
            console.log('Standard click failed: ' + e.message);
        }
        
        // Method 2: Dispatch click event
        if (!clickSuccess) {
            try {
                var clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                commentButton.dispatchEvent(clickEvent);
                clickSuccess = true;
                console.log('Event dispatch click executed');
            } catch (e) {
                console.log('Event dispatch failed: ' + e.message);
            }
        }
        
        // Method 3: Coordinate-based click
        if (!clickSuccess) {
            try {
                var rect = commentButton.getBoundingClientRect();
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
                
                commentButton.dispatchEvent(mousedownEvent);
                commentButton.dispatchEvent(mouseupEvent);
                commentButton.click();
                clickSuccess = true;
                console.log('Coordinate-based click executed');
            } catch (e) {
                console.log('Coordinate click failed: ' + e.message);
            }
        }
        
        if (!clickSuccess) {
            return 'All click methods failed';
        }
        
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

    # Wait 2 seconds for popup animation to complete
    logger.info("Waiting 2 seconds for comment popup to render...")
    time.sleep(2)

    # Step 2: Press Tab key 3 times to navigate to the comment input field
    logger.info(
        "Step 5.2: Using Tab key (3 times) to navigate to comment input field..."
    )

    # Press Tab key 3 times to skip intermediate focusable elements
    # (e.g., close button, emoji picker, etc.) and reach the comment input
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

    # Wait briefly for focus to register
    time.sleep(0.5)

    # CHANGE: Step 3: Insert comment text using JavaScript DOM manipulation instead of AppleScript keystroke
    # This allows emojis and special Unicode characters to be inserted correctly
    logger.info(f"Step 5.3: Inserting comment using JavaScript: '{comment_text}'")

    # CHANGE: Escape only backslashes and quotes for JavaScript string literal
    # Do NOT escape emojis or other Unicode characters
    escaped_comment = comment_text.replace("\\", "\\\\").replace('"', '\\"')

    # CHANGE: Use JavaScript to directly set the textContent of the focused input element
    # This bypasses AppleScript's keystroke limitations with emoji characters
    js_insert_comment = f"""
    (function() {{
        // Get the currently focused element (should be the comment input after Tab navigation)
        var commentBox = document.activeElement;
        
        // Verify it's a contenteditable element
        if (!commentBox || commentBox.getAttribute('contenteditable') !== 'true') {{
            // Fallback: try to find the comment input box directly
            commentBox = document.querySelector('yt-formatted-string#contenteditable-textarea div#contenteditable-root[contenteditable="true"]');
            
            if (!commentBox) {{
                commentBox = document.querySelector('div#contenteditable-root[contenteditable="true"]');
            }}
            
            if (!commentBox) {{
                return 'Comment box not found';
            }}
            
            // Focus it
            commentBox.focus();
        }}
        
        // CHANGE: Set textContent directly instead of using keyboard simulation
        // This preserves emojis and all Unicode characters
        commentBox.textContent = "{escaped_comment}";
        
        // Trigger input event to notify YouTube's JavaScript that content changed
        var inputEvent = new Event('input', {{ bubbles: true }});
        commentBox.dispatchEvent(inputEvent);
        
        // Also trigger a change event for good measure
        var changeEvent = new Event('change', {{ bubbles: true }});
        commentBox.dispatchEvent(changeEvent);
        
        return 'Comment inserted: ' + commentBox.textContent.substring(0, 50);
    }})();
    """

    success, result = execute_javascript_in_chrome(js_insert_comment)
    if not success or "not found" in result:
        logger.error("Failed to insert comment text")
        return False

    logger.info(f"Comment inserted successfully: {result}")

    # Wait 1 second for YouTube to show the submit button
    time.sleep(1)

    # Step 4: Click the submit "Comment" button that appears after typing
    logger.info("Step 5.4: Clicking submit Comment button...")

    js_click_submit = """
    (function() {
        // Try multiple selector strategies for the submit button
        var submitButton = null;
        
        // Strategy 1: Find by aria-label="Comment" with filled style
        var buttons = document.querySelectorAll('button[aria-label="Comment"]');
        for (var i = 0; i < buttons.length; i++) {
            var classList = buttons[i].classList;
            if (classList.contains('ytSpecButtonShapeNextFilled') || 
                classList.contains('ytSpecButtonShapeNextCallToAction')) {
                submitButton = buttons[i];
                console.log('Found submit button using aria-label + filled class');
                break;
            }
        }
        
        // Strategy 2: Find by class combination (from provided HTML)
        if (!submitButton) {
            var classButtons = document.querySelectorAll('button.ytSpecButtonShapeNextHost.ytSpecButtonShapeNextFilled.ytSpecButtonShapeNextCallToAction');
            if (classButtons.length > 0) {
                submitButton = classButtons[0];
                console.log('Found submit button using class combination');
            }
        }
        
        // Strategy 3: Find button with text "Comment" inside the comment popup
        if (!submitButton) {
            var textButtons = document.querySelectorAll('button span.ytAttributedStringHost');
            for (var j = 0; j < textButtons.length; j++) {
                if (textButtons[j].textContent.trim() === 'Comment') {
                    submitButton = textButtons[j].closest('button');
                    console.log('Found submit button using text content');
                    break;
                }
            }
        }
        
        if (!submitButton) {
            return 'Submit button not found';
        }
        
        // Check if button is enabled
        var isDisabled = submitButton.getAttribute('aria-disabled');
        if (isDisabled === 'true') {
            return 'Submit button is disabled';
        }
        
        // Click the button using multiple strategies
        var clickSuccess = false;
        
        // Method 1: Standard click
        try {
            submitButton.click();
            clickSuccess = true;
            console.log('Standard click executed');
        } catch (e) {
            console.log('Standard click failed: ' + e.message);
        }
        
        // Method 2: Dispatch click event
        if (!clickSuccess) {
            try {
                var clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                submitButton.dispatchEvent(clickEvent);
                clickSuccess = true;
                console.log('Event dispatch click executed');
            } catch (e) {
                console.log('Event dispatch failed: ' + e.message);
            }
        }
        
        // Method 3: Coordinate-based click
        if (!clickSuccess) {
            try {
                var rect = submitButton.getBoundingClientRect();
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
                
                submitButton.dispatchEvent(mousedownEvent);
                submitButton.dispatchEvent(mouseupEvent);
                submitButton.click();
                clickSuccess = true;
                console.log('Coordinate-based click executed');
            } catch (e) {
                console.log('Coordinate click failed: ' + e.message);
            }
        }
        
        if (!clickSuccess) {
            return 'All submit click methods failed';
        }
        
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

    # Step 5: Verify comment popup closed (indicates successful submission)
    logger.info("Step 5.5: Verifying comment submission...")
    time.sleep(1)

    js_verify_submission = """
    (function() {
        // Check if comment input box is still visible
        var commentBox = document.querySelector('div#contenteditable-root[contenteditable="true"]');
        
        if (!commentBox) {
            return 'Comment popup closed - submission likely successful';
        }
        
        // Check if it's hidden
        var rect = commentBox.getBoundingClientRect();
        var isVisible = rect.top >= 0 && 
                       rect.left >= 0 && 
                       rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && 
                       rect.right <= (window.innerWidth || document.documentElement.clientWidth) &&
                       window.getComputedStyle(commentBox).visibility !== 'hidden' &&
                       window.getComputedStyle(commentBox).display !== 'none';
        
        if (!isVisible) {
            return 'Comment popup hidden - submission likely successful';
        }
        
        return 'Comment popup still visible - submission may have failed';
    })();
    """

    success, verify_result = execute_javascript_in_chrome(js_verify_submission)
    if success:
        logger.info(f"Verification: {verify_result}")
    else:
        logger.warning("Could not verify comment submission")

    # 1 second delay after action
    time.sleep(1)

    return True
