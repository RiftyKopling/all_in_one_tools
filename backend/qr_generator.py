"""
Backend: Generate static QR code as PIL Image.
"""
import qrcode
from PIL import Image


def generate_qr(
    data: str,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
) -> Image.Image:
    """
    Generate a static QR code.

    Args:
        data: Text/URL to encode.
        box_size: Pixel size of each QR module (default 10).
        border: Quiet zone in modules (default 4).
        fill_color: Foreground color (default "black").
        back_color: Background color (default "white").

    Returns:
        PIL Image (RGB) of the QR code.
    """
    qr = qrcode.QRCode(
        version=None,  # auto-fit
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img.convert("RGB")