import os
import json
import requests
import feedparser
from datetime import datetime
from google import genai
from google.genai import types

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

# =========================
# MEMORY — simpan data kemarin
# =========================

MEMORY_FILE = "market_memory.json"

def load_memory():
   if os.path.exists(MEMORY_FILE):
       with open(MEMORY_FILE, "r") as f:
           return json.load(f)
   return {}

def save_memory(data):
   with open(MEMORY_FILE, "w") as f:
       json.dump(data, f, indent=2)

# =========================
# TOOL: Ambil berita RSS
# =========================

def fetch_news():
   rss_sources = [
       "https://rss.cnn.com/rss/money_latest.rss",
       "https://feeds.bbci.co.uk/news/business/rss.xml",
       "https://finance.yahoo.com/news/rssindex",
       "https://www.cnbcindonesia.com/rss",
       "https://rss.kontan.co.id/news/investasi",
   ]

   news_items = []
   for rss in rss_sources:
       try:
           feed = feedparser.parse(rss)
           for item in feed.entries[:5]:
               news_items.append({
                   "title": item.title,
                   "link": item.link,
                   "source": feed.feed.get("title", "Unknown")
               })
       except:
           continue

   return news_items if news_items else [{"title": "No news available", "link": "", "source": ""}]

# =========================
# TOOL: Cek apakah berita relevan ke saham tertentu
# =========================

def filter_relevant_news(news_items, saham_list):
   keywords = list(saham_list.keys()) + list(saham_list.values()) + [
       "bank", "telkom", "astra", "rupiah", "ihsg", "bi rate",
       "inflasi", "ekspor", "impor", "ojk", "bei", "saham",
       "dividen", "laba", "pendapatan", "ekonomi indonesia"
   ]

   relevant = []
   general = []

   for item in news_items:
       title_lower = item["title"].lower()
       if any(kw.lower() in title_lower for kw in keywords):
           relevant.append(item)
       else:
           general.append(item)

   return relevant, general

# =========================
# TOOL: Format berita untuk prompt
# =========================

def format_news(relevant, general):
   text = "=== BERITA RELEVAN SAHAM INDONESIA ===\n"
   if relevant:
       for item in relevant:
           text += f"- [{item['source']}] {item['title']}\n"
   else:
       text += "Tidak ada berita spesifik hari ini.\n"

   text += "\n=== BERITA PASAR GLOBAL ===\n"
   for item in general[:5]:
       text += f"- [{item['source']}] {item['title']}\n"

   return text

# =========================
# AGENTIC STEP 1: Planning
# Gemini memutuskan sendiri fokus analisis hari ini
# =========================

def agent_plan(news_text, memory):
   yesterday = memory.get("last_report_date", "tidak ada data")
   prev_risks = memory.get("top_risks", "tidak ada data")
   prev_sentiment = memory.get("overall_sentiment", "tidak ada data")

   plan_prompt = f"""
Kamu adalah agentic AI analis saham BEI.

Konteks dari laporan kemarin ({yesterday}):
- Sentimen keseluruhan: {prev_sentiment}
- Risiko utama yang dipantau: {prev_risks}

Berita hari ini:
{news_text}

Tugasmu:
1. Tentukan FOKUS UTAMA analisis hari ini (sektor apa yang paling perlu diperhatikan?)
2. Tentukan 3 saham prioritas yang perlu analisis LEBIH DALAM hari ini
3. Tentukan apakah kondisi hari ini LEBIH BAIK, SAMA, atau LEBIH BURUK dari kemarin
4. Identifikasi apakah ada RISIKO BARU yang muncul dibanding kemarin

Jawab dalam format JSON:
{{
 "fokus_hari_ini": "...",
 "saham_prioritas": ["KODE1", "KODE2", "KODE3"],
 "kondisi_vs_kemarin": "lebih baik / sama / lebih buruk",
 "ada_risiko_baru": true/false,
 "risiko_baru": "..."
}}

Hanya jawab JSON, tidak ada teks lain.
"""

   response = client.models.generate_content(
       model="gemini-2.5-flash",
       contents=plan_prompt,
       config={"max_output_tokens": 1000}
   )

   try:
       clean = response.text.strip().replace("```json", "").replace("```", "")
       return json.loads(clean)
   except:
       return {
           "fokus_hari_ini": "pasar umum",
           "saham_prioritas": ["BBCA", "BBRI", "TLKM"],
           "kondisi_vs_kemarin": "sama",
           "ada_risiko_baru": False,
           "risiko_baru": ""
       }

# =========================
# AGENTIC STEP 2: Deep Analysis
# Analisis mendalam untuk saham prioritas
# =========================

def agent_deep_analysis(saham_prioritas, news_text):
   saham_info = {k: v for k, v in BLUE_CHIP_SAHAM.items() if k in saham_prioritas}
   saham_str = ", ".join([f"{k} ({v})" for k, v in saham_info.items()])

   deep_prompt = f"""
Kamu adalah analis saham senior. Lakukan analisis MENDALAM untuk saham prioritas hari ini.

Saham prioritas: {saham_str}
Berita relevan: {news_text}

Untuk setiap saham, analisis:
1. Dampak berita jangka pendek (hari ini - 1 minggu)
2. Dampak berita jangka menengah (1-3 bulan)
3. Apakah ini mengubah thesis investasi jangka panjang?
4. Level confidence analisis ini: TINGGI / SEDANG / RENDAH

Jawab dalam format JSON:
{{
 "KODE_SAHAM": {{
   "dampak_pendek": "...",
   "dampak_menengah": "...",
   "ubah_thesis": true/false,
   "penjelasan_thesis": "...",
   "confidence": "TINGGI/SEDANG/RENDAH"
 }}
}}

Hanya jawab JSON, tidak ada teks lain.
"""

   response = client.models.generate_content(
       model="gemini-2.5-flash",
       contents=deep_prompt,
       config={"max_output_tokens": 2000}
   )

   try:
       clean = response.text.strip().replace("```json", "").replace("```", "")
       return json.loads(clean)
   except:
       return {}

# =========================
# AGENTIC STEP 3: Final Report
# Gemini tulis laporan final berdasarkan semua data
# =========================

def agent_final_report(news_text, plan, deep_analysis, memory):
   saham_list = ", ".join([f"{k} ({v})" for k, v in BLUE_CHIP_SAHAM.items()])
   yesterday_sentiment = memory.get("overall_sentiment", "tidak ada data kemarin")

   report_prompt = f"""
Kamu adalah analis saham senior BEI. Tulis laporan harian blue chip berdasarkan data berikut.

SEMUA SAHAM DIPANTAU: {saham_list}

FOKUS ANALISIS HARI INI: {plan.get('fokus_hari_ini')}
KONDISI VS KEMARIN: {plan.get('kondisi_vs_kemarin')}
RISIKO BARU: {plan.get('risiko_baru', 'tidak ada')}

ANALISIS MENDALAM SAHAM PRIORITAS:
{json.dumps(deep_analysis, indent=2, ensure_ascii=False)}

BERITA HARI INI:
{news_text}

SENTIMEN KEMARIN: {yesterday_sentiment}

---

Tulis laporan dengan format Discord markdown persis seperti ini:

╔════════════════════════════════════╗
　　　📈 BLUE CHIP DAILY RESEARCH
　　　BEI Watchlist — Laporan Harian
╚════════════════════════════════════╝

🌍 **KONDISI PASAR**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
[3-4 kalimat. Sebutkan perubahan vs kemarin jika ada]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 **FOKUS ANALISIS HARI INI**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
[Jelaskan kenapa AI memilih fokus ini hari ini]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **ANALISIS MENDALAM — SAHAM PRIORITAS**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔

[Untuk 3 saham prioritas, gunakan format:]

┌─────────────────────────────────┐
│ 🏦 [KODE] — [NAMA]  🔬 PRIORITAS │
└─────────────────────────────────┘
Sentimen     : 🟢/🔴/🟡 [Positif/Negatif/Netral]
Jangka Pendek: [dampak minggu ini]
Jangka Menengah: [dampak 1-3 bulan]
Thesis Berubah?: [Ya/Tidak — penjelasan singkat]
Confidence   : 🔵 TINGGI / 🟡 SEDANG / 🔴 RENDAH
Aksi         : ✅ Accumulate / ⏸️ Hold / ⏳ Wait and See

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **SAHAM LAINNYA**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔

[Untuk 7 saham lainnya, format ringkas:]

┌─────────────────────────────┐
│ 🏦 [KODE] — [NAMA]           │
└─────────────────────────────┘
Sentimen  : 🟢/🔴/🟡
Alasan    : [1 kalimat]
Aksi      : ✅/⏸️/⏳

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **RISIKO UTAMA HARI INI**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
▸ [Risiko 1]
▸ [Risiko 2]
▸ [Risiko 3 — tandai 🆕 jika risiko baru]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **INSIGHT UNTUK PEMULA**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
[1 paragraf pelajaran dari kondisi hari ini]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **WATCHLIST SUMMARY**
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
🟢 BBCA  ·  Hold
🟢 BBRI  ·  Hold
[isi semua 10 saham]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ⚠️ Bukan rekomendasi finansial resmi.
> Selalu lakukan riset mandiri sebelum berinvestasi.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PENTING:
- Semua 10 saham wajib muncul
- Jangan prediksi harga pasti
- Output harus selesai sempurna sampai baris terakhir
"""

   response = client.models.generate_content(
       model="gemini-2.5-flash",
       contents=report_prompt,
       config={"max_output_tokens": 8192}
   )

   return response.text

# =========================
# DISCORD SENDER
# =========================

def send_discord(text):
   chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
   total = len(chunks)

   for i, chunk in enumerate(chunks):
       if i == 0:
           payload = {"content": chunk}
       else:
           payload = {"content": f"*(lanjutan {i+1}/{total})*\n{chunk}"}

       res = requests.post(WEBHOOK_URL, json=payload)
       if res.status_code not in [200, 204]:
           print(f"Gagal kirim part {i+1}: {res.status_code}")
       else:
           print(f"Part {i+1}/{total} terkirim.")

# =========================
# MAIN AGENTIC LOOP
# =========================

def main():
   print("🤖 Agentic AI starting...")
   today = datetime.now().strftime("%Y-%m-%d")

   # Load memory
   memory = load_memory()
   print(f"📂 Memory loaded. Last run: {memory.get('last_report_date', 'never')}")

   # Step 1: Fetch & filter news
   print("📰 Fetching news...")
   news_items = fetch_news()
   relevant, general = filter_relevant_news(news_items, BLUE_CHIP_SAHAM)
   news_text = format_news(relevant, general)
   print(f"✅ {len(relevant)} relevant news, {len(general)} general news found.")

   # Step 2: Agent plans focus
   print("🧠 Agent planning focus...")
   plan = agent_plan(news_text, memory)
   print(f"📌 Focus: {plan.get('fokus_hari_ini')}")
   print(f"📌 Priority stocks: {plan.get('saham_prioritas')}")

   # Step 3: Deep analysis on priority stocks
   print("🔬 Running deep analysis...")
   deep_analysis = agent_deep_analysis(plan.get("saham_prioritas", []), news_text)

   # Step 4: Generate final report
   print("📝 Generating final report...")
   report = agent_final_report(news_text, plan, deep_analysis, memory)

   # Step 5: Send to Discord
   print("📤 Sending to Discord...")
   send_discord(report)

   # Step 6: Save memory for tomorrow
   new_memory = {
       "last_report_date": today,
       "overall_sentiment": plan.get("kondisi_vs_kemarin"),
       "top_risks": plan.get("risiko_baru", ""),
       "last_focus": plan.get("fokus_hari_ini"),
       "last_priority_stocks": plan.get("saham_prioritas")
   }
   save_memory(new_memory)
   print(f"💾 Memory saved for tomorrow.")
   print("✅ Agentic report sent successfully.")

if __name__ == "__main__":
   main()
