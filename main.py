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

Gunakan logika sederhana seperti mentor yang menjelaskan ke pemula.

---

INPUT:
Berikut adalah kumpulan berita pasar terbaru:

{NEWS_DATA}

---

OUTPUT WAJIB:

1. KONDISI PASAR HARI INI
Jelaskan secara sederhana:
- pasar cenderung naik, turun, atau tidak jelas
- alasan utama dalam 2–4 kalimat

---

2. HAL PALING PENTING HARI INI
Ambil 2–3 poin yang benar-benar mempengaruhi pasar.
Abaikan hal yang tidak penting.

---

3. ARTINYA UNTUK INVESTOR PEMULA
Jelaskan:
- apakah kondisi ini cenderung aman atau berisiko
- aset atau sektor apa yang biasanya terpengaruh (contoh sederhana)

---

4. SIKAP YANG MASUK AKAL HARI INI
Berikan arahan sederhana seperti:
- “lebih baik tunggu dulu”
- “boleh tetap pegang aset”
- “hati-hati jika ingin tambah posisi”
- “tidak perlu panik”

(Jangan beri instruksi beli/jual spesifik)

---

5. RISIKO UTAMA HARI INI
Jelaskan 1–3 risiko yang bisa mengubah kondisi pasar secara tiba-tiba.

---

GAYA PENULISAN:
- seperti mentor ke pemula
- tenang, tidak menakutkan
- tidak terlalu formal
- mudah dipahami dalam sekali baca

Tujuan utama:
membantu pengguna mengambil keputusan lebih tenang dan masuk akal setiap hari.
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
