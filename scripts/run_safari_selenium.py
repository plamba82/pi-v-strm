#!/usr/bin/env python3
# scripts/run_safari_selenium.py
# Requires macOS Safari and safaridriver enabled (Develop -> Allow Remote Automation)
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

VIDEO_URL = "https://youtu.be/SRTDi0Z80RE?si=qx-xSYA6vkCsgPtX"
# Create Safari driver (macOS only)
driver = webdriver.Safari()
driver.get(VIDEO_URL)
time.sleep(5)
try:
    video = driver.find_element(By.TAG_NAME, "video")
    ready = driver.execute_script("return document.querySelector('video').readyState")
    paused = driver.execute_script("return document.querySelector('video').paused")
    print("Has <video>:", bool(video))
    print("readyState:", ready, "paused:", paused)
finally:
    driver.quit()