from itertools import permutations
import random

# Emojis
emojis = ["🙏", "❤️", "😍", "🔁", "🔥", "🔱", "💖", "🌸"]

# 50+ engagement suffixes (same meaning)
suffixes = [
    "drop yours",
    "show me yours",
    "let me see yours",
    "send yours",
    "share yours",
    "reply with it",
    "your turn",
    "now yours",
    "drop below",
    "comment yours",
    "I want yours",
    "let’s see yours",
    "show yours here",
    "from you",
    "please share",
    "waiting for yours",
    "now show yours",
    "I’m waiting for it",
    "what about yours",
    "your move",
    "show it here",
    "send it now",
    "drop it here",
    "reply yours",
    "your reply?",
    "now it’s your turn",
    "I’m curious yours",
    "waiting for your reply",
    "drop it quickly",
    "don’t hold back",
    "show yours fast",
    "send it over",
    "your response?",
    "let’s see it",
    "drop your answer",
    "I want to see it",
    "show me now",
    "your version?",
    "reply below",
    "drop it now",
    "let’s check yours",
    "waiting… yours?",
    "your reaction?",
    "show response",
    "send response",
    "now respond",
    "your share?",
    "let’s go yours",
    "drop your side",
    "waiting on you",
    "show your side",
    "reply quickly",
    "your input?",
    "let’s see that",
    "show what you got",
    "send your side",
    "drop your take",
]

# Generate permutations
perms = permutations(emojis, 3)

output_lines = []

for p in perms:
    suffix = random.choice(suffixes)
    line = " ".join(p) + " 👉 " + suffix
    output_lines.append(line)

# Shuffle for better randomness
random.shuffle(output_lines)

# Save output
file_path = "emoji_permutations_viral.txt"

with open(file_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Generated:", len(output_lines))
print("Saved to:", file_path)
