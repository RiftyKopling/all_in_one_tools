"""
Backend logic untuk kompresi PDF.
Cara kerja: setiap gambar yang ada di dalam PDF diekstrak, diperkecil
resolusinya, dikompres ulang sebagai JPEG, lalu ditanam kembali ke PDF.
Tidak ada kode UI di file ini -- murni logic.
"""

import io

import pymupdf  # PyMuPDF
from PIL import Image


def _pil_from_pixmap(pix: pymupdf.Pixmap) -> Image.Image:
    """Convert PyMuPDF Pixmap to PIL Image, handling alpha correctly."""
    if pix.alpha:
        # Pixmap has alpha: convert to RGBA PIL image
        img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
        return img
    else:
        # No alpha: RGB
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return img


def _apply_transparency(img: Image.Image) -> Image.Image:
    """Paste image onto white background if it has transparency."""
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.getchannel("A"))
        return bg
    elif img.mode == "P":
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.getchannel("A"))
        return bg
    return img.convert("RGB")


def compress_pdf(input_path: str, output_path: str,
                image_quality: int = 50, max_dimension: int = 1600) -> None:
    """
    Kompres PDF dengan mengecilkan & mengompres ulang gambar di dalamnya.

    Args:
        input_path: path file PDF asli
        output_path: path untuk menyimpan hasil kompresi
        image_quality: kualitas JPEG untuk gambar di dalam PDF (1-100)
        max_dimension: batas maksimum lebar/tinggi gambar (px)
    """
    doc = pymupdf.open(input_path)

    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]

            # Cek apakah gambar punya SMask (soft mask / transparency mask)
            smask_xref = img[1] if len(img) > 1 else 0

            # Ekstrak gambar utama
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
            except Exception:
                continue

            # Jika ada SMask, ekstrak dan terapkan sebagai alpha channel
            if smask_xref:
                try:
                    smask_img = doc.extract_image(smask_xref)
                    smask_bytes = smask_img["image"]
                    smask_pil = Image.open(io.BytesIO(smask_bytes))
                    # SMask biasanya grayscale, resize ke ukuran gambar utama
                    if smask_pil.size != pil_img.size:
                        smask_pil = smask_pil.resize(pil_img.size, Image.Resampling.LANCZOS)
                    # Pastikan mode L (grayscale) untuk mask
                    if smask_pil.mode != "L":
                        smask_pil = smask_pil.convert("L")
                    # Tempelkan mask ke gambar
                    if pil_img.mode != "RGBA":
                        pil_img = pil_img.convert("RGBA")
                    pil_img.putalpha(smask_pil)
                except Exception:
                    # Gagal ekstrak/apply SMask, lanjutkan tanpa transparansi
                    pass

            # Handle transparency: paste onto white background
            pil_img = _apply_transparency(pil_img)

            pil_img.thumbnail((max_dimension, max_dimension))

            buffer = io.BytesIO()
            pil_img.save(buffer, format="JPEG", quality=image_quality, optimize=True)
            buffer.seek(0)

            try:
                page.replace_image(xref, stream=buffer.read())
            except Exception:
                continue

    # garbage=4 & deflate=True membersihkan objek tak terpakai + kompres stream
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()