"""
Backend logic untuk kompresi gambar (JPG/PNG).
"""

from PIL import Image


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
    img = _apply_transparency(img)

    img.thumbnail((max_dimension, max_dimension))
    img.save(output_path, format="JPEG", quality=quality, optimize=True)