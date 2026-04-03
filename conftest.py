# conftest.py
# Robust Playwright fixtures for pytest designed to avoid profile / user-data-dir issues.
import os
import tempfile
import pytest
from playwright.sync_api import sync_playwright

# CHANGE: allow overriding headless via env for easy local debugging
DEFAULT_HEADLESS = os.environ.get("PLAYWRIGHT_HEADLESS", "1") != "0"

@pytest.fixture(scope="session")
def pw():
    """Start Playwright once per test session and close at the end."""
    # CHANGE: use sync_playwright context manager to ensure proper startup/cleanup
    with sync_playwright() as p:
        yield p
    # sync_playwright will be closed when context manager exits

@pytest.fixture(scope="session")
def browser(pw):
    """
    Launch a single browser for the entire session. Use conservative args to avoid
    profile/sandbox problems seen on some macOS/Linux setups.
    """
    launch_args = [
        "--disable-dev-shm-usage",      # avoid /dev/shm issues in containers
        "--no-sandbox",                 # avoids common sandbox permission issues
        "--disable-setuid-sandbox",     # further sandbox safety
        "--disable-gpu",                # GPU can cause platform specific crashes
    ]

    headless = DEFAULT_HEADLESS

    try:
        browser = pw.chromium.launch(headless=headless, args=launch_args)
    except Exception as e:
        # CHANGE: re-raise after printing to help diagnostics
        print("ERROR: failed to launch Chromium. Exception:", e)
        print("Hint: run `python -m playwright install` and check PWDEBUG=1 logs.")
        raise

    yield browser

    # Teardown: try-close safely
    try:
        browser.close()
    except Exception:
        pass

@pytest.fixture(scope="function")
def context(browser, request):
    """
    Create a fresh context per test. Use an ephemeral user-data dir by default (Playwright does that)
    but if a persistent directory is required, set PLAYWRIGHT_PERSIST_DIR env var.
    """
    persist_dir = os.environ.get("PLAYWRIGHT_PERSIST_DIR")
    ctx = None
    if persist_dir:
        # Optionally use a temp subdir of the requested persist dir to avoid collisions.
        tmp = tempfile.mkdtemp(prefix="pw_persist_", dir=persist_dir)
        ctx = browser.new_context(storage_state=None)  # still ephemeral; choose persistent_context if needed
    else:
        ctx = browser.new_context()

    yield ctx

    try:
        ctx.close()
    except Exception:
        pass

@pytest.fixture(scope="function")
def page(context):
    """Yield a new page bound to the function-scoped context."""
    page = context.new_page()
    yield page
    try:
        page.close()
    except Exception:
        pass