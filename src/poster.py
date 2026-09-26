"""
Main posting script for the Instagram Auto Poster.

What it does:
  1. Figures out which "day" of the 30-day plan today is (based on START_DATE).
  2. Looks inside content/dayXX/ for the right files:
       - morning slot -> morning_video.mp4
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
import argparse
import requests
from pathlib import Path
from datetime import date, datetime

from caption_generator import generate_caption

GRAPH_API = "https://graph.facebook.com/v19.0"


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
    caption = generate_caption()

    if args.slot == "morning":
        video_path = day_folder / "morning_video.mp4"
        if not video_path.exists():
            print(f"ERROR: Missing file {video_path}. Add it before this slot runs.")
            sys.exit(1)

        video_url = build_url(repo_raw_base, str(video_path))
        print(f"Uploading video: {video_url}")
        container_id = create_video_container(ig_user_id, access_token, video_url, caption)
        wait_until_ready(container_id, access_token)
        result = publish_container(ig_user_id, access_token, container_id)
        print("Morning video posted successfully:", result)

    else:  # evening -> carousel
        image_files = sorted(day_folder.glob("evening_*.jpg")) + \
                      sorted(day_folder.glob("evening_*.jpeg")) + \
                      sorted(day_folder.glob("evening_*.png"))

        if not (2 <= len(image_files) <= 10):
            print(f"ERROR: Need 2-10 images named evening_1.jpg, evening_2.jpg... "
                  f"in {day_folder}. Found {len(image_files)}.")
            sys.exit(1)

        children_ids = []
        for img_path in image_files:
            img_url = build_url(repo_raw_base, str(img_path))
            print(f"Uploading carousel image: {img_url}")
            children_ids.append(create_image_container(ig_user_id, access_token, img_url, is_carousel_item=True))

        carousel_id = create_carousel_container(ig_user_id, access_token, children_ids, caption)
        wait_until_ready(carousel_id, access_token)
        result = publish_container(ig_user_id, access_token, carousel_id)
        print("Evening carousel posted successfully:", result)


if __name__ == "__main__":
    main()
