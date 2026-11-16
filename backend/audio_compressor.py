"""
Backend logic untuk kompresi audio.
Memakai ffmpeg lewat subprocess (sama seperti video_compressor).
"""

import subprocess
import os


# Mapping ekstensi input -> codec default
CODEC_MAP = {
    "mp3": "libmp3lame",
    "m4a": "aac",
    "aac": "aac",
    "ogg": "libvorbis",
    "flac": "flac",
    "wav": "pcm_s16le",
    "wma": "libmp3lame",  # wma input -> encode ke mp3
}

# Format lossless (tidak pakai bitrate)
LOSSLESS_EXTS = {"flac", "wav"}

# Preset bitrate yang ditawarkan ke user
BITRATE_PRESETS = ["64k", "96k", "128k", "192k", "256k", "320k"]


def _get_codec_for_output(output_ext: str) -> str:
    """Return codec for target output extension."""
    return CODEC_MAP.get(output_ext.lower(), "libmp3lame")


def _is_lossless(ext: str) -> bool:
    return ext.lower() in LOSSLESS_EXTS


def compress_audio(
    input_path: str,
    output_path: str,
    bitrate: str = "128k",
    convert_to_mp3: bool = False,
) -> str:
    """
    Kompres/konversi audio pakai ffmpeg.

    Args:
        input_path: path file audio asli
        output_path: path untuk menyimpan hasil (ekstensi akan disesuaikan jika convert_to_mp3)
        bitrate: target bitrate untuk format lossy (mis. "128k"). Diabaikan untuk lossless.
        convert_to_mp3: jika True, output dipaksa ke .mp3 dengan codec libmp3lame.

    Returns:
        Path to the actual output file written (may differ from output_path if convert_to_mp3 changed extension).
    """
    input_ext = os.path.splitext(input_path)[1].lstrip(".").lower()

    # Tentukan output extension & codec
    if convert_to_mp3:
        output_ext = "mp3"
        codec = "libmp3lame"
        # Pastikan output_path pakai .mp3
        if not output_path.lower().endswith(".mp3"):
            output_path = os.path.splitext(output_path)[0] + ".mp3"
    else:
        output_ext = os.path.splitext(output_path)[1].lstrip(".").lower()
        if not output_ext:
            output_ext = input_ext
        codec = _get_codec_for_output(output_ext)

    # Bangun command ffmpeg
    command = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",              # drop video stream (cover art, dll)
        "-map_metadata", "0",  # pertahankan metadata
        "-c:a", codec,
    ]

    # Bitrate hanya untuk format lossy
    if not _is_lossless(output_ext):
        command.extend(["-b:a", bitrate])
    else:
        # Lossless: gunakan compression level (FLAC) atau biarkan default (WAV)
        if output_ext == "flac":
            command.extend(["-compression_level", "8"])  # max compression

    command.append(output_path)

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal: {result.stderr}")

    return output_path