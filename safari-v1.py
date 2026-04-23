#!/usr/bin/env python3
import subprocess
import time
import json
import sys
import argparse
from typing import List, Dict, Any, Optional
from multiprocessing import Process


# ----------------------------
# AppleScript helper
# ----------------------------
def _run_osascript(cmd: str, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-e", cmd],
        check=False,
        capture_output=capture,
        text=True,
    )


# ----------------------------
# Safari helpers
# ----------------------------
def _activate_safari(verbose=False) -> bool:
    res = _run_osascript('tell application "Safari" to activate')
    if res.returncode != 0:
        if verbose:
            print("DEBUG: Failed to activate Safari:", res.stderr)
        return False
    if verbose:
        print("DEBUG: Safari activated")
    return True


def create_window_for_profile(
    profile_name: Optional[str] = None, verbose=False
) -> Optional[int]:
    """
    Create a new Safari window (document) and return its index.
    IMPORTANT CHANGE: create the new document and capture it into a variable (nw)
    then operate on that 'nw' window instance so title setting is deterministic.
    Returns None on failure.
    """
    # sanitize profile_name to safely embed inside AppleScript double-quoted JS string
    safe_title = ""
    if profile_name:
        safe_title = profile_name.replace("\\", "\\\\").replace('"', '\\"')

    # Use local variable 'nw' for the newly-created window so another process/window
    # becoming front does not change which window we operate on.
    script = f"""
    tell application "Safari"
        activate
        set nw to make new document
        delay 0.25
        try
            set t to current tab of nw
            set URL of t to "about:blank"
            do JavaScript "document.title = \\"{safe_title}\\"" in t
        end try
        set idx to index of nw
        return idx
    end tell
    """
    res = _run_osascript(script)
    if res.returncode != 0:
        if verbose:
            print("DEBUG: create_window_for_profile failed:", res.stderr)
        return None
    out = (res.stdout or "").strip()
    try:
        return int(out)
    except Exception:
        if verbose:
            print("DEBUG: create_window_for_profile parse failed, stdout:", out)
        return None


def open_url(url: str, window_index: Optional[int] = None, verbose=False) -> bool:
    """
    Open URL in the specified Safari window (current tab).
    If window_index is None, uses window 1 (original behavior).
    """
    win = window_index if window_index is not None else 1
    script = f"""
    tell application "Safari"
        activate
        if (count of windows) = 0 then
            make new document
        end if
        set URL of current tab of window {win} to "{url}"
    end tell
    """
    res = _run_osascript(script)
    success = res.returncode == 0
    if verbose:
        print(f"DEBUG: Open URL {url} in window {win} result: {success}")
        if not success:
            print("DEBUG: stderr:", res.stderr)
    return success


def perform_search_accessibility(
    search_term: str, window_index: Optional[int] = None, verbose=False
) -> bool:
    """
    Bring the target window to front (so keystrokes go to it), then use System Events to type into address bar and submit.
    Note: GUI-focus is global — accessibility keystrokes will route to the frontmost window.
    """
    win = window_index if window_index is not None else 1
    script = f"""
    tell application "Safari"
        activate
        try
            set index of window {win} to 1
        end try
    end tell
    delay 0.25
    tell application "System Events"
        tell process "Safari"
            try
                keystroke "l" using {{command down}} -- focus address bar
                delay 0.3
                keystroke "{search_term}"
                delay 0.3
                key code 36 -- Enter
                delay 2 -- wait for results to load
                return true
            on error
                return false
            end try
        end tell
    end tell
    """
    res = _run_osascript(script)
    out = (res.stdout or "").strip().lower()
    success = "true" in out
    if verbose:
        print(
            f"DEBUG: Accessibility search '{search_term}' in window {win} result: {success}"
        )
        if not success:
            print("DEBUG: stderr:", res.stderr)
    return success


def play_video(window_index: Optional[int] = None, verbose=False) -> bool:
    """
    Bring the target window to front and attempt to click a Play button using Accessibility.
    Use the same window index when locating buttons so we target the correct window.
    """
    win = window_index if window_index is not None else 1
    script = f"""
    tell application "Safari"
        activate
        try
            set index of window {win} to 1
        end try
    end tell
    delay 0.25
    tell application "System Events"
        tell process "Safari"
            try
                set playButtons to buttons of window {win}
                repeat with btn in playButtons
                    try
                        if (name of btn contains "Play" or name of btn contains "play") then
                            click btn
                            exit repeat
                        end if
                    end try
                end repeat
                return true
            on error
                return false
            end try
        end tell
    end tell
    """
    res = _run_osascript(script)
    out = (res.stdout or "").strip().lower()
    success = "true" in out
    if verbose:
        print(f"DEBUG: play video in window {win} result: {success}")
        if not success:
            print("DEBUG: stderr:", res.stderr)
    return success


# ----------------------------
# Automation executor
# ----------------------------
def execute_automation_steps(
    steps: List[Dict[str, Any]], window_index: Optional[int] = None, verbose=False
) -> bool:
    for i, step in enumerate(steps):
        step_type = step.get("type")
        success = False

        if verbose:
            print(
                f"DEBUG: Executing step {i+1}/{len(steps)}: {step_type} (window {window_index})"
            )

        if step_type == "open_url":
            url = step.get("url")
            if url:
                success = open_url(url, window_index, verbose)

        elif step_type == "search":
            search_term = step.get("search_term")
            if search_term:
                success = perform_search_accessibility(
                    search_term, window_index, verbose
                )

        elif step_type == "go_to_absolute_url":
            abs_url = step.get("url")
            if abs_url:
                success = open_url(abs_url, window_index, verbose)

        elif step_type == "play_video":
            success = play_video(window_index, verbose)

        else:
            print(f"❌ Unknown step type: {step_type}")
            return False

        if not success:
            print(f"❌ Failed at step {i+1}: {step_type}")
            return False

        # Fixed 3-second delay between steps
        if verbose:
            print("DEBUG: Waiting 3s before next step")
        time.sleep(3)

    return True


# ----------------------------
# Per-profile runner (worker)
# ----------------------------
def run_single_profile(
    profile: Dict[str, Any],
    profile_index: int,
    profile_name: Optional[str] = None,
    verbose=False,
):
    """
    profile_name is explicitly passed in from the parent to avoid any loop-capture issues.
    """
    # Prefer explicitly passed profile_name; fallback to profile dict
    profile_name = profile_name or profile.get(
        "profile_name", f"profile_{profile_index}"
    )
    automation_steps = profile.get("automation_steps", [])

    # Fill in default URLs if missing (profile-level or global fallback handled by caller)
    for step in automation_steps:
        if step.get("type") in ["open_url", "go_to_absolute_url"] and "url" not in step:
            # parent pre-filled with profile/global fallback; leave as-is if still missing
            step["url"] = step.get("url")

    print(f"🚀 [{profile_name}] Starting (worker)")

    if not _activate_safari(verbose):
        print(f"❌ [{profile_name}] Failed to activate Safari")
        return

    # Create a dedicated window for this profile (pass profile_name so document.title is set)
    win_index = create_window_for_profile(profile_name=profile_name, verbose=verbose)
    if win_index is None:
        print(f"❌ [{profile_name}] Failed to create a new Safari window")
        return

    # Execute automation steps targeting this window
    success = execute_automation_steps(
        automation_steps, window_index=win_index, verbose=verbose
    )

    if success:
        print(f"✅ [{profile_name}] Profile completed")
    else:
        print(f"❌ [{profile_name}] Profile failed")


# ----------------------------
# Profile runner (spawns workers)
# ----------------------------
def run_profiles_from_json(json_path: str, verbose=False):
    with open(json_path, "r") as f:
        config = json.load(f)

    global_url = config.get("global_url")
    profiles = config.get("profiles", [])

    # Pre-fill missing step urls with profile.url or global_url
    for prof in profiles:
        for step in prof.get("automation_steps", []):
            if (
                step.get("type") in ["open_url", "go_to_absolute_url"]
                and "url" not in step
            ):
                step["url"] = prof.get("url", global_url)

    # Spawn one worker Process per profile to run concurrently.
    # Stagger process starts by 3 seconds so each profile window is launched 3s apart.
    processes: List[Process] = []
    for idx, prof in enumerate(profiles):
        profile_name = prof.get("profile_name", f"profile_{idx}")
        p = Process(target=run_single_profile, args=(prof, idx, profile_name, verbose))
        p.start()
        processes.append(p)
        if verbose:
            print(
                f"DEBUG: Spawned worker PID={p.pid} for profile idx={idx} ({profile_name})"
            )
        # delay 3s between spawning processes so Safari window creations are staggered
        time.sleep(3)

    # Wait for all to finish
    for p in processes:
        p.join()
        if verbose:
            print(f"DEBUG: Worker PID={p.pid} exited with code {p.exitcode}")


# ----------------------------
# Argument parser
# ----------------------------
def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Open Safari profiles from JSON config (concurrent)."
    )
    p.add_argument(
        "--config", "-c", default="profiles.json", help="Path to JSON config file"
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Enable debug output")
    return p.parse_args(argv)


# ----------------------------
# Main
# ----------------------------
def main(argv):
    args = parse_args(argv)
    run_profiles_from_json(args.config, args.verbose)


if __name__ == "__main__":
    main(sys.argv[1:])
