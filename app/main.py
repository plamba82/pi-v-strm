import pytest
from playwright.sync_api import sync_playwright

VIDEO_URL = "https://youtu.be/SRTDi0Z80RE?si=qx-xSYA6vkCsgPtX"

def test_video_playback():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set True in CI
        page = browser.new_page()

        # Open video page
        page.goto(VIDEO_URL, timeout=60000)

        # Wait for video element
        page.wait_for_selector("video", timeout=30000)

        video = page.locator("video")

        # Ensure video is loaded enough to play
        page.wait_for_function(
            "document.querySelector('video').readyState >= 3"
        )

        # Check video is playing (not paused)
        is_paused = video.evaluate("v => v.paused")
        assert is_paused is False, "Video is not playing"

        # Check currentTime progresses
        time1 = video.evaluate("v => v.currentTime")
        page.wait_for_timeout(3000)
        time2 = video.evaluate("v => v.currentTime")

        assert time2 > time1, "Video is not progressing"

        browser.close()