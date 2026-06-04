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
    feed = feedparser.parse(rss)

    for item in feed.entries[:5]:
        news_items.append({
            "title": item.title,
            "link": item.link
        })

news_text = "\n".join([f"{n['title']} - {n['link']}" for n in news_items])

# =========================
# HEDGE FUND OS PROMPT
# =========================

prompt = f"""
Anda adalah AI Hedge Fund Operating System (Hedge Fund OS v1).

Anda bertugas sebagai sistem intelijen pasar real-time untuk investor institusional.

Anda TIDAK merangkum berita.
Anda MENYULAP data menjadi keputusan strategis.

---

FORMAT OUTPUT:

1. MARKET STATE (KONDISI PASAR SAAT INI)
- Jelaskan kondisi global market saat ini dalam 3-5 kalimat

---

2. MARKET REGIME DETECTION
Tentukan market sedang berada di:
- Risk On
- Risk Off
- Transition Phase

Jelaskan alasannya.

---

3. SENTIMENT SCORING (0–100)
- Bullish %
- Bearish %
- Netral %
Sertakan logika singkat.

---

4. NARRATIVE SHIFT (PERUBAHAN CERITA PASAR)
Jelaskan:
- Narasi lama
- Narasi baru
- Apa yang sedang berubah di mindset investor global

---

5. SECTOR ROTATION MAP
- Momentum sectors
- Early accumulation sectors
- High risk / overheated sectors

---

6. MARKET OPPORTUNITY SCORE (TOP 3 THEMES)
Berikan 3 tema terbesar dengan skor (0–100):
Contoh:
- AI infrastructure (85/100)
- Energy transition (70/100)

---

7. RISK RADAR (SISTEMIK & TERSEMBUNYI)
Jelaskan risiko yang tidak terlihat oleh retail investor.

---

8. SCENARIO MATRIX
- Bull case
- Base case
- Bear case

---

9. NEXT ACTION FRAMEWORK
Apa yang harus dipantau:
- data ekonomi
- event global
- indikator penting
- sektor yang harus diamati

---

10. NEWS INPUT
{news_text}

---

Gunakan Bahasa Indonesia profesional, tajam, seperti laporan hedge fund real.
Hindari emoji berlebihan.
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
# DISCORD SENDER (ANTI LIMIT)
# =========================

def send_discord(text):
    chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]

    for i, chunk in enumerate(chunks):
        header = f"HEDGE FUND OS | PART {i+1}/{len(chunks)}\n"
        requests.post(
            WEBHOOK_URL,
            json={"content": header + chunk}
        )

send_discord(report)

print("Hedge Fund OS report sent successfully")
