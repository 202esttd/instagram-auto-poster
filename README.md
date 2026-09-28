# Instagram Auto Poster (30-Day Plan)

Automatically posts 2 times a day to Instagram for 30 days:
- **Morning (9:00 AM IST):** 1 video (Reel)
- **Evening (9:00 PM IST):** 1 carousel of 5-6 images

Runs entirely for free on GitHub Actions — no server, no computer needed to
stay on.

---

## 1. One-time setup

### A. Instagram side
1. Convert your Instagram account to a **Business** or **Creator** account
   (Settings -> Account type and tools -> Switch to Professional Account).
2. Go to [developers.facebook.com](https://developers.facebook.com), create a
   new **App** with the use case **"Manage messaging & content on Instagram"**.
3. In the app: Use cases -> Customize -> **Permissions and features** and add
   `instagram_business_basic` and `instagram_business_content_publish`.
4. App roles -> Roles -> **Instagram Testers** -> add your Instagram username,
   then accept the invite at instagram.com/accounts/manage_access.
5. Use cases -> Customize -> **API setup with Instagram login** -> Add account
   -> **Generate token**. This token is your `IG_ACCESS_TOKEN`.
6. The account ID shown next to your username is your `IG_USER_ID`.

### B. GitHub side
1. Create a free account at [github.com](https://github.com).
2. Create a **new PUBLIC repository** (must be public so Instagram's servers
   can fetch your media files — this repo will only contain your content
   files, no personal/sensitive data).
3. Upload all the files/folders from this project into that repo (drag and
   drop works fine on github.com, no command line needed).
4. Go to your repo → **Settings → Secrets and variables → Actions → New
   repository secret**, and add these four secrets:

   | Secret name        | Value                                                                 |
   |---------------------|------------------------------------------------------------------------|
   | `IG_ACCESS_TOKEN`   | The long-lived token from step A5                                     |
   | `IG_USER_ID`        | Your Instagram Business Account ID from step A6                       |
   | `START_DATE`        | The date you want Day 1 to post, format `YYYY-MM-DD` (e.g. `2026-10-01`) |
   | `REPO_RAW_BASE`     | `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO_NAME/main` |

That's it — the automation is now fully configured.

---

## 2. Adding your content

For each day (1 to 30), create a folder `content/dayXX` (e.g. `content/day01`,
`content/day02`, ... `content/day30`) containing:

```
content/day01/
  morning_video.mp4      <- 9:16 vertical video for the Reel
  evening_1.jpg          <- carousel image 1 (9:16 vertical)
  evening_2.jpg
  evening_3.jpg
  evening_4.jpg
  evening_5.jpg
  evening_6.jpg          <- optional 6th image
```

File names must match exactly (lowercase, this pattern). The script
automatically figures out which day's folder to use based on `START_DATE`.

**Note:** since the repo is public, anyone with the link could technically
browse these files. Don't put anything in the repo you don't want publicly
visible.

---

## 3. How the schedule works

- The workflow in `.github/workflows/post.yml` runs automatically every day
  at 9:00 AM and 9:00 PM IST via GitHub Actions' free scheduler.
- It calculates "Day N" as `(today's date - START_DATE) + 1`.
- If Day N is outside 1-30, it simply does nothing (safe to leave the
  workflow running after the campaign ends).
- Captions are auto-generated from `config/caption_data.json` — edit that
  file any time to change the moods, outfit words, or hashtags used.

You can also trigger a post manually any time from your repo's **Actions**
tab → "Instagram Auto Poster" → "Run workflow".

---

## 4. Important things to know

- **Access tokens expire** (long-lived tokens last ~60 days). Since your plan
  is 30 days, one token should last the whole campaign — but if you extend
  the plan, you'll need to generate a new token and update the
  `IG_ACCESS_TOKEN` secret before it expires.
- **Video specs:** Instagram Reels currently work best with vertical 9:16
  video, under ~90 seconds, in MP4 format.
- **Carousel limits:** Instagram allows 2-10 items per carousel — this setup
  uses 5-6 images per your plan.
- **Rate limits:** Instagram allows up to 25 posts per rolling 24-hour period
  per account via the API — 2 posts a day is well within that limit.
- If a post fails, check the **Actions** tab on GitHub — every run's logs are
  saved there and will show the exact error from Instagram.

---

## Full-auto mode (AI-generated images)

The system can create the fashion images itself, using your character
reference images so the same identity is kept in every picture.

1. Put 2-4 clear reference images of your character in the `character/`
   folder (`ref1.jpg`, `ref2.jpg`, ...).
2. Get a Gemini API key at https://aistudio.google.com/apikey (billing must be
   enabled for image models) and add it as the GitHub secret `GEMINI_API_KEY`.
3. Generate ahead of time (recommended, so you can review): Actions ->
   **Generate Images** -> Run workflow (start with from_day 1, to_day 1). Look at
   the pictures in `content/day01/`; delete any you dislike and re-run to
   regenerate only the missing ones.
4. If a day already has images, nothing is regenerated. If a day has none, the
   daily post workflow generates them automatically just before posting.
5. Video is optional: if `content/dayXX/morning_video.mp4` exists it is posted
   as a Reel in the morning; otherwise the morning post is an AI-generated
   carousel.

Optional repository *variables* (Settings -> Secrets and variables -> Actions
-> Variables): `IMAGE_MODEL` (default `gemini-3.1-flash-image`), `IMAGE_ASPECT`
(default `9:16`), `IMAGES_PER_POST` (default `5`).
