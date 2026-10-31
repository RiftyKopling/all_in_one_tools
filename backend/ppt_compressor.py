"""
Backend logic untuk kompresi PPTX.

PPTX sebenarnya adalah file ZIP berisi XML + media (gambar).
Strateginya: extract zip -> kompres tiap gambar di folder ppt/media ->
zip ulang jadi pptx baru. Tidak perlu parsing XML slide sama sekali.
"""

import io
import os
import shutil
import zipfile

from PIL import Image


def compress_pptx(input_path: str, output_path: str,
                  quality: int = 60, max_dimension: int = 1600) -> None:
    """
    Kompres gambar-gambar di dalam file PPTX.

    Args:
        input_path: path file .pptx asli
        output_path: path untuk menyimpan hasil kompresi
        quality: kualitas JPEG untuk gambar hasil kompresi (1-100)
        max_dimension: batas maksimum lebar/tinggi gambar (px)
    """
    tmp_dir = output_path + "_tmp_extract"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    with zipfile.ZipFile(input_path, "r") as zf:
        zf.extractall(tmp_dir)

    media_dir = os.path.join(tmp_dir, "ppt", "media")
    if os.path.isdir(media_dir):
        for filename in os.listdir(media_dir):
            filepath = os.path.join(media_dir, filename)
            ext = filename.lower().rsplit(".", 1)[-1]

            if ext not in ("jpg", "jpeg", "png", "bmp"):
                continue  # biarkan format lain (svg, wmf, dll) apa adanya

            try:
                img = Image.open(filepath)
            except Exception:
                continue

            img.thumbnail((max_dimension, max_dimension))

            if ext == "png":
                img.save(filepath, format="PNG", optimize=True)
            else:
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                img.save(filepath, format="JPEG", quality=quality, optimize=True)

    # zip ulang jadi pptx baru
    if os.path.exists(output_path):
        os.remove(output_path)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, tmp_dir)
                zf.write(full_path, arcname)

    shutil.rmtree(tmp_dir)
