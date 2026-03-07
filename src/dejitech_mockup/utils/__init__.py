"""
Utility functions for media analysis, color parsing, and calculations.
"""

from __future__ import annotations

import json
import subprocess
import re
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

try:
    import ffmpeg
except ImportError:
    ffmpeg = None  # type: ignore


@dataclass
class MediaInfo:
    """Container for media file information."""
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool
    codec: str
    bitrate: Optional[int] = None
    audio_codec: Optional[str] = None
    audio_bitrate: Optional[int] = None


def get_media_info(file_path: Path) -> MediaInfo:
    """
    Use ffprobe to get comprehensive media information.
    Returns MediaInfo dataclass with all relevant details.
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python not installed. Run: pip install ffmpeg-python")
    
    try:
        probe = ffmpeg.probe(str(file_path))
        
        video_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "video"),
            None
        )
        audio_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "audio"),
            None
        )
        
        if video_stream is None:
            raise ValueError(f"No video stream found in {file_path}")
        
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        
        # Duration
        duration = float(probe.get("format", {}).get("duration", 0))
        if duration == 0 and "duration" in video_stream:
            duration = float(video_stream["duration"])
        
        # FPS
        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)
        
        # Bitrate
        bitrate = int(probe.get("format", {}).get("bit_rate", 0)) or None
        
        # Audio info
        has_audio = audio_stream is not None
        audio_codec = audio_stream.get("codec_name") if audio_stream else None
        audio_bitrate = int(audio_stream.get("bit_rate", 0)) if audio_stream and audio_stream.get("bit_rate") else None
        
        return MediaInfo(
            width=width,
            height=height,
            duration=duration,
            fps=fps,
            has_audio=has_audio,
            codec=video_stream.get("codec_name", "unknown"),
            bitrate=bitrate,
            audio_codec=audio_codec,
            audio_bitrate=audio_bitrate,
        )
        
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFprobe error: {e.stderr.decode() if e.stderr else str(e)}")


def get_media_dimensions(file_path: Path) -> tuple[int, int]:
    """Get width and height of a video or image."""
    info = get_media_info(file_path)
    return info.width, info.height


def get_video_duration(file_path: Path) -> float:
    """Get duration of a video in seconds."""
    info = get_media_info(file_path)
    return info.duration


def is_vertical(width: int, height: int) -> bool:
    """Check if dimensions represent a vertical (portrait) video."""
    return height > width


def make_even(n: int) -> int:
    """Ensure a number is divisible by 2."""
    return n if n % 2 == 0 else n - 1


def parse_hex_color(color: str) -> str:
    """
    Parse hex color to FFmpeg format.
    Accepts: #RRGGBB, RRGGBB, 0xRRGGBB, rgb(r,g,b)
    Returns: 0xRRGGBB format for FFmpeg
    """
    color = color.strip()
    
    # Handle rgb() format
    rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color, re.IGNORECASE)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return f"0x{r:02x}{g:02x}{b:02x}"
    
    if color.startswith("#"):
        color = color[1:]
    elif color.startswith("0x"):
        return color
    
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    
    if len(color) != 6:
        raise ValueError(f"Invalid hex color: {color}. Use format: #RRGGBB or RRGGBB")
    
    try:
        int(color, 16)
    except ValueError:
        raise ValueError(f"Invalid hex color: {color}")
    
    return f"0x{color}"


def parse_gradient(gradient_str: str) -> tuple[str, str]:
    """
    Parse gradient string format.
    Accepts: "#color1:#color2" or "color1:color2"
    Returns: tuple of (color1, color2) in FFmpeg format
    """
    parts = gradient_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid gradient format: {gradient_str}. Use: #color1:#color2")
    
    return parse_hex_color(parts[0]), parse_hex_color(parts[1])


def calculate_scaling(
    video_w: int,
    video_h: int,
    frame_w: int,
    frame_h: int,
    fill_percent: float = 0.90,
) -> tuple[int, int, int, int]:
    """
    Calculate scaled video dimensions and position for centering.
    Returns: (scaled_width, scaled_height, x_offset, y_offset)
    """
    video_ar = video_w / video_h
    
    if is_vertical(video_w, video_h):
        target_h = int(frame_h * fill_percent)
        target_w = int(target_h * video_ar)
        
        if target_w > frame_w * fill_percent:
            target_w = int(frame_w * fill_percent)
            target_h = int(target_w / video_ar)
    else:
        target_w = int(frame_w * fill_percent)
        target_h = int(target_w / video_ar)
        
        if target_h > frame_h * fill_percent:
            target_h = int(frame_h * fill_percent)
            target_w = int(target_h * video_ar)
    
    target_w = make_even(target_w)
    target_h = make_even(target_h)
    
    x_offset = (frame_w - target_w) // 2
    y_offset = (frame_h - target_h) // 2
    
    return target_w, target_h, x_offset, y_offset


def parse_timestamp(ts: str) -> float:
    """
    Parse timestamp string to seconds.
    Accepts: "10", "1:30", "01:30:00", "90.5"
    """
    ts = ts.strip()
    
    # Pure seconds (with optional decimal)
    if re.match(r'^\d+\.?\d*$', ts):
        return float(ts)
    
    # MM:SS or HH:MM:SS
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    
    raise ValueError(f"Invalid timestamp format: {ts}")


def format_duration(seconds: float) -> str:
    """Format seconds to HH:MM:SS string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
    return f"{minutes:02d}:{secs:05.2f}"


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def check_vaapi_available() -> bool:
    """Check if VA-API hardware acceleration is available."""
    try:
        result = subprocess.run(
            ["vainfo"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_nvenc_available() -> bool:
    """Check if NVIDIA NVENC is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "h264_nvenc" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def estimate_output_size(
    duration: float,
    width: int,
    height: int,
    crf: int,
    fps: float = 30,
) -> int:
    """
    Estimate output file size in bytes.
    This is a rough estimate based on CRF and resolution.
    """
    pixels_per_frame = width * height
    frames = duration * fps
    
    # CRF to quality factor (lower CRF = higher quality = bigger file)
    quality_factor = (51 - crf) / 51
    
    # Base bits per pixel (rough estimate)
    bits_per_pixel = 0.1 * quality_factor + 0.02
    
    total_bits = pixels_per_frame * frames * bits_per_pixel
    return int(total_bits / 8)


def get_font_path(font_name: str) -> Optional[str]:
    """
    Try to find a font file path by name.
    Returns None if not found.
    """
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", font_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None
