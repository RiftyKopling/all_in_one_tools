"""
Backend logic untuk memotong (crop) halaman PDF.
Digunakan untuk menghapus watermark (mis. CamScanner) dengan memotong tepi halaman.
"""

import pymupdf  # PyMuPDF
from PIL import Image
import io


def crop_pdf(
    input_path: str,
    output_path: str,
    top_pct: float = 0.0,
    bottom_pct: float = 0.0,
    left_pct: float = 0.0,
    right_pct: float = 0.0,
) -> None:
    """
    Potong semua halaman PDF berdasarkan persentase dari dimensi mediabox.

    Args:
        input_path: path file PDF asli
        output_path: path untuk menyimpan hasil crop
        top_pct: persentase tinggi halaman yang dipotong dari atas (0-100)
        bottom_pct: persentase tinggi halaman yang dipotong dari bawah (0-100)
        left_pct: persentase lebar halaman yang dipotong dari kiri (0-100)
        right_pct: persentase lebar halaman yang dipotong dari kanan (0-100)
    """
    if not (0 <= top_pct < 100 and 0 <= bottom_pct < 100 and
            0 <= left_pct < 100 and 0 <= right_pct < 100):
        raise ValueError("Persentase crop harus 0-100")

    doc = pymupdf.open(input_path)

    for page in doc:
        mb = page.mediabox
        w = mb.width
        h = mb.height

        left = w * left_pct / 100.0
        right = w * right_pct / 100.0
        top = h * top_pct / 100.0
        bottom = h * bottom_pct / 100.0

        new_rect = pymupdf.Rect(
            mb.x0 + left,
            mb.y0 + top,
            mb.x1 - right,
            mb.y1 - bottom,
        )

        # Validasi: cropbox tidak boleh kosong
        if new_rect.width <= 0 or new_rect.height <= 0:
            raise ValueError("Crop terlalu besar, halaman menjadi kosong")

        page.set_cropbox(new_rect)

    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()


def render_page_preview(
    input_path: str,
    page_index: int = 0,
    dpi: int = 100,
    crop_pcts: tuple[float, float, float, float] | None = None,
) -> Image.Image:
    """
    Render halaman PDF ke PIL Image untuk preview.

    Args:
        input_path: path file PDF
        page_index: indeks halaman (0-based)
        dpi: resolusi render
        crop_pcts: optional (top, bottom, left, right) persentase untuk preview crop

    Returns:
        PIL Image (RGB)
    """
    doc = pymupdf.open(input_path)
    if page_index >= len(doc):
        page_index = 0
    page = doc[page_index]

    # Apply cropbox temporarily for preview if provided
    if crop_pcts is not None:
        top_pct, bottom_pct, left_pct, right_pct = crop_pcts
        mb = page.mediabox
        w = mb.width
        h = mb.height
        left = w * left_pct / 100.0
        right = w * right_pct / 100.0
        top = h * top_pct / 100.0
        bottom = h * bottom_pct / 100.0
        new_rect = pymupdf.Rect(
            mb.x0 + left,
            mb.y0 + top,
            mb.x1 - right,
            mb.y1 - bottom,
        )
        if new_rect.width > 0 and new_rect.height > 0:
            page.set_cropbox(new_rect)

    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def get_pdf_info(input_path: str) -> dict:
    """Ambil info dasar PDF: jumlah halaman, ukuran halaman pertama."""
    doc = pymupdf.open(input_path)
    info = {
        "page_count": len(doc),
        "first_page_size": None,
    }
    if len(doc) > 0:
        mb = doc[0].mediabox
        info["first_page_size"] = (mb.width, mb.height)
    doc.close()
    return info