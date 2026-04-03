#!/usr/bin/env python3
"""
scripts/check_video_state.py

Robust Playwright diagnostic for video pages.
Usage:
  python scripts/check_video_state.py --url "https://abc.com/shorts/BlM4BzShEvI?feature=share" [--headless]

Features:
 - Handles browser/context/page launch failures with clear diagnostics.
 - Prints helpful hints (PWDEBUG, playwright install).
 - Optionally leaves the browser open for manual inspection (--keep-open).
 - Captures basic video element state and media-like requests.
"""
from __future__ import annotations
import argparse
import sys
import time
import traceback
from typing import List, Tuple

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Error as PWError

MEDIA_EXTS = (".m3u8", ".mpd", ".m4s", ".ts", ".mp4", "videoplayback", "googlevideo")

def is_media_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    return any(ext in lower for ext in MEDIA_EXTS)

def launch_browser(pw, headless: bool, launch_args: List[str], timeout: int = 60000):
    """Try to launch Chromium and return the browser instance or raise with diagnostics."""
    try:
        browser = pw.chromium.launch(headless=headless, args=launch_args, timeout=timeout)
        return browser
    except Exception as e:
        # Provide helpful diagnostics
        print("ERROR: Failed to launch Chromium.")
        print("Exception:", repr(e))
        print("Common causes:")
        print(" - Playwright browsers not installed. Run: python -m playwright install")
        print(" - OS sandbox/permission issues (try '--no-sandbox' launch arg)")
        print(" - Corrupt Playwright caches / user-data dirs")
        print("Tip: re-run with PWDEBUG=1 for verbose browser logs.")
        traceback.print_exc()
        raise

def run(url: str, headless: bool = False, keep_open: bool = False) -> int:
    print(f"Diagnostic start: {url}")
    print(f"Headless: {headless}  Keep open: {keep_open}")
    captured: List[Tuple[str, str]] = []

    # Conservative launch args that often avoid sandbox/profile crashes
    launch_args = [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
    ]

    try:
        with sync_playwright() as p:
            try:
                browser = launch_browser(p, headless=headless, launch_args=launch_args)
            except Exception:
                # launch_browser already printed diagnostics
                return 2

            ctx = None
            page = None
            try:
                # Create a fresh ephemeral context (avoid persistent profile reuse)
                print("Creating browser context...")
                ctx = browser.new_context()
                print("Creating new page...")
                page = ctx.new_page()
            except Exception as e:
                print("ERROR: Failed to create browser context or new page.")
                print("This often means the browser binary crashed immediately after launch.")
                print("Exception:", repr(e))
                traceback.print_exc()
                # Attempt to close browser gracefully
                try:
                    browser.close()
                except Exception:
                    pass
                return 3

            # Attach basic request/response capture
            page.on("request", lambda r: captured.append(("REQ", r.url)))
            page.on("response", lambda r: captured.append(("RES", r.url)))

            try:
                print("Navigating to target URL...")
                page.goto(url, timeout=45000)
            except PWTimeoutError as te:
                print("Timeout while loading the page:", te)
            except Exception as e:
                print("Error during page.goto():", repr(e))
                traceback.print_exc()

            # Small wait for JS-driven requests to start
            time.sleep(2)

            # Inspect video element state (if present)
            try:
                has_video = page.evaluate("!!document.querySelector('video')")
                if not has_video:
                    print("No <video> element found in DOM (yet). The page may use JS/XHR to obtain manifests or an iframe/custom player.")
                else:
                    try:
                        ready = page.evaluate("document.querySelector('video').readyState")
                        paused = page.evaluate("document.querySelector('video').paused")
                        current_time = page.evaluate("document.querySelector('video').currentTime")
                        buffered_len = page.evaluate("document.querySelector('video').buffered.length")
                        print(f"Video element state: readyState={ready}, paused={paused}, currentTime={current_time}, bufferedRanges={buffered_len}")
                    except Exception as e:
                        print("Warning: failed to read video element properties:", repr(e))
            except Exception as e:
                print("Warning: evaluating page for <video> failed:", repr(e))

            # Attempt to provoke network activity by muted play (non-destructive)
            try:
                page.evaluate("v => (v && (v.muted = true), v && v.play())", page.locator("video"))
            except Exception:
                # ignore failures: some pages throw when calling play()
                pass

            # Wait to capture streaming requests
            wait_after = 6
            print(f"Waiting {wait_after}s to capture network activity...")
            time.sleep(wait_after)

            media_reqs = [u for t, u in captured if is_media_url(u)]
            print(f"Captured total events: {len(captured)}, media-like URLs: {len(media_reqs)}")
            if media_reqs:
                print("Example media requests (up to 50):")
                for u in media_reqs[:50]:
                    print(" ", u)
            else:
                print("No media-like HTTP requests detected.")
                print("Possible reasons:")
                print(" - Player fetches manifests via JS API calls that use non-standard URLs")
                print(" - Media delivered via WebRTC/blob: URLs (not HTTP segments)")
                print(" - Autoplay blocked; try headful and unmute manually")
                print(" - Server requires headers/cookies (inspect browser DevTools)")

            if keep_open and not headless:
                # Leave browser open for manual inspection
                hold = 12
                print(f"Keep-open: leaving browser open for {hold}s for manual inspection...")
                time.sleep(hold)

            # Clean shutdown
            try:
                if page:
                    page.close()
            except Exception:
                pass
            try:
                if ctx:
                    ctx.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

            return 0

    except Exception as outer:
        print("Top-level failure:", repr(outer))
        traceback.print_exc()
        return 4

def main():
    parser = argparse.ArgumentParser(description="Playwright video page diagnostic")
    parser.add_argument("--url", required=True, help="Page URL to load")
    parser.add_argument("--headless", action="store_true", help="Run headless (default: visible)")
    parser.add_argument("--keep-open", action="store_true", help="Keep a visible browser open briefly for manual inspection")
    args = parser.parse_args()

    # Default behavior: visible browser (helps debugging). --headless makes it headless.
    headless = args.headless
    rc = run(args.url, headless=headless, keep_open=args.keep_open)
    if rc != 0:
        print("Diagnostics finished with errors (exit code", rc, "). See above output for hints.")
        print("Recommended next steps:")
        print(" - Ensure playwright browsers installed: python -m playwright install")
        print(" - Re-run with PWDEBUG=1 for verbose logs: PWDEBUG=1 python scripts/check_video_state.py --url <URL> --headless")
        print(" - If browser crashes immediately, try deleting playwright caches (backup first):")
        print("     rm -rf ~/.cache/ms-playwright ~/.local/share/ms-playwright")
    else:
        print("Diagnostics finished OK.")
    sys.exit(rc)

if __name__ == "__main__":
    main()