import logging
import subprocess
from typing import Tuple
import time
import random

logger = logging.getLogger(__name__)

# Core roots (expandable mythology base)
roots = [
    "narayan",
    "hari",
    "hari hari",
    "bhajman",
    "teri",
    "nayri",
    "badri",
    "bolo",
    "bhagwan",
    "lakshmi",
    "mahadev",
    "bhole",
    "parvati",
    "krishna",
    "dev",
    "devta",
    "guru",
    "deva",
    "nath",
    "narayan",
    "govind",
    "gopal",
]

# Divine prefixes
prefixes = ["jai", "om", "shree", "har har", "jai jai", "om namo", "jai ho"]

# Divine suffix/epithets (this is what expands into 1000+)
epithets = [
    "dev",
    "nath",
    "bhagwan",
    "swami",
    "prabhu",
    "ishwar",
    "mahadev",
    "avatar",
    "kripa",
    "shakti",
    "roop",
    "sena",
    "dhar",
    "pati",
    "raj",
    "giri",
    "lal",
    "anand",
    "maya",
    "jyoti",
    "teja",
    "sagar",
]
emojis = [
    "🙏",
    "❤️",
    "🔥",
    "✨",
    "💫",
    "🕉️",
    "🌸",
    "⚡",
    "💖",
    "😇",
    "🌺",
    "🌼",
    "🌿",
    "🌞",
    "🌙",
    "⭐",
    "🌈",
    "💥",
    "🪔",
    "🔱",
    "☀️",
    "🌊",
    "🌷",
    "🍀",
    "🌻",
    "🪷",
    "💎",
    "🧿",
    "📿",
    "🛕",
    "🕊️",
    "💐",
    "🌟",
    "🔥",
    "💓",
    "💞",
    "💝",
    "💗",
    "💘",
    "💟",
    "💤",
    "🌌",
    "🌠",
    "🪶",
    "🧡",
    "💛",
    "💚",
    "💙",
    "🤍",
    "💜",
]


def generate_gods_name() -> str:
    prefix = random.choice(prefixes)
    root = random.choice(roots)
    epithet = random.choice(epithets)
    emoji = random.choice(emojis)
    name = f"{prefix} {root} {emoji}"
    return name.strip()


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


# CHANGE: Modified to accept lock parameter for typing synchronization
def type_like_human(
    text: str, target_selector: str, lock=None, profile_index=0
) -> bool:
    """Type text character by character with human-like timing."""
    logger.info(f"Typing '{text}' character by character...")

    # CHANGE: Acquire lock only during typing operation
    if lock:
        logger.info(f"[Profile-{profile_index + 1}] 🔒 Waiting for typing lock...")
        lock.acquire()
        logger.info(f"[Profile-{profile_index + 1}] ✅ Acquired typing lock")

    try:
        for i, char in enumerate(text):
            escaped_char = (
                char.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            )

            js_type_char = f"""
            (function() {{
                try {{
                    let iframe = document.querySelector("iframe#chatframe");
                    if (!iframe) return 'ERROR: Iframe not found';
                    
                    let doc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!doc) return 'ERROR: Iframe document not accessible';
                    
                    var input = doc.querySelector('{target_selector}');
                    if (!input) {{
                        return 'ERROR: Input not found';
                    }}
                    
                    input.focus();
                    
                    if (input.contentEditable === 'true' || input.contentEditable === '') {{
                        var currentText = input.textContent || '';
                        input.textContent = currentText + '{escaped_char}';
                        
                        var range = doc.createRange();
                        var sel = iframe.contentWindow.getSelection();
                        range.selectNodeContents(input);
                        range.collapse(false);
                        sel.removeAllRanges();
                        sel.addRange(range);
                        
                        var inputEvent = new InputEvent('input', {{ 
                            bubbles: true, 
                            cancelable: true,
                            inputType: 'insertText',
                            data: '{escaped_char}'
                        }});
                        input.dispatchEvent(inputEvent);
                        
                        var changeEvent = new Event('change', {{ bubbles: true }});
                        input.dispatchEvent(changeEvent);
                        
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

            if not success:
                logger.error(
                    f"JavaScript execution failed for character '{char}' at position {i}: {result}"
                )
                return False

            if result.startswith("ERROR") or result.startswith("EXCEPTION"):
                logger.error(
                    f"Failed to type character '{char}' at position {i}: {result}"
                )
                return False

            if result.startswith("SUCCESS"):
                logger.debug(result)
            else:
                logger.warning(f"Unexpected result for character '{char}': {result}")

            base_delay = random.uniform(0.08, 0.15)

            if random.random() < 0.1:
                base_delay += random.uniform(0.3, 0.8)

            if char == " ":
                base_delay += random.uniform(0.05, 0.1)

            time.sleep(base_delay)

        logger.info(f"Finished typing: {text}")
        return True
    finally:
        # CHANGE: Release lock immediately after typing completes
        if lock:
            lock.release()
            logger.info(f"[Profile-{profile_index + 1}] 🔓 Released typing lock")


def wait_for_send_button_enabled(max_wait=15):
    """Wait for the send button to become enabled after typing."""
    logger.info("Waiting for send button to become enabled...")

    waited = 0
    check_interval = 1

    while waited < max_wait:
        js_check_button = """
        (function() {
            let iframe = document.querySelector("iframe#chatframe");
            if (!iframe) return 'chat_iframe_not_found';
            
            let doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return 'iframe_not_ready';
            
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


# CHANGE: Modified to accept lock parameter
def send_live_chat_message(msg="jai ho", lock=None, profile_index=0):
    """
    Find the live chat input in iframe, activate it, type message with human-like behavior, and send the message.
    """
    logger.info("Starting live chat message process...")

    logger.info("Waiting for page to fully load...")
    time.sleep(3)

    # CHANGE: No lock needed for waiting/finding input
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

    # CHANGE: No lock needed for preparing input
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

    # CHANGE: Lock is acquired inside type_like_human function
    message = msg
    if not type_like_human(message, selector_used, lock, profile_index):
        logger.error("Failed to type message")
        return False

    # CHANGE: No lock needed for verification
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

    if not success or msg.lower() not in result.lower():
        logger.error(f"Text was not properly entered. Current content: {result}")
        return False

    # CHANGE: No lock needed for waiting for button
    button_ready, button_selector = wait_for_send_button_enabled(max_wait=15)
    if not button_ready:
        logger.error("Send button never became enabled")
        return False

    time.sleep(random.uniform(0.5, 1.0))

    # CHANGE: No lock needed for clicking button
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


# CHANGE: New wrapper function that accepts lock parameter
def send_messages_in_loop_with_lock(
    count=1000, min_delay_ms=1, max_delay_ms=999, lock=None, profile_index=0
):
    """
    Send live chat messages in a loop with randomized delays.
    Lock is only acquired during typing operations.

    Args:
        count: Number of messages to send (default: 1000)
        min_delay_ms: Minimum delay in milliseconds between messages (default: 1)
        max_delay_ms: Maximum delay in milliseconds between messages (default: 999)
        lock: Threading lock for typing synchronization (optional)
        profile_index: Profile index for logging (default: 0)
    """
    logger.info(
        f"Starting loop to send {count} messages with {min_delay_ms}-{max_delay_ms}ms delays"
    )

    successful_sends = 0
    failed_sends = 0

    for i in range(1, count + 1):
        try:
            message = generate_gods_name()
            logger.info(f"[{i}/{count}] Attempting to send: {message}")

            # CHANGE: Pass lock to send_live_chat_message
            success = send_live_chat_message(
                msg=message, lock=lock, profile_index=profile_index
            )

            if success:
                successful_sends += 1
                logger.info(f"[{i}/{count}] ✓ Message sent successfully")
            else:
                failed_sends += 1
                logger.warning(f"[{i}/{count}] ✗ Message send failed")

            if i < count:
                delay_ms = random.randint(min_delay_ms, max_delay_ms)
                delay_seconds = delay_ms / 1000.0
                logger.info(f"Waiting {delay_ms}ms before next message...")
                time.sleep(delay_seconds)

        except KeyboardInterrupt:
            logger.warning(f"Loop interrupted by user at iteration {i}/{count}")
            break
        except Exception as e:
            failed_sends += 1
            logger.error(f"[{i}/{count}] Unexpected error: {e}")
            continue

    logger.info("=" * 60)
    logger.info(
        f"Loop completed: {successful_sends} successful, {failed_sends} failed out of {i} attempts"
    )
    logger.info("=" * 60)

    return successful_sends, failed_sends


# CHANGE: Keep original function for backward compatibility
def send_messages_in_loop(count=1000, min_delay_ms=1, max_delay_ms=999):
    return send_messages_in_loop_with_lock(count, min_delay_ms, max_delay_ms, None, 0)


# Example usage (for direct test/run)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    send_messages_in_loop(count=1000, min_delay_ms=1, max_delay_ms=999)
