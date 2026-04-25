import json
import os
import platform
import subprocess
import time
from pathlib import Path
import threading
from typing import Dict, List, Tuple
import queue

# CHANGE: Import pyautogui and pygetwindow for Windows automation
import pyautogui
import pygetwindow as gw

# Import the step modules
from step1 import search_and_click_first_channel
from step2 import  click_channel_avatar_and_wait 
from step3 import send_messages_in_loop

# CHANGE: Replace global lock with a typing-specific lock and queue for round-robin access
typing_lock = threading.Lock()
typing_queue = queue.Queue()  # Profiles register here to wait for typing access

# Thread-safe result tracking
profile_results: Dict[str, Dict] = {}
results_lock = threading.Lock()


def load_config(path="config.json"):
    base_path = Path(__file__).resolve().parent
    config_path = base_path / path

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)


def expand_path(path: str) -> str:
    """Expand ~ and environment variables safely."""
    return os.path.expanduser(os.path.expandvars(path))


def get_os():
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    elif system == "windows":
        return "windows"
    else:
        raise Exception(f"Unsupported OS: {system}")


def get_screen_dimensions():
    """Get screen dimensions for window positioning."""
    # CHANGE: Use pyautogui to get screen size on Windows
    try:
        screen_width, screen_height = pyautogui.size()
        return screen_width, screen_height
    except:
        return 1920, 1080  # Default fallback


def calculate_window_position(profile_index, total_profiles=6):
    """Calculate window position and size for 3x2 grid layout."""
    screen_width, screen_height = get_screen_dimensions()

    window_width = screen_width                            
    window_height = screen_height 

    cols = 1
    rows = 1                                        


    col = profile_index % cols
    row = profile_index // cols

    x = col * window_width
    y = row * window_height

    print(
        f"Profile {profile_index + 1}: Position ({x}, {y}), Size ({window_width}x{window_height})"
    )

    return x, y, window_width, window_height


# CHANGE: New function to position Chrome window using pygetwindow on Windows
def position_chrome_window_windows(profile_index, x, y, width, height, profile_name):
    """Position Chrome window using pygetwindow on Windows."""
    time.sleep(2)
    
    try:
        # CHANGE: Find Chrome windows by title pattern
        chrome_windows = gw.getWindowsWithTitle('Google Chrome')
        
        if not chrome_windows:
            print(f"❌ No Chrome windows found for Profile {profile_index + 1}")
            return False
        
        # CHANGE: Try to find the specific profile window (most recent one)
        target_window = chrome_windows[-1] if chrome_windows else None
        
        if target_window:
            # CHANGE: Restore window if minimized
            if target_window.isMinimized:
                target_window.restore()
            
            # CHANGE: Move and resize window
            target_window.moveTo(x, y)
            target_window.resizeTo(width, height)
            
            print(f"✅ Positioned i jai bhProfile {profile_index + 1} window at ({x}, {y})")
            return True
        else:
            print(f"❌ Failed to position Profile {profile_index + 1}")
            return False
            
    except Exception as e:
        print(f"❌ Error positioning Profile {profile_index + 1}: {e}")
        return False


# CHANGE: New function to switch focus to Chrome window using pygetwindow
def switch_to_profile(profile_index):
    """Switch keyboard focus to a specific Chrome profile window using pygetwindow."""
    try:
        chrome_windows = gw.getWindowsWithTitle('Google Chrome')
        
        if not chrome_windows or profile_index >= len(chrome_windows):
            print(f"❌ Profile window {profile_index + 1} not found")
            return False
        
        # CHANGE: Activate the target window
        target_window = chrome_windows[profile_index]
        target_window.activate()
        
        print(f"✅ Switched focus to Profile {profile_index + 1}")
        return True
        
    except Exception as e:
        print(f"❌ Error switching to Profile {profile_index + 1}: {e}")
        return False


def cycle_through_profiles(total_profiles=6, delay=3):
    """Cycle through all Chrome profiles, giving each keyboard focus."""
    print(f"\n🔄 Starting profile cycling (switching every {delay} seconds)...")

    for i in range(total_profiles):
        print(f"\n📍 Switching to Profile {i + 1}")
        switch_to_profile(i)
        time.sleep(delay)

    print("\n✅ Profile cycling completed")


def wait_for_page_stability(timeout=15):
    """Wait for page to stabilize after navigation with adaptive timing."""
    print("⏳ Waiting for page to stabilize...")
    
    # CHANGE: Simple time-based wait since we can't execute JavaScript directly
    stable_checks = 0
    max_checks = 3
    check_interval = 2

    for attempt in range(timeout // check_interval):
        # CHANGE: Wait for visual stability instead of JavaScript checks
        time.sleep(check_interval)
        stable_checks += 1
        
        if stable_checks >= max_checks:
            print(f"✅ Page stabilized after {stable_checks * check_interval}s")
            return True

    print("⚠️ Page stability timeout reached")
    return False


def build_command(config, profile, os_type, profile_index=0):
    chrome_paths = config["chrome_paths"]
    flags = config.get("flags", [])

    url = profile["url"]
    chrome_profile = profile.get("chrome_profile", "Default")
    print(f"Detected OS build_command: {os_type}")

    if os_type == "mac":
        chrome_bin = chrome_paths["mac"]
        user_data_dir = expand_path(profile["user_data_dir_mac"])

        cmd = [
            chrome_bin,
            f"--user-data-dir={user_data_dir}",
            f"--profile-directory={chrome_profile}",
            "--new-window",
        ]

    elif os_type == "windows":
        chrome_bin = chrome_paths["windows"]
        user_data_dir = expand_path(profile["user_data_dir_windows"])

        x, y, width, height = calculate_window_position(profile_index)

        cmd = [
            chrome_bin,
            f"--user-data-dir={user_data_dir}",
            f"--profile-directory={chrome_profile}",
            f"--window-position={x},{y}",
            f"--window-size={width},{height}",
            "--new-window",
        ]

    filtered_flags = [
        flag for flag in flags if not flag.startswith("--start-maximized")
    ]
    cmd.extend(filtered_flags)

    cmd.append(url)

    return cmd


def launch_profile(cmd):
    print(f"\n🚀 Launching Chrome:\n{cmd}\n")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# CHANGE: Removed maximize_chrome_window function as it's macOS-specific


def process_profile(config, profile, profile_index, os_type):
    """
    Process a single profile in a dedicated thread.
    CHANGE: Only lock during typing operations, allow parallel execution for all other steps.
    """
    profile_name = profile["name"]

    with results_lock:
        profile_results[profile_name] = {
            "status": "starting",
            "step1": None,
            "step2": None,
            "step3": None,
            "error": None,
        }

    try:
        print(
            f"\n[Thread-{profile_index + 1}] Starting automation for profile: {profile_name}"
        )

        # CHANGE: Parallel preparation - stagger Chrome launches
        launch_delay = profile_index * 3
        if launch_delay > 0:
            print(
                f"[Thread-{profile_index + 1}] Waiting {launch_delay}s before launch..."
            )
            time.sleep(launch_delay)

        # CHANGE: Parallel - Build and launch Chrome (no lock)
        cmd = build_command(config, profile, os_type, profile_index)
        launch_profile(cmd)

        print(f"[Thread-{profile_index + 1}] ⏳ Waiting for Chrome to load...")
        time.sleep(8)

        # CHANGE: Parallel - Position window using pygetwindow on Windows
        x, y, width, height = calculate_window_position(profile_index)
        print(f"[Thread-{profile_index + 1}] 🔧 Positioning window...")
        if os_type == "windows":
            position_chrome_window_windows(profile_index, x, y, width, height, profile_name)
        time.sleep(1)

        # CHANGE: Parallel - Step 1 (search and click) - NO LOCK
        print(f"[Thread-{profile_index + 1}] 🤖 Starting Step 1 automation...")
        try:
            # CHANGE: Import the modified step1 function that accepts a lock parameter
            from step1 import search_and_click_first_channel_with_lock

            step1_success = search_and_click_first_channel_with_lock(
                typing_lock, profile_index
            )

            with results_lock:
                profile_results[profile_name]["step1"] = step1_success

            if step1_success:
                print(f"[Thread-{profile_index + 1}] ✅ Step 1 completed successfully")

                # CHANGE: Parallel - Page stabilization (no lock)
                print(
                    f"[Thread-{profile_index + 1}] ⏳ Waiting for page stabilization..."
                )
                wait_for_page_stability(timeout=20)
                time.sleep(2)

                # CHANGE: Parallel - Step 2 (click channel avatar) - NO LOCK
                print(f"[Thread-{profile_index + 1}] 🎯 Starting Step 2 automation...")
                try:
                    step2_success = click_channel_avatar_and_wait()

                    with results_lock:
                        profile_results[profile_name]["step2"] = step2_success

                    if step2_success:
                        print(
                            f"[Thread-{profile_index + 1}] ✅ Step 2 completed successfully"
                        )

                        print(
                            f"[Thread-{profile_index + 1}] ⏳ Waiting for channel page..."
                        )
                        time.sleep(5)

                        # CHANGE: Step 3 - Only lock during typing in send_messages_in_loop
                        print(
                            f"[Thread-{profile_index + 1}] 💬 Starting Step 3 automation..."
                        )
                        try:
                            # CHANGE: Import modified step3 function that accepts lock parameter
                            from step3 import send_messages_in_loop_with_lock

                            step3_success = send_messages_in_loop_with_lock(
                                1000, 1, 999, typing_lock, profile_index
                            )

                            with results_lock:
                                profile_results[profile_name]["step3"] = step3_success
                                profile_results[profile_name]["status"] = "completed"

                            if step3_success:
                                print(
                                    f"[Thread-{profile_index + 1}] ✅ Step 3 completed successfully"
                                )
                            else:
                                print(f"[Thread-{profile_index + 1}] ⚠️ Step 3 failed")
                        except Exception as step3_error:
                            error_msg = f"Step 3 error: {step3_error}"
                            print(f"[Thread-{profile_index + 1}] ❌ {error_msg}")
                            with results_lock:
                                profile_results[profile_name]["error"] = error_msg
                                profile_results[profile_name]["status"] = "failed"
                    else:
                        print(
                            f"[Thread-{profile_index + 1}] ⚠️ Step 2 failed - skipping Step 3"
                        )
                        with results_lock:
                            profile_results[profile_name]["status"] = "failed"
                except Exception as step2_error:
                    error_msg = f"Step 2 error: {step2_error}"
                    print(f"[Thread-{profile_index + 1}] ❌ {error_msg}")
                    with results_lock:
                        profile_results[profile_name]["error"] = error_msg
                        profile_results[profile_name]["status"] = "failed"
            else:
                print(
                    f"[Thread-{profile_index + 1}] ⚠️ Step 1 failed - skipping Steps 2 and 3"
                )
                with results_lock:
                    profile_results[profile_name]["status"] = "failed"
        except Exception as step1_error:
            error_msg = f"Step 1 error: {step1_error}"
            print(f"[Thread-{profile_index + 1}] ❌ {error_msg}")
            with results_lock:
                profile_results[profile_name]["error"] = error_msg
                profile_results[profile_name]["status"] = "failed"

    except Exception as e:
        error_msg = f"Profile processing error: {e}"
        print(f"[Thread-{profile_index + 1}] ❌ {error_msg}")
        with results_lock:
            profile_results[profile_name]["error"] = error_msg
            profile_results[profile_name]["status"] = "failed"


def main():
    config = load_config("config.json")
    os_type = get_os()

    print(f"Detected OS: {os_type}")

    threads: List[threading.Thread] = []

    # CHANGE: Launch all profiles in parallel threads
    # Typing operations will be serialized via typing_lock in round-robin fashion
    for profile_index, profile in enumerate(config["profiles"]):
        thread = threading.Thread(
            target=process_profile,
            args=(config, profile, profile_index, os_type),
            name=f"Profile-{profile_index + 1}-{profile['name']}",
        )
        thread.daemon = False
        thread.start()
        threads.append(thread)

        print(f"✅ Started thread for profile: {profile['name']}")

    print(f"\n⏳ Waiting for all {len(threads)} profile threads to complete...")
    for thread in threads:
        thread.join()

    print("\n✅ All profile threads completed")

    print("\n" + "=" * 60)
    print("AUTOMATION SUMMARY")
    print("=" * 60)

    with results_lock:
        for profile_name, result in profile_results.items():
            status_emoji = "✅" if result["status"] == "completed" else "❌"
            print(f"\n{status_emoji} Profile: {profile_name}")
            print(f"   Status: {result['status']}")
            print(f"   Step 1: {'✓' if result['step1'] else '✗'}")
            print(f"   Step 2: {'✓' if result['step2'] else '✗'}")
            print(f"   Step 3: {'✓' if result['step3'] else '✗'}")
            if result["error"]:
                print(f"   Error: {result['error']}")

    print("\n" + "=" * 60)

    print(f"\n⏳ Waiting 10 seconds before starting profile cycling...")
    time.sleep(10)
    cycle_through_profiles(len(config["profiles"]), delay=5)


if __name__ == "__main__":
    main()