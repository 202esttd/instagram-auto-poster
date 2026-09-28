"""
Main posting script for the Instagram Auto Poster.

What it does:
  1. Figures out which "day" of the 30-day plan today is (based on START_DATE).
  2. Looks inside content/dayXX/ for the right files:
       - morning slot -> morning_video.mp4 (if present) else morning_1.jpg... carousel
       - evening slot -> evening_1.jpg, evening_2.jpg, ... (carousel, 2-10 images)
  3. Builds a public URL for each file (repo must be PUBLIC on GitHub).
  4. Generates a caption automatically.
  5. Uploads to Instagram via the Graph API and publishes the post.

Run manually for testing:
  python src/poster.py --slot morning
  python src/poster.py --slot evening
"""
import os
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from datetime import date, datetime

from caption_generator import generate_caption

GRAPH_API = "https://graph.instagram.com/v23.0"


def get_day_number(start_date_str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = date.today()
    return (today - start).days + 1


def build_url(base, relative_path):
    return f"{base.rstrip('/')}/{relative_path.lstrip('/')}"


def create_image_container(ig_user_id, access_token, image_url, is_carousel_item=False):
    payload = {"image_url": image_url, "access_token": access_token}
    if is_carousel_item:
        payload["is_carousel_item"] = "true"
    resp = requests.post(f"{GRAPH_API}/{ig_user_id}/media", data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def create_video_container(ig_user_id, access_token, video_url, caption):
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
    }
    resp = requests.post(f"{GRAPH_API}/{ig_user_id}/media", data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def create_carousel_container(ig_user_id, access_token, children_ids, caption):
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": access_token,
    }
    resp = requests.post(f"{GRAPH_API}/{ig_user_id}/media", data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def wait_until_ready(container_id, access_token, timeout=180):
    params = {"fields": "status_code", "access_token": access_token}
    waited = 0
    while waited < timeout:
        resp = requests.get(f"{GRAPH_API}/{container_id}", params=params)
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed to process on Instagram's side.")
        time.sleep(5)
        waited += 5
    raise TimeoutError(f"Container {container_id} was not ready after {timeout}s.")


def publish_container(ig_user_id, access_token, creation_id):
    payload = {"creation_id": creation_id, "access_token": access_token}
    resp = requests.post(f"{GRAPH_API}/{ig_user_id}/media_publish", data=payload)
    resp.raise_for_status()
    return resp.json()


def find_images(folder, slot):
    files = []
    for ext in ("jpg", "jpeg", "png"):
        files += sorted(folder.glob(f"{slot}_*.{ext}"))
    return files


def read_look(folder, slot):
    path = folder / f"{slot}_look.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def post_carousel(ig_user_id, access_token, repo_raw_base, image_files, caption):
    children_ids = []
    for img_path in image_files[:10]:
        img_url = build_url(repo_raw_base, img_path.as_posix())
        print(f"Uploading carousel image: {img_url}")
        children_ids.append(create_image_container(ig_user_id, access_token, img_url, is_carousel_item=True))
    carousel_id = create_carousel_container(ig_user_id, access_token, children_ids, caption)
    wait_until_ready(carousel_id, access_token)
    return publish_container(ig_user_id, access_token, carousel_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=["morning", "evening"])
    args = parser.parse_args()

    ig_user_id = os.environ["IG_USER_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    start_date = os.environ["START_DATE"]
    repo_raw_base = os.environ["REPO_RAW_BASE"]

    day_number = get_day_number(start_date)
    if day_number < 1 or day_number > 30:
        print(f"Day {day_number} is outside the 30-day plan (1-30). Nothing to post today.")
        sys.exit(0)

    day_folder = Path(f"content/day{day_number:02d}")
    look = read_look(day_folder, args.slot)
    caption = generate_caption(outfit=look.get("outfit_label"), mood=look.get("mood"))

    video_path = day_folder / "morning_video.mp4"
    if args.slot == "morning" and video_path.exists():
        video_url = build_url(repo_raw_base, video_path.as_posix())
        print(f"Uploading video: {video_url}")
        container_id = create_video_container(ig_user_id, access_token, video_url, caption)
        wait_until_ready(container_id, access_token)
        print("Morning video posted successfully:", publish_container(ig_user_id, access_token, container_id))
        return

    image_files = find_images(day_folder, args.slot)
    if not (2 <= len(image_files) <= 10):
        print(f"ERROR: need 2-10 images named {args.slot}_1.jpg, {args.slot}_2.jpg... "
              f"in {day_folder}. Found {len(image_files)}.")
        sys.exit(1)

    result = post_carousel(ig_user_id, access_token, repo_raw_base, image_files, caption)
    print(f"{args.slot.capitalize()} carousel posted successfully:", result)


if __name__ == "__main__":
    main()
