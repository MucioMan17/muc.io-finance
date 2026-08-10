# YouTube auto-upload setup — full walkthrough

This is the one-time setup that lets the bot upload to YouTube when you tap **Publish**.
It looks like a lot, but it's ~10 minutes of clicking, once, forever. Follow it top to bottom.

You need three things, in order:
1. A **YouTube channel** (free).
2. A **Google Cloud project** with the **YouTube Data API** turned on.
3. An **OAuth client** (a little `.json` key file) that you download and drop into `secrets/`.

Then you run one command and click "Allow" in a browser. Done.

> The Google console gets redesigned often, so button names may differ slightly from what's
> written here. When they do, I've noted the old *and* new names. If you get stuck on any single
> step, stop and tell me exactly what you see on screen — that's faster than guessing.

---

## Step 1 — Make sure you have a YouTube channel

1. Go to **https://youtube.com**, sign in with the Google account you want to post from.
2. Click your profile picture (top-right) → **Create a channel** (if you don't have one yet) → follow the prompts.

✅ **Checkpoint:** you can visit your channel page. Remember *which Google account* this is — everything below must use the **same** account.

---

## Step 2 — Create a Google Cloud project

1. Go to **https://console.cloud.google.com** (sign in with the *same* account).
2. Top-left, click the **project dropdown** (says "Select a project" or shows a project name).
3. Click **New Project** → Name it anything (e.g. `muc-finance`) → **Create**.
4. Wait a few seconds, then make sure that new project is **selected** in the top-left dropdown.

✅ **Checkpoint:** the top-left shows your project name (`muc-finance`).

---

## Step 3 — Turn on the YouTube Data API

1. Left menu (☰) → **APIs & Services → Library**. (Or go to **https://console.cloud.google.com/apis/library**.)
2. Search for **YouTube Data API v3**.
3. Click it → click **Enable**.

✅ **Checkpoint:** the page now shows "API enabled" / a "Manage" button.

---

## Step 4 — Set up the consent screen (a.k.a. "Google Auth Platform")

This is the screen Google shows you when you approve the app. You have to fill it out once.

1. Left menu → **APIs & Services → OAuth consent screen**.
   - In the newer console this is called **Google Auth Platform**. If you see a "Google Auth
     Platform not configured yet" page, click **Get Started**.
2. Fill in:
   - **App name:** `muc.io finance` (anything is fine)
   - **User support email:** your email
   - **Audience / User type:** choose **External**
   - **Developer contact email:** your email
3. Click through **Save / Next / Create** until it's done. You can skip optional stuff.

### Step 4b — Add yourself as a Test user (IMPORTANT)
While the app is in "Testing" mode, only accounts you list can use it — so add yourself:
1. In the OAuth consent screen / Auth Platform, find the **Audience** section (or scroll to **Test users**).
2. Click **Add users** → type the **same Gmail address** you're using → **Save**.

✅ **Checkpoint:** your email appears in the Test users list.

### Step 4c — (Recommended) Publish the app so you don't re-login every week
Apps left in "Testing" force you to sign in again every **7 days**. Since this is your own app for
your own channel, publish it:
1. In the same **Audience** / consent screen area, find **Publishing status: Testing**.
2. Click **Publish app** → confirm.
3. It will say the app is unverified — that's expected and fine for personal use. You'll just click
   past a warning screen the first time (see Step 7).

> Skipping 4c is OK — the app still works, you'll just re-run the sign-in command once a week.

---

## Step 5 — Create the OAuth client (your key file)

1. Left menu → **APIs & Services → Credentials**. (Or **https://console.cloud.google.com/apis/credentials**.)
   - In the newer console: **Google Auth Platform → Clients**.
2. Click **+ Create Credentials → OAuth client ID** (newer console: **Create client**).
3. **Application type: Desktop app** ← this exact choice matters.
4. Name it anything → **Create**.
5. A popup appears. Click **Download JSON**. (You can re-download it any time from the ⬇ icon on that
   client's row.)

✅ **Checkpoint:** a file named like `client_secret_1234-abcd.apps.googleusercontent.com.json` is in
your **Downloads**.

---

## Step 6 — Put the key file where the app expects it

The app looks for it at exactly `secrets/youtube_client_secret.json` inside the project folder.

Open a terminal in the project folder (`C:\Users\<you>\muc.io-finance`) and run:

**Windows:**
```
del "secrets\youtube_client_secret.json" 2>nul & for /f "delims=" %A in ('dir /b /o-d "%USERPROFILE%\Downloads\client_secret*.json"') do @(copy "%USERPROFILE%\Downloads\%A" "secrets\youtube_client_secret.json" & goto ok)
:ok
```

**mac/Linux:**
```
mkdir -p secrets && cp "$(ls -t ~/Downloads/client_secret*.json | head -1)" secrets/youtube_client_secret.json
```

Then confirm the file is valid JSON (this shows no secrets — just prints OK):
```
python -c "import json; json.load(open(r'secrets/youtube_client_secret.json')); print('JSON OK - good to go')"
```

✅ **Checkpoint:** it prints **`JSON OK - good to go`**.

---

## Step 7 — Sign in once

```
python run.py --auth-youtube
```

A browser window opens:
1. Pick your Google account.
2. You'll likely see **"Google hasn't verified this app."** That's normal for your own app.
   Click **Advanced → Go to muc.io finance (unsafe) → Continue**.
3. Click **Allow** to grant upload permission.

Back in the terminal you'll see:
```
✅ YouTube authorized — token cached. Publishing will just work now.
```

The login is saved to `secrets/youtube_token.json` and refreshed automatically. You won't do this
again (unless you skipped Step 4c — then it's once a week).

---

## Step 8 — Test a real (safe) upload

1. In `config.yaml`, set the video to hidden while testing:
   ```yaml
   post:
     privacy: "unlisted"
   ```
2. Build a clip and open the cockpit:
   ```
   python run.py --sample
   python run.py --bot
   ```
3. In Telegram: `/queue` → tap **✅ Publish**. The bot uploads it and sends you a `youtu.be/...` link.
4. Open the link — only people with the link can see it, so it's a safe dry run.

When you're happy, set `privacy: "public"` and every future Publish goes live.

---

## Common snags

- **`No secrets/youtube_client_secret.json found`** → the file isn't at that exact path/name. Redo Step 6.
- **`JSONDecodeError: Extra data`** → the file is corrupted (often two files glued together). Re-download
  a fresh copy (Step 5) and redo Step 6.
- **`Access blocked / app not verified` and no "Advanced" link** → you're not a Test user. Redo Step 4b
  with the exact email you're signing in with.
- **Asked to sign in again after ~a week** → you skipped Step 4c. Publish the app (Step 4c) to stop this.
- **Wrong channel gets the upload** → you signed in with a different Google account than your channel's.
  Delete `secrets/youtube_token.json` and run Step 7 again with the right account.
