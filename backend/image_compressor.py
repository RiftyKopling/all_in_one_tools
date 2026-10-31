"""
Backend logic untuk kompresi gambar (JPG/PNG).
"""

from PIL import Image


def compress_image(input_path: str, output_path: str,
                    quality: int = 70, max_dimension: int = 1920) -> None:
    """
    Kompres gambar dengan resize + re-encode JPEG.

    Args:
        input_path: path gambar asli
        output_path: path untuk menyimpan hasil kompresi
        quality: kualitas JPEG (1-100)
        max_dimension: batas maksimum lebar/tinggi (px)
    """
    img = Image.open(input_path)

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    img.thumbnail((max_dimension, max_dimension))
    img.save(output_path, format="JPEG", quality=quality, optimize=True)
