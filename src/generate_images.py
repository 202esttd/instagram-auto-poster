"""
Generates the fashion images for the 30-day plan using the Gemini image API,
using your character reference images (character/ folder) to keep the same
identity in every picture.

Usage:
  python src/generate_images.py --day 1                 # both slots for day 1
  python src/generate_images.py --from-day 1 --to-day 30
  python src/generate_images.py --day 3 --slot evening
  python src/generate_images.py --auto --slot evening   # today's day (used by the workflow)

Existing images are never regenerated (so re-running costs nothing extra).
"""
import os
import io
import sys
import json
import time
import base64
import random
import argparse
from datetime import date, datetime
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
STYLE = json.load(open(ROOT / "config" / "style_data.json", encoding="utf-8"))
CAPTION = json.load(open(ROOT / "config" / "caption_data.json", encoding="utf-8"))

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("IMAGE_MODEL") or "gemini-3.1-flash-image"
ASPECT = os.environ.get("IMAGE_ASPECT") or "9:16"
IMAGES_PER_POST = int(os.environ.get("IMAGES_PER_POST") or 5)


def load_reference_parts():
    folder = ROOT / "character"
    files = []
    for ext in ("jpg", "jpeg", "png", "webp"):
        files += sorted(folder.glob(f"*.{ext}"))
    if not files:
        print("ERROR: no reference images found in the 'character/' folder.")
        sys.exit(1)
    parts = []
    for f in files[:6]:
        img = Image.open(f).convert("RGB")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        parts.append({"inlineData": {"mimeType": "image/jpeg",
                                     "data": base64.b64encode(buf.getvalue()).decode()}})
    print(f"Loaded {len(parts)} reference image(s).")
    return parts


def build_look(day, slot):
    slot_idx = 0 if slot == "morning" else 1
    idx = (day - 1) * 2 + slot_idx

    combos = [(g, c) for g in STYLE["garments"] for c in STYLE["colors"]]
    random.Random(2026).shuffle(combos)
    garment, color = combos[idx % len(combos)]

    def pick(items, seed):
        items = list(items)
        random.Random(seed).shuffle(items)
        return items[idx % len(items)]

    heels = pick(STYLE["heels"], 11)
    setting = pick(STYLE["settings"], 22)
    lighting = pick(STYLE["lighting"], 33)
    mood = pick(CAPTION["moods"], 44)

    first = STYLE["shots"][0]
    others = random.Random(idx).sample(STYLE["shots"][1:], k=min(IMAGES_PER_POST - 1, len(STYLE["shots"]) - 1))
    shots = [first] + others

    return {
        "day": day, "slot": slot, "garment": garment, "color": color,
        "outfit_label": f"{color} {garment}", "heels": heels,
        "setting": setting, "lighting": lighting, "mood": mood, "shots": shots,
    }


def build_prompt(look, shot):
    return (
        "Create a high-end fashion editorial photograph of the fictional character shown in the "
        "reference images. IDENTITY: keep her face, facial features, skin tone, hair and body "
        "proportions EXACTLY identical to the reference images. Do not alter, beautify or change "
        "the face in any way. "
        f"OUTFIT: {look['outfit_label']}. FOOTWEAR: {look['heels']}. "
        f"LOCATION: {look['setting']}. SHOT: {shot}. LIGHTING: {look['lighting']}. "
        "Vertical 9:16 composition, professional fashion magazine photoshoot quality, sharp focus, "
        "realistic skin texture, natural anatomy, correct hands and fingers, tasteful and fully clothed. "
        "No text, no watermark, no logos."
    )


def generate_one(prompt, ref_parts):
    models = [MODEL]
    if not MODEL.endswith("-preview"):
        models.append(MODEL + "-preview")
    body = {
        "contents": [{"parts": ref_parts + [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": ASPECT}},
    }
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            r = requests.post(url, headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
                              json=body, timeout=300)
            if r.status_code == 404:
                print(f"  model '{model}' not found, trying next option...")
                break
            if r.status_code in (429, 500, 503):
                wait = 20 * (attempt + 1)
                print(f"  API busy ({r.status_code}), waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Gemini API error {r.status_code}: {r.text[:400]}")
            data = r.json()
            for cand in data.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        return base64.b64decode(inline["data"])
            print("  no image returned (possibly blocked by safety filter), retrying...")
    return None


def save_jpeg(raw, path):
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.height > 1920:
        img = img.resize((int(img.width * 1920 / img.height), 1920))
    img.save(path, "JPEG", quality=90)


def generate_post(day, slot, ref_parts):
    folder = ROOT / "content" / f"day{day:02d}"
    folder.mkdir(parents=True, exist_ok=True)

    if slot == "morning" and (folder / "morning_video.mp4").exists():
        print(f"Day {day} morning: video found, skipping image generation.")
        return
    existing = [p for ext in ("jpg", "jpeg", "png") for p in folder.glob(f"{slot}_*.{ext}")]
    if len(existing) >= 2:
        print(f"Day {day} {slot}: images already exist, skipping.")
        return

    look = build_look(day, slot)
    (folder / f"{slot}_look.json").write_text(json.dumps(look, indent=2), encoding="utf-8")
    print(f"Day {day} {slot}: {look['outfit_label']} | {look['heels']} | {look['setting']}")

    made = 0
    for i, shot in enumerate(look["shots"], start=1):
        path = folder / f"{slot}_{i}.jpg"
        if path.exists():
            made += 1
            continue
        print(f"  generating image {i}/{len(look['shots'])}: {shot}")
        raw = generate_one(build_prompt(look, shot), ref_parts)
        if raw is None:
            print(f"  WARNING: image {i} failed, skipping it.")
            continue
        save_jpeg(raw, path)
        made += 1
        time.sleep(2)

    if made < 2:
        print(f"ERROR: only {made} image(s) generated for day {day} {slot}; a carousel needs at least 2.")
        sys.exit(1)


def main():
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY is not set.")
        sys.exit(1)

    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int)
    ap.add_argument("--from-day", type=int)
    ap.add_argument("--to-day", type=int)
    ap.add_argument("--slot", choices=["morning", "evening", "both"], default="both")
    ap.add_argument("--auto", action="store_true", help="use today's day number from START_DATE")
    args = ap.parse_args()

    if args.auto:
        start = datetime.strptime(os.environ["START_DATE"], "%Y-%m-%d").date()
        day = (date.today() - start).days + 1
        if not 1 <= day <= 30:
            print(f"Day {day} is outside the 30-day plan. Nothing to generate.")
            return
        days = [day]
    elif args.day:
        days = [args.day]
    elif args.from_day and args.to_day:
        days = list(range(args.from_day, args.to_day + 1))
    else:
        ap.error("use --day N, --from-day A --to-day B, or --auto")

    slots = ["morning", "evening"] if args.slot == "both" else [args.slot]
    refs = load_reference_parts()
    for d in days:
        for s in slots:
            generate_post(d, s, refs)
    print("Done.")


if __name__ == "__main__":
    main()
