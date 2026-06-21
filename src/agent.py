import os
import sqlite3
import feedparser
import requests
import trafilatura
from datetime import datetime, timedelta

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

FEEDS = [
    "https://medium.com/feed/tag/bug-bounty",
    "https://medium.com/feed/tag/bugbounty",
    "https://infosecwriteups.com/feed",
]

KEYWORDS = [
    "xss", "ssrf", "idor", "rce", "lfi", "sqli",
    "csrf", "xxe", "ssti", "bug bounty", "writeup", "vulnerability"
]

DB_PATH = "seen_articles.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY, seen_at TEXT)")
    conn.commit()
    return conn

def is_seen(conn, url):
    return conn.execute("SELECT 1 FROM seen WHERE url=?", (url,)).fetchone() is not None

def mark_seen(conn, url):
    conn.execute("INSERT OR IGNORE INTO seen (url, seen_at) VALUES (?, ?)", (url, datetime.utcnow().isoformat()))
    conn.commit()

def is_relevant(title, summary):
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)

def fetch_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        return text[:4000] if text else None
    except:
        return None

def call_groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + GROQ_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        },
        timeout=30
    )
    return r.json()["choices"][0]["message"]["content"].strip()

def send_telegram(text):
    requests.post(
        "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        },
        timeout=10
    )

def run():
    conn = init_db()
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=25)

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get("link", "")
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                pub = entry.get("published_parsed")
                if not url or is_seen(conn, url):
                    continue
                if pub and datetime(*pub[:6]) < cutoff:
                    continue
                if is_relevant(title, summary):
                    articles.append({"title": title, "url": url})
                mark_seen(conn, url)
        except Exception as e:
            print("Feed error:", e)

    today = datetime.utcnow().strftime("%A, %B %d")
    if not articles:
        send_telegram(f"<b>Daily Digest — {today}</b>\n\nNo new writeups today.")
        return

    send_telegram(f"<b>Daily Digest — {today}</b>\n\n{len(articles)} new writeup(s) below.")

    for a in articles[:10]:
        try:
            text = fetch_text(a["url"])
            if not text:
                print("No text:", a["url"])
                continue
            prompt = f"""Summarize this bug bounty writeup:

Title: {a['title']}
Content: {text}

Use this format:
VULN TYPE: 
PLATFORM: 
BOUNTY: 
SEVERITY: 

STEPS:
1. 
2. 
3. 

ROOT CAUSE: 
IMPACT: 
KEY LESSON: """
            summary = call_groq(prompt)
            send_telegram(f"<b>{a['title']}</b>\n\n{summary}\n\n<a href='{a['url']}'>Read more</a>")
            print("Sent:", a["title"])
        except Exception as e:
            print("Error:", a["url"], str(e))

if __name__ == "__main__":
    run()
