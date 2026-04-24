import json
import os
import platform
import subprocess
import time
from pathlib import Path

# Import the step modules
from step1 import search_and_click_first_channel
from step2 import click_channel_avatar_and_wait
from step3 import send_live_chat_message


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
    try:
        if platform.system().lower() == "darwin":
            # macOS - get screen size using system_profiler
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
            )
            # Parse for resolution - this is a simplified approach
            # For production, consider using pyobjc or other libraries
            return 1920, 1080  # Default fallback
        else:
            # Windows - could use wmi or other methods
            return 1920, 1080  # Default fallback
    except:
        return 1920, 1080  # Default fallback


def calculate_window_position(profile_index, total_profiles=6):
    """Calculate window position and size for 3x2 grid layout."""
    screen_width, screen_height = get_screen_dimensions()

    # Window dimensions: 1/3 screen width, 1/2 screen height
    window_width = screen_width // 3
    window_height = screen_height // 2

    # Create 3x2 grid (3 columns, 2 rows)
    cols = 3
    rows = 2

    # Calculate position based on profile index
    col = profile_index % cols
    row = profile_index // cols

    x = col * window_width
    y = row * window_height

    print(
        f"Profile {profile_index + 1}: Position ({x}, {y}), Size ({window_width}x{window_height})"
    )

    return x, y, window_width, window_height


def position_chrome_window_macos(profile_index, x, y, width, height):
    """Position Chrome window using AppleScript on macOS."""
    # Wait for window to be created and get the most recent window
    time.sleep(2)  # Allow window creation to complete

    script = f"""
    tell application "Google Chrome"
        set windowCount to count of windows
        if windowCount > 0 then
            -- Get the most recently created window (last in the list)
            set targetWindow to window 1
            set bounds of targetWindow to {{{x}, {y}, {x + width}, {y + height}}}
            return "Window positioned at " & {x} & "," & {y}
        else
            return "No windows found"
        end if
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Positioned Profile {profile_index + 1} window at ({x}, {y})")
            return True
        else:
            print(f"❌ Failed to position Profile {profile_index + 1}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error positioning Profile {profile_index + 1}: {e}")
        return False


def switch_to_profile(profile_index):
    """Switch keyboard focus to a specific Chrome profile window using AppleScript."""
    if platform.system().lower() != "darwin":
        print("Profile switching only supported on macOS")
        return False

    script = f"""
    tell application "Google Chrome"
        set windowCount to count of windows
        if windowCount >= {profile_index + 1} then
            set index of window {profile_index + 1} to 1
            activate
            return "Switched to profile {profile_index + 1}"
        else
            return "Profile window not found"
        end if
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Switched focus to Profile {profile_index + 1}")
            return True
        else:
            print(
                f"❌ Failed to switch to Profile {profile_index + 1}: {result.stderr}"
            )
            return False
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

    # Check page load state multiple times
    stable_checks = 0
    max_checks = 3
    check_interval = 2

    for attempt in range(timeout // check_interval):
        js_check_stability = """
        (function() {
            // Check if page is still loading
            if (document.readyState !== 'complete') {
                return 'loading';
            }
            
            // Check for YouTube-specific loading indicators
            var loadingSpinners = document.querySelectorAll('[role="progressbar"], .loading, .spinner');
            if (loadingSpinners.length > 0) {
                return 'loading';
            }
            
            // Check if we're on a search results page with channel results
            var channelResults = document.querySelectorAll('ytd-channel-renderer, .ytd-channel-renderer');
            if (channelResults.length > 0) {
                return 'search_results_ready';
            }
            
            // Check if we're on a channel page
            var channelPage = document.querySelector('#channel-header, ytd-c4-tabbed-header-renderer');
            if (channelPage) {
                return 'channel_page_ready';
            }
            
            return 'unknown_page';
        })();
        """

        try:
            from step1 import execute_javascript_in_chrome

            success, result = execute_javascript_in_chrome(js_check_stability)

            if success and result in ["search_results_ready", "channel_page_ready"]:
                stable_checks += 1
                if stable_checks >= max_checks:
                    print(f"✅ Page stabilized: {result}")
                    return True
            else:
                stable_checks = 0  # Reset counter if page is still loading

        except Exception as e:
            print(f"⚠️ Error checking page stability: {e}")

        time.sleep(check_interval)

    print("⚠️ Page stability timeout reached")
    return False


# -----------------------------
# Chrome Launcher
# -----------------------------


def build_command(config, profile, os_type, profile_index=0):
    chrome_paths = config["chrome_paths"]
    flags = config.get("flags", [])

    url = profile["url"]
    chrome_profile = profile.get("chrome_profile", "Default")
    print(f"Detected OS build_command: {os_type}")
    print(
        f"Detected OS profile build_command: {expand_path(profile['user_data_dir_mac'])}"
    )

    if os_type == "mac":
        chrome_bin = chrome_paths["mac"]
        user_data_dir = expand_path(profile["user_data_dir_mac"])

        cmd = [
            chrome_bin,
            f"--user-data-dir={user_data_dir}",
            f"--profile-directory={chrome_profile}",
            "--new-window",  # Force new window instead of tab
        ]

    elif os_type == "windows":
        chrome_bin = chrome_paths["windows"]
        user_data_dir = expand_path(profile["user_data_dir_windows"])

        # Calculate window position for this profile (3x2 grid)
        x, y, width, height = calculate_window_position(profile_index)

        cmd = [
            chrome_bin,
            f"--user-data-dir={user_data_dir}",
            f"--profile-directory={chrome_profile}",
            f"--window-position={x},{y}",
            f"--window-size={width},{height}",
            "--new-window",
        ]

    # Add global flags (remove --start-maximized as it conflicts with positioning)
    filtered_flags = [
        flag for flag in flags if not flag.startswith("--start-maximized")
    ]
    cmd.extend(filtered_flags)

    # Add URL last
    cmd.append(url)

    return cmd


def launch_profile(cmd):
    print(f"\n🚀 Launching Chrome:\n{cmd}\n")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# -----------------------------
# Main Runner
# -----------------------------
def maximize_chrome_window():
    """Maximize the active Chrome window using AppleScript on macOS."""
    if platform.system().lower() != "darwin":
        print("Window maximization only supported on macOS")
        return False

    script = """
    tell application "Google Chrome"
        activate
        delay 0.5
        tell front window
            tell application "System Events"
                keystroke "f" using {control down, command down}
            end tell
        end tell
        return "Window maximized"
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("✅ Chrome window maximized")
            return True
        else:
            print(f"❌ Failed to maximize window: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error maximizing window: {e}")
        return False


def main():
    config = load_config("config.json")
    os_type = get_os()

    print(f"Detected OS: {os_type}")

    # Launch all profiles
    for profile_index, profile in enumerate(config["profiles"]):
        try:
            cmd = build_command(config, profile, os_type, profile_index)
            launch_profile(cmd)

            # Wait for Chrome to fully load
            print(f"⏳ Waiting for Chrome to load for profile: {profile['name']}")
            time.sleep(5)  # Initial load time

            # Position window using system-level commands (macOS only)
            if os_type == "mac":
                x, y, width, height = calculate_window_position(profile_index)
                print(f"🔧 Positioning window for Profile {profile_index + 1}")
                position_chrome_window_macos(profile_index, x, y, width, height)
                time.sleep(1)  # Allow positioning to complete

            # Execute Step 1: Search and click first channel
            print(f"🤖 Starting Step 1 automation for profile: {profile['name']}")
            try:
                maximize_chrome_window()
                step1_success = search_and_click_first_channel()
                if step1_success:
                    print(
                        f"✅ Step 1 completed successfully for profile: {profile['name']}"
                    )

                    # Wait for page to stabilize after Step 1
                    print(
                        f"⏳ Waiting for page stabilization after Step 1 for profile: {profile['name']}"
                    )
                    wait_for_page_stability(
                        timeout=20
                    )  # Extended timeout for slow connections

                    # Additional wait for slow connections
                    time.sleep(2)

                    # Execute Step 2: Click channel avatar and wait for page load
                    print(
                        f"🎯 Starting Step 2 automation for profile: {profile['name']}"
                    )

                    try:
                        step2_success = click_channel_avatar_and_wait()
                        if step2_success:
                            print(
                                f"✅ Step 2 completed successfully for profile: {profile['name']}"
                            )

                            # Wait for channel page to fully load before Step 3
                            print(
                                f"⏳ Waiting for channel page stabilization for profile: {profile['name']}"
                            )
                            time.sleep(5)  # Allow channel page to fully load

                            # Execute Step 3: Send live chat message
                            print(
                                f"💬 Starting Step 3 automation for profile: {profile['name']}"
                            )

                            try:
                                step3_success = send_live_chat_message()
                                if step3_success:
                                    print(
                                        f"✅ Step 3 completed successfully for profile: {profile['name']}"
                                    )
                                else:
                                    print(
                                        f"⚠️ Step 3 failed for profile: {profile['name']}"
                                    )
                            except Exception as step3_error:
                                print(
                                    f"❌ Step 3 error for profile {profile['name']}: {step3_error}"
                                )
                        else:
                            print(
                                f"⚠️ Step 2 failed for profile: {profile['name']} - skipping Step 3"
                            )
                    except Exception as step2_error:
                        print(
                            f"❌ Step 2 error for profile {profile['name']}: {step2_error}"
                        )
                else:
                    print(
                        f"⚠️ Step 1 failed for profile: {profile['name']} - skipping Steps 2 and 3"
                    )
            except Exception as step1_error:
                print(f"❌ Step 1 error for profile {profile['name']}: {step1_error}")

        except Exception as e:
            print(f"❌ Failed for profile {profile['name']}: {e}")

    # After all profiles are launched, start profile cycling
    print(f"\n⏳ Waiting 10 seconds before starting profile cycling...")
    time.sleep(10)

    # Start cycling through profiles for keyboard input
    cycle_through_profiles(len(config["profiles"]), delay=5)


if __name__ == "__main__":
    main()
