"""
Export functionality - formats, platforms, and upload integrations.
"""

from __future__ import annotations

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass

import ffmpeg

from ..constants import (
    ExportFormat,
    Platform,
    Quality,
    QUALITY_CRF_MAP,
    PLATFORM_SETTINGS,
)
from ..utils import (
    make_even,
    check_vaapi_available,
    check_nvenc_available,
    estimate_output_size,
    get_media_info,
    format_size,
)


@dataclass
class ExportConfig:
    """Configuration for video export."""
    format: ExportFormat = ExportFormat.MP4
    platform: Optional[Platform] = None
    quality: Quality = Quality.MEDIUM
    crf: Optional[int] = None
    fps: Optional[float] = None
    resolution: Optional[tuple[int, int]] = None
    max_size_mb: Optional[float] = None
    hw_accel: bool = False
    codec: str = "libx264"
    preset: str = "ultrafast"
    audio_bitrate: str = "192k"
    
    # GIF specific
    gif_fps: int = 15
    gif_width: int = 480
    gif_dither: str = "sierra2_4a"
    
    # Loop
    loop: bool = False
    loop_count: int = 0  # 0 = infinite


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    output_path: Path
    file_size: int
    duration: float
    format: str
    error: Optional[str] = None


def get_encoder(config: ExportConfig) -> tuple[str, dict]:
    """
    Determine the best encoder and its options based on config and availability.
    Returns (encoder_name, encoder_options).
    """
    options = {}
    
    if config.hw_accel:
        # Try VA-API first (AMD)
        if check_vaapi_available():
            return "h264_vaapi", {
                "vaapi_device": "/dev/dri/renderD128",
                "vf": "format=nv12,hwupload",
            }
        # Try NVENC (NVIDIA)
        elif check_nvenc_available():
            return "h264_nvenc", {
                "preset": "p4",
                "rc": "vbr",
            }
    
    # Fallback to software encoding
    crf = config.crf if config.crf is not None else QUALITY_CRF_MAP[config.quality]
    
    return "libx264", {
        "preset": config.preset,
        "crf": crf,
        "pix_fmt": "yuv420p",
        "movflags": "+faststart",
    }


def apply_platform_settings(config: ExportConfig) -> ExportConfig:
    """Apply platform-specific settings to the export config."""
    if config.platform is None:
        return config
    
    settings = PLATFORM_SETTINGS.get(config.platform, {})
    
    if "resolution" in settings and config.resolution is None:
        config.resolution = settings["resolution"]
    
    if "fps" in settings and config.fps is None:
        config.fps = settings["fps"]
    
    if "max_size_mb" in settings and config.max_size_mb is None:
        config.max_size_mb = settings["max_size_mb"]
    
    if "audio_bitrate" in settings:
        config.audio_bitrate = settings["audio_bitrate"]
    
    return config


def export_video(
    stream: Any,
    audio_stream: Optional[Any],
    output_path: Path,
    config: ExportConfig,
    duration: float,
) -> ExportResult:
    """
    Export the composed video with the given configuration.
    """
    config = apply_platform_settings(config)
    
    try:
        if config.format == ExportFormat.GIF:
            return _export_gif(stream, output_path, config, duration)
        elif config.format == ExportFormat.WEBM:
            return _export_webm(stream, audio_stream, output_path, config)
        else:
            return _export_mp4(stream, audio_stream, output_path, config)
    except ffmpeg.Error as e:
        return ExportResult(
            success=False,
            output_path=output_path,
            file_size=0,
            duration=0,
            format=config.format.value,
            error=e.stderr.decode() if e.stderr else str(e),
        )


def _export_mp4(
    stream: Any,
    audio_stream: Optional[Any],
    output_path: Path,
    config: ExportConfig,
) -> ExportResult:
    """Export as MP4."""
    encoder, encoder_opts = get_encoder(config)
    
    output_args = {
        "vcodec": encoder,
        "acodec": "aac",
        "audio_bitrate": config.audio_bitrate,
        **encoder_opts,
    }
    
    if config.fps:
        stream = stream.filter("fps", fps=config.fps)
    
    if audio_stream is not None:
        output = ffmpeg.output(stream, audio_stream, str(output_path), **output_args, shortest=None)
    else:
        output = ffmpeg.output(stream, str(output_path), **output_args, an=None)
    
    output.overwrite_output().run(quiet=True)
    
    # Get result info
    file_size = output_path.stat().st_size
    info = get_media_info(output_path)
    
    return ExportResult(
        success=True,
        output_path=output_path,
        file_size=file_size,
        duration=info.duration,
        format="mp4",
    )


def _export_webm(
    stream: Any,
    audio_stream: Optional[Any],
    output_path: Path,
    config: ExportConfig,
) -> ExportResult:
    """Export as WebM (VP9)."""
    crf = config.crf if config.crf is not None else QUALITY_CRF_MAP[config.quality]
    
    output_args = {
        "vcodec": "libvpx-vp9",
        "crf": crf,
        "b:v": "0",
        "acodec": "libopus",
        "audio_bitrate": config.audio_bitrate,
    }
    
    if config.fps:
        stream = stream.filter("fps", fps=config.fps)
    
    if audio_stream is not None:
        output = ffmpeg.output(stream, audio_stream, str(output_path), **output_args, shortest=None)
    else:
        output = ffmpeg.output(stream, str(output_path), **output_args, an=None)
    
    output.overwrite_output().run(quiet=True)
    
    file_size = output_path.stat().st_size
    info = get_media_info(output_path)
    
    return ExportResult(
        success=True,
        output_path=output_path,
        file_size=file_size,
        duration=info.duration,
        format="webm",
    )


def _export_gif(
    stream: Any,
    output_path: Path,
    config: ExportConfig,
    duration: float,
) -> ExportResult:
    """Export as animated GIF with optimized palette."""
    # Scale down for GIF
    stream = stream.filter("fps", fps=config.gif_fps)
    stream = stream.filter("scale", w=config.gif_width, h=-1, flags="lanczos")
    
    # Generate palette
    palette_path = output_path.parent / f".{output_path.stem}_palette.png"
    
    # Two-pass GIF encoding for quality
    palette_stream = stream.filter("palettegen", stats_mode="diff")
    ffmpeg.output(palette_stream, str(palette_path)).overwrite_output().run(quiet=True)
    
    # Apply palette
    palette_input = ffmpeg.input(str(palette_path))
    gif_stream = ffmpeg.filter([stream, palette_input], "paletteuse", dither=config.gif_dither)
    
    output_args = {}
    if config.loop:
        output_args["loop"] = config.loop_count
    
    ffmpeg.output(gif_stream, str(output_path), **output_args).overwrite_output().run(quiet=True)
    
    # Cleanup palette
    palette_path.unlink(missing_ok=True)
    
    file_size = output_path.stat().st_size
    
    return ExportResult(
        success=True,
        output_path=output_path,
        file_size=file_size,
        duration=duration,
        format="gif",
    )


def export_thumbnail(
    video_path: Path,
    output_path: Path,
    timestamp: float = 0,
    width: int = 1280,
) -> Path:
    """Extract a thumbnail frame from a video."""
    stream = ffmpeg.input(str(video_path), ss=timestamp)
    stream = stream.filter("scale", w=width, h=-1)
    
    ffmpeg.output(
        stream,
        str(output_path),
        vframes=1,
    ).overwrite_output().run(quiet=True)
    
    return output_path


def export_sprites(
    video_path: Path,
    output_dir: Path,
    count: int = 10,
) -> list[Path]:
    """Generate sprite thumbnails throughout the video."""
    info = get_media_info(video_path)
    interval = info.duration / count
    
    output_dir.mkdir(parents=True, exist_ok=True)
    sprites = []
    
    for i in range(count):
        timestamp = i * interval
        output_path = output_dir / f"sprite_{i:03d}.jpg"
        export_thumbnail(video_path, output_path, timestamp, width=320)
        sprites.append(output_path)
    
    return sprites


def compress_to_size(
    input_path: Path,
    output_path: Path,
    target_size_mb: float,
    min_crf: int = 18,
    max_crf: int = 40,
) -> ExportResult:
    """
    Compress video to target file size using binary search on CRF.
    """
    info = get_media_info(input_path)
    target_bytes = int(target_size_mb * 1024 * 1024)
    
    best_crf = max_crf
    best_size = 0
    
    for crf in range(min_crf, max_crf + 1, 2):
        temp_output = output_path.parent / f".temp_{output_path.name}"
        
        stream = ffmpeg.input(str(input_path))
        ffmpeg.output(
            stream,
            str(temp_output),
            vcodec="libx264",
            crf=crf,
            preset="medium",
            acodec="aac",
            audio_bitrate="128k",
        ).overwrite_output().run(quiet=True)
        
        size = temp_output.stat().st_size
        
        if size <= target_bytes:
            best_crf = crf
            best_size = size
            shutil.move(temp_output, output_path)
            break
        
        temp_output.unlink(missing_ok=True)
    
    if not output_path.exists():
        # Use max CRF if we couldn't hit target
        stream = ffmpeg.input(str(input_path))
        ffmpeg.output(
            stream,
            str(output_path),
            vcodec="libx264",
            crf=max_crf,
            preset="medium",
            acodec="aac",
            audio_bitrate="96k",
        ).overwrite_output().run(quiet=True)
        best_size = output_path.stat().st_size
    
    return ExportResult(
        success=True,
        output_path=output_path,
        file_size=best_size,
        duration=info.duration,
        format="mp4",
    )


# ============================================================================
# Multi-format Export
# ============================================================================


def export_multi_format(
    stream: Any,
    audio_stream: Optional[Any],
    output_base: Path,
    formats: list[ExportFormat],
    config: ExportConfig,
    duration: float,
) -> dict[str, ExportResult]:
    """Export to multiple formats at once."""
    results = {}
    
    for fmt in formats:
        fmt_config = ExportConfig(
            format=fmt,
            quality=config.quality,
            crf=config.crf,
            fps=config.fps,
            hw_accel=config.hw_accel,
        )
        
        output_path = output_base.parent / f"{output_base.stem}.{fmt.value}"
        result = export_video(stream, audio_stream, output_path, fmt_config, duration)
        results[fmt.value] = result
    
    return results


# ============================================================================
# Upload Integrations (Stubs)
# ============================================================================


def upload_to_s3(
    file_path: Path,
    bucket: str,
    key: str,
    region: str = "us-east-1",
) -> str:
    """Upload to AWS S3. Requires boto3 and AWS credentials."""
    try:
        import boto3
        s3 = boto3.client("s3", region_name=region)
        s3.upload_file(str(file_path), bucket, key)
        return f"s3://{bucket}/{key}"
    except ImportError:
        raise RuntimeError("boto3 not installed. Run: pip install boto3")


def upload_to_cloudinary(
    file_path: Path,
    cloud_name: str,
    api_key: str,
    api_secret: str,
) -> str:
    """Upload to Cloudinary. Requires cloudinary package."""
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )
        
        result = cloudinary.uploader.upload(
            str(file_path),
            resource_type="video",
        )
        return result["secure_url"]
    except ImportError:
        raise RuntimeError("cloudinary not installed. Run: pip install cloudinary")
