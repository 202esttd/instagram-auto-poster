"""
Randomly generates a fashion-style caption using templates + hashtags
stored in config/caption_data.json. No AI/API needed — pure template mixing.
"""
import json
import random
from pathlib import Path


def generate_caption():
    data_path = Path(__file__).parent.parent / "config" / "caption_data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    template = random.choice(data["templates"])
    mood = random.choice(data["moods"])
    outfit = random.choice(data["outfit_types"])
    hashtags = " ".join(random.sample(data["hashtags"], k=min(15, len(data["hashtags"]))))

    return template.format(mood=mood, outfit=outfit, hashtags=hashtags)


if __name__ == "__main__":
    # Quick manual test: run "python src/caption_generator.py" to preview a caption
    print(generate_caption())
