import pyautogui
import time
import platform
import random
import subprocess  # CHANGE: Added for AppleScript window activation

# === PROFILE-SPECIFIC COORDINATES ===
# CHANGE: Define coordinates for each profile index, 490. 332
PROFILE_COORDINATES = {
    0: {"text_box_x": 96, "text_box_y": 970, "send_x": 428, "send_y": 970},
    1: {
        "text_box_x": 586,  # Profile 1 coordinates (500px offset)
        "text_box_y": 970,
        "send_x": 918,
        "send_y": 970,
    },
    2: {
        "text_box_x": 1076,  # Profile 2 coordinates (1000px offset)
        "text_box_y": 970,
        "send_x": 1388,
        "send_y": 970,
    },
    3: {
        "text_box_x": 1566,  # Profile 3 coordinates (1500px offset)
        "text_box_y": 970,
        "send_x": 1868,
        "send_y": 970,
    },
}

# === FALLBACK COORDINATES (for backward compatibility) ===
TEXT_BOX_X = 96  # Default coordinates for profile 0
TEXT_BOX_Y = 1040
SEND_X = 428
SEND_Y = 1040

messages = [
    "jai jai bhagwan",
    "jai ho..",
    "hare ram here krishna...",
]


def human_type(text):
    """
    Types text with human-like characteristics:
    - Variable typing speed (50-150ms per character)
    - Random pauses between words
    - Occasional typos with corrections
    """
    words = text.split(" ")

    for i, word in enumerate(words):
        if len(word) > 3 and random.random() < 0.05:
            typo_pos = random.randint(1, len(word) - 1)
            typo_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            typo_word = word[:typo_pos] + typo_char + word[typo_pos + 1 :]

            for char in typo_word:
                pyautogui.write(char, interval=random.uniform(0.05, 0.15))

            time.sleep(random.uniform(0.2, 0.4))
            for _ in range(len(typo_word) - typo_pos):
                pyautogui.press("backspace")
                time.sleep(random.uniform(0.05, 0.1))

            for char in word[typo_pos:]:
                pyautogui.write(char, interval=random.uniform(0.05, 0.15))
        else:
            for char in word:
                pyautogui.write(char, interval=random.uniform(0.05, 0.15))

        if i < len(words) - 1:
            pyautogui.write(" ", interval=random.uniform(0.05, 0.1))
            time.sleep(random.uniform(0.1, 0.3))

        if word.endswith((".", "?", "!")):
            time.sleep(random.uniform(0.3, 0.6))


def ensure_chrome_focus_macos():
    """
    Explicitly activate Chrome and bring frontmost window to focus (macOS only).
    """
    script = """
    tell application "Google Chrome"
        activate
        delay 0.3
    end tell
    """
    try:
        subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=2
        )
    except Exception:
        pass  # CHANGE: Silently fail if AppleScript unavailable


def send_in_window(
    profile_index,
    message,
    text_box_x=None,
    text_box_y=None,
    send_x=None,
    send_y=None,
):
    """
    Send a message in the currently active window using profile-specific coordinates.

    Args:
        profile_index: Index of the profile (0, 1, 2, or 3) to determine coordinates
        message: Text to type and send
        text_box_x: X coordinate of text box (optional, uses profile-specific if None)
        text_box_y: Y coordinate of text box (optional, uses profile-specific if None)
        send_x: X coordinate of send button (optional, uses profile-specific if None)
        send_y: Y coordinate of send button (optional, uses profile-specific if None)
    """
    # CHANGE: Get profile-specific coordinates if not provided
    if profile_index in PROFILE_COORDINATES:
        coords = PROFILE_COORDINATES[profile_index]
        actual_text_box_x = (
            text_box_x if text_box_x is not None else coords["text_box_x"]
        )
        actual_text_box_y = (
            text_box_y if text_box_y is not None else coords["text_box_y"]
        )
        actual_send_x = send_x if send_x is not None else coords["send_x"]
        actual_send_y = send_y if send_y is not None else coords["send_y"]

        print(
            f"Using coordinates for profile {profile_index}: text_box=({actual_text_box_x}, {actual_text_box_y}), send=({actual_send_x}, {actual_send_y})"
        )
    else:
        # CHANGE: Fallback to default coordinates for unknown profile indices
        actual_text_box_x = text_box_x if text_box_x is not None else TEXT_BOX_X
        actual_text_box_y = text_box_y if text_box_y is not None else TEXT_BOX_Y
        actual_send_x = send_x if send_x is not None else SEND_X
        actual_send_y = send_y if send_y is not None else SEND_Y

        print(
            f"Warning: Unknown profile_index {profile_index}, using default coordinates"
        )

    # CHANGE: Ensure window has focus before clicking (macOS only)
    if platform.system().lower() == "darwin":
        ensure_chrome_focus_macos()
        time.sleep(0.5)  # CHANGE: Additional delay for focus transition

    pyautogui.moveTo(
        actual_text_box_x, actual_text_box_y, duration=random.uniform(0.4, 0.7)
    )
    pyautogui.doubleClick()

    time.sleep(random.uniform(0.1, 0.3))

    human_type(message)

    time.sleep(random.uniform(0.2, 0.5))

    pyautogui.moveTo(actual_send_x, actual_send_y, duration=random.uniform(0.2, 0.4))
    pyautogui.click()

    time.sleep(random.uniform(0.6, 1.2))


def run_standalone():
    """Run the automation in standalone mode (original behavior)."""
    print("Automation is ready. Make sure all windows are open.")
    input("Press Enter when you're ready to start...")

    try:
        profile_index = 0  # CHANGE: Start with profile 0
        while True:
            for msg in messages:
                send_in_window(profile_index, msg)
                print(f"Message sent to profile {profile_index}. Switching window...")

                if platform.system().lower() == "darwin":
                    pyautogui.hotkey("command", "tab")
                else:
                    pyautogui.hotkey("alt", "tab")

                # CHANGE: Cycle through profiles 0-3
                profile_index = (profile_index + 1) % 4

                # CHANGE: Increased delay to ensure window switch completes
                time.sleep(random.uniform(2.0, 2.5))
    except KeyboardInterrupt:
        print("\nAutomation stopped.")


if __name__ == "__main__":
    run_standalone()
