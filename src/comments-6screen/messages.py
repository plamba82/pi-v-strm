# src/comments-6screen/messages.py
import logging
import subprocess
from typing import Tuple
import time
import random

# CHANGE: Configure logger for this module
logger = logging.getLogger(__name__)

# CHANGE: Set up basic logging configuration if not already configured
if not logger.handlers:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# Deity-specific word collections
DEITY_DATA = {
    "ram": {
        "roots": [
            "ram",
            "rama",
            "raghava",
            "raghunath",
            "raghupati",
            "dasharathi",
            "ayodhyapati",
            "koshalapati",
            "raghukulbhushan",
            "maryada",
            "purushottam",
            "sitapati",
            "janakivallabh",
            "kodanda",
            "dhanurdhar",
            "raghuvar",
            "raghunandan",
            "raghukul",
            "raghuraj",
            "ramchandra",
            "ramji",
        ],
        "prefixes": [
            "jai",
            "jai jai",
            "shree",
            "bhagwan",
            "prabhu",
            "maharaj",
            "raghupati",
            "jai shree",
            "om",
            "har har",
        ],
        "epithets": [
            "ji",
            "bhagwan",
            "prabhu",
            "swami",
            "maharaj",
            "dev",
            "nath",
            "pati",
            "vallabh",
            "dhar",
            "bhushan",
            "kulbhushan",
            "var",
            "nandan",
            "raj",
            "chandra",
            "avatar",
            "purushottam",
            "maryada",
        ],
    },
    "hanuman": {
        "roots": [
            "hanuman",
            "bajrang",
            "bajrangbali",
            "pavanputra",
            "maruti",
            "kesari",
            "anjaneya",
            "sankatmochan",
            "mahaveer",
            "ramdoot",
            "veer",
            "balaji",
            "kapish",
            "rudra",
            "bhakt",
            "rambhakt",
            "veerhanuman",
            "jaihanuman",
            "hanumanta",
            "mahakaal",
            "chiranjeevi",
            "mahavir",
            "pavansut",
            "anjani",
        ],
        "prefixes": [
            "jai",
            "jai jai",
            "veer",
            "mahaveer",
            "pavan",
            "bajrang",
            "sankat",
            "ram",
            "jai bajrang",
            "om",
            "shree",
        ],
        "epithets": [
            "bali",
            "veer",
            "mahaveer",
            "sankatmochan",
            "ramdoot",
            "pavanputra",
            "anjaneya",
            "kesarinandan",
            "bhakt",
            "rambhakt",
            "sevak",
            "rakshak",
            "kapish",
            "kapiraj",
            "bal",
            "shakti",
            "tej",
            "mahatej",
            "gada",
            "gadaadhari",
            "veerbal",
            "chiranjeevi",
            "prabhu",
            "swami",
            "nath",
        ],
    },
    "vishnu": {
        "roots": [
            "vishnu",
            "narayana",
            "hari",
            "govind",
            "gopal",
            "keshav",
            "madhav",
            "damodar",
            "vasudev",
            "janardhan",
            "achyut",
            "anant",
            "padmanabh",
            "murari",
            "mukund",
            "trivikram",
            "vaman",
            "upendra",
            "purushottam",
            "jagannath",
            "vithal",
            "panduranga",
            "venkatesh",
        ],
        "prefixes": [
            "jai",
            "om",
            "shree",
            "bhagwan",
            "prabhu",
            "hari",
            "om namo",
            "jai jai",
            "har har",
            "shree hari",
            "om hari",
        ],
        "epithets": [
            "dev",
            "bhagwan",
            "prabhu",
            "swami",
            "nath",
            "hari",
            "avatar",
            "purushottam",
            "anant",
            "achyut",
            "mukund",
            "govind",
            "keshav",
            "madhav",
            "damodar",
            "janardhan",
            "padmanabh",
            "trivikram",
            "upendra",
        ],
    },
    "krishna": {
        "roots": [
            "krishna",
            "kanha",
            "kanhaiya",
            "gopal",
            "govind",
            "gopala",
            "murari",
            "mohan",
            "manohar",
            "shyam",
            "ghanshyam",
            "banke",
            "bihari",
            "giridhar",
            "gokulnath",
            "nandlal",
            "yashodanandan",
            "devaki",
            "vasudev",
            "madhav",
            "keshav",
            "mukund",
            "murlidhar",
            "radhapati",
            "vrindavan",
        ],
        "prefixes": [
            "jai",
            "shree",
            "radhe",
            "jai shree",
            "om",
            "gopala",
            "govind",
            "jai govind",
            "hari",
            "madhav",
            "kanha",
            "banke",
        ],
        "epithets": [
            "ji",
            "bhagwan",
            "prabhu",
            "swami",
            "nath",
            "gopal",
            "govind",
            "mohan",
            "manohar",
            "bihari",
            "giridhar",
            "murlidhar",
            "nandlal",
            "lal",
            "kanhaiya",
            "kanha",
            "shyam",
            "ghanshyam",
            "mukund",
            "madhav",
        ],
    },
    "radha": {
        "roots": [
            "radha",
            "radhika",
            "radhe",
            "radhey",
            "kishori",
            "vrindavani",
            "vrishbhanu",
            "kirtida",
            "gopi",
            "gopika",
            "shyama",
            "lalita",
            "radhey",
            "radharani",
            "vraja",
            "braj",
            "gokul",
            "vrindavan",
        ],
        "prefixes": [
            "jai",
            "shree",
            "radhe",
            "jai radhe",
            "om",
            "radhey",
            "kishori",
            "jai shree",
            "vrindavani",
            "braj",
        ],
        "epithets": [
            "ji",
            "rani",
            "ma",
            "mata",
            "devi",
            "kishori",
            "radhika",
            "shyama",
            "gopika",
            "gopi",
            "vrindavani",
            "vrishbhanu",
            "kirtida",
            "lalita",
            "priya",
            "vallabha",
            "shakti",
            "prakriti",
        ],
    },
    "sita": {
        "roots": [
            "sita",
            "janaki",
            "vaidehi",
            "maithili",
            "bhoomija",
            "rampriya",
            "janaknandini",
            "videha",
            "sitaram",
            "radhika",
            "lakshmi",
            "shree",
            "janakputri",
            "mithila",
            "ayodhya",
            "raghukulvadhu",
        ],
        "prefixes": [
            "jai",
            "shree",
            "mata",
            "jai mata",
            "om",
            "janaki",
            "vaidehi",
            "jai shree",
            "sitaram",
            "maithili",
        ],
        "epithets": [
            "ji",
            "mata",
            "ma",
            "devi",
            "rani",
            "janaki",
            "vaidehi",
            "maithili",
            "bhoomija",
            "rampriya",
            "janaknandini",
            "videha",
            "putri",
            "nandini",
            "kulvadhu",
            "lakshmi",
            "shakti",
            "prakriti",
        ],
    },
    "durga": {
        "roots": [
            "durga",
            "devi",
            "mata",
            "amba",
            "ambika",
            "jagdamba",
            "bhavani",
            "chandika",
            "mahishasurmardini",
            "sherawali",
            "navdurga",
            "mahamaya",
            "shakti",
            "kali",
            "chamunda",
            "katyayani",
            "mahagauri",
            "siddhidatri",
            "brahmacharini",
            "kushmanda",
            "skandmata",
            "kaalaratri",
        ],
        "prefixes": [
            "jai",
            "jai mata",
            "mata",
            "om",
            "shree",
            "maha",
            "jai maa",
            "jagat",
            "bhavani",
            "amba",
            "devi",
        ],
        "epithets": [
            "mata",
            "ma",
            "devi",
            "amba",
            "ambika",
            "bhavani",
            "jagdamba",
            "sherawali",
            "mardini",
            "shakti",
            "mahamaya",
            "chandika",
            "gauri",
            "kali",
            "chamunda",
            "katyayani",
            "siddhidatri",
            "brahmacharini",
        ],
    },
    "shiva": {
        "roots": [
            "shiva",
            "shankar",
            "shambhu",
            "mahadev",
            "bholenath",
            "neelkanth",
            "rudra",
            "mahakaal",
            "natraj",
            "gangadhar",
            "chandrashekar",
            "trishul",
            "damru",
            "om",
            "har",
            "bhole",
            "baba",
            "sadashiv",
            "mahesh",
            "ishwar",
            "parameshwar",
            "umapati",
            "ardhnarishwar",
            "dakshinamurti",
        ],
        "prefixes": [
            "jai",
            "om",
            "har har",
            "bam bam",
            "shiv",
            "maha",
            "bhole",
            "jai bhole",
            "om namah",
            "har",
            "shambhu",
        ],
        "epithets": [
            "dev",
            "nath",
            "baba",
            "ji",
            "shankar",
            "shambhu",
            "mahadev",
            "bholenath",
            "neelkanth",
            "rudra",
            "mahakaal",
            "natraj",
            "gangadhar",
            "chandrashekar",
            "trishuldhari",
            "damruwala",
            "sadashiv",
            "mahesh",
            "ishwar",
            "parameshwar",
            "umapati",
            "ardhnarishwar",
        ],
    },
    "ganesha": {
        "roots": [
            "ganesha",
            "ganesh",
            "ganpati",
            "gajanana",
            "lambodara",
            "ekdanta",
            "vighnharta",
            "vighnaharan",
            "siddhivinayak",
            "mangalmurti",
            "modak",
            "mushak",
            "vakratunda",
            "sumukh",
            "kapila",
            "gajakarna",
            "vinayak",
            "pillai",
            "chaturthi",
            "bappa",
            "morya",
        ],
        "prefixes": [
            "jai",
            "shree",
            "ganpati",
            "jai ganpati",
            "om",
            "vighnharta",
            "mangal",
            "siddhivinayak",
            "bappa",
            "jai bappa",
        ],
        "epithets": [
            "ji",
            "bappa",
            "dev",
            "nath",
            "pati",
            "vinayak",
            "gajanana",
            "lambodara",
            "ekdanta",
            "vighnharta",
            "vighnaharan",
            "siddhivinayak",
            "mangalmurti",
            "vakratunda",
            "sumukh",
            "kapila",
            "gajakarna",
            "morya",
        ],
    },
}

# Common emojis for all deities
emojis = [
    "🙏🙏🙏",
    "🙏🙏🙏🙏",
    "🙏🙏🙏🙏🙏",
    "🙏🙏🙏🙏🙏🙏",
    "🙏🙏🙏🙏🙏🙏🙏",
    "❤️❤️",
    "❤️❤️❤️",
    "❤️❤️❤️❤️",
    "❤️❤️❤️❤️❤️",
    "🔥🔥",
    "🔥🔥🔥",
    "🔥🔥🔥🔥",
    "🕉️🕉️🕉️",
    "🕉️🕉️🕉️🕉️",
    "🕉️🕉️🕉️🕉️🕉️",
    "🌸🌸🌸",
    "🌸🌸🌸🌸",
    "🌸🌸🌸🌸🌸",
    "💖💖",
    "💖💖💖",
    "💖💖💖💖",
    "🪔🪔🪔",
    "🪔🪔🪔🪔",
    "🪔🪔🪔🪔🪔",
    "🔱🔱🔱",
    "🔱🔱🔱🔱",
    "🔱🔱🔱🔱🔱",
    "🙏❤️🙏",
    "🙏🔥🙏",
    "🙏🕉️🙏",
    "🙏🌸🙏",
    "🙏💖🙏",
    "🙏🪔🙏",
    "🙏🔱🙏",
    "❤️🙏❤️",
    "❤️🔥❤️",
    "❤️🕉️❤️",
    "❤️🌸❤️",
    "❤️💖❤️",
    "❤️🪔❤️",
    "❤️🔱❤️",
    "🔥🙏🔥",
    "🔥❤️🔥",
    "🔥🕉️🔥",
    "🔥🌸🔥",
    "🔥💖🔥",
    "🔥🪔🔥",
    "🔥🔱🔥",
    "🕉️🙏🕉️",
    "🕉️❤️🕉️",
    "🕉️🔥🕉️",
    "🕉️🌸🕉️",
    "🕉️💖🕉️",
    "🕉️🪔🕉️",
    "🕉️🔱🕉️",
    "🌸🙏🌸",
    "🌸❤️🌸",
    "🌸🔥🌸",
    "🌸🕉️🌸",
    "🌸💖🌸",
    "🌸🪔🌸",
    "🌸🔱🌸",
    "💖🙏💖",
    "💖❤️💖",
    "💖🔥💖",
    "💖🕉️💖",
    "💖🌸💖",
    "💖🪔💖",
    "💖🔱💖",
    "🪔🙏🪔",
    "🪔❤️🪔",
    "🪔🔥🪔",
    "🪔🕉️🪔",
    "🪔🌸🪔",
    "🪔💖🪔",
    "🪔🔱🪔",
    "🔱🙏🔱",
    "🔱❤️🔱",
    "🔱🔥🔱",
    "🔱🕉️🔱",
    "🔱🌸🔱",
    "🔱💖🔱",
    "🔱🪔🔱",
]


def generate_gods_name(deity_name: str = None) -> str:
    """
    Generate a devotional name based on specific deity or random selection.

    Args:
        deity_name: Name of the deity (ram, hanuman, vishnu, krishna, radha, sita, durga, shiva, ganesha)
                   If None, uses the original mixed approach

    Returns:
        Formatted devotional string
    """
    # CHANGE: Add debug logging for function entry
    logger.debug(f"generate_gods_name called with deity_name: {deity_name}")

    if deity_name and deity_name.lower() in DEITY_DATA:
        # CHANGE: Log when using deity-specific generation
        logger.info(f"Using deity-specific generation for: {deity_name.lower()}")

        # Use deity-specific word lists
        deity_data = DEITY_DATA[deity_name.lower()]
        prefix = random.choice(deity_data["prefixes"])
        root = random.choice(deity_data["roots"])
        epithet = random.choice(deity_data["epithets"])
        emoji = random.choice(emojis)

        logger.info(f"Using deity-specific generation for deity_data: {deity_data}")
        logger.info(f"Using deity-specific generation for prefix: {prefix}")
        logger.info(f"Using deity-specific generation for root: {root}")
        logger.info(f"Using deity-specific generation for epithet: {epithet}")
        logger.info(f"Using deity-specific generation for emoji: {emoji}")

        # Deity-specific patterns
        patterns = [
            f"{prefix} {root} - {emoji}",
            f"{prefix} {root} {epithet} - {emoji}",
            f"{root} {epithet} - {emoji}",
            f"{prefix} {root}",
            f"{root} {epithet}",
            f"{root} - {emoji}",
            f"{prefix} - {emoji}",
            f"{root}",
            f" - {emoji}",
            f"{prefix} {root}  - {emoji} {emoji}",
            f"{emoji} {prefix} {root}",
            f"{root} {emoji} - {emoji}",
            f"{prefix} {root} {epithet}",
            f"{epithet} {root}  - {emoji}",
            f"{prefix} {epithet}  -  {emoji}",
        ]

        # CHANGE: Log the selected components for deity-specific generation
        selected_pattern = random.choice(patterns)
        logger.debug(
            f"Deity-specific generation - prefix: {prefix}, root: {root}, epithet: {epithet}, pattern: {selected_pattern}"
        )

        return selected_pattern.strip()
    else:
        # CHANGE: Log when falling back to mixed approach
        if deity_name:
            logger.warning(
                f"Deity '{deity_name}' not found in DEITY_DATA, falling back to mixed approach"
            )
        else:
            logger.info(
                "No deity specified, using mixed approach for random generation"
            )

        # Fallback to original mixed approach for backward compatibility
        roots = [
            "narayan",
            "hari",
            "hari hari",
            "bhajman",
            "teri",
            "nayri",
            "badri",
            "bolo",
            "bhagwan",
            "lakshmi",
            "mahadev",
            "bhole",
            "parvati",
            "krishna",
            "dev",
            "devta",
            "guru",
            "deva",
            "nath",
            "narayan",
            "govind",
            "gopal",
        ]

        prefixes = ["jai", "om", "shree", "har har", "jai jai", "om namo", "jai ho"]

        epithets = [
            "dev",
            "nath",
            "bhagwan",
            "swami",
            "prabhu",
            "ishwar",
            "mahadev",
            "avatar",
            "kripa",
            "shakti",
            "roop",
            "sena",
            "dhar",
            "pati",
            "raj",
            "giri",
            "lal",
            "anand",
            "maya",
            "jyoti",
            "teja",
            "sagar",
        ]

        prefix = random.choice(prefixes)
        root = random.choice(roots)
        epithet = random.choice(epithets)
        emoji = random.choice(emojis)

        patterns = [
            f"{prefix} {root} {emoji}",
            f"{prefix} {root}",
            f"{root} {emoji}",
            f"{prefix} {emoji}",
            f"{root}",
            f"{emoji}",
            f"{prefix} {root} {emoji} {emoji}",
            f"{emoji} {prefix} {root}",
            f"{root} {emoji} {emoji}",
            f"{prefix} {root} {emoji} {root}",
        ]

        # CHANGE: Log the selected components for mixed generation
        selected_pattern = random.choice(patterns)
        logger.debug(
            f"Mixed generation - prefix: {prefix}, root: {root}, epithet: {epithet}, pattern: {selected_pattern}"
        )

        return selected_pattern.strip()


def get_available_deities() -> list:
    """Return list of available deity names"""
    # CHANGE: Log when available deities are requested
    logger.debug("get_available_deities called")
    available = list(DEITY_DATA.keys())
    logger.info(f"Available deities: {available}")
    return available


def generate_deity_specific_names(deity_name: str, count: int = 5) -> list:
    """
    Generate multiple devotional names for a specific deity.

    Args:
        deity_name: Name of the deity
        count: Number of names to generate

    Returns:
        List of devotional strings
    """
    # CHANGE: Log function entry with parameters
    logger.debug(
        f"generate_deity_specific_names called with deity_name: {deity_name}, count: {count}"
    )

    if deity_name.lower() not in DEITY_DATA:
        # CHANGE: Log error condition before raising exception
        logger.error(
            f"Deity '{deity_name}' not found in DEITY_DATA. Available deities: {get_available_deities()}"
        )
        raise ValueError(
            f"Deity '{deity_name}' not found. Available: {get_available_deities()}"
        )

    # CHANGE: Log successful generation
    logger.info(f"Generating {count} names for deity: {deity_name}")
    names = [generate_gods_name(deity_name) for _ in range(count)]
    logger.debug(f"Generated names: {names}")
    return names


# Example usage and testing
if __name__ == "__main__":
    # CHANGE: Set logging level to DEBUG for testing
    logging.getLogger(__name__).setLevel(logging.DEBUG)

    print("Available deities:", get_available_deities())
    print()

    # # Test each deity
    # for deity in get_available_deities():
    #     print(f"{deity.upper()} examples:")
    #     for i in range(3):
    #         print(f"  {i+1}. {generate_gods_name(deity)}")
    #     print()

    # Test random generation (original behavior)
    print("RANDOM examples:")
    for i in range(3):
        print(f"  {i+1}. {generate_gods_name("vishnu")}")

    # CHANGE: Test fallback condition with invalid deity
    print("\nTesting fallback with invalid deity:")
    try:
        invalid_name = generate_gods_name("invalid_deity")
        print(f"Fallback result: {invalid_name}")
    except Exception as e:
        print(f"Error: {e}")
