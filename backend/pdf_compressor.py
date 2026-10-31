"""
Backend logic untuk kompresi PDF.
Cara kerja: setiap gambar yang ada di dalam PDF diekstrak, diperkecil
resolusinya, dikompres ulang sebagai JPEG, lalu ditanam kembali ke PDF.
Tidak ada kode UI di file ini -- murni logic.
"""

import io

import pymupdf  # PyMuPDF
from PIL import Image


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
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
            except Exception:
                # gambar tidak bisa dibaca PIL (misal format aneh), skip
                continue

            if pil_img.mode in ("RGBA", "P", "LA"):
                pil_img = pil_img.convert("RGB")

            pil_img.thumbnail((max_dimension, max_dimension))

            buffer = io.BytesIO()
            pil_img.save(buffer, format="JPEG", quality=image_quality, optimize=True)
            buffer.seek(0)

            try:
                page.replace_image(xref, stream=buffer.read())
            except Exception:
                # beberapa xref (mis. mask/stencil) tidak bisa direplace, skip
                continue

    # garbage=4 & deflate=True membersihkan objek tak terpakai + kompres stream
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()
