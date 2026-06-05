import os
import json
import time
import requests
import feedparser
from datetime import datetime
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

# =========================
# MEMORY
# =========================

MEMORY_FILE = "market_memory.json"

def load_memory():
   if os.path.exists(MEMORY_FILE):
       with open(MEMORY_FILE, "r") as f:
           return json.load(f)
   return {}

def save_memory(data):
   with open(MEMORY_FILE, "w") as f:
       json.dump(data, f, indent=2, ensure_ascii=False)

# =========================
# GEMINI WRAPPER WITH RETRY
# =========================

def gemini_generate(prompt, max_tokens=1000, retries=3, delay=15):
   for attempt in range(retries):
       try:
           response = client.models.generate_content(
               model="gemini-2.0-flash",
               contents=prompt,
               config={"max_output_tokens": max_tokens}
           )
           return response
       except Exception as e:
           print(f"⚠️ Gemini error attempt {attempt+1}/{retries}: {e}")
           if attempt < retries - 1:
               print(f"⏳ Retry dalam {delay} detik...")
               time.sleep(delay)
           else:
               raise

# =========================
# TOOL: Fetch News
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
# TOOL: Filter News
# =========================

def filter_relevant_news(news_items):
   keywords = list(BLUE_CHIP_SAHAM.keys()) + list(BLUE_CHIP_SAHAM.values()) + [
       "bank", "telkom", "astra", "rupiah", "ihsg", "bi rate",
       "inflasi", "ekspor", "impor", "ojk", "bei", "saham",
       "dividen", "laba", "pendapatan", "ekonomi indonesia",
       "suku bunga", "fed", "dollar", "komoditas", "minyak"
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

def format_news(relevant, general):
   text = "=== BERITA RELEVAN ===\n"
   text += "\n".join([f"- [{i['source']}] {i['title']}" for i in relevant]) if relevant else "Tidak ada berita spesifik.\n"
   text += "\n\n=== BERITA GLOBAL ===\n"
   text += "\n".join([f"- [{i['source']}] {i['title']}" for i in general[:6]])
   return text

# =========================
# TOOL: Macro Sentiment Score
# =========================

def agent_macro_score(news_text):
   prompt = f"""
Berikan skor sentimen makro ekonomi hari ini dari 1-10.
1 = sangat bearish, 10 = sangat bullish.

Berita: {news_text}

Jawab JSON saja:
{{
 "skor": 7,
 "label": "Bullish / Netral / Bearish",
 "alasan": "1 kalimat singkat"
}}
"""
   response = gemini_generate(prompt, max_tokens=300)
   try:
       clean = response.text.strip().replace("```json", "").replace("```", "")
       return json.loads(clean)
   except:
       return {"skor": 5, "label": "Netral", "alasan": "Data tidak cukup untuk penilaian."}

# =========================
# AGENTIC STEP 1: Planning
# =========================

def agent_plan(news_text, memory):
   yesterday = memory.get("last_report_date", "tidak ada data")
   prev_risks = memory.get("top_risks", "tidak ada data")
   prev_sentiment = memory.get("overall_sentiment", "tidak ada data")
   prev_score = memory.get("macro_score", "tidak ada data")

   prompt = f"""
Kamu adalah agentic AI analis saham BEI.

Data kemarin ({yesterday}):
- Sentimen: {prev_sentiment}
- Skor makro: {prev_score}/10
- Risiko: {prev_risks}

Berita hari ini:
{news_text}

Tugasmu:
1. Tentukan fokus utama analisis hari ini
2. Pilih 3 saham prioritas yang paling terdampak berita
3. Nilai kondisi vs kemarin
4. Deteksi risiko baru jika ada
5. Berikan rekomendasi sektor: DEFENSIF / GROWTH / MIXED

Jawab JSON saja:
{{
 "fokus_hari_ini": "...",
 "saham_prioritas": ["KODE1", "KODE2", "KODE3"],
 "kondisi_vs_kemarin": "lebih baik / sama / lebih buruk",
 "ada_risiko_baru": true,
 "risiko_baru": "...",
 "rekomendasi_sektor": "DEFENSIF / GROWTH / MIXED",
 "alasan_sektor": "..."
}}
"""
   response = gemini_generate(prompt, max_tokens=1000)
   try:
       clean = response.text.strip().replace("```json", "").replace("```", "")
       return json.loads(clean)
   except:
       return {
           "fokus_hari_ini": "pasar umum",
           "saham_prioritas": ["BBCA", "BBRI", "TLKM"],
           "kondisi_vs_kemarin": "sama",
           "ada_risiko_baru": False,
           "risiko_baru": "",
           "rekomendasi_sektor": "MIXED",
           "alasan_sektor": "Data tidak cukup."
       }

# =========================
# AGENTIC STEP 2: Deep Analysis
# =========================

def agent_deep_analysis(saham_prioritas, news_text):
   saham_info = {k: v for k, v in BLUE_CHIP_SAHAM.items() if k in saham_prioritas}
   saham_str = ", ".join([f"{k} ({v})" for k, v in saham_info.items()])

   prompt = f"""
Analisis mendalam untuk saham prioritas hari ini.

Saham: {saham_str}
Berita: {news_text}

Untuk setiap saham jawab:
1. Dampak jangka pendek (minggu ini)
2. Dampak jangka menengah (1-3 bulan)
3. Apakah thesis investasi berubah?
4. Confidence: TINGGI / SEDANG / RENDAH
5. Sentimen: positif / negatif / netral
6. Aksi: Accumulate / Hold / Wait and See

Jawab JSON saja:
{{
 "KODE": {{
   "dampak_pendek": "...",
   "dampak_menengah": "...",
   "ubah_thesis": true,
   "penjelasan_thesis": "...",
   "confidence": "TINGGI/SEDANG/RENDAH",
   "sentimen": "positif/negatif/netral",
   "aksi": "Accumulate/Hold/Wait and See"
 }}
}}
"""
   response = gemini_generate(prompt, max_tokens=2000)
   try:
       clean = response.text.strip().replace("```json", "").replace("```", "")
       return json.loads(clean)
   except:
       return {}

# =========================
# AGENTIC STEP 3: Final Report
# =========================

def agent_final_report(news_text, plan, deep_analysis, macro, memory, today):
   saham_list = ", ".join([f"{k} ({v})" for k, v in BLUE_CHIP_SAHAM.items()])
   yesterday_sentiment = memory.get("overall_sentiment", "tidak ada data kemarin")
   prev_score = memory.get("macro_score", "-")

   skor = macro.get("skor", 5)
   if skor >= 7:
       macro_emoji = "🟢"
   elif skor >= 4:
       macro_emoji = "🟡"
   else:
       macro_emoji = "🔴"

   prompt = f"""
Tulis laporan riset saham blue chip harian untuk Discord.

DATA:
- Tanggal: {today}
- Semua saham: {saham_list}
- Fokus hari ini: {plan.get('fokus_hari_ini')}
- Kondisi vs kemarin: {plan.get('kondisi_vs_kemarin')}
- Rekomendasi sektor: {plan.get('rekomendasi_sektor')} — {plan.get('alasan_sektor')}
- Risiko baru: {plan.get('risiko_baru', 'tidak ada')}
- Skor makro: {skor}/10 ({macro.get('label')}) — {macro.get('alasan')}
- Skor makro kemarin: {prev_score}/10
- Sentimen kemarin: {yesterday_sentiment}
- Analisis mendalam: {json.dumps(deep_analysis, ensure_ascii=False)}
- Berita: {news_text}

FORMAT LAPORAN (ikuti persis, gunakan Discord markdown):

📈 **BLUE CHIP DAILY RESEARCH**
`{today} · BEI Watchlist`

─────────────────────────────────

🌍 **Kondisi Pasar**
[3-4 kalimat ringkasan. Sebutkan perubahan vs kemarin dan arah pasar hari ini]

{macro_emoji} **Skor Makro · {skor}/10 · {macro.get('label')}**
> {macro.get('alasan')}
> *(kemarin: {prev_score}/10)*

─────────────────────────────────

🔍 **Fokus & Strategi Hari Ini**
Fokus · {plan.get('fokus_hari_ini')}
Sektor · {plan.get('rekomendasi_sektor')} — {plan.get('alasan_sektor')}

─────────────────────────────────

🔬 **Analisis Prioritas**

[Untuk setiap saham prioritas gunakan format ini:]

**[KODE] · [NAMA]**
> Sentimen · 🟢/🔴/🟡 [Positif/Negatif/Netral]
> Jangka Pendek · [1 kalimat]
> Jangka Menengah · [1 kalimat]
> Thesis Berubah · Ya/Tidak — [penjelasan singkat]
> Confidence · TINGGI/SEDANG/RENDAH
> Aksi · Accumulate/Hold/Wait and See

─────────────────────────────────

📋 **Saham Lainnya**

[Format satu baris per saham untuk 7 saham sisanya:]
**KODE** · 🟢/🔴/🟡 · Aksi · [alasan 1 kalimat]

─────────────────────────────────

⚠️ **Risiko Hari Ini**
▸ [Risiko 1]
▸ [Risiko 2]
▸ [Risiko 3 — tambahkan 🆕 jika risiko baru]

─────────────────────────────────

💡 **Insight**
[1 paragraf singkat pelajaran dari kondisi pasar hari ini untuk investor pemula]

─────────────────────────────────
*Bukan rekomendasi finansial resmi · Riset mandiri tetap diperlukan*

PENTING:
- Semua 10 saham wajib muncul
- Output harus selesai sempurna sampai baris terakhir
- Jangan prediksi harga pasti
"""

   response = gemini_generate(prompt, max_tokens=8192)
   return response.text

# =========================
# DISCORD SENDER
# =========================

def send_discord(text):
   chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
   total = len(chunks)

   for i, chunk in enumerate(chunks):
       payload = {"content": chunk if i == 0 else f"*(lanjutan {i+1}/{total})*\n{chunk}"}
       res = requests.post(WEBHOOK_URL, json=payload)
       if res.status_code not in [200, 204]:
           print(f"Gagal kirim part {i+1}: {res.status_code}")
       else:
           print(f"✅ Part {i+1}/{total} terkirim.")

# =========================
# MAIN
# =========================

def main():
   today = datetime.now().strftime("%Y-%m-%d")
   print(f"🤖 Agentic AI starting — {today}")

   memory = load_memory()
   print(f"📂 Last run: {memory.get('last_report_date', 'never')}")

   print("📰 Fetching news...")
   news_items = fetch_news()
   relevant, general = filter_relevant_news(news_items)
   news_text = format_news(relevant, general)
   print(f"✅ {len(relevant)} relevant, {len(general)} general news.")

   print("📊 Scoring macro sentiment...")
   macro = agent_macro_score(news_text)
   print(f"📊 Macro score: {macro.get('skor')}/10 — {macro.get('label')}")

   print("🧠 Planning...")
   plan = agent_plan(news_text, memory)
   print(f"📌 Focus: {plan.get('fokus_hari_ini')}")
   print(f"📌 Priority: {plan.get('saham_prioritas')}")
   print(f"📌 Sector: {plan.get('rekomendasi_sektor')}")

   print("🔬 Deep analysis...")
   deep_analysis = agent_deep_analysis(plan.get("saham_prioritas", []), news_text)

   print("📝 Generating report...")
   report = agent_final_report(news_text, plan, deep_analysis, macro, memory, today)

   print("📤 Sending to Discord...")
   send_discord(report)

   save_memory({
       "last_report_date": today,
       "overall_sentiment": plan.get("kondisi_vs_kemarin"),
       "top_risks": plan.get("risiko_baru", ""),
       "last_focus": plan.get("fokus_hari_ini"),
       "last_priority_stocks": plan.get("saham_prioritas"),
       "macro_score": macro.get("skor"),
       "macro_label": macro.get("label"),
       "rekomendasi_sektor": plan.get("rekomendasi_sektor")
   })

   print("💾 Memory saved.")
   print("✅ Done.")

if __name__ == "__main__":
   main()
