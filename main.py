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
        news_items.append(f"{item.title} - {item.link}")

news_text = "\n".join(news_items)

# =========================
# PROMPT (SNYDER RESEARCH OS)
# =========================

prompt = f"""
Anda adalah AI sistem analisis pasar global bernama Snyder Research OS.

Tugas Anda adalah mengubah berita menjadi intelijen pasar tingkat institusi.

Jangan merangkum berita satu per satu.
Fokus pada pola besar, hubungan antar peristiwa, dan dampak ke pasar.

---

FORMAT OUTPUT:

1. GAMBARAN PASAR GLOBAL
Jelaskan kondisi pasar saat ini secara singkat dan jelas.

---

2. ARAH PASAR
Tentukan apakah pasar:
- Risk On
- Risk Off
- Transisi

Berikan alasan sederhana.

---

3. SENTIMEN PASAR (0–100)
- Bullish %
- Bearish %
- Netral %

---

4. SEKTOR TERPENGARUH
- Sektor menguat
- Sektor melemah
- Sektor netral

---

5. TEMA PASAR
Sebutkan 2–4 tema besar yang sedang terbentuk di pasar global.

---

6. RISIKO UTAMA
Jelaskan risiko penting yang mungkin tidak terlihat investor retail.

---

7. SKENARIO PASAR
- Bull case
- Base case
- Bear case

---

8. ARAH PEMANTAUAN
Apa yang harus diperhatikan dalam beberapa hari ke depan:
- data ekonomi
- event global
- sentimen pasar

---

9. SUMBER BERITA
{news_text}

---

Gunakan bahasa Indonesia yang natural, jelas, dan profesional seperti laporan riset.
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
        header = f"📊 SNYDER RESEARCH OS | PART {i+1}/{len(chunks)}\n"
        requests.post(
            WEBHOOK_URL,
            json={"content": header + chunk}
        )

send_discord(report)

print("Snyder Research OS report sent successfully")
