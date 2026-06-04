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
Anda adalah seorang analis investasi makro global senior yang bekerja di perusahaan manajemen investasi tingkat institusi.

Tugas Anda adalah mengubah berita mentah menjadi INTELIJEN INVESTASI yang terstruktur dan mudah dipahami.

JANGAN merangkum berita. JANGAN mengulang isi berita.

Fokus pada analisis, dampak, dan insight.

---

FORMAT OUTPUT:

1. SENTIMEN PASAR
Berikan:
- Sentimen umum: Bullish / Netral / Bearish
- Skor (0–100)
- Penjelasan singkat

---

2. DAMPAK MAKRO GLOBAL
Analisis dampak terhadap:
- ekonomi global
- inflasi dan suku bunga
- sentimen risiko investor

---

3. DAMPAK SEKTOR
Bagi menjadi:
- Sektor yang diuntungkan
- Sektor yang tertekan

Sebutkan sektor secara spesifik (contoh: teknologi, energi, keuangan, AI, dll)

---

4. TEMA INVESTASI YANG MUNCUL
Identifikasi 2–4 tema besar yang sedang berkembang di pasar.
Jelaskan secara singkat alasan munculnya tema tersebut.

---

5. RISIKO UTAMA
Jelaskan risiko penting yang perlu diperhatikan, seperti:
- risiko ekonomi
- risiko geopolitik
- risiko valuasi pasar
- risiko sistemik

---

6. AREA PELUANG (tanpa rekomendasi beli/jual)
Sebutkan sektor atau tren yang layak dipelajari lebih lanjut.
Berikan alasan singkat mengapa menarik.

---

7. INSIGHT UTAMA
Berikan satu insight mendalam yang tidak terlihat oleh investor pemula.

---

DATA BERITA:
{news_text}

---

Gunakan bahasa Indonesia yang profesional, jelas, dan ringkas seperti laporan riset institusi keuangan.
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
