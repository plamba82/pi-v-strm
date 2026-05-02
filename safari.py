#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
import threading
import json
from typing import Optional


def _run_osascript(cmd: str, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-e", cmd],
        check=False,
        capture_output=capture,
        text=True,
    )


def _activate_safari(verbose: bool = False) -> bool:
    res = _run_osascript('tell application "Safari" to activate')
    if res.returncode != 0:
        if verbose:
            print("DEBUG: activate returned non-zero:", res.returncode, res.stderr)
        return False
    if verbose:
        print("DEBUG: Safari activation AppleScript executed.")
    return True


def _click_via_file_newwindow(profile_name: str, verbose: bool = False) -> bool:
    item_name = f"New {profile_name} Window"
    script = f"""
    tell application "Safari" to activate
    delay 0.25
    tell application "System Events"
        tell process "Safari"
            set mb to menu bar 1
            set clicked to false
            repeat with m in menu bar items of mb
                try
                    if name of m is "File" then
                        set fileMenu to menu 1 of m
                        repeat with mi in menu items of fileMenu
                            try
                                if name of mi is "New Window" then
                                    click mi
                                    delay 0.3
                                    try
                                        click menu item "{item_name}" of menu 1 of mi
                                        set clicked to true
                                        exit repeat
                                    end try
                                end if
                            end try
                        end repeat
                    end if
                end try
                if clicked then exit repeat
            end repeat
            if clicked is false then
                repeat with m in menu bar items of mb
                    try
                        click m
                        delay 0.3
                        try
                            click menu item "{item_name}" of menu 1 of m
                            set clicked to true
                            exit repeat
                        end try
                        repeat with mi in menu items of menu 1 of m
                            try
                                if name of mi is "New Window" then
                                    click mi
                                    delay 0.3
                                    try
                                        click menu item "{item_name}" of menu 1 of mi
                                        set clicked to true
                                        exit repeat
                                    end try
                                end if
                            end try
                        end repeat
                    end try
                    if clicked then exit repeat
                end repeat
            end if
            return clicked
        end tell
    end tell
    """
    if verbose:
        print("DEBUG: running AppleScript to click File -> New Window ->", item_name)
    res = _run_osascript(script)
    if res.returncode != 0:
        if verbose:
            print("DEBUG: osascript returned non-zero:", res.returncode, res.stderr)
        return False
    out = (res.stdout or "").strip().lower()
    if "true" in out:
        if verbose:
            print("DEBUG: AppleScript reported success (true).")
        return True
    if res.returncode == 0:
        if verbose:
            print(
                "DEBUG: AppleScript exit code 0 (treating as success). stdout:",
                repr(res.stdout),
            )
        return True
    return False


def _get_safari_window_count() -> int:
    script = 'tell application "Safari" to count windows'
    res = _run_osascript(script)
    try:
        return int((res.stdout or "0").strip())
    except Exception:
        return 0


def _close_safari_window_by_index(index: int, verbose: bool = False) -> bool:
    script = f'tell application "Safari" to close window {index}'
    res = _run_osascript(script)
    if res.returncode != 0:
        if verbose:
            print(f"DEBUG: failed to close Safari window {index}:", res.stderr)
        return False
    if verbose:
        print(f"DEBUG: closed Safari window {index} (osascript exit 0).")
    return True


def _close_new_window_after_delay(
    window_index: int, delay_seconds: int, verbose: bool = False
) -> None:
    def _worker():
        if verbose:
            print(
                f"DEBUG: will close Safari window {window_index} in {delay_seconds} seconds..."
            )
        try:
            time.sleep(delay_seconds)
            if _close_safari_window_by_index(window_index, verbose=verbose):
                print(
                    f"ℹ️ Closed Safari window {window_index} after {delay_seconds} second(s)."
                )
            else:
                print(
                    f"⚠️ Failed to close Safari window {window_index} after {delay_seconds} second(s)."
                )
        except Exception as e:
            if verbose:
                print(f"DEBUG: exception in close thread: {e}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def open_safari_with_profile_name(
    profile_name: str,
    url: Optional[str] = None,
    method: str = "auto",
    verbose: bool = False,
    close_after: int = 5,
) -> bool:
    if not profile_name:
        print(f"❌ Profile name is required.")
        return False

    if not _activate_safari(verbose=verbose):
        print(
            "❌ Failed to activate Safari. Ensure Safari is installed and accessible."
        )
        return False
    time.sleep(0.25)

    before_count = _get_safari_window_count()

    tried = []
    methods = []
    if method == "file":
        methods = ["file"]
    elif method == "keystroke":
        methods = ["keystroke"]
    else:
        methods = ["file", "keystroke"]

    success = False
    for m in methods:
        tried.append(m)
        try:
            if m == "file":
                if verbose:
                    print(
                        "DEBUG: attempting File -> New Window -> New <profile> Window"
                    )
                ok = _click_via_file_newwindow(profile_name, verbose=verbose)
                if ok:
                    success = True
                    time.sleep(0.6)
                    break
                else:
                    if verbose:
                        print("DEBUG: file-menu attempt did not click the target item.")
                    continue
            # Keystroke fallback removed: no index mapping without PROFILE_MAP
        except subprocess.CalledProcessError:
            print(f"❌ Automation permission error while trying {m}.")
            print("   Grant Accessibility/Automation access:")
            print(
                "   System Settings → Privacy & Security → Automation (or Accessibility)."
            )
            print("   Enable 'System Events' and 'Safari' for Terminal / Python.")
            return False
        except Exception as e:
            if verbose:
                print(f"DEBUG: method {m} raised exception: {e}")
            continue

    if not success:
        print("❌ All methods attempted but none succeeded. Methods tried:", tried)
        print("Hints:")
        print(
            " - Ensure the profile menu label is exactly 'New <profile-name> Window' under File -> New Window."
        )
        print(
            " - Grant Terminal/Python Accessibility/Automation permissions (System Settings → Privacy & Security → Automation/Accessibility)."
        )
        print(" - Run with --verbose to see AppleScript stderr/stdout.")
        return False

    if url:
        time.sleep(2)
        try:
            subprocess.run(["open", "-a", "Safari", url], check=True)
            print(f"   → Loaded: {url}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to open URL: {url}")

    print(
        f"✅ Attempted profile selection for: {profile_name!r} (methods tried: {tried})"
    )

    after_count = _get_safari_window_count()
    new_window_index = after_count if after_count > before_count else after_count

    if close_after and close_after > 0:
        _close_new_window_after_delay(new_window_index, close_after, verbose=verbose)
        if verbose:
            print(
                f"DEBUG: scheduled to close Safari window {new_window_index} after {close_after}s"
            )

    return True


def run_profiles_from_json(json_path, method="auto", verbose=False):
    with open(json_path, "r") as f:
        config = json.load(f)
    global_url = config.get("global_url")
    profiles = config.get("profiles", [])
    threads = []
    for i, prof in enumerate(profiles):
        profile_name = prof["profile_name"]
        url = prof.get("url", global_url)
        duration = prof.get("duration", 15)
        t = threading.Thread(
            target=open_safari_with_profile_name,
            args=(profile_name, url, method, verbose, duration),
        )
        t.start()
        threads.append(t)
        if i < len(profiles) - 1:
            time.sleep(3)  # 3-second delay between launches
    for t in threads:
        t.join()


def parse_args(argv):
    p = argparse.ArgumentParser(description="Open Safari profiles from JSON config.")
    p.add_argument(
        "--config", "-c", default="profiles.json", help="Path to JSON config file"
    )
    p.add_argument("--method", "-m", choices=["auto", "file"], default="auto")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable debug output")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    run_profiles_from_json(args.config, args.method, args.verbose)


if __name__ == "__main__":
    main(sys.argv[1:])
