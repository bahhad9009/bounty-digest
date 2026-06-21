# BountyDigest — Daily Bug Bounty Writeup Agent

Automatically fetches new bug bounty writeups every day, summarizes them with AI, and sends them to your Telegram.

## Setup (5 minutes)

### Step 1 — Upload to GitHub

1. Go to github.com and create a new repository (name it `bounty-digest`)
2. Upload all these files to the repo (drag and drop works)

### Step 2 — Add your secrets

1. In your GitHub repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** and add these 3 secrets:

| Secret name | Value |
|---|---|
| `GROQ_API_KEY` | your Groq API key |
| `TELEGRAM_TOKEN` | your Telegram bot token |
| `TELEGRAM_CHAT_ID` | your Telegram chat ID |

### Step 3 — Run it

- It will run automatically every day at 8:00 AM UTC
- To test it right now: go to **Actions tab → Daily Bounty Digest → Run workflow**

## What you get on Telegram every morning

1. A header message: "Daily Digest — 5 new writeups found"
2. One message per writeup containing:
   - Vuln type + severity + bounty amount
   - 3 steps to reproduce
   - Root cause
   - Key lesson for hunters
   - Link to full writeup

## Customize

**Change delivery time** — edit `cron: '0 8 * * *'` in `.github/workflows/daily.yml`
- `0 6 * * *` = 6 AM UTC
- `0 20 * * *` = 8 PM UTC

**Add more sources** — add RSS feed URLs to the `FEEDS` list in `src/agent.py`

**Change keywords** — edit the `KEYWORDS` list in `src/agent.py` to focus on specific vuln types

## Sources monitored

- Medium (bug-bounty, bugbounty, ethical-hacking tags)
- InfoSec Writeups
- PortSwigger Research
- Intigriti Blog
- HackerOne Blog
