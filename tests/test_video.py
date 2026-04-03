# tests/test_video.py
# This test file forces Playwright to use WebKit (Safari-like engine) by providing
# a local `page` fixture that launches p.webkit. Set PLAYWRIGHT_HEADLESS=0 to run headful.
import os
import pytest
from typing import List
from playwright.sync_api import sync_playwright
from utils.player import VideoPlayer
from utils.url_utils import extract_video_id

# Replace with the URL you want to test
VIDEO_URL = "https://youtu.be/SRTDi0Z80RE?si=qx-xSYA6vkCsgPtX"

# Playback duration to assert (milliseconds)
PLAYBACK_MS = 15000


@pytest.fixture(scope="function")
def page():
    """
    Test-local page fixture that launches Playwright WebKit (Safari-like).
    This overrides any global `page` fixture from conftest.py for tests in this module.
    """
    headless = os.environ.get("PLAYWRIGHT_HEADLESS", "1") != "0"
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            yield page
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass


def test_video_page_loads(page):
    page.goto(VIDEO_URL, timeout=60000)
    # Robust check: ensure expected video id is present in final URL (handles redirects)
    video_id = extract_video_id(VIDEO_URL)
    assert video_id in page.url


def test_video_id_extraction():
    video_id = extract_video_id(VIDEO_URL)
    assert video_id == "SRTDi0Z80RE"


def test_video_playback(page):
    page.goto(VIDEO_URL)

    player = VideoPlayer(page)

    assert player.wait_for_player(), "No <video> element found on the page"
    player.wait_until_playable()

    # Ensure playback starts (mute + play); fail with clear message if blocked
    assert player.ensure_playing(timeout=10000), "Failed to start playback (autoplay may be blocked)"

    # Verify the video progresses over a 15 second window
    assert player.is_progressing(wait_time=PLAYBACK_MS), f"Video did not progress during {PLAYBACK_MS/1000:.0f}s playback"
    # Additionally ensure it's considered playing at the end of the window
    assert player.is_playing(), "Video is not playing after playback window"


def test_video_buffering(page):
    page.goto(VIDEO_URL)

    player = VideoPlayer(page)

    assert player.wait_for_player(), "No <video> element found on the page"
    player.wait_until_playable()

    # Ensure playback so buffering will show
    assert player.ensure_playing(timeout=10000), "Failed to start playback (autoplay may be blocked)"

    # Wait the full playback window to allow buffering to occur
    page.wait_for_timeout(PLAYBACK_MS)

    buffered = player.get_buffered_ranges()
    assert buffered > 0, f"No buffering detected during {PLAYBACK_MS/1000:.0f}s"


def _is_media_request(req) -> bool:
    """
    Heuristics to detect media-like requests from captured Request objects.
    """
    try:
        rt = getattr(req, "resource_type", None)
    except Exception:
        rt = None

    url = (req.url or "").lower()
    if rt == "media":
        return True

    MEDIA_PATTERNS = [
        ".m4s", ".mp4", ".m3u8", ".mpd", ".ts", ".webm", "videoplayback", "googlevideo.com", "/videoplayback?"
    ]
    if any(p in url for p in MEDIA_PATTERNS):
        return True

    try:
        resp = req.response()
    except Exception:
        resp = None

    if resp:
        ct = (resp.headers.get("content-type") or "").lower()
        cl = resp.headers.get("content-length")
        if ("video" in ct) or ("audio" in ct) or ("application/vnd.apple.mpegurl" in ct) or ("application/dash+xml" in ct):
            return True
        try:
            if cl and int(cl) > 100000:
                return True
        except Exception:
            pass

    return False


def test_video_network_requests(page):
    captured = []
    page.on("request", lambda r: captured.append(r))

    page.goto(VIDEO_URL)
    player = VideoPlayer(page)

    assert player.wait_for_player(), "No <video> element found on the page"
    player.wait_until_playable()
    assert player.ensure_playing(timeout=10000), "Failed to start playback (autoplay may be blocked)"

    # Wait the full playback window to capture streaming requests emitted during playback
    page.wait_for_timeout(PLAYBACK_MS)

    media_requests: List[str] = []
    for req in captured:
        try:
            if _is_media_request(req):
                media_requests.append(req.url)
        except Exception:
            continue

    # Deduplicate while preserving order
    seen = set()
    dedup = []
    for u in media_requests:
        if u not in seen:
            seen.add(u)
            dedup.append(u)

    assert len(dedup) > 0, f"No video stream requests detected during {PLAYBACK_MS/1000:.0f}s"