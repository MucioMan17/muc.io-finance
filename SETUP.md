# Setup — get it running

Two tracks: **(A)** get the code running locally, **(B)** create the accounts & keys.
You can do the whole first section tonight for **free** (dry mode), then add keys as you go.

---

## A. Run the code (free, no keys needed)

You need **Python 3.10+** and (for actual video) the **ffmpeg** binary.

**Windows (Command Prompt):**
```
cd muc.io-finance
pip install -r requirements.txt
copy .env.example .env
copy config.example.yaml config.yaml
python run.py --init-db
python run.py --sample
```

**macOS / Linux:**
```bash
cd muc.io-finance
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
python run.py --init-db
python run.py --sample
```

> A virtual environment (`.venv`) is optional — if `pip install` runs against your normal
> Python, that's fine and everything still works.

`--sample` pulls a real finance headline, writes a script, and renders a chart card
into `./output/`. With no AI key it uses a labelled template — proof the pipeline works
end to end before you spend anything.

Install **ffmpeg** (only needed to produce the actual .mp4):
- macOS: `brew install ffmpeg`
- Windows: `winget install ffmpeg`
- Linux: `sudo apt install ffmpeg`

---

## B. The accounts & keys (in order)

### 1. AI brain — ~5 min  *(the writer)*
- Go to **https://openrouter.ai** → sign up → **Keys** → create a key.
- Put it in `.env` as `LLM_API_KEY`. (One key, hundreds of models — swap `LLM_MODEL` anytime.)
- Add a few dollars of credit; at your volume it lasts a long time.

### 2. Telegram cockpit — ~5 min  *(your phone remote)*
- In Telegram, message **@BotFather** → `/newbot` → follow prompts → copy the token
  into `.env` as `TELEGRAM_BOT_TOKEN`.
- Message **@userinfobot** to get your numeric id → put it in `.env` as `TELEGRAM_CHAT_ID`
  (this locks the bot to only you).
- Run `python run.py --bot`, open your bot in Telegram, send `/start`.

### 3. Voice — already free
- Uses `edge-tts` (installed via requirements). No account needed. Pick a different
  voice by editing `tts.voice` in `config.yaml` later.

### 4. YouTube — ~15 min  *(when you're ready to publish)*
- **https://console.cloud.google.com** → new project → enable **YouTube Data API v3**.
- Create an **OAuth client ID** (type: Desktop) → download the JSON.
- Save it to `secrets/youtube_client_secret.json` (path is set in `.env`).
- First publish opens a browser to authorize; after that it's one tap in Telegram.

### 5. TikTok — no key needed to start
- Just make the account. v1 hands you the finished video in Telegram to post in the
  app (a few seconds). API auto-posting needs TikTok app approval — a later upgrade.

### 6. Newsletter — ~10 min  *(the asset you own)*
- Pick a free tier (e.g. Buttondown, MailerLite, or beehiiv). Create the list, grab your
  signup link, and put it in your video descriptions/bios. (Wiring the daily send into the
  engine is a Phase-3 task — see `docs/blueprint.md`.)

### 7. Hosting — when you want it running 24/7
- Runs on your own computer for free while you test.
- For always-on: a ~$5/mo VPS, or leave it running on a spare machine. `python run.py --serve`
  keeps the buffer full; `python run.py --bot` runs the cockpit (run both).

---

## What works today vs. what needs a key

| Piece | Works now (free) | Needs a key |
|---|---|---|
| Pull news, pick a story, verify | ✅ | — |
| Write the script | ✅ template | 🔑 real writing → AI key (step 1) |
| Chart card | ✅ | — |
| Voice + .mp4 video | ✅ once ffmpeg installed | — |
| Review + publish from phone | — | 🔑 Telegram (step 2) |
| Auto-upload to YouTube | — | 🔑 YouTube OAuth (step 4) |

Start with A + steps 1–2. That alone gets you real scripts you review on your phone.
