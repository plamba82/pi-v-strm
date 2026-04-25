import logging
import time
import random

# CHANGE: Import pyautogui for Windows automation instead of subprocess/AppleScript
import pyautogui

logger = logging.getLogger(__name__)

# CHANGE: Configuration for absolute coordinates (adjust these for your screen)
CHAT_INPUT_COORDINATES = {
    # CHANGE: Default coordinates for 1920x1080 screen
    # Adjust these values based on where the chat input appears on YOUR screen
    "x": 1544,  # Horizontal position in pixels from left edge
    "y": 925,   # Vertical position in pixels from top edge
}

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
# roots = [
#     "hanuman",
#     "bajrang",
#     "bajrangbali",
#     "pavan",
#     "pavansut",a
#     "pavanputra",
#     "anjani",
#     "anjaneya",
#     "anjanisuta",
#     "kesari",
#     "kesarinandan",
#     "maruti",
#     "ramdoot",
#     "ramduta",
#     "ram bhakt",
#     "ram bhakta",
#     "sankatmochan",
#     "sankat mochan",
#     "mahavir",
#     "veer",
#     "balaji",
#     "kapish",
#     "kapiraj",
#     "rudra",
#     "rudravatar",
#     "chiranjeevi",
#     "langur",
#     "vanar",
#     "jai hanuman",
#     "jai bajrangbali",
# ]
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

# epithets = [
#     "bal",
#     "veer",
#     "mahaveer",
#     "bali",
#     "bajrang",
#     "bajrangbali",
#     "pavanputra",
#     "ramdoot",
#     "bhakt",
#     "ram bhakt",
#     "sankatmochan",
#     "kapeesh",
#     "kapiraj",
#     "anand",
#     "shakti",
#     "teja",
#     "jyoti",
#     "veerata",
#     "parakram",
#     "rakshak",
#     "dhar",
#     "sevak",
#     "dut",
#     "chiranjeevi",
#     "rudravatar",
#     "pratap",
#     "balwan",
#     "dayalu",
#     "kripalu",
# ]
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


# CHANGE: Simplified wait function - no DOM inspection on Windows
def wait_for_live_chat_input(max_wait=30):
    """Wait for live chat input field to appear - simplified for Windows."""
    logger.info("Waiting for live chat to be ready...")
    
    # CHANGE: Simple time-based wait since we can't inspect DOM directly without browser automation
    time.sleep(max_wait / 2)
    
    logger.info("Assuming live chat is ready after wait period")
    return True


# CHANGE: Modified to use pyautogui for typing instead of JavaScript injection
def type_like_human(text: str, lock=None, profile_index=0) -> bool:
    """Type text character by character with human-like timing using pyautogui."""
    logger.info(f"Typing '{text}' character by character...")

    # CHANGE: Acquire lock only during typing operation
    if lock:
        logger.info(f"[Profile-{profile_index + 1}] 🔒 Waiting for typing lock...")
        lock.acquire()
        logger.info(f"[Profile-{profile_index + 1}] ✅ Acquired typing lock")

    try:
        # CHANGE: Use pyautogui to type each character with human-like delays
        for char in text:
            pyautogui.write(char, interval=random.uniform(0.08, 0.15))
            
            # CHANGE: Random pauses for human-like typing behavior
            if random.random() < 0.1:
                time.sleep(random.uniform(0.3, 0.8))
            
            # CHANGE: Slightly longer pause after spaces
            if char == " ":
                time.sleep(random.uniform(0.05, 0.1))

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


# CHANGE: Simplified function - no DOM state checking on Windows
def wait_for_send_button_enabled(max_wait=15):
    """Wait for the send button to become enabled - simplified for Windows."""
    logger.info("Waiting for send button to be ready...")
    # CHANGE: Simple delay instead of DOM polling
    time.sleep(2)
    logger.info("Assuming send button is ready")
    return True


# CHANGE: Helper function to find the correct chat input coordinates interactively
def find_chat_input_coordinates():
    """
    Interactive helper to find the correct chat input coordinates for your screen.
    Run this once to determine the coordinates, then update CHAT_INPUT_COORDINATES.
    """
    print("\n" + "="*60)
    print("CHAT INPUT COORDINATE FINDER")
    print("="*60)
    print("\nInstructions:")
    print("1. Navigate to YouTube live stream with chat visible")
    print("2. Move your mouse EXACTLY over the chat input field")
    print("3. Press ENTER when positioned correctly")
    print("\nWaiting for you to position the mouse...")
    
    input()
    
    # CHANGE: Get current mouse position
    x, y = pyautogui.position()
    
    print("\n" + "="*60)
    print(f"✅ Chat input coordinates found: ({x}, {y})")
    print("="*60)
    print("\nUpdate your step3.py file with these values:")
    print(f'\nCHAT_INPUT_COORDINATES = {{')
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
def click_chat_input_by_percentage(x_percent=0.86, y_percent=0.88):
    """
    Click chat input using percentage of screen dimensions.
    More portable across different screen resolutions.
    
    Args:
        x_percent: Horizontal position as percentage of screen width (0.0 to 1.0)
        y_percent: Vertical position as percentage of screen height (0.0 to 1.0)
    """
    try:
        # CHANGE: Get screen dimensions
        screen_width, screen_height = pyautogui.size()
        
        # CHANGE: Calculate absolute coordinates from percentages
        chat_x = int(screen_width * x_percent)
        chat_y = int(screen_height * y_percent)
        
        logger.info(f"Screen size: {screen_width}x{screen_height}")
        logger.info(f"Calculated coordinates: ({chat_x}, {chat_y}) from {x_percent*100}%, {y_percent*100}%")
        
        # CHANGE: Click at calculated position
        pyautogui.moveTo(chat_x, chat_y, duration=0.5)
        time.sleep(0.3)
        pyautogui.click()
        
        logger.info("Chat input clicked successfully using percentage-based coordinates")
        return True
        
    except Exception as e:
        logger.error(f"Failed to click chat input: {e}")
        return False


# CHANGE: Rewritten to click chat input coordinates BEFORE EVERY message
def send_live_chat_message(msg="jai ho", lock=None, profile_index=0):
    """
    Find the live chat input using absolute coordinates, type message with human-like behavior, and send.
    CRITICAL: Clicks chat input coordinates BEFORE EVERY message to ensure focus.
    """
    logger.info("Starting live chat message process...")

    try:
        # CHANGE: Step 1 - Click on chat input using absolute coordinates (MOVED INSIDE FUNCTION)
        # This ensures the input is focused BEFORE EVERY message, not just the first one
        chat_x = CHAT_INPUT_COORDINATES["x"]
        chat_y = CHAT_INPUT_COORDINATES["y"]
        
        logger.info(f"Using absolute coordinates: ({chat_x}, {chat_y})")
        
        # CHANGE: Move mouse to chat input position and click to regain focus
        logger.info(f"Moving mouse to chat input position...")
        pyautogui.moveTo(chat_x, chat_y, duration=0.5)
        logger.info(f"Clicking chat input at ({chat_x}, {chat_y})")
        pyautogui.click()

        logger.info("Chat input clicked and focused successfully")
        # CHANGE: Step 2 - Type message with lock (thread-safe typing)
        message = msg
        if not type_like_human(message, lock, profile_index):
            logger.error("Failed to type message")
            return False

        # CHANGE: Step 3 - Wait briefly before sending
        time.sleep(random.uniform(0.5, 1.0))

        # CHANGE: Step 4 - Send message by pressing Enter
        pyautogui.press('enter')
        logger.info("Message sent successfully via Enter key")

        time.sleep(2)
        return True
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

# CHANGE: Updated wrapper function - no changes needed here, just for reference
def send_messages_in_loop_with_lock(
    count=1000, min_delay_ms=1, max_delay_ms=999, lock=None, profile_index=0
):
    """
    Send live chat messages in a loop with randomized delays.
    Lock is only acquired during typing operations.
    
    CHANGE: Each call to send_live_chat_message() now clicks the chat input first,
    ensuring focus is regained before every message.
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

            # CHANGE: This now clicks chat input coordinates before typing each message
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

    # CHANGE: Uncomment to find coordinates interactively
    # find_chat_input_coordinates()

    send_messages_in_loop(count=1000, min_delay_ms=1, max_delay_ms=999)