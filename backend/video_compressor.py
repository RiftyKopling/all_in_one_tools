"""
Backend logic untuk kompresi video.
Memakai ffmpeg lewat subprocess (perlu ffmpeg ter-install di sistem,
bukan library python murni -- ini pendekatan paling stabil & cepat).
"""

import subprocess


def compress_video(input_path: str, output_path: str,
                    crf: int = 28, preset: str = "medium") -> None:
    """
    Kompres video pakai H.264 (libx264).

    Args:
        input_path: path video asli
        output_path: path untuk menyimpan hasil kompresi
        crf: Constant Rate Factor, 18-28 umum dipakai.
             Makin besar = file makin kecil, kualitas makin turun.
        preset: kecepatan encoding vs efisiensi kompresi
                (ultrafast, fast, medium, slow, ...)
    """
    command = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-acodec", "aac",
        "-b:a", "128k",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal: {result.stderr}")
