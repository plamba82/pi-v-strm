 # Code generated via "Slingshot" 
from playwright.sync_api import sync_playwright
import traceback, sys

def run():
    try:
        with sync_playwright() as p:
            # Try launching headless; switch headless=False to see GUI
            b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            ctx = b.new_context()
            page = ctx.new_page()
            page.goto("https://example.com", timeout=10000)
            print("OK: loaded example.com ->", page.url)
            page.close()
            ctx.close()
            b.close()
    except Exception as e:
        print("ERROR launching Chromium:", repr(e))
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()