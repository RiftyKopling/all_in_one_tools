"""
Backend logic untuk konversi gambar ke PDF dengan dukungan edit per-gambar
(rotasi 90°/180°, crop) dan opsi layout.
"""

from __future__ import annotations

import io
from typing import List, Dict, Any

from PIL import Image


# Page dimensions at 72 DPI (A4)
A4_PORTRAIT = (595, 842)
A4_LANDSCAPE = (842, 595)


def mm_to_px(mm: int, dpi: int = 72) -> int:
    """Convert millimetres to pixels at given DPI."""
    return int(mm * dpi / 25.4)


def _clamp_crop(img_w: int, img_h: int, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    """Clamp crop rectangle to image bounds."""
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = max(1, min(w, img_w - x))
    h = max(1, min(h, img_h - y))
    return x, y, w, h


def apply_edits(img: Image.Image, edit: Dict[str, Any]) -> Image.Image:
    """
    Apply rotation and crop to a PIL image.

    Args:
        img: Source PIL Image (not mutated).
        edit: Dict with keys:
            - "rotation": int, one of 0, 90, 180, 270 (clockwise degrees)
            - "crop": dict with keys "x", "y", "w", "h" (pixels). If w==0 or h==0 -> no crop.

    Returns:
        New PIL Image with edits applied (RGB mode).
    """
    if img is None:
        raise ValueError("Input image is None")

    # Work on a copy
    result = img.copy()

    # Rotation (clockwise). PIL rotates counter-clockwise, so negate.
    rot = int(edit.get("rotation", 0)) % 360
    if rot:
        result = result.rotate(-rot, expand=True)

    # Crop
    crop = edit.get("crop", {})
    x = int(crop.get("x", 0))
    y = int(crop.get("y", 0))
    w = int(crop.get("w", 0))
    h = int(crop.get("h", 0))

    if w > 0 and h > 0:
        img_w, img_h = result.size
        x, y, w, h = _clamp_crop(img_w, img_h, x, y, w, h)
        result = result.crop((x, y, x + w, y + h))

    # Ensure RGB mode for PDF
    if result.mode != "RGB":
        result = result.convert("RGB")

    return result


def _fit_to_page(img: Image.Image, page_w: int, page_h: int, margin_px: int) -> Image.Image:
    """Scale image to fit within page minus margin, preserving aspect ratio. Returns centred image on white background."""
    canvas = Image.new("RGB", (page_w, page_h), "white")

    # Available area inside margins
    avail_w = page_w - 2 * margin_px
    avail_h = page_h - 2 * margin_px

    img_w, img_h = img.size
    scale = min(avail_w / img_w, avail_h / img_h, 1.0)  # don't upscale beyond original
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    x = (page_w - new_w) // 2
    y = (page_h - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas


def _grid_two(left: Image.Image | None, right: Image.Image | None,
              page_w: int, page_h: int, margin_px: int) -> Image.Image:
    """Place two images side-by-side on one page."""
    canvas = Image.new("RGB", (page_w, page_h), "white")

    # Each cell gets half width minus margin
    cell_w = (page_w - 3 * margin_px) // 2  # left margin + gap + right margin
    cell_h = page_h - 2 * margin_px

    def place(img: Image.Image | None, col: int) -> None:
        if img is None:
            return
        img_w, img_h = img.size
        scale = min(cell_w / img_w, cell_h / img_h, 1.0)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        x = margin_px + col * (cell_w + margin_px) + (cell_w - new_w) // 2
        y = margin_px + (cell_h - new_h) // 2
        canvas.paste(resized, (x, y))

    place(left, 0)
    place(right, 1)
    return canvas


def compose_pages(images: List[Image.Image], layout: str, orientation: str = "portrait",
                  margin_mm: int = 10) -> List[Image.Image]:
    """
    Convert list of edited images into PDF pages according to layout.

    Args:
        images: List of PIL Images (already edited, RGB mode).
        layout: "1_per_page" or "2_per_page_grid".
        orientation: "portrait" or "landscape".
        margin_mm: Margin in millimetres.

    Returns:
        List of page-sized PIL Images (RGB).
    """
    if not images:
        raise ValueError("No images provided")

    if orientation == "portrait":
        page_w, page_h = A4_PORTRAIT
    else:
        page_w, page_h = A4_LANDSCAPE

    margin_px = mm_to_px(margin_mm)

    pages = []
    if layout == "1_per_page":
        for im in images:
            pages.append(_fit_to_page(im, page_w, page_h, margin_px))
    elif layout == "2_per_page_grid":
        for i in range(0, len(images), 2):
            left = images[i]
            right = images[i + 1] if i + 1 < len(images) else None
            pages.append(_grid_two(left, right, page_w, page_h, margin_px))
    else:
        raise ValueError(f"Unsupported layout: {layout}")

    return pages


def generate_pdf(image_dicts: List[Dict[str, Any]], settings: Dict[str, Any],
                 output_path: str) -> bytes:
    """
    End-to-end: apply edits, compose pages, write multi-page PDF.

    Args:
        image_dicts: List of {"original": PIL.Image, "edit": {...}}
        settings: Dict with keys:
            - "layout": "1_per_page" | "2_per_page_grid"
            - "orientation": "portrait" | "landscape"
            - "margin_mm": int (default 10)
            - "quality": int 0-100 (default 90)
        output_path: Path to write the PDF file.

    Returns:
        PDF file bytes (for streaming/download).
    """
    if not image_dicts:
        raise ValueError("No images to convert")

    # Apply per-image edits
    edited_images = [
        apply_edits(img_dict["original"], img_dict.get("edit", {}))
        for img_dict in image_dicts
    ]

    # Compose pages
    layout = settings.get("layout", "1_per_page")
    orientation = settings.get("orientation", "portrait")
    margin_mm = int(settings.get("margin_mm", 10))
    pages = compose_pages(edited_images, layout, orientation, margin_mm)

    # Save as multi-page PDF
    quality = int(settings.get("quality", 90))
    pages[0].save(
        output_path,
        "PDF",
        resolution=72,
        save_all=True,
        append_images=pages[1:],
        quality=quality,
    )

    # Return bytes
    with open(output_path, "rb") as f:
        return f.read()