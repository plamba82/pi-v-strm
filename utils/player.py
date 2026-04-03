# utils/player.py
# Playwright-backed VideoPlayer helper. Intended to be used with Playwright WebKit
# (Safari-like engine). Works with the `page` fixture provided in tests/test_video.py.
from typing import Optional


class VideoPlayer:
    """
    Helper to find an HTML5 <video>, wait until playable, start playback (muted),
    and introspect playback state (currentTime, buffered ranges).
    Designed to be used with Playwright page objects (e.g., WebKit).
    """

    def __init__(self, page):
        self.page = page
        self.video_selector = "video"

    def wait_for_player(self, timeout: int = 30000) -> bool:
        """
        Wait for a <video> element to appear on the page.
        Returns True if found within timeout, else False.
        Uses a visible-element wait first, then a JS existence fallback.
        """
        try:
            self.page.wait_for_selector(self.video_selector, timeout=timeout)
            return True
        except Exception:
            try:
                self.page.wait_for_function(
                    "!!document.querySelector('video')",
                    timeout=timeout
                )
                return True
            except Exception:
                return False

    def wait_until_playable(self, timeout: int = 30000) -> None:
        """
        Wait until the video has enough data to play (readyState >= 3).
        Will raise Playwright timeout if not satisfied within timeout.
        """
        self.page.wait_for_function(
            "document.querySelector('video') && document.querySelector('video').readyState >= 3",
            timeout=timeout
        )

    def ensure_playing(self, timeout: int = 8000) -> bool:
        """
        Try to start playback reliably in automated environments:
         - mute the video element
         - call play()
         - wait until !paused

        Returns True when playback is observed within timeout, False otherwise.
        """
        if not self.wait_for_player(timeout=timeout):
            return False

        try:
            # Mute and attempt play() in page context; some sites return a Promise.
            self.page.locator(self.video_selector).evaluate(
                "v => (v.muted = true, v.play())"
            )
        except Exception:
            # If evaluate throws, continue to wait for playing state
            pass

        try:
            self.page.wait_for_function(
                "document.querySelector('video') && !document.querySelector('video').paused",
                timeout=timeout
            )
            return True
        except Exception:
            return False

    def is_playing(self) -> bool:
        """Return True if the video element reports not paused."""
        try:
            return bool(self.page.locator(self.video_selector).evaluate(
                "v => !!v && !v.paused"
            ))
        except Exception:
            return False

    def get_current_time(self) -> float:
        """Return currentTime (seconds) of the video element."""
        return float(self.page.locator(self.video_selector).evaluate(
            "v => v.currentTime"
        ))

    def is_progressing(self, wait_time: int = 3000) -> bool:
        """
        Check that currentTime advances over wait_time milliseconds.
        Returns True if progressed, False otherwise.
        """
        try:
            t1 = self.get_current_time()
        except Exception:
            return False

        self.page.wait_for_timeout(wait_time)

        try:
            t2 = self.get_current_time()
        except Exception:
            return False

        return (t2 - t1) > 0.1  # tolerate small rounding

    def get_buffered_ranges(self) -> int:
        """Return the number of buffered ranges (0 if unavailable)."""
        try:
            return int(self.page.locator(self.video_selector).evaluate(
                "v => (v && v.buffered) ? v.buffered.length : 0"
            ))
        except Exception:
            return 0