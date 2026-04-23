#!/usr/bin/env python3
"""
Small diagnostic helper for macOS AppleScript automation.
Usage:
  python3 scripts/diagnostics.py --config profiles.json          # quick checks
  python3 scripts/diagnostics.py --config profiles.json --run-g  # runs g.py --verbose and captures output
"""
import argparse
import json
import shutil
import subprocess
import sys
import os


def check_python():
    print("Python executable:", sys.executable)
    try:
        v = sys.version.splitlines()[0]
        print("Python version:", v)
    except Exception:
        pass


def check_osascript():
    path = shutil.which("osascript")
    print("osascript path:", path)
    if not path:
        print(
            "ERROR: osascript not found in PATH. On macOS it should exist at /usr/bin/osascript."
        )
        return
    try:
        res = subprocess.run(
            ["osascript", "-e", 'return "OK"'], capture_output=True, text=True
        )
        print("osascript returncode:", res.returncode)
        print("osascript stdout:", repr(res.stdout.strip()))
        print("osascript stderr:", repr(res.stderr.strip()))
        if res.returncode != 0:
            print(
                "WARN: osascript returned non-zero. Check Accessibility permissions and osascript output above."
            )
    except Exception as e:
        print("EXCEPTION running osascript:", e)


def check_profiles(config_path):
    print("Checking config file:", config_path)
    if not os.path.exists(config_path):
        print("ERROR: Config file not found.")
        return
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
        profiles = cfg.get("profiles", [])
        print("Loaded config. global_url:", cfg.get("global_url"))
        print("Profiles found (count):", len(profiles))
        for i, p in enumerate(profiles):
            print(
                f"  {i+1}. profile_name='{p.get('profile_name')}', steps={len(p.get('automation_steps', []))}"
            )
    except Exception as e:
        print("ERROR parsing config:", e)


def run_g_script(g_path, config_path):
    if not os.path.exists(g_path):
        print("ERROR: g.py not found at", g_path)
        return
    cmd = [sys.executable, g_path, "--config", config_path, "--verbose"]
    print("Running:", " ".join(cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print("g.py exit code:", p.returncode)
        print("g.py STDOUT:")
        print(p.stdout or "(no stdout)")
        print("g.py STDERR:")
        print(p.stderr or "(no stderr)")
    except subprocess.TimeoutExpired:
        print("ERROR: g.py timed out after 120s.")
    except Exception as e:
        print("ERROR running g.py:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="profiles.json", help="Path to profiles.json")
    ap.add_argument(
        "--run-g", action="store_true", help="Run g.py --verbose after checks"
    )
    ap.add_argument("--g-path", default="g.py", help="Path to g.py")
    args = ap.parse_args()

    check_python()
    print("-----")
    check_osascript()
    print("-----")
    check_profiles(args.config)
    print("-----")
    print(
        "Accessibility note: if System Events / Safari actions fail, grant Accessibility permissions (Terminal/Python) in System Settings → Privacy & Security → Accessibility."
    )
    if args.run_g:
        print("----- Running g.py now -----")
        run_g_script(args.g_path, args.config)


if __name__ == "__main__":
    main()
