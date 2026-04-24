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


def wait_for_live_chat_input(max_wait=30):
    """Wait for live chat input field to appear and activate it within iframe."""
    logger.info("Waiting for live chat input field to appear...")

    waited = 0
    check_interval = 2

    while waited < max_wait:
        js_diagnose = """
        (function() {
            var diagnostics = {
                iframes: [],
                chatElements: []
            };
            
            var allIframes = document.querySelectorAll('iframe');
            for (var i = 0; i < allIframes.length; i++) {
                var iframe = allIframes[i];
                diagnostics.iframes.push({
                    id: iframe.id || 'no-id',
                    src: iframe.src ? iframe.src.substring(0, 100) : 'no-src',
                    name: iframe.name || 'no-name',
                    className: iframe.className || 'no-class'
                });
            }
            
            var chatSelectors = [
                'iframe#chatframe',
                'iframe[src*="live_chat"]',
                'iframe[title*="chat" i]',
                'yt-live-chat-renderer',
                '#chat-container',
                '#chat'
            ];
            
            chatSelectors.forEach(function(selector) {
                var elem = document.querySelector(selector);
                if (elem) {
                    diagnostics.chatElements.push(selector);
                }
            });
            
            return JSON.stringify(diagnostics);
        })();
        """

        success, diag_result = execute_javascript_in_chrome(js_diagnose)
        if success:
            logger.info(f"Page diagnostics: {diag_result}")

        js_find_and_activate = """
        (function() {
            var iframeSelectors = [
                'iframe#chatframe',
                'iframe[src*="live_chat"]',
                'iframe[title*="chat" i]'
            ];
            
            var iframe = null;
            var usedSelector = null;
            
            for (var i = 0; i < iframeSelectors.length; i++) {
                iframe = document.querySelector(iframeSelectors[i]);
                if (iframe) {
                    usedSelector = iframeSelectors[i];
                    break;
                }
            }
            
            if (!iframe) return "chat_iframe_not_found";
            
            var doc = null;
            try {
                doc = iframe.contentDocument || iframe.contentWindow.document;
            } catch(e) {
                return "iframe_access_denied:" + e.message;
            }
            
            if (!doc) return "iframe_not_ready";
            
            var inputSelectors = [
                'div#input[contenteditable]',
                'div#input[contenteditable="true"]',
                'div[contenteditable][id*="input"]',
                'div[contenteditable][class*="input"]',
                '#message-input',
                'input[type="text"]',
                'textarea'
            ];
            
            var input = null;
            var usedInputSelector = null;
            
            for (var j = 0; j < inputSelectors.length; j++) {
                input = doc.querySelector(inputSelectors[j]);
                if (input) {
                    usedInputSelector = inputSelectors[j];
                    break;
                }
            }
            
            if (!input) {
                var bodyContent = doc.body ? doc.body.innerHTML.substring(0, 500) : 'no-body';
                return "input_not_found_in_iframe:body_preview:" + bodyContent;
            }
            
            var rect = input.getBoundingClientRect();
            var isVisible = rect.width > 0 && rect.height > 0;
            
            if (!isVisible) {
                return "input_found_but_not_visible:" + usedInputSelector;
            }
            
            try {
                input.scrollIntoView({behavior: 'smooth', block: 'center'});
                input.focus();
                input.click();
                
                // CHANGE: Only use textContent to avoid TrustedHTML policy violation
                input.textContent = '';
                
                var events = ['mousedown', 'mouseup', 'click', 'focus', 'focusin'];
                events.forEach(function(eventType) {
                    var event = new Event(eventType, { bubbles: true });
                    input.dispatchEvent(event);
                });
                
                return 'input_found_and_activated:' + usedInputSelector + ':iframe:' + usedSelector;
            } catch(e) {
                return 'activation_error:' + e.message;
            }
        })();
        """

        success, result = execute_javascript_in_chrome(js_find_and_activate)

        if success and result.startswith("input_found_and_activated"):
            parts = result.split(":")
            selector_used = parts[1]
            iframe_selector = parts[3] if len(parts) > 3 else "iframe#chatframe"
            logger.info(
                f"Live chat input found and activated using selector: {selector_used} in {iframe_selector}"
            )
            return True, selector_used
        elif success and result == "chat_iframe_not_found":
            logger.warning(f"Chat iframe not found, waiting... ({waited}s/{max_wait}s)")
        elif success and result == "iframe_not_ready":
            logger.warning(f"Chat iframe not ready, waiting... ({waited}s/{max_wait}s)")
        elif success and result.startswith("iframe_access_denied"):
            logger.error(f"Cannot access iframe (CORS issue): {result}")
            logger.error(
                "This may be a cross-origin security restriction. Try opening the live chat in a popout window."
            )
            return False, None
        elif success and result.startswith("input_not_found_in_iframe"):
            logger.warning(f"Input not found in iframe. Preview: {result[50:150]}")
        elif success and result.startswith("input_found_but_not_visible"):
            logger.warning(f"Input found but not visible: {result}")
        elif success and result.startswith("activation_error"):
            logger.error(f"Failed to activate input: {result}")
        else:
            logger.warning(f"Unexpected result: {result[:200]} ({waited}s/{max_wait}s)")

        time.sleep(check_interval)
        waited += check_interval

    logger.error(f"Live chat input not found after {max_wait} seconds")
    return False, None


def type_like_human(text: str, target_selector: str) -> bool:
    """Type text character by character with human-like timing."""
    logger.info(f"Typing '{text}' character by character...")

    for i, char in enumerate(text):
        escaped_char = (
            char.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        )

        js_type_char = f"""
        (function() {{
            try {{
                // Access the iframe and its document
                let iframe = document.querySelector("iframe#chatframe");
                if (!iframe) return 'ERROR: Iframe not found';
                
                let doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc) return 'ERROR: Iframe document not accessible';
                
                var input = doc.querySelector('{target_selector}');
                if (!input) {{
                    return 'ERROR: Input not found';
                }}
                
                // Focus the input first
                input.focus();
                
                // Add character to the content
                if (input.contentEditable === 'true' || input.contentEditable === '') {{
                    // For contenteditable div - use more robust method
                    var currentText = input.textContent || '';
                    input.textContent = currentText + '{escaped_char}';
                    
                    // Move cursor to end
                    var range = doc.createRange();
                    var sel = iframe.contentWindow.getSelection();
                    range.selectNodeContents(input);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);
                    
                    // Trigger comprehensive input events
                    var inputEvent = new InputEvent('input', {{ 
                        bubbles: true, 
                        cancelable: true,
                        inputType: 'insertText',
                        data: '{escaped_char}'
                    }});
                    input.dispatchEvent(inputEvent);
                    
                    var changeEvent = new Event('change', {{ bubbles: true }});
                    input.dispatchEvent(changeEvent);
                    
                    // Also trigger keydown/keyup for better compatibility
                    var keydownEvent = new KeyboardEvent('keydown', {{ 
                        bubbles: true, 
                        key: '{escaped_char}',
                        code: 'Key' + '{escaped_char}'.toUpperCase()
                    }});
                    input.dispatchEvent(keydownEvent);
                    
                    var keyupEvent = new KeyboardEvent('keyup', {{ 
                        bubbles: true, 
                        key: '{escaped_char}',
                        code: 'Key' + '{escaped_char}'.toUpperCase()
                    }});
                    input.dispatchEvent(keyupEvent);
                    
                }} else {{
                    // For regular input fields
                    input.value += '{escaped_char}';
                    
                    var inputEvent = new Event('input', {{ bubbles: true }});
                    input.dispatchEvent(inputEvent);
                }}
                
                return 'SUCCESS: Typed char at position ' + {i} + ', total length: ' + input.textContent.length;
            }} catch(e) {{
                return 'EXCEPTION: ' + e.message;
            }}
        }})();
        """

        success, result = execute_javascript_in_chrome(js_type_char)

        # Enhanced logging
        if not success:
            logger.error(
                f"JavaScript execution failed for character '{char}' at position {i}: {result}"
            )
            return False

        if result.startswith("ERROR") or result.startswith("EXCEPTION"):
            logger.error(f"Failed to type character '{char}' at position {i}: {result}")
            return False

        if result.startswith("SUCCESS"):
            logger.debug(result)
        else:
            logger.warning(f"Unexpected result for character '{char}': {result}")

        # Human-like typing delays
        base_delay = random.uniform(0.08, 0.15)

        if random.random() < 0.1:
            base_delay += random.uniform(0.3, 0.8)

        if char == " ":
            base_delay += random.uniform(0.05, 0.1)

        time.sleep(base_delay)

    logger.info(f"Finished typing: {text}")
    return True


def wait_for_send_button_enabled(max_wait=15):
    """Wait for the send button to become enabled after typing."""
    logger.info("Waiting for send button to become enabled...")

    waited = 0
    check_interval = 1

    while waited < max_wait:
        js_check_button = """
        (function() {
            // Access the iframe and its document
            let iframe = document.querySelector("iframe#chatframe");
            if (!iframe) return 'chat_iframe_not_found';
            
            let doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return 'iframe_not_ready';
            
            // Look for send button in the iframe
            var selectors = [
                'button[aria-label="Send"]:not([disabled])',
                '#send-button button[aria-label="Send"]:not([disabled])',
                'yt-button-renderer button[aria-label="Send"]:not([disabled])',
                '.ytSpecButtonShapeNextHost[aria-label="Send"]:not([disabled])',
                '#message-buttons button[aria-label="Send"]:not([disabled])'
            ];
            
            for (var i = 0; i < selectors.length; i++) {
                var button = doc.querySelector(selectors[i]);
                if (button && !button.disabled && button.offsetParent !== null) {
                    return 'send_button_enabled:' + selectors[i];
                }
            }
            
            return 'send_button_not_ready';
        })();
        """

        success, result = execute_javascript_in_chrome(js_check_button)
        if success and result.startswith("send_button_enabled"):
            selector_used = result.split(":")[1]
            logger.info(f"Send button is now enabled: {selector_used}")
            return True, selector_used

        time.sleep(check_interval)
        waited += check_interval

    logger.error(f"Send button did not become enabled after {max_wait} seconds")
    return False, None


def send_live_chat_message():
    """
    Find the live chat input in iframe, activate it, type 'jai ho' with human-like behavior, and send the message.
    """
    logger.info("Starting live chat message process...")

    logger.info("Waiting for page to fully load...")
    time.sleep(3)

    input_found, selector_used = wait_for_live_chat_input(max_wait=45)
    if not input_found:
        logger.error("Live chat input field never appeared")

        js_final_check = """
        (function() {
            return {
                url: window.location.href,
                title: document.title,
                iframeCount: document.querySelectorAll('iframe').length,
                hasChat: !!document.querySelector('yt-live-chat-renderer'),
                readyState: document.readyState
            };
        })();
        """
        success, final_info = execute_javascript_in_chrome(js_final_check)
        if success:
            logger.error(f"Final page state: {final_info}")

        return False

    logger.info("Waiting for iframe to stabilize...")
    time.sleep(2)

    js_prepare_input = f"""
    (function() {{
        try {{
            var iframeSelectors = [
                'iframe#chatframe',
                'iframe[src*="live_chat"]',
                'iframe[title*="chat" i]'
            ];
            
            var iframe = null;
            for (var i = 0; i < iframeSelectors.length; i++) {{
                iframe = document.querySelector(iframeSelectors[i]);
                if (iframe) break;
            }}
            
            if (!iframe) return 'ERROR: Iframe not found';
            
            let doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return 'ERROR: Iframe document not accessible';
            
            var input = doc.querySelector('{selector_used}');
            if (!input) {{
                return 'ERROR: Input element disappeared';
            }}
            
            input.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            input.click();
            input.focus();
            
            // CHANGE: Only use textContent to avoid TrustedHTML policy violation
            input.textContent = '';
            
            var events = ['mousedown', 'mouseup', 'click', 'focus', 'focusin'];
            events.forEach(function(eventType) {{
                var event = new Event(eventType, {{ bubbles: true }});
                input.dispatchEvent(event);
            }});
            
            return 'SUCCESS: Input prepared and activated, current text: "' + input.textContent + '"';
        }} catch(e) {{
            return 'EXCEPTION: ' + e.message;
        }}
    }})();
    """

    success, result = execute_javascript_in_chrome(js_prepare_input)
    logger.info(f"Input preparation result: {result}")

    if not success or result.startswith("ERROR") or result.startswith("EXCEPTION"):
        logger.error(f"Failed to prepare input field: {result}")
        return False

    logger.info("Input field prepared and activated, starting to type message...")

    message = "jai ho"
    if not type_like_human(message, selector_used):
        logger.error("Failed to type message")
        return False

    js_verify_text = f"""
    (function() {{
        try {{
            var iframeSelectors = [
                'iframe#chatframe',
                'iframe[src*="live_chat"]',
                'iframe[title*="chat" i]'
            ];
            
            var iframe = null;
            for (var i = 0; i < iframeSelectors.length; i++) {{
                iframe = document.querySelector(iframeSelectors[i]);
                if (iframe) break;
            }}
            
            if (!iframe) return 'ERROR: Iframe not found';
            
            let doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return 'ERROR: Iframe document not accessible';
            
            var input = doc.querySelector('{selector_used}');
            if (!input) return 'ERROR: Input not found';
            
            return 'Text in input: "' + input.textContent + '"';
        }} catch(e) {{
            return 'EXCEPTION: ' + e.message;
        }}
    }})();
    """

    success, result = execute_javascript_in_chrome(js_verify_text)
    logger.info(f"Text verification: {result}")

    if not success or "jai ho" not in result.lower():
        logger.error(f"Text was not properly entered. Current content: {result}")
        return False

    button_ready, button_selector = wait_for_send_button_enabled(max_wait=15)
    if not button_ready:
        logger.error("Send button never became enabled")
        return False

    time.sleep(random.uniform(0.5, 1.0))

    js_click_send = f"""
    (function() {{
        try {{
            var iframeSelectors = [
                'iframe#chatframe',
                'iframe[src*="live_chat"]',
                'iframe[title*="chat" i]'
            ];
            
            var iframe = null;
            for (var i = 0; i < iframeSelectors.length; i++) {{
                iframe = document.querySelector(iframeSelectors[i]);
                if (iframe) break;
            }}
            
            if (!iframe) return 'ERROR: Iframe not found';
            
            let doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return 'ERROR: Iframe document not accessible';
            
            var button = doc.querySelector('{button_selector}');
            if (!button) {{
                return 'ERROR: Send button disappeared';
            }}
            
            if (button.disabled) {{
                return 'ERROR: Send button is disabled';
            }}
            
            button.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            
            button.click();
            
            var mousedownEvent = new MouseEvent('mousedown', {{ bubbles: true }});
            button.dispatchEvent(mousedownEvent);
            
            var mouseupEvent = new MouseEvent('mouseup', {{ bubbles: true }});
            button.dispatchEvent(mouseupEvent);
            
            var clickEvent = new MouseEvent('click', {{ bubbles: true }});
            button.dispatchEvent(clickEvent);
            
            return 'SUCCESS: Send button clicked using selector: {button_selector}';
        }} catch(e) {{
            return 'EXCEPTION: ' + e.message;
        }}
    }})();
    """

    success, result = execute_javascript_in_chrome(js_click_send)
    logger.info(f"Send button click result: {result}")

    if not success or result.startswith("ERROR") or result.startswith("EXCEPTION"):
        logger.error(f"Failed to click send button: {result}")
        return False

    logger.info(f"Message sent successfully: {result}")

    time.sleep(2)

    js_verify_sent = """
    (function() {
        try {
            var iframeSelectors = [
                'iframe#chatframe',
                'iframe[src*="live_chat"]',
                'iframe[title*="chat" i]'
            ];
            
            var iframe = null;
            for (var i = 0; i < iframeSelectors.length; i++) {
                iframe = document.querySelector(iframeSelectors[i]);
                if (iframe) break;
            }
            
            if (!iframe) return 'ERROR: iframe_not_found';
            
            let doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return 'ERROR: iframe_not_ready';
            
            var input = doc.querySelector('div#input[contenteditable]');
            if (input) {
                var content = input.textContent.trim();
                if (content === '') {
                    return 'SUCCESS: message_sent_successfully';
                } else {
                    return 'WARNING: Input still contains: "' + content + '"';
                }
            }
            return 'ERROR: Input element not found for verification';
        } catch(e) {
            return 'EXCEPTION: ' + e.message;
        }
    })();
    """

    success, result = execute_javascript_in_chrome(js_verify_sent)
    logger.info(f"Message verification: {result}")

    if success and "message_sent_successfully" in result:
        logger.info("Message confirmed sent - input field cleared")
    else:
        logger.warning(f"Message send status unclear: {result}")

    return True


# Example usage (for direct test/run)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    send_live_chat_message()
