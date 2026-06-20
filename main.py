import os
import sys
import time
from datetime import datetime
import requests
from google import genai
from google.genai import types

# ==========================================
# 1. CORE CONFIGURATION
# ==========================================
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not GEMINI_KEY or not DISCORD_URL:
    print("[FATAL ERROR] API Key atau Webhook URL tidak ditemukan di environment variables.")
    sys.exit(1)

print("[INFO] Memulai Inisiasi Elite Ekosistem Auditor Agent (GenAI SDK Terbaru)...")

# Inisialisasi client baru sesuai standar SDK resmi Google
client = genai.Client(api_key=GEMINI_KEY)

# ==========================================
# 2. AGENT BRAIN: MAX LEVEL INSTRUCTIONS
# ==========================================
system_instruction = (
    "Anda adalah 'Elite Institutional Crypto Auditor' yang bertugas secara otonom. "
    "Tugas Anda adalah melakukan riset web live dan menyusun audit laporan mingguan untuk aset Solana (SOL) dan Sui (SUI). "
    "Laporan ini digunakan oleh investor institusional untuk menjaga strategi DCA hingga 2030.\n\n"
    "ATURAN MUTLAK KELUARAN (OUTPUT):\n"
    "1. WAJIB menggunakan Bahasa Indonesia formal, tajam, dan profesional.\n"
    "2. JANGAN membandingkan Solana dan Sui. Berikan analisis mendalam secara terpisah karena keduanya di-hold secara mandiri.\n"
    "3. SARING TOTAL SEMUA NOISE: Dilarang keras membahas harga, grafik harian, prediksi harga, atau rumor media sosial.\n"
    "4. PRIORITASKAN SUMBER KREDIBEL: Lakukan pencarian informasi spesifik dari platform institusional seperti Messari, The Block, CoinDesk, CoinMarketCap, DefiLlama, Blockworks, serta blog resmi ekosistem terkait.\n\n"
    "STRUKTUR LAPORAN UNTUK MASING-MASING ASET:\n"
    "A. Adopsi Institusi & Modal: Perusahaan besar yang masuk, kemitraan strategis, tren arus dana/TVL.\n"
    "B. Arsitektur & Update Teknis: Upgrade jaringan, peningkatan keamanan, adopsi developer.\n"
    "C. Kewaspadaan Fundamental (Red Flags): Downtime jaringan, eksploitasi bug, tekanan regulasi yang spesifik, jadwal unlock token.\n\n"
    "Jika tidak ada update material, tulis: 'Tidak ada pergerakan material minggu ini.'\n"
    "Di akhir laporan, WAJIB buat daftar 'Sumber Data Utama' berupa nama situs atau domain yang Anda gunakan untuk menyusun laporan ini."
)

# ==========================================
# 3. TEXT PAGINATION LOGIC (SMART CHUNKING)
# ==========================================
def split_text(text, limit=4000):
    """Memotong teks agar kompatibel dengan limit 4096 karakter Discord Embed."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1: 
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks

# ==========================================
# 4. DEPLOY RESEARCH MISSION
# ==========================================
print("[INFO] Agent sedang menyisir internet untuk mencari data institusi & teknis terbaru (Solana & Sui)...")

research_prompt = (
    "Cari data fundamental, berita institusi, dan update teknis terbaru untuk Solana (SOL) dan Sui (SUI) dalam 7 hari terakhir. "
    "Fokuskan pencarian pada portal berita crypto kredibel dan data on-chain. "
    "Susun laporan sesuai struktur ketat yang telah diinstruksikan. Gunakan format Markdown."
)

try:
    # Menggunakan model dengan suffix -latest untuk menghindari error 404
    response = client.models.generate_content(
        model='gemini-1.5-pro-latest',
        contents=research_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[{"google_search": {}}],
            temperature=0.2 # Diturunkan agar gaya bahasa lebih analitis dan tidak berhalusinasi
        )
    )
    report_content = response.text
except Exception as e:
    print(f"[FATAL ERROR] Kegagalan sistem saat Agent melakukan riset web: {e}")
    sys.exit(1)

# ==========================================
# 5. DISPATCH ENCRYPTED REPORT (WITH PAGINATION)
# ==========================================
print("[INFO] Menyusun format dan mengirim transmisi data intelijen ke Discord...")

current_date = datetime.utcnow().strftime('%d %B %Y | %H:%M UTC')
text_chunks = split_text(report_content)
total_chunks = len(text_chunks)

for index, chunk in enumerate(text_chunks):
    if index == 0:
        title = "🏛️ INSTITUTIONAL GRADE REPORT: SOLANA & SUI"
        content_msg = "⚠️ **LAPORAN AUDIT EKOSISTEM MINGGUAN TELAH TERSEDIA** ⚠️"
    else:
        title = f"📄 LANJUTAN LAPORAN (Bagian {index + 1}/{total_chunks})"
        content_msg = "" 

    payload = {
        "username": "Tier-1 Auditor Agent",
        "avatar_url": "https://images.unsplash.com/photo-1620321023374-d1a68fbc720d?q=80&w=200&auto=format&fit=crop",
        "content": content_msg,
        "embeds": [
            {
                "title": title,
                "description": chunk,
                "color": 16766720,  # Gold/Emas
                "fields": [
                    {
                        "name": "⚙️ Status Transmisi",
                        "value": f"Bagian {index + 1} dari {total_chunks} | Filter Sumber Kredibel: AKTIF",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Otorisasi Akses Eksklusif • {current_date}"
                }
            }
        ]
    }

    try:
        res = requests.post(DISCORD_URL, json=payload)
        if res.status_code == 204:
            print(f"[SUCCESS] Transmisi {index + 1}/{total_chunks} berhasil dikirim.")
        else:
            print(f"[ERROR] Transmisi ditolak oleh Discord. Kode Status: {res.status_code}, Respon: {res.text}")
    except Exception as e:
        print(f"[FATAL ERROR] Gagal mengirim chunk {index + 1}: {e}")
    
    # Jeda 2 detik antar pengiriman untuk menghindari Rate Limit Discord
    time.sleep(2) 

print("[INFO] Semua misi intelijen selesai dieksekusi.")
