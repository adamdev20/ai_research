import os
import requests
import feedparser
from google import genai

# =========================
# CONFIG (SECRET FROM GITHUB)
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
# COLLECT NEWS (WITH LINKS)
# =========================

news_items = []

for rss in rss_sources:
    feed = feedparser.parse(rss)

    for item in feed.entries[:5]:
        news_items.append({
            "title": item.title,
            "link": item.link
        })

news_text = "\n".join(
    [f"{n['title']} - {n['link']}" for n in news_items]
)

# =========================
# PROMPT (FINAL INTELLIGENCE VERSION)
# =========================

prompt = f"""
Anda adalah analis investasi makro global senior di institusi keuangan.

Tugas Anda adalah mengubah berita menjadi INTELIJEN INVESTASI yang mendalam dan terstruktur.

JANGAN merangkum berita secara biasa.

Gunakan analisis, konteks, hubungan antar peristiwa, dan dampak pasar.

---

FORMAT OUTPUT:

1. RINGKASAN KONDISI PASAR
Jelaskan kondisi pasar global saat ini secara singkat dan jelas.

---

2. ANALISIS MENDALAM (CORE INSIGHT)
Jelaskan:
- kenapa berita ini penting
- dampak tersembunyi
- hubungan antar berita
- dampak jangka pendek dan panjang

---

3. DAMPAK KE SEKTOR
- Sektor yang diuntungkan
- Sektor yang tertekan
- alasan logis

---

4. TEMA INVESTASI GLOBAL
Identifikasi 2–4 tren besar yang sedang terbentuk di pasar.

---

5. RISIKO UTAMA
Jelaskan risiko utama yang mungkin tidak disadari investor umum.

---

6. ARAH STRATEGIS (NON-REKOMENDASI)
Sebutkan:
- apa yang harus dipantau
- data penting yang perlu diperhatikan
- sektor untuk observasi

---

7. LANGKAH SELANJUTNYA
Berikan action plan sederhana:
- apa yang harus dilihat besok
- indikator penting
- fokus analisis berikutnya

---

8. SUMBER BERITA
Gunakan link berikut sebagai referensi:
{news_text}

---

Gunakan Bahasa Indonesia yang profesional, jelas, dan seperti laporan riset institusi keuangan.
Jangan gunakan emoji berlebihan.
"""

# =========================
# GEMINI RESPONSE
# =========================

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

report = response.text

# =========================
# DISCORD LIMIT SAFETY
# =========================

if len(report) > 1900:
    report = report[:1900]

# =========================
# SEND TO DISCORD
# =========================

requests.post(
    WEBHOOK_URL,
    json={"content": report}
)

print("Report sent successfully")
