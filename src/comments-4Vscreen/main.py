import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, List
import sys
import random  # CHANGE: Added for randomized launch delays
from messages import (
    generate_gods_name,
)  # CHANGE: Updated import to use function for dynamic message generation

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from auto_type import send_in_window, messages as auto_type_messages


def load_config(path: str = "config.json") -> Dict:
    """Load profile configuration from JSON file."""
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)


def get_os_type() -> str:
    """Detect operating system."""
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    elif system == "windows":
        return "windows"
    else:
        raise Exception(f"Unsupported OS: {system}")


def expand_path(path: str) -> str:
    """Expand ~ and environment variables in path."""
    return os.path.expanduser(os.path.expandvars(path))


def get_screen_dimensions():
    """Get screen dimensions based on platform"""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
            )
            # Parse for resolution - simplified approach
            import re

            resolution_match = re.search(r"Resolution: (\d+) x (\d+)", result.stdout)
            if resolution_match:
                width = int(resolution_match.group(1))
                height = int(resolution_match.group(2))
                return width, height
            else:
                # Fallback to common resolution
                return 1920, 1080
        elif platform.system() == "Windows":
            result = subprocess.run(
                [
                    "wmic",
                    "path",
                    "Win32_VideoController",
                    "get",
                    "CurrentHorizontalResolution,CurrentVerticalResolution",
                    "/format:value",
                ],
                capture_output=True,
                text=True,
            )
            lines = result.stdout.strip().split("\n")
            width = height = None
            for line in lines:
                if "CurrentHorizontalResolution=" in line:
                    width = int(line.split("=")[1])
                elif "CurrentVerticalResolution=" in line:
                    height = int(line.split("=")[1])
            if width and height:
                return width, height
            else:
                return 1920, 1080
        else:
            # Linux fallback
            return 1920, 1080
    except Exception:
        # Fallback to common resolution if detection fails
        return 1920, 1080


def calculate_window_position(
    profile_index: int, window_width: int = 490, window_height: int = None
):
    """
    Calculate window position for 1×4 horizontal layout with 10px gaps and full screen height.

    Args:
        profile_index: Index of the profile (0-based)
        window_width: Width of each window (default: 490)
        window_height: Height of each window (default: full screen height)

    Returns:
        Tuple of (x, y, width, height) coordinates
    """
    # CHANGE: Get screen dimensions and use full height
    screen_width, screen_height = get_screen_dimensions()

    if window_height is None:
        window_height = screen_height  # CHANGE: Use full screen height

    # CHANGE: Modified for 1×4 horizontal layout with full height
    HORIZONTAL_SPACING = window_width - 10  # 490 - 10 = 480px
    START_X = 0
    START_Y = 0

    # CHANGE: All windows in single row, positioned horizontally with full height
    x = START_X + (profile_index * HORIZONTAL_SPACING)
    y = START_Y

    return (x, y, window_width, window_height)


def build_chrome_command(
    chrome_path: str,
    user_data_dir: str,
    profile_name: str,
    url: str,
    os_type: str,
    flags: List[str] = None,
) -> List[str]:
    """
    Build Chrome launch command WITHOUT position (position applied after load).

    Args:
        chrome_path: Path to Chrome executable
        user_data_dir: Chrome user data directory
        profile_name: Chrome profile directory name
        url: URL to open
        os_type: Operating system type ('mac' or 'windows')
        flags: Additional Chrome flags

    Returns:
        Command as list of strings
    """
    # CHANGE: Get screen dimensions for full height window
    screen_width, screen_height = get_screen_dimensions()

    # CHANGE: Use full screen height instead of fixed 360px
    cmd = [
        chrome_path,
        f"--user-data-dir={expand_path(user_data_dir)}",
        f"--profile-directory={profile_name}",
        "--new-window",
        f"--window-size=490,{screen_height}",  # CHANGE: Use full screen height
        "--force-device-scale-factor=1",
        "--disable-features=CalculateNativeWinOcclusion",
    ]

    if flags:
        cmd.extend(flags)

    cmd.append(url)

    return cmd


# CHANGE: Updated function to use full screen height
def reposition_window_macos(profile_index: int):
    """
    Reposition a Chrome window to its 1×4 grid position using AppleScript with full screen height.

    Args:
        profile_index: Index of the profile window (0-based)
    """
    x, y, width, height = calculate_window_position(
        profile_index
    )  # CHANGE: Get full dimensions

    script = f"""
    tell application "Google Chrome"
        set windowCount to count of windows
        if windowCount > {profile_index} then
            set targetWindow to window {profile_index + 1}
            set bounds of targetWindow to {{{x}, {y}, {x + width}, {y + height}}}
            return "Window repositioned"
        else
            return "Window not found"
        end if
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(
                f"✅ Repositioned Profile {profile_index + 1} to ({x}, {y}) with size {width}x{height}"
            )
        else:
            print(
                f"⚠️ Failed to reposition Profile {profile_index + 1}: {result.stderr}"
            )
    except Exception as e:
        print(f"❌ Error repositioning Profile {profile_index + 1}: {e}")


# CHANGE: Updated function to use full screen height
def reposition_window_windows(profile_index: int):
    """
    Reposition a Chrome window to its 1×4 grid position using PowerShell with full screen height.

    Args:
        profile_index: Index of the profile window (0-based)
    """
    x, y, width, height = calculate_window_position(
        profile_index
    )  # CHANGE: Get full dimensions

    script = f"""
    $chrome = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ""}}
    if ($chrome) {{
        $windows = $chrome | Select-Object -ExpandProperty MainWindowHandle
        if ($windows.Count -gt {profile_index}) {{
            $window = $windows[{profile_index}]
            Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {{
                    [DllImport("user32.dll")]
                    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
                }}
"@
            [Win32]::MoveWindow($window, {x}, {y}, {width}, {height}, $true)
        }}
    }}
    """

    try:
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(
                f"✅ Repositioned Profile {profile_index + 1} to ({x}, {y}) with size {width}x{height}"
            )
        else:
            print(f"⚠️ Failed to reposition Profile {profile_index + 1}")
    except Exception as e:
        print(f"❌ Error repositioning Profile {profile_index + 1}: {e}")


def execute_javascript_macos(profile_index: int, js_code: str):
    """
    Execute JavaScript in a specific Chrome window using AppleScript.

    Args:
        profile_index: Index of the profile window (0-based)
        js_code: JavaScript code to execute
    """
    script = f"""
    tell application "Google Chrome"
        set windowCount to count of windows
        if windowCount > {profile_index} then
            set targetWindow to window {profile_index + 1}
            tell targetWindow
                set activeTab to active tab
                execute activeTab javascript "{js_code}"
            end tell
            return "JavaScript executed"
        else
            return "Window not found"
        end if
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Executed JavaScript in Profile {profile_index + 1}")
        else:
            print(
                f"⚠️ Failed to execute JavaScript in Profile {profile_index + 1}: {result.stderr}"
            )
    except Exception as e:
        print(f"❌ Error executing JavaScript in Profile {profile_index + 1}: {e}")


def execute_javascript_windows(profile_index: int, js_code: str):
    """
    Execute JavaScript in a specific Chrome window using PowerShell.

    Args:
        profile_index: Index of the profile window (0-based)
        js_code: JavaScript code to execute
    """
    script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $chrome = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ""}}
    if ($chrome) {{
        $windows = $chrome | Select-Object -ExpandProperty MainWindowHandle
        if ($windows.Count -gt {profile_index}) {{
            $window = $windows[{profile_index}]
            [System.Windows.Forms.SendKeys]::SendWait("^+j")
            Start-Sleep -Milliseconds 500
            [System.Windows.Forms.SendKeys]::SendWait("{js_code}{{ENTER}}")
        }}
    }}
    """

    try:
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(f"✅ Executed JavaScript in Profile {profile_index + 1}")
        else:
            print(f"⚠️ Failed to execute JavaScript in Profile {profile_index + 1}")
    except Exception as e:
        print(f"❌ Error executing JavaScript in Profile {profile_index + 1}: {e}")


def scroll_window_macos(profile_index: int, scroll_count: int = 3):
    """
    Scroll down in a specific Chrome window using AppleScript.

    Args:
        profile_index: Index of the profile window (0-based)
        scroll_count: Number of times to scroll down (default: 3)
    """
    scroll_js = "window.scrollBy(0, window.innerHeight);"

    for i in range(scroll_count):
        execute_javascript_macos(profile_index, scroll_js)
        time.sleep(0.3)
        print(f"   📜 Scroll {i + 1}/{scroll_count} completed")


def scroll_window_windows(profile_index: int, scroll_count: int = 3):
    """
    Scroll down in a specific Chrome window using PowerShell.

    Args:
        profile_index: Index of the profile window (0-based)
        scroll_count: Number of times to scroll down (default: 3)
    """
    scroll_js = "window.scrollBy(0, window.innerHeight);"

    for i in range(scroll_count):
        execute_javascript_windows(profile_index, scroll_js)
        time.sleep(0.3)
        print(f"   📜 Scroll {i + 1}/{scroll_count} completed")


def switch_chrome_window_macos(profile_index: int):
    """
    Switch to a specific Chrome window using AppleScript on macOS.

    Args:
        profile_index: Index of the profile window to activate (0-based)
    """
    script = f"""
    tell application "Google Chrome"
        activate
        set windowCount to count of windows
        if windowCount > {profile_index} then
            set index of window {profile_index + 1} to 1
            return "Switched to window {profile_index + 1}"
        else
            return "Window not found"
        end if
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Switched to Profile {profile_index + 1}")
        else:
            print(
                f"⚠️ Failed to switch to Profile {profile_index + 1}: {result.stderr}"
            )
    except Exception as e:
        print(f"❌ Error switching to Profile {profile_index + 1}: {e}")


def switch_chrome_window_windows(profile_index: int):
    """
    Switch to a specific Chrome window using PowerShell on Windows.

    Args:
        profile_index: Index of the profile window to activate (0-based)
    """
    script = f"""
    $chrome = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ""}}
    if ($chrome) {{
        $windows = $chrome | Select-Object -ExpandProperty MainWindowHandle
        if ($windows.Count -gt {profile_index}) {{
            $window = $windows[{profile_index}]
            Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {{
                    [DllImport("user32.dll")]
                    public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")]
                    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                }}
"@
            [Win32]::ShowWindow($window, 9)
            [Win32]::SetForegroundWindow($window)
        }}
    }}
    """

    try:
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(f"✅ Switched to Profile {profile_index + 1}")
        else:
            print(f"⚠️ Failed to switch to Profile {profile_index + 1}")
    except Exception as e:
        print(f"❌ Error switching to Profile {profile_index + 1}: {e}")


def process_profile(profile_index: int, os_type: str, iteration: int):
    """
    Process a single profile: activate → scroll 3 times → type message → submit.

    Args:
        profile_index: Index of the profile (0-based)
        os_type: Operating system type
        iteration: Current iteration number (for logging)
    """
    print(f"\n🔄 [Iteration {iteration}] Processing Profile {profile_index + 1}...")

    if os_type == "mac":
        switch_chrome_window_macos(profile_index)
    else:
        switch_chrome_window_windows(profile_index)
    time.sleep(1)

    print(f"   📜 Scrolling 3 times...")
    # if os_type == "mac":
    #     scroll_window_macos(profile_index, scroll_count=3)
    # else:
    #     scroll_window_windows(profile_index, scroll_count=3)
    # time.sleep(2)
    print(f"   ✉️ Typing and submitting message...")
    send_in_window(profile_index, generate_gods_name("vishnu"))
    print(f"✅ [Iteration {iteration}] Profile {profile_index + 1} completed")


def launch_chrome_profiles(config: Dict, os_type: str):
    """
    STEP 1: Launch Chrome instances with random delays (1-5s).
    STEP 2: Wait for all to load, then apply 1×4 horizontal positioning with full screen height.
    STEP 3: Run 20-iteration loop to process all profiles.

    Args:
        config: Configuration dictionary from config.json
        os_type: Operating system type
    """
    chrome_path = config["chrome_paths"][os_type]
    profiles = config["profiles"]
    flags = config.get("flags", [])

    # CHANGE: Updated maximum profile limit from 6 to 4 for 1×4 layout
    if len(profiles) > 4:
        print("⚠️ Warning: Maximum 4 profiles supported (1×4 horizontal layout)")
        print(f"   Only the first 4 profiles will be launched\n")
        profiles = profiles[:4]

    # CHANGE: Display screen dimensions being used
    screen_width, screen_height = get_screen_dimensions()
    print(f"📺 Detected screen resolution: {screen_width}x{screen_height}")
    print(f"   Each profile window will be 490x{screen_height} (full height)\n")

    # ========== STEP 1: Launch all profiles with random delays ==========
    print(
        f"🚀 STEP 1: Launching {len(profiles)} Chrome profile(s) with random delays (1-5s)...\n"
    )

    for profile_index, profile in enumerate(profiles):
        user_data_dir_key = f"user_data_dir_{os_type}"

        # CHANGE: Build command without position flag
        cmd = build_chrome_command(
            chrome_path=chrome_path,
            user_data_dir=profile[user_data_dir_key],
            profile_name=profile["chrome_profile"],
            url=profile["url"],
            os_type=os_type,
            flags=flags,
        )

        print(f"🚀 Launching Profile {profile_index + 1}: {profile['name']}")
        print(f"   URL: {profile['url']}")

        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✅ Profile {profile_index + 1} launched successfully")

            # CHANGE: Random delay between 1-5 seconds before next launch
            delay = random.uniform(1.0, 5.0)
            print(f"   ⏱️  Waiting {delay:.1f}s before next launch...\n")
            time.sleep(delay)
        except Exception as e:
            print(f"❌ Failed to launch Profile {profile_index + 1}: {e}\n")
            continue

    # CHANGE: Wait for all profiles to fully load before positioning
    print("⏳ Waiting for all profiles to fully load...")
    time.sleep(8)  # CHANGE: Increased wait time to ensure all windows are ready

    # ========== STEP 2: Apply 1×4 horizontal positioning with full height after all profiles loaded ==========
    print(
        "\n📐 STEP 2: Applying 1×4 horizontal positioning with full screen height to all windows...\n"
    )

    for profile_index in range(len(profiles)):
        x, y, width, height = calculate_window_position(
            profile_index
        )  # CHANGE: Get full dimensions

        # CHANGE: Updated positioning description for 1×4 layout with full height
        print(
            f"📍 Positioning Profile {profile_index + 1} to Position {profile_index + 1} (X={x}, Y={y}, Size={width}x{height})"
        )

        if os_type == "mac":
            reposition_window_macos(profile_index)
        else:
            reposition_window_windows(profile_index)

        time.sleep(0.3)  # CHANGE: Small delay between repositioning operations

    # CHANGE: Updated completion message for 1×4 layout with full height
    print(
        "\n✅ All windows positioned in 1×4 horizontal layout with full screen height\n"
    )

    # CHANGE: Inject click tracking JavaScript
    print("🔧 Injecting click tracking JavaScript...")
    click_tracker_js = "document.addEventListener('click', function(e) { console.log('You clicked at x, y = ' + e.clientX + ', ' + e.clientY); });"

    for profile_index in range(len(profiles)):
        if os_type == "mac":
            execute_javascript_macos(profile_index, click_tracker_js)
        else:
            execute_javascript_windows(profile_index, click_tracker_js)
        time.sleep(0.5)

    print("✅ STEP 2 completed - All profiles positioned and configured\n")

    # ========== STEP 3: 20-iteration loop to process all profiles ==========
    print("🔄 STEP 3: Starting 20-iteration loop...\n")
    TOTAL_ITERATIONS = 2000

    for iteration in range(1, TOTAL_ITERATIONS + 1):
        print(f"\n{'='*60}")
        print(f"🔁 ITERATION {iteration}/{TOTAL_ITERATIONS}")
        print(f"{'='*60}")

        for profile_index in range(len(profiles)):
            process_profile(profile_index, os_type, iteration)
            time.sleep(0.1)

        print(f"\n✅ Iteration {iteration}/{TOTAL_ITERATIONS} completed")

    print(f"\n{'='*60}")
    print(f"🎉 All {TOTAL_ITERATIONS} iterations completed successfully!")
    print(f"{'='*60}\n")


def main():
    """Main entry point."""
    try:
        config = load_config("config.json")
        os_type = get_os_type()
        print(f"Detected OS: {os_type}\n")

        launch_chrome_profiles(config, os_type)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Please create a config.json file with the required configuration.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
