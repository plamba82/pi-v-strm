import json
import time
import subprocess
import logging
import random
from pathlib import Path
from datetime import datetime
from itertools import permutations

# Import step modules
from step1 import search_youtube, get_search_results_count
from step2 import find_and_click_first_short, get_short_info
from step3 import click_comment_button_and_add_comment

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variable to store comments loaded at application startup
COMMENTS_LIST = []

emojis = ["🙏", "❤️", "😍", "🔁", "🔥", "🔱", "💖", "🌸"]
deities_with_weights = [
    # 🌟 CORE EVERGREEN HIGH VIRALITY (MAX TRAFFIC)
    ("shiv ji", 15),
    ("mahadev", 15),
    ("bholenath", 14),
    ("shiva", 13),
    ("hanuman ji", 15),
    ("pawan putra hanuman", 13),
    ("anjaneya", 10),
    ("krishna ji", 14),
    ("radha krishna", 14),
    ("kanha ji", 12),
    ("madhav", 9),
    ("ram ji", 14),
    ("jai shree ram", 15),
    ("shri ram", 13),
    ("ram lala", 12),
    ("ganesh ji", 13),
    ("ganpati bappa", 14),
    ("vinayak", 10),
    ("vishnu ji", 11),
    ("narayan", 10),
    ("hari vishnu", 9),
    # 🔥 GODDESS POWER (HIGH ENGAGEMENT + EMOTION)
    ("durga maa", 13),
    ("maa durga", 13),
    ("adishakti", 12),
    ("kali maa", 13),
    ("maa kali", 13),
    ("mahakali", 12),
    ("lakshmi maa", 12),
    ("maa lakshmi", 12),
    ("mahalaxmi", 11),
    ("saraswati maa", 11),
    ("maa saraswati", 11),
    ("vidya devi", 8),
    ("parvati maa", 10),
    ("gouri maa", 8),
    # 🛕 REGIONAL HIGH DEMAND (STRONG BUT NICHE)
    ("murugan", 11),
    ("lord murugan", 11),
    ("karthikeya", 10),
    ("subramanya swamy", 10),
    ("ayyappa swamy", 12),
    ("swami samarth", 11),
    ("balaji", 13),
    ("venkateswara swamy", 12),
    ("tirupati balaji", 13),
    ("jagannath", 12),
    ("lord jagannath", 12),
    ("puri jagannath", 11),
    ("khatu shyam ji", 13),
    ("shyam baba", 12),
    ("sai baba", 14),
    ("shirdi sai baba", 13),
    # 🔱 SHAIV SPECIAL FORMS (VIRAL DURING RELIGIOUS SPIKES)
    ("neelkanth mahadev", 11),
    ("rudra shiva", 12),
    ("bhairav baba", 10),
    ("kala bhairav", 10),
    ("nandi mahadev", 9),
    ("ashutosh shiva", 11),
    # 📿 EPIC STORY BASED (VERY STRONG STORY CONTENT)
    ("sita ram", 13),
    ("janki mata", 10),
    ("hanuman ram", 12),
    ("lord rama", 14),
    ("ayodhya ram", 14),
    ("krishna arjun", 11),
    ("gita krishna", 12),
    ("pandurang vitthal", 11),
    ("vitthal rukhmini", 11),
    # 🎉 FESTIVAL SPIKE (VERY HIGH BUT TIME DEPENDENT)
    ("shivratri mahadev", 14),
    ("mahashivratri shiva", 14),
    ("navratri maa durga", 14),
    ("durga puja maa", 13),
    ("janmashtami krishna", 14),
    ("krishna janmashtami", 13),
    ("ganesh chaturthi bappa", 15),
    ("bappa morya", 14),
    ("ram navami ram ji", 14),
    ("diwali laxmi maa", 13),
    # 🌍 REGIONAL DEVOTIONAL (STABLE NICHE TRAFFIC)
    ("ayyarappa", 9),
    ("swami ayyappa", 11),
    ("khandoba maharaj", 8),
    ("mariamman devi", 9),
    ("santoshi maa", 10),
    ("vaishno devi mata", 12),
    ("chamunda maa", 10),
    # 🙏 GENERIC GOD FOR SEO BLENDING
    ("bhagwan shiva", 10),
    ("bhagwan krishna", 10),
    ("bhagwan ram", 11),
    ("ishwar", 7),
    ("parmeshwar", 7),
    ("bhagwan vishnu", 9),
]

phrases = [
    "recently uploaded",
    "new upload",
    "latest",
    "newly added",
    "fresh",
    "recent",
    "last hour",
    "today's",
    "just now",
]

phrase_weights = [10, 9, 8, 9, 10, 8, 7, 6, 10]


deities = [d[0] for d in deities_with_weights]
weights = [d[1] for d in deities_with_weights]


def generate_deity():
    return random.choices(deities, weights=weights, k=1)[0]


def generate_message(deity: str = None) -> str:
    phrase = random.choices(phrases, weights=phrase_weights, k=1)[0]
    deity = deity or generate_deity()
    return f"{phrase} {deity} new #shorts"


def load_comments(comments_file: str = "src/chrome/comments.csv") -> list:
    """
    Load comments from a text file into a list.
    Each line in the file is treated as a separate comment.

    Args:
        comments_file: Path to the comments text file

    Returns:
        List of comment strings

    Raises:
        FileNotFoundError: If the comments file doesn't exist
    """
    try:
        with open(comments_file, "r", encoding="utf-8") as f:
            comments = [line.strip() for line in f if line.strip()]

        if not comments:
            logger.warning(f"No comments found in {comments_file}")
            return []

        logger.info(
            f"Successfully loaded {len(comments)} comments from {comments_file}"
        )
        return comments
    except FileNotFoundError:
        logger.error(f"Comments file not found: {comments_file}")
        raise
    except Exception as e:
        logger.error(f"Failed to load comments from {comments_file}: {e}")
        raise


def load_keywords(keywords_file: str = "src/chrome/keywords.json") -> dict:
    """
    Load keywords configuration from JSON file.

    Args:
        keywords_file: Path to the keywords.json file

    Returns:
        Dictionary containing day-wise keyword arrays

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        json.JSONDecodeError: If the JSON is malformed
    """
    try:
        with open(keywords_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Successfully loaded keywords from {keywords_file}")
        return data
    except FileNotFoundError:
        logger.error(f"Keywords file not found: {keywords_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {keywords_file}: {e}")
        raise


def get_keyword_for_today(keywords_data: dict) -> str:
    """
    Get a random keyword for the current day of the week.

    Args:
        keywords_data: Dictionary containing day-wise keyword arrays

    Returns:
        Random keyword string for today, or empty string if not found

    Raises:
        ValueError: If no keywords found for the current day
    """
    current_day = datetime.now().strftime("%A")
    logger.info(f"Current day: {current_day}")

    day_data = keywords_data.get(current_day)
    if not day_data:
        logger.error(f"No keywords found for {current_day}")
        raise ValueError(f"No keywords configured for {current_day}")

    keyword_objects = day_data.get("keyword", [])
    if not keyword_objects:
        logger.error(f"Empty keyword array for {current_day}")
        raise ValueError(f"Empty keyword array for {current_day}")

    keywords = [kw.get("value") for kw in keyword_objects if kw.get("value")]
    if not keywords:
        logger.error(f"No valid keyword values found for {current_day}")
        raise ValueError(f"No valid keyword values for {current_day}")

    selected_keyword = random.choice(keywords)
    logger.info(f"Selected keyword for {current_day}: '{selected_keyword}'")

    return selected_keyword


def load_profiles(json_path: str) -> dict:
    """
    Load profiles configuration from JSON file.

    Args:
        json_path: Path to the profiles.json file

    Returns:
        Dictionary containing global_url and profiles list

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        json.JSONDecodeError: If the JSON is malformed
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(
            f"Successfully loaded {len(data.get('profiles', []))} profiles from {json_path}"
        )
        return data
    except FileNotFoundError:
        logger.error(f"Profile file not found: {json_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {json_path}: {e}")
        raise


def execute_applescript(script: str) -> tuple[bool, str]:
    """
    Execute an AppleScript and return the result.

    Args:
        script: AppleScript code to execute

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            logger.error(f"AppleScript error: {result.stderr}")
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error("AppleScript execution timed out")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Failed to execute AppleScript: {e}")
        return False, str(e)


def open_chrome_with_url(url: str) -> bool:
    """
    Open Chrome browser and navigate to URL using AppleScript.

    Args:
        url: URL to navigate to

    Returns:
        True if successful, False otherwise
    """
    script = f"""
    tell application "Google Chrome"
        activate
        make new window
        set URL of active tab of front window to "{url}"
    end tell
    """

    success, output = execute_applescript(script)
    if success:
        logger.info(f"Chrome opened and navigated to: {url}")
    else:
        logger.error(f"Failed to open Chrome: {output}")
    return success


def close_chrome_window() -> bool:
    """
    Close the frontmost Chrome window using AppleScript.

    Returns:
        True if successful, False otherwise
    """
    script = """
    tell application "Google Chrome"
        close front window
    end tell
    """

    success, output = execute_applescript(script)
    if success:
        logger.info("Chrome window closed successfully")
    else:
        logger.error(f"Failed to close Chrome window: {output}")
    return success


def process_profile(profile: dict, global_url: str, search_query: str = None) -> None:
    """
    Process a single profile: open browser once, then loop 100 times through search/shorts/comment cycle.

    Args:
        profile: Dictionary containing profile_name and url
        global_url: Fallback URL if profile doesn't specify one
        search_query: Optional search query to override profile URL (from keywords.json)
    """
    profile_name = profile.get("profile_name", "Unknown")
    profile_url = profile.get("url", "")
    # CHANGE: Remove duration usage - browser stays open indefinitely
    # duration = profile.get("duration", 30)

    logger.info(f"Processing profile: {profile_name}")
    # CHANGE: Log that we'll run 100 iterations instead of duration
    logger.info(f"Will execute 100 iterations of search → shorts → comment cycle")

    try:
        # Open Chrome and navigate to YouTube homepage (only once)
        if not open_chrome_with_url(global_url):
            logger.error(f"Failed to open browser for profile: {profile_name}")
            return

        # Wait for YouTube to load
        time.sleep(3)

        # Determine search query
        if search_query:
            logger.info(f"Using keyword-based search query: '{search_query}'")
            final_search_query = search_query
        elif profile_url.startswith("search:"):
            final_search_query = profile_url.replace("search:", "").strip()
            logger.info(f"Using profile search query: '{final_search_query}'")
        else:
            logger.warning("No search query provided, skipping profile")
            return

        # Fibonacci sequence for random sleep durations (in seconds)
        fibonacci_seconds = [1, 2, 3, 5, 8, 13, 21, 29, 37, 45, 60]

        # CHANGE: Loop 100 times through the entire workflow
        for iteration in range(1, 200):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Iteration {iteration}/100 for profile: {profile_name}")
            logger.info(f"{'=' * 60}")

            try:
                deities_temp = generate_deity()
                # Execute Step 1: Search YouTube
                if search_youtube(
                    generate_message(deity=deities_temp), wait_for_results=True
                ):
                    logger.info("✓ Step 1 completed: Search successful")

                    results_count = get_search_results_count()
                    if results_count > 0:
                        logger.info(f"Found {results_count} video results")
                else:
                    logger.error(
                        f"✗ Step 1 failed in iteration {iteration}: Search unsuccessful"
                    )
                    # CHANGE: Continue to next iteration instead of breaking
                    continue

                # Execute Step 2: Find and play first Short + Like
                logger.info("\n" + "=" * 60)
                logger.info(
                    f"Starting Step 2 (Iteration {iteration}): Shorts automation + Like"
                )
                logger.info("=" * 60)

                if find_and_click_first_short():
                    logger.info(
                        "✓ Step 2 completed: Short loaded and liked successfully"
                    )

                    short_info = get_short_info()
                    if short_info:
                        logger.info(
                            f"Playing Short: {short_info.get('title', 'Unknown')}"
                        )
                        logger.info(
                            f"Duration: {short_info.get('duration', 'Unknown')}s"
                        )

                    # Execute Step 3: Add comment
                    logger.info("\n" + "=" * 60)
                    logger.info(
                        f"Starting Step 3 (Iteration {iteration}): Comment automation"
                    )
                    logger.info("=" * 60)

                    if COMMENTS_LIST:
                        selected_comment = random.choice(COMMENTS_LIST)
                        selected_comment = (
                            "Jai " + deities_temp + " Ji" + selected_comment
                        )
                        logger.info(f"Selected random comment: '{selected_comment}'")

                        if click_comment_button_and_add_comment(
                            comment_text=selected_comment
                        ):
                            logger.info(
                                "✓ Step 3 completed: Comment added successfully"
                            )
                        else:
                            logger.warning(
                                f"✗ Step 3 failed in iteration {iteration}: Could not add comment"
                            )
                    else:
                        logger.warning(
                            f"✗ Step 3 skipped in iteration {iteration}: No comments available"
                        )
                else:
                    logger.warning(
                        f"✗ Step 2 failed in iteration {iteration}: Could not load Short"
                    )
                    # CHANGE: Continue to next iteration instead of breaking
                    continue

            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")
                # CHANGE: Continue to next iteration instead of breaking
                continue

            # CHANGE: Add random Fibonacci sleep at the end of each iteration
            sleep_time = random.choice(fibonacci_seconds)
            logger.info(f"Sleeping for {sleep_time} seconds (Fibonacci random wait)")
            time.sleep(sleep_time)
        # CHANGE: Log completion of all iterations
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Completed all 100 iterations for profile: {profile_name}")
        logger.info(f"{'=' * 60}")

    except Exception as e:
        logger.error(f"Unexpected error for profile {profile_name}: {e}")
    # CHANGE: Remove finally block that closes browser - keep it open
    # finally:
    #     close_chrome_window()
    #     logger.info(f"Browser closed for profile: {profile_name}")


def check_accessibility_permissions() -> bool:
    """
    Check if Terminal/Python has accessibility permissions.

    Returns:
        True if permissions are granted, False otherwise
    """
    script = """
    tell application "System Events"
        return true
    end tell
    """

    success, _ = execute_applescript(script)
    if not success:
        logger.warning(
            "⚠️  Accessibility permissions required!\n"
            "Go to: System Preferences → Security & Privacy → Privacy → Accessibility\n"
            "Add Terminal (or your Python IDE) to the allowed apps list."
        )
    return success


def main():
    """
    Main entry point: load keywords, load comments, load profiles, and process each one sequentially.
    """
    try:
        # Load keywords at application startup
        keywords_data = load_keywords("src/chrome/keywords.json")

        # Get keyword for current day
        try:
            # daily_keyword = get_keyword_for_today(keywords_data)
            daily_keyword = generate_message()
        except ValueError as e:
            logger.error(f"Failed to get keyword for today: {e}")
            logger.error("Exiting due to missing keyword configuration")
            return

        # Load comments at application startup (global scope)
        global COMMENTS_LIST
        COMMENTS_LIST = load_comments("src/chrome/comments.csv")

        if not COMMENTS_LIST:
            logger.warning("No comments loaded. Comments will not be added to Shorts.")

        # Check accessibility permissions first
        if not check_accessibility_permissions():
            logger.error("Accessibility permissions not granted. Exiting.")
            return

        # Load profiles from JSON
        config = load_profiles("profiles.json")

        global_url = config.get("global_url", "https://www.youtube.com/")
        profiles = config.get("profiles", [])

        if not profiles:
            logger.warning("No profiles found in configuration")
            return

        # Process each profile
        for idx, profile in enumerate(profiles, 1):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing profile {idx}/{len(profiles)}")
            logger.info(f"{'=' * 60}")
            process_profile(profile, global_url, search_query=daily_keyword)

        logger.info("\n" + "=" * 60)
        logger.info("All profiles processed successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
