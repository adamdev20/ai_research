import os
import requests
import feedparser
from google import genai

# =========================
# CONFIG
# =========================

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)

# =========================
# RSS SOURCES
# =========================

rss_sources = [
    "https://rss.cnn.com/rss/money_latest.rss",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://finance.yahoo.com/news/rssindex"
]

# =========================
# COLLECT NEWS
# =========================

news_items = []

for rss in rss_sources:
    try:
        feed = feedparser.parse(rss)

        for item in feed.entries[:5]:
            news_items.append(f"{item.title} - {item.link}")

    except:
        continue

# fallback kalau kosong
if not news_items:
    news_items.append("No market news available today.")

news_text = "\n".join(news_items)

# =========================
# PROMPT
# =========================

prompt = f"""
Anda adalah analis investasi pribadi untuk pemula.

Tugas Anda bukan menjelaskan berita secara panjang, tetapi membantu pengguna memahami:

1. apa yang sedang terjadi di pasar
2. kenapa itu penting
3. dampaknya ke investasi
4. apa sikap yang masuk akal hari ini

Gunakan bahasa Indonesia yang sederhana, jelas, dan tidak rumit.

Hindari:
- istilah teknis yang sulit
- penjelasan terlalu panjang
- prediksi pasti

---

INPUT:
Berikut adalah kumpulan berita pasar terbaru:

{news_text}

---

OUTPUT WAJIB:

1. KONDISI PASAR HARI INI
2. HAL PALING PENTING HARI INI
3. ARTINYA UNTUK INVESTOR PEMULA
4. SIKAP YANG MASUK AKAL HARI INI
5. RISIKO UTAMA HARI INI

Gunakan bahasa seperti mentor yang menjelaskan ke pemula.
"""

# =========================
# GEMINI CALL
# =========================

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

report = response.text

# =========================
# DISCORD SENDER (SAFE)
# =========================

def send_discord(text):
    chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]

    for i, chunk in enumerate(chunks):
        header = f"📊 SNYDER RESEARCH OS | PART {i+1}/{len(chunks)}\n"
        requests.post(
            WEBHOOK_URL,
            json={"content": header + chunk}
        )

send_discord(report)

print("Snyder Research OS report sent successfully")
