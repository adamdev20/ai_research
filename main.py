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
# BLUE CHIP WATCHLIST
# =========================

BLUE_CHIP_SAHAM = {
   "BBCA": "Bank Central Asia",
   "BBRI": "Bank Rakyat Indonesia",
   "BMRI": "Bank Mandiri",
   "TLKM": "Telkom Indonesia",
   "ASII": "Astra International",
   "UNVR": "Unilever Indonesia",
   "ICBP": "Indofood CBP",
   "KLBF": "Kalbe Farma",
   "HMSP": "HM Sampoerna",
   "INDF": "Indofood Sukses Makmur",
}

SAHAM_LIST = ", ".join([f"{k} ({v})" for k, v in BLUE_CHIP_SAHAM.items()])

# =========================
# RSS SOURCES
# =========================

rss_sources = [
   "https://rss.cnn.com/rss/money_latest.rss",
   "https://feeds.bbci.co.uk/news/business/rss.xml",
   "https://finance.yahoo.com/news/rssindex",
   "https://www.cnbcindonesia.com/rss",
   "https://rss.kontan.co.id/news/investasi",
]

# =========================
# COLLECT NEWS
# =========================

news_items = []

for rss in rss_sources:
   try:
       feed = feedparser.parse(rss)
       for item in feed.entries[:5]:
           news_items.append(f"- {item.title} | {item.link}")
   except:
       continue

if not news_items:
   news_items.append("No market news available today.")

news_text = "\n".join(news_items)

# =========================
# PROMPT
# =========================

prompt = f"""
Kamu adalah analis saham senior BEI yang khusus mengikuti saham blue chip Indonesia.

Saham yang kamu pantau hari ini:
{SAHAM_LIST}

Berikut adalah berita pasar terkini:
{news_text}

---

Buat laporan riset harian. Gunakan bahasa Indonesia yang jelas untuk investor pemula.

FORMAT OUTPUT (gunakan markdown Discord: **bold**, __underline__, > quote):

**📈 BLUE CHIP DAILY RESEARCH**
__Laporan Otomatis — BEI Blue Chip Watchlist__

---

**📌 KONDISI PASAR HARI INI**
[3-4 kalimat ringkasan situasi pasar global & Indonesia]

---

**📊 DAMPAK KE SAHAM BLUE CHIP**
[Untuk tiap saham yang terdampak berita, gunakan format ini:]

> **[KODE] — [NAMA]**
> Sentimen: 🟢 Positif / 🔴 Negatif / 🟡 Netral
> Alasan: [1-2 kalimat singkat]
> Aksi: Hold / Accumulate / Wait and See

[Jika tidak ada dampak langsung, tulis: "Tidak ada dampak berita langsung hari ini untuk saham ini."]

---

**⚠️ RISIKO UTAMA HARI INI**
• [Risiko 1]
• [Risiko 2]
• [Risiko 3]

---

**💡 INSIGHT UNTUK PEMULA**
[1 paragraf pelajaran atau pengingat penting]

---

**📋 WATCHLIST SUMMARY**
[Buat tabel teks polos karena Discord tidak render tabel markdown:]

KODE  | SENTIMEN   | AKSI
------|------------|------------------
BBCA  | 🟢 Positif | Accumulate
BBRI  | 🟡 Netral  | Hold
[isi semua 10 saham]

---

⚠️ *Laporan ini bukan rekomendasi finansial resmi. Selalu lakukan riset mandiri sebelum berinvestasi.*

---

PENTING:
- Jangan prediksi harga pasti
- Fokus dampak jangka menengah 1-3 bulan
- Semua 10 saham wajib muncul di watchlist summary
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
# DISCORD WEBHOOK SENDER
# =========================

def send_discord(text):
   # Split per 1900 karakter agar aman (limit Discord 2000)
   chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
   total = len(chunks)

   for i, chunk in enumerate(chunks):
       # Part pertama pakai header banner
       if i == 0:
           payload = {"content": chunk}
       else:
           payload = {"content": f"*(lanjutan {i+1}/{total})*\n{chunk}"}

       res = requests.post(WEBHOOK_URL, json=payload)

       if res.status_code not in [200, 204]:
           print(f"Gagal kirim part {i+1}: {res.status_code} - {res.text}")
       else:
           print(f"Part {i+1}/{total} terkirim.")

send_discord(report)
print("✅ Blue chip research report sent to Discord.")
