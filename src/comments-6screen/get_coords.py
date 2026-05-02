import asyncio
import pyautogui
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])

        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        await page.goto("https://www.youtube.com/live/WXMTKy5JqyI?si=gUJ1m4dHPQp51pQB")

        # 🔍 Locate element (change selector as needed)
        locator = page.locator("text=More information")

        # Wait until visible
        await locator.wait_for(state="visible")

        # 📦 Get bounding box (relative to page viewport)
        box = await locator.bounding_box()

        if not box:
            print("Element not found")
            return

        print("Bounding Box:", box)

        # 🧮 Convert to screen coordinates
        # Get browser window position
        window = await page.evaluate(
            """
            () => {
                return {
                    x: window.screenX,
                    y: window.screenY,
                    innerHeight: window.innerHeight,
                    outerHeight: window.outerHeight
                }
            }
        """
        )

        # Chrome toolbar height adjustment
        chrome_toolbar_height = window["outerHeight"] - window["innerHeight"]

        screen_x = window["x"] + box["x"] + box["width"] / 2
        screen_y = window["y"] + chrome_toolbar_height + box["y"] + box["height"] / 2

        print(f"Screen Coordinates: ({screen_x}, {screen_y})")

        # 🎯 Move & click using PyAutoGUI
        pyautogui.moveTo(screen_x, screen_y, duration=0.5)
        pyautogui.click()

        # Optional: type something
        pyautogui.write("Hello from hybrid automation!", interval=0.05)

        await asyncio.sleep(5)
        await browser.close()


asyncio.run(main())
