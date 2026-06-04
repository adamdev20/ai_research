import os
import requests
import feedparser
from google import genai

# =========================
# LOAD SECRETS
# =========================

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# =========================
# GEMINI CLIENT
# =========================

client = genai.Client(api_key=GEMINI_API_KEY)

# =========================
# RSS NEWS SOURCES
# =========================

rss_sources = [
    "https://rss.cnn.com/rss/money_latest.rss",
    "https://feeds.bbci.co.uk/news/business/rss.xml"
]

# =========================
# COLLECT NEWS
# =========================

news_titles = []

for rss in rss_sources:
    feed = feedparser.parse(rss)

    for item in feed.entries[:5]:
        news_titles.append(item.title)

news_text = "\n".join(news_titles)

# =========================
# AI PROMPT
# =========================

prompt = f"""
You are a professional investment research assistant.

Analyze today's news and create a report.

Format:

📈 Daily Investment Brief

🌎 Global Economy
- Key developments

🤖 AI & Technology
- Important updates

⚠️ Risks
- Things investors should watch

💡 Opportunities
- Long-term opportunities

📝 Summary
- Short conclusion

News:
{news_text}
"""

# =========================
# GENERATE SUMMARY
# =========================

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

summary = response.text

# Discord limit ~2000 chars
if len(summary) > 1900:
    summary = summary[:1900]

# =========================
# SEND TO DISCORD
# =========================

requests.post(
    WEBHOOK_URL,
    json={"content": summary}
)

print("Report sent successfully")
