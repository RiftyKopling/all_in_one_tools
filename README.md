# All-in-One File Compressor & Image-to-PDF Tool

Aplikasi Streamlit ringan untuk **mengompres file** (PDF, gambar, PowerPoint, video, dan audio) dan **menggabungkan gambar menjadi PDF** dengan editor bawaan (rotasi & crop).

---

## ✨ Fitur

| Kategori | Detail |
|----------|--------|
| **Kompres PDF** | Mengecilkan resolusi & kualitas gambar di dalam PDF (via PyMuPDF + Pillow). |
| **Kompres Gambar** | Resize + re-encode JPEG (Pillow). |
| **Kompres PPTX** | Ekstrak media, kompres gambar di `ppt/media/`, zip ulang (zipfile + Pillow). |
| **Kompres Video** | Transcode H.264/AAC via `ffmpeg` (butuh ffmpeg di sistem). |
| **Kompres Audio** | Resize + re-encode audio (MP3, WAV, FLAC, dll) via `ffmpeg` (butuh ffmpeg di sistem). |
| **Images → PDF (NEW)** | Upload multi-gambar → grid preview → edit per gambar (rotasi 90°/180°, crop X/Y/W/H) → layout 1/halaman atau 2/halaman grid → orientasi portrait/landscape → margin & kualitas → generate & download PDF. |

---

## 🚀 Quick Start

### 1. Prasyarat
- **Python 3.9+**
- **ffmpeg** (untuk kompresi video dan audio)
  - Windows: `winget install Gyan.FFmpeg` atau unduh dari <https://ffmpeg.org/download.html>
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`

### 2. Instalasi
```bash
git clone https://github.com/RiftyKopling/all-in-one-tool.git
cd all-in-one-tool
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 3. Jalankan
```bash
streamlit run app.py
```
Buka <http://localhost:8501> di browser.

---

## 📂 Struktur Proyek

```
all-in-one-tool/
├── app.py                 # UI Streamlit (tab: Kompres File | Images → PDF)
├── requirements.txt       # streamlit, pymupdf, pillow
├── Kompresor.bat          # Launcher Windows (opsional)
├── .streamlit/
│   └── config.toml        # Konfigurasi Streamlit
└── backend/
    ├── __init__.py
    ├── pdf_compressor.py
    ├── image_compressor.py
    ├── ppt_compressor.py
    ├── video_compressor.py
    ├── audio_compressor.py  # NEW: Logic kompresi audio
    └── image_to_pdf.py    # Logic Images → PDF (edit, layout, generate)
```

---

## 🖼️ Images → PDF – Panduan Singkat

1. Buka tab **📄 Images → PDF**.
2. **Upload** beberapa file PNG/JPG (drag-drop atau *browse*).
3. **Grid preview** muncul. Klik **✏️ Edit** pada gambar:
   - **Rotasi**: tombol `↻ 90°`, `↺ -90°`, `↻ 180°` (dropdown "Sudut" ikut berubah).
   - **Crop**: isi `X`, `Y`, `W`, `H` (pixel). `0` = tidak crop. Tombol **Auto-fit** / **Reset Crop** mengosongkan crop.
   - **✅ Simpan Edit** → kembali ke grid.
4. **Pengaturan Output PDF** (sidebar kanan):
   - Layout: `1 gambar per halaman` / `2 gambar per halaman (grid)`
   - Orientasi: `Portrait` / `Landscape`
   - Margin (mm), Kualitas (0–100)
5. Klik **🔄 Generate PDF** → **⬇️ Download PDF** (nama file bisa diubah sebelum download).

---

## ⚙️ Konfigurasi Streamlit (opsional)

Edit `.streamlit/config.toml`:
```toml
[server]
maxUploadSize = 200   # MB, default 200
enableCORS = false
```

---

## 📦 Dependencies

| Paket | Fungsi |
|-------|--------|
| `streamlit` | Web UI framework |
| `pymupdf` (fitz) | Manipulasi PDF (kompres, ekstrak gambar) |
| `pillow` | Pemrosesan gambar (resize, crop, rotate, encode) |
| `ffmpeg` (system) | Transcoding video & audio (CLI) |

---

## 🛠️ Development

- Semua logika kompresi & konversi berada di folder `backend/` (pure functions, no UI).
- UI hanya di `app.py`; memanggil fungsi backend.
- Tambah fitur baru: buat modul di `backend/`, import di `app.py`.

### Menjalankan tes cepat backend
```bash
python -c "
from backend.image_to_pdf import apply_edits, generate_pdf
from PIL import Image
img = Image.new('RGB', (200,100), 'red')
print(apply_edits(img, {'rotation':90, 'crop':{}}).size)  # (100,200)
"
```

---

## 📄 Lisensi

MIT License – bebas digunakan, dimodifikasi, dan didistribusikan.

---

## 🤝 Kontribusi

PR & issue dipersilakan!  
1. Fork repo  
2. Buat branch fitur (`git checkout -b fitur/awesome`)  
3. Commit & push  
4. Buka Pull Request

**Dibuat dengan ❤️ menggunakan Python + Streamlit.**