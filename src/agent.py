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
    "https://medium.com/feed/tag/ethical-hacking",
    "https://infosecwriteups.com/feed",
    "https://portswigger.net/research/rss",
    "https://blog.intigriti.com/feed/",
    "https://www.hackerone.com/blog.rss",
]

KEYWORDS = [
    "xss", "ssrf", "idor", "rce", "lfi", "sqli", "sql injection",
    "csrf", "open redirect", "xxe", "ssti", "subdomain takeover",
    "authentication bypass", "privilege escalation", "account takeover",
    "bug bounty", "writeup", "vulnerability", "cve", "exploit"
]

DB_PATH = "seen_articles.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            url TEXT PRIMARY KEY,
            seen_at TEXT
        )
    """)
    conn.commit()
    return conn

def is_seen(conn, url):
    row = conn.execute("SELECT 1 FROM seen WHERE url=?", (url,)).fetchone()
    return row is not None

def mark_seen(conn, url):
    conn.execute("INSERT OR IGNORE INTO seen (url, seen_at) VALUES (?, ?)",
                 (url, datetime.utcnow().isoformat()))
    conn.commit()

def is_relevant(title, summary):
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)

def fetch_article_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded, max_tree_size=10000000)
        return text[:4000] if text else None
    except Exception:
        return None

def summarize(title, text):
    prompt = f"""You are a bug bounty learning assistant. Summarize this writeup in a structured way.

Title: {title}

Content:
{text}

Reply in this EXACT format (keep it concise):

VULN TYPE: [e.g. SSRF, XSS, IDOR, RCE]
PLATFORM: [e.g. HackerOne, Bugcrowd, or Unknown]
BOUNTY: [amount if mentioned, else Unknown]
SEVERITY: [Critical / High / Medium / Low / Unknown]

STEPS:
1. [first step]
2. [second step]
3. [third step]

ROOT CAUSE: [one sentence]

IMPACT: [one sentence]

KEY LESSON: [one actionable tip for bug hunters]"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3,
        },
        timeout=30,
    )
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload, timeout=10)

def format_message(title, url, summary):
    return f"""<b>New Writeup</b>

<b>{title}</b>

{summary}

<a href="{url}">Read full writeup</a>"""

def format_digest_header(count):
    today = datetime.utcnow().strftime("%A, %B %d")
    if count == 0:
        return f"<b>Daily Digest — {today}</b>\n\nNo new writeups found today. Check back tomorrow!"
    return f"<b>Daily Digest — {today}</b>\n\n{count} new writeup(s) found and summarized for you below."

def run():
    conn = init_db()
    new_articles = []

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            cutoff = datetime.utcnow() - timedelta(hours=25)

            for entry in feed.entries:
                url = entry.get("link", "")
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                published = entry.get("published_parsed")

                if not url or is_seen(conn, url):
                    continue

                if published:
                    pub_dt = datetime(*published[:6])
                    if pub_dt < cutoff:
                        continue

                if not is_relevant(title, summary):
                    mark_seen(conn, url)
                    continue

                new_articles.append({"title": title, "url": url})
                mark_seen(conn, url)

        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")

    send_telegram(format_digest_header(len(new_articles)))

    for article in new_articles[:10]:
        try:
            text = fetch_article_text(article["url"])
            if not text:
                continue
            summary = summarize(article["title"], text)
            msg = format_message(article["title"], article["url"], summary)
            send_telegram(msg)
            print(f"Sent: {article['title']}")
        except Exception as e:
            print(f"Error processing {article['url']}: {e}")

if __name__ == "__main__":
    run()
