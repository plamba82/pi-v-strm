#!/usr/bin/env python3
# scripts/run_webkit_check.py
# Simple Playwright WebKit check: opens URL and prints video element info + some requests.
from playwright.sync_api import sync_playwright
import time

VIDEO_URL = "https://youtu.be/SRTDi0Z80RE?si=qx-xSYA6vkCsgPtX"

with sync_playwright() as p:
    browser = p.webkit.launch(headless=False)  # use visible Safari-like engine
    ctx = browser.new_context()
    page = ctx.new_page()
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    page.goto(VIDEO_URL, timeout=60000)
    time.sleep(5)  # allow player to initialise
    has_video = page.evaluate("!!document.querySelector('video')")
    print("Has <video> element:", has_video)
    if has_video:
        print("readyState:", page.evaluate("document.querySelector('video').readyState"))
        print("paused:", page.evaluate("document.querySelector('video').paused"))
    # Print media-like requests (example)
    media = [u for u in requests if any(ext in u for ext in [".m3u8", ".ts", ".m4s", ".mp4", ".mpd"])]
    print("Detected media requests:", len(media))
    for u in media[:20]:
        print(" ", u)
    page.close()
    ctx.close()
    browser.close()