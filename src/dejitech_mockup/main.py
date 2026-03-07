"""
DejiTech Mockup - Complete CLI Application.

A high-performance CLI tool for overlaying screen recordings onto device mockup
frames with professional defaults, visual effects, and intelligent auto-scaling.
"""

from __future__ import annotations

import json
import os
import sys
import time
import shutil
import hashlib
from pathlib import Path
from typing import Annotated, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    ffmpeg = None  # type: ignore
    FFMPEG_AVAILABLE = False

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.tree import Tree

from .constants import (
    __version__,
    Quality,
    Resolution,
    Platform,
    ExportFormat,
    IntroAnimation,
    OutroAnimation,
    LogoPosition,
    GradientDirection,
    QUALITY_CRF_MAP,
    RESOLUTION_MAP,
    PLATFORM_SETTINGS,
    DEFAULT_DEVICE,
    DEFAULT_BG_COLOR,
    DEFAULT_FILL_PERCENT,
    CONFIG_DIR,
    DATA_DIR,
    CACHE_DIR,
    HISTORY_FILE,
)
from .utils import (
    get_media_info,
    get_media_dimensions,
    get_video_duration,
    is_vertical,
    make_even,
    parse_hex_color,
    parse_gradient,
    parse_timestamp,
    calculate_scaling,
    check_vaapi_available,
    format_duration,
    format_size,
    MediaInfo,
)
from .devices import (
    discover_devices,
    get_device,
    get_assets_dirs,
    ensure_assets_dir,
    DeviceInfo,
)
from .effects import (
    EffectConfig,
    create_background,
    apply_shadow,
    apply_reflection,
    apply_corner_radius,
    apply_border,
    apply_intro_animation,
    apply_outro_animation,
    apply_progress_bar,
    apply_text_overlay,
    apply_watermark,
    apply_logo_overlay,
    apply_cta,
)
from .exporters import (
    ExportConfig,
    ExportResult,
    export_video,
    export_thumbnail,
    export_sprites,
    export_multi_format,
    compress_to_size,
    get_encoder,
)
from .presets import (
    Preset,
    list_presets,
    get_preset,
    save_preset,
    delete_preset,
    BUILTIN_PRESETS,
)


# ============================================================================
# CLI Setup
# ============================================================================

console = Console()

app = typer.Typer(
    name="dejitech-mockup",
    help="[bold cyan]DejiTech Mockup[/] - Professional device mockup video generator",
    rich_markup_mode="rich",
    add_completion=True,
    no_args_is_help=False,
)

# Sub-command groups
devices_app = typer.Typer(help="Device management commands")
preset_app = typer.Typer(help="Preset management commands")
store_app = typer.Typer(help="Device store commands")

app.add_typer(devices_app, name="devices")
app.add_typer(preset_app, name="preset")
app.add_typer(store_app, name="store")


# ============================================================================
# History Management
# ============================================================================


def ensure_dirs():
    """Ensure all required directories exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def add_to_history(entry: dict):
    """Add a render to history."""
    ensure_dirs()
    
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
    
    entry["timestamp"] = datetime.now().isoformat()
    history.insert(0, entry)
    
    # Keep last 100 entries
    history = history[:100]
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_history(limit: int = 10) -> list:
    """Get recent history entries."""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
            return history[:limit]
    except json.JSONDecodeError:
        return []


# ============================================================================
# Main Render Command
# ============================================================================


@app.command()
def render(
    video: Annotated[Path, typer.Argument(help="Input video file", exists=True)],
    # Device options
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Device frame to use")] = None,
    fill: Annotated[float, typer.Option("--fill", "-f", help="Fill percentage (0.5-1.0)", min=0.5, max=1.0)] = DEFAULT_FILL_PERCENT,
    # Output options
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output file path")] = None,
    format: Annotated[ExportFormat, typer.Option("--format", help="Output format")] = ExportFormat.MP4,
    # Background options
    bg_color: Annotated[str, typer.Option("--bg-color", "-bg", help="Background color (hex)")] = DEFAULT_BG_COLOR,
    bg_image: Annotated[Optional[Path], typer.Option("--bg-image", help="Background image")] = None,
    bg_video: Annotated[Optional[Path], typer.Option("--bg-video", help="Background video")] = None,
    bg_gradient: Annotated[Optional[str], typer.Option("--bg-gradient", help="Background gradient (#color1:#color2)")] = None,
    gradient_direction: Annotated[GradientDirection, typer.Option("--gradient-dir", help="Gradient direction")] = GradientDirection.VERTICAL,
    bg_blur: Annotated[bool, typer.Option("--bg-blur", help="Use blurred video as background")] = False,
    bg_blur_strength: Annotated[int, typer.Option("--blur-strength", help="Blur strength (1-50)", min=1, max=50)] = 20,
    # Video processing
    start: Annotated[Optional[str], typer.Option("--start", "-ss", help="Start timestamp (e.g., 00:05 or 5)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", "-to", help="End timestamp")] = None,
    duration: Annotated[Optional[str], typer.Option("--duration", "-t", help="Duration (e.g., 10 or 00:10)")] = None,
    speed: Annotated[float, typer.Option("--speed", help="Playback speed multiplier", min=0.25, max=4.0)] = 1.0,
    reverse: Annotated[bool, typer.Option("--reverse", help="Reverse playback")] = False,
    fps: Annotated[Optional[int], typer.Option("--fps", help="Output frame rate")] = None,
    resolution: Annotated[Optional[Resolution], typer.Option("--resolution", "-r", help="Output resolution preset")] = None,
    loop: Annotated[bool, typer.Option("--loop", help="Create looping video")] = False,
    loop_count: Annotated[int, typer.Option("--loop-count", help="Number of loops (0=infinite)")] = 0,
    # Effects
    shadow: Annotated[bool, typer.Option("--shadow", help="Add drop shadow")] = False,
    shadow_opacity: Annotated[float, typer.Option("--shadow-opacity", help="Shadow opacity", min=0.0, max=1.0)] = 0.5,
    shadow_blur: Annotated[int, typer.Option("--shadow-blur", help="Shadow blur radius")] = 20,
    shadow_offset: Annotated[int, typer.Option("--shadow-offset", help="Shadow offset")] = 10,
    glow: Annotated[bool, typer.Option("--glow", help="Add glow effect")] = False,
    glow_color: Annotated[str, typer.Option("--glow-color", help="Glow color")] = "0xffffff",
    glow_strength: Annotated[int, typer.Option("--glow-strength", help="Glow strength")] = 10,
    reflection: Annotated[bool, typer.Option("--reflection", help="Add reflection effect")] = False,
    reflection_opacity: Annotated[float, typer.Option("--reflection-opacity", help="Reflection opacity")] = 0.3,
    corner_radius: Annotated[int, typer.Option("--corner-radius", help="Video corner radius")] = 0,
    border: Annotated[Optional[str], typer.Option("--border", help="Border (e.g., '2px #fff')")] = None,
    rotation: Annotated[float, typer.Option("--rotate", help="Rotation angle in degrees")] = 0.0,
    perspective: Annotated[bool, typer.Option("--perspective", help="Add 3D perspective")] = False,
    # Animation
    intro: Annotated[IntroAnimation, typer.Option("--intro", help="Intro animation")] = IntroAnimation.NONE,
    intro_duration: Annotated[float, typer.Option("--intro-duration", help="Intro duration (seconds)")] = 0.5,
    outro: Annotated[OutroAnimation, typer.Option("--outro", help="Outro animation")] = OutroAnimation.NONE,
    outro_duration: Annotated[float, typer.Option("--outro-duration", help="Outro duration (seconds)")] = 0.5,
    device_float: Annotated[bool, typer.Option("--float", help="Floating animation")] = False,
    # Branding
    logo: Annotated[Optional[Path], typer.Option("--logo", help="Logo image to overlay")] = None,
    logo_position: Annotated[LogoPosition, typer.Option("--logo-position", help="Logo position")] = LogoPosition.BOTTOM_RIGHT,
    logo_scale: Annotated[float, typer.Option("--logo-scale", help="Logo scale (0.05-0.5)")] = 0.1,
    logo_opacity: Annotated[float, typer.Option("--logo-opacity", help="Logo opacity")] = 1.0,
    watermark: Annotated[Optional[str], typer.Option("--watermark", help="Watermark text")] = None,
    watermark_position: Annotated[LogoPosition, typer.Option("--watermark-position", help="Watermark position")] = LogoPosition.BOTTOM_RIGHT,
    watermark_opacity: Annotated[float, typer.Option("--watermark-opacity", help="Watermark opacity")] = 0.5,
    text: Annotated[Optional[str], typer.Option("--text", help="Text overlay")] = None,
    text_position: Annotated[LogoPosition, typer.Option("--text-position", help="Text position")] = LogoPosition.TOP_CENTER,
    text_size: Annotated[int, typer.Option("--text-size", help="Text size")] = 48,
    text_color: Annotated[str, typer.Option("--text-color", help="Text color")] = "0xffffff",
    cta: Annotated[Optional[str], typer.Option("--cta", help="Call-to-action text")] = None,
    cta_style: Annotated[str, typer.Option("--cta-style", help="CTA style (pill/box)")] = "pill",
    progress_bar: Annotated[bool, typer.Option("--progress-bar", help="Show progress bar")] = False,
    progress_color: Annotated[str, typer.Option("--progress-color", help="Progress bar color")] = "0x3b82f6",
    endcard: Annotated[float, typer.Option("--endcard", help="End card duration (seconds)")] = 0.0,
    # Audio
    music: Annotated[Optional[Path], typer.Option("--music", help="Background music file")] = None,
    music_volume: Annotated[float, typer.Option("--music-volume", help="Music volume (0.0-1.0)")] = 0.3,
    mute: Annotated[bool, typer.Option("--mute", help="Mute original audio")] = False,
    voiceover: Annotated[Optional[Path], typer.Option("--voiceover", help="Voiceover audio")] = None,
    # Quality & Export
    quality: Annotated[Quality, typer.Option("--quality", "-q", help="Quality preset")] = Quality.MEDIUM,
    crf: Annotated[Optional[int], typer.Option("--crf", help="Custom CRF value", min=0, max=51)] = None,
    platform: Annotated[Optional[Platform], typer.Option("--platform", "-p", help="Target platform")] = None,
    max_size: Annotated[Optional[float], typer.Option("--max-size", help="Max file size in MB")] = None,
    hw: Annotated[bool, typer.Option("--hw", help="Use hardware acceleration")] = False,
    # Presets
    preset_name: Annotated[Optional[str], typer.Option("--preset", help="Use a saved preset")] = None,
    save_as_preset: Annotated[Optional[str], typer.Option("--save-preset", help="Save settings as preset")] = None,
    # Developer
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show FFmpeg command without executing")] = False,
    preview: Annotated[bool, typer.Option("--preview", help="Render only first 5 seconds")] = False,
    debug: Annotated[bool, typer.Option("--debug", help="Show debug overlay")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show FFmpeg output")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output result as JSON")] = False,
    thumbnail: Annotated[bool, typer.Option("--thumbnail", help="Also export thumbnail")] = False,
):
    """
    [bold green]Render[/] a screen recording onto a device mockup frame.
    
    [dim]Examples:[/]
        dejitech-mockup render recording.mp4
        dejitech-mockup render recording.mp4 --device iphone15 --shadow --hw
        dejitech-mockup render recording.mp4 --bg-gradient "#000:#333" --intro fade
        dejitech-mockup render recording.mp4 --preset tiktok
    """
    # Check ffmpeg-python is available
    if not FFMPEG_AVAILABLE:
        console.print(Panel(
            "[red]ffmpeg-python module is not installed![/]\n\n"
            "Install it with:\n"
            "  [cyan]pip install ffmpeg-python[/]\n\n"
            "Also ensure FFmpeg is installed on your system:\n"
            "  [cyan]sudo pacman -S ffmpeg[/]  (Arch Linux)",
            title="Missing Dependency",
        ))
        raise typer.Exit(1)
    
    ensure_dirs()
    start_time = time.time()
    
    # Load preset if specified
    if preset_name:
        loaded_preset = get_preset(preset_name)
        if not loaded_preset:
            console.print(f"[red]Preset '{preset_name}' not found.[/]")
            raise typer.Exit(1)
        # Apply preset values (CLI args override preset)
        if device is None:
            device = loaded_preset.device
        if bg_color == DEFAULT_BG_COLOR:
            bg_color = loaded_preset.bg_color
        if loaded_preset.shadow and not shadow:
            shadow = True
        if loaded_preset.intro != "none" and intro == IntroAnimation.NONE:
            intro = IntroAnimation(loaded_preset.intro)
        # ... apply other preset values as needed
    
    # Discover available devices
    all_devices = discover_devices()
    device_name = (device or DEFAULT_DEVICE).lower()
    
    if device_name not in all_devices:
        if not all_devices:
            console.print(Panel(
                f"[red]No device frames found![/]\n\n"
                f"Add device frame images to one of these locations:\n"
                + "\n".join(f"  - [cyan]{d}[/]" for d in get_assets_dirs()),
                title="Missing Assets",
            ))
            raise typer.Exit(1)
        
        available = ", ".join(sorted(all_devices.keys()))
        console.print(f"[red]Device '{device_name}' not found.[/] Available: {available}")
        raise typer.Exit(1)
    
    device_info = all_devices[device_name]
    frame_path = device_info.path
    
    # Parse colors
    try:
        bg_hex = parse_hex_color(bg_color)
    except ValueError as e:
        console.print(f"[red]Invalid color:[/] {e}")
        raise typer.Exit(1)
    
    # Get media info
    console.print("[dim]Analyzing media...[/]")
    video_info = get_media_info(video)
    frame_w, frame_h = device_info.width, device_info.height
    
    # Calculate video duration with trimming
    video_duration = video_info.duration
    start_seconds = parse_timestamp(start) if start else 0
    
    if end:
        end_seconds = parse_timestamp(end)
        video_duration = end_seconds - start_seconds
    elif duration:
        video_duration = parse_timestamp(duration)
    else:
        video_duration = video_duration - start_seconds
    
    if preview:
        video_duration = min(video_duration, 5.0)
    
    # Apply speed change to duration
    video_duration = video_duration / speed
    
    # Calculate scaling
    scaled_w, scaled_h, x_off, y_off = calculate_scaling(
        video_info.width, video_info.height,
        frame_w, frame_h, fill
    )
    
    # Ensure even dimensions
    frame_w = make_even(frame_w)
    frame_h = make_even(frame_h)
    
    # Determine CRF
    crf_value = crf if crf is not None else QUALITY_CRF_MAP[quality]
    
    # Check hardware acceleration
    use_hw = hw
    if use_hw and not check_vaapi_available():
        console.print("[yellow]Warning:[/] VA-API not available, falling back to software encoding")
        use_hw = False
    
    # Set output path
    if output is None:
        suffix = f".{format.value}"
        output = video.parent / f"{video.stem}_mockup{suffix}"
    
    # Build effect configuration
    effect_config = EffectConfig(
        bg_color=bg_hex,
        bg_image=str(bg_image) if bg_image else None,
        bg_video=str(bg_video) if bg_video else None,
        bg_gradient=bg_gradient,
        gradient_direction=gradient_direction,
        bg_blur=bg_blur,
        bg_blur_strength=bg_blur_strength,
        shadow=shadow,
        shadow_opacity=shadow_opacity,
        shadow_blur=shadow_blur,
        shadow_offset_x=shadow_offset,
        shadow_offset_y=shadow_offset,
        glow=glow,
        glow_color=glow_color,
        glow_strength=glow_strength,
        reflection=reflection,
        reflection_opacity=reflection_opacity,
        corner_radius=corner_radius,
        rotation=rotation,
        perspective=perspective,
        intro=intro,
        intro_duration=intro_duration,
        outro=outro,
        outro_duration=outro_duration,
        device_float=device_float,
        logo_path=str(logo) if logo else None,
        logo_position=logo_position,
        logo_scale=logo_scale,
        logo_opacity=logo_opacity,
        watermark_text=watermark,
        watermark_position=watermark_position,
        watermark_opacity=watermark_opacity,
        text_overlay=text,
        text_position=text_position,
        text_size=text_size,
        text_color=text_color,
        cta_text=cta,
        cta_style=cta_style,
        progress_bar=progress_bar,
        progress_bar_color=progress_color,
        endcard_duration=endcard,
    )
    
    # Parse border if specified
    if border:
        parts = border.split()
        if len(parts) >= 1:
            border_w = int(parts[0].replace("px", ""))
            effect_config.border_width = border_w
        if len(parts) >= 2:
            effect_config.border_color = parse_hex_color(parts[1])
    
    # Display configuration
    if not json_output:
        table = Table(title="Render Configuration", show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        table.add_row("Input", str(video))
        table.add_row("Device", f"{device_name} ({frame_path.name})")
        table.add_row("Video Size", f"{video_info.width}x{video_info.height}")
        table.add_row("Frame Size", f"{frame_w}x{frame_h}")
        table.add_row("Scaled To", f"{scaled_w}x{scaled_h} @ ({x_off}, {y_off})")
        table.add_row("Duration", format_duration(video_duration))
        table.add_row("Quality", f"CRF {crf_value}")
        table.add_row("Encoder", "h264_vaapi (HW)" if use_hw else "libx264 (SW)")
        if shadow:
            table.add_row("Effects", "Shadow")
        if intro != IntroAnimation.NONE:
            table.add_row("Intro", intro.value)
        table.add_row("Output", str(output))
        console.print(table)
        console.print()
    
    # Build FFmpeg filter graph
    input_args = {}
    if start:
        input_args["ss"] = start_seconds
    if preview:
        input_args["t"] = 5
    elif duration:
        input_args["t"] = parse_timestamp(duration)
    elif end:
        input_args["t"] = video_duration * speed  # Compensate for speed
    
    video_input = ffmpeg.input(str(video), **input_args)
    frame_input = ffmpeg.input(str(frame_path))
    
    # Video stream with processing
    vid_stream = video_input.video
    
    # Apply speed change
    if speed != 1.0:
        vid_stream = vid_stream.filter("setpts", f"{1/speed}*PTS")
    
    # Apply reverse
    if reverse:
        vid_stream = vid_stream.filter("reverse")
    
    # Scale video
    vid_stream = vid_stream.filter(
        "scale",
        w=scaled_w,
        h=scaled_h,
        force_original_aspect_ratio="decrease",
    ).filter(
        "scale",
        w="trunc(iw/2)*2",
        h="trunc(ih/2)*2",
    )
    
    # Apply corner radius (simplified)
    if corner_radius > 0:
        vid_stream = vid_stream.filter("format", pix_fmts="yuva420p")
    
    # Apply border
    if effect_config.border_width > 0:
        vid_stream = vid_stream.filter(
            "pad",
            w=f"iw+{effect_config.border_width*2}",
            h=f"ih+{effect_config.border_width*2}",
            x=effect_config.border_width,
            y=effect_config.border_width,
            color=effect_config.border_color,
        )
    
    # Create background
    background = create_background(
        effect_config,
        frame_w,
        frame_h,
        video_duration + 10,
        video_input.video if bg_blur else None,
    )
    
    # Determine how many times we need to use vid_stream
    # If shadow or reflection is enabled, we need to split the stream
    needs_split = shadow or reflection
    
    if needs_split:
        # Count outputs needed: 1 for main + 1 for shadow (if enabled) + 1 for reflection (if enabled)
        num_outputs = 1 + (1 if shadow else 0) + (1 if reflection else 0)
        split_streams = vid_stream.filter_multi_output('split', outputs=num_outputs)
        
        stream_idx = 0
        main_stream = split_streams[stream_idx]
        stream_idx += 1
        
        if shadow:
            shadow_source = split_streams[stream_idx]
            stream_idx += 1
        
        if reflection:
            reflection_source = split_streams[stream_idx]
            stream_idx += 1
    else:
        main_stream = vid_stream
    
    # Apply shadow
    shadow_stream = None
    shadow_x, shadow_y = x_off, y_off
    if shadow:
        # Create shadow layer from split stream
        shadow_stream = shadow_source.filter(
            "colorchannelmixer",
            rr=0, rg=0, rb=0,
            gr=0, gg=0, gb=0,
            br=0, bg=0, bb=0,
        )
        shadow_stream = shadow_stream.filter("boxblur", luma_radius=shadow_blur)
        shadow_x = x_off + shadow_offset
        shadow_y = y_off + shadow_offset
    
    # Compose layers
    if shadow_stream is not None:
        composed = background.overlay(shadow_stream, x=shadow_x, y=shadow_y, shortest=1)
        composed = composed.overlay(main_stream, x=x_off, y=y_off)
    else:
        composed = composed if 'composed' in dir() else background.overlay(main_stream, x=x_off, y=y_off, shortest=1)
        composed = background.overlay(main_stream, x=x_off, y=y_off, shortest=1)
    
    # Add reflection
    if reflection:
        # Create reflection from split stream
        reflect_h = int(frame_h * 0.2)
        reflection_stream = reflection_source.filter("vflip")
        reflection_stream = reflection_stream.filter("crop", w=scaled_w, h=reflect_h, x=0, y=0)
        composed = composed.overlay(
            reflection_stream,
            x=x_off,
            y=y_off + scaled_h + 5,
            shortest=1,
        )
    
    # Overlay device frame
    composed = composed.overlay(frame_input, x=0, y=0)
    
    # Apply intro animation
    if intro != IntroAnimation.NONE:
        composed = apply_intro_animation(composed, effect_config, frame_w, frame_h, video_info.fps)
    
    # Apply outro animation
    if outro != OutroAnimation.NONE:
        composed = apply_outro_animation(composed, effect_config, video_duration, video_info.fps)
    
    # Apply text overlay
    if text:
        composed = apply_text_overlay(composed, effect_config, frame_w, frame_h)
    
    # Apply watermark
    if watermark:
        composed = apply_watermark(composed, effect_config, frame_w, frame_h)
    
    # Apply CTA
    if cta:
        composed = apply_cta(composed, effect_config, frame_w, frame_h)
    
    # Apply progress bar
    if progress_bar:
        composed = apply_progress_bar(composed, effect_config, frame_w, frame_h, video_duration)
    
    # Apply logo
    if logo:
        logo_input = ffmpeg.input(str(logo))
        composed = apply_logo_overlay(composed, logo_input, effect_config, frame_w, frame_h)
    
    # Apply FPS change
    if fps:
        composed = composed.filter("fps", fps=fps)
    
    # Apply resolution preset
    if resolution:
        target_w, target_h = RESOLUTION_MAP[resolution]
        composed = composed.filter("scale", w=target_w, h=target_h, force_original_aspect_ratio="decrease")
        composed = composed.filter("pad", w=target_w, h=target_h, x="(ow-iw)/2", y="(oh-ih)/2", color=bg_hex)
    
    # Debug overlay
    if debug:
        composed = composed.filter(
            "drawtext",
            text=f"Device: {device_name} | {frame_w}x{frame_h} | Video: {scaled_w}x{scaled_h} @ ({x_off},{y_off})",
            fontsize=18,
            fontcolor="white",
            x=10,
            y=10,
            box=1,
            boxcolor="black@0.7",
            boxborderw=5,
        )
    
    # Audio processing
    audio_stream = None
    if not mute and video_info.has_audio:
        audio_stream = video_input.audio
        
        if speed != 1.0:
            audio_stream = audio_stream.filter("atempo", speed)
        
        if reverse:
            audio_stream = audio_stream.filter("areverse")
    
    # Mix with background music
    if music and music.exists():
        music_input = ffmpeg.input(str(music), stream_loop=-1)
        music_audio = music_input.audio.filter("volume", music_volume)
        
        if audio_stream is not None:
            # Mix original and music
            audio_stream = ffmpeg.filter([audio_stream, music_audio], "amix", inputs=2, duration="first")
        else:
            audio_stream = music_audio
    
    # Add voiceover
    if voiceover and voiceover.exists():
        vo_input = ffmpeg.input(str(voiceover))
        if audio_stream is not None:
            audio_stream = ffmpeg.filter([audio_stream, vo_input.audio], "amix", inputs=2, duration="first")
        else:
            audio_stream = vo_input.audio
    
    # Build output
    output_args = {}
    
    if use_hw:
        output_args.update({
            "vcodec": "h264_vaapi",
            "vaapi_device": "/dev/dri/renderD128",
        })
    else:
        output_args.update({
            "vcodec": "libx264",
            "preset": "ultrafast",
            "crf": crf_value,
            "pix_fmt": "yuv420p",
            "movflags": "+faststart",
        })
    
    if audio_stream is not None:
        output_args.update({
            "acodec": "aac",
            "audio_bitrate": "192k",
        })
        final_output = ffmpeg.output(composed, audio_stream, str(output), **output_args, shortest=None)
    else:
        final_output = ffmpeg.output(composed, str(output), **output_args, an=None)
    
    final_output = final_output.overwrite_output()
    
    # Dry run - show command
    if dry_run:
        cmd = final_output.compile()
        console.print(Panel(
            Syntax(" ".join(cmd), "bash", theme="monokai"),
            title="FFmpeg Command",
        ))
        return
    
    # Execute render
    if not json_output:
        console.print("[bold cyan]Rendering...[/]")
    
    try:
        if verbose:
            final_output.run()
        else:
            final_output.run(quiet=True)
        
        # Compress to size if needed
        if max_size and output.exists():
            current_size = output.stat().st_size / (1024 * 1024)
            if current_size > max_size:
                console.print(f"[yellow]Compressing to {max_size}MB...[/]")
                compress_to_size(output, output, max_size)
        
        # Export thumbnail if requested
        thumbnail_path = None
        if thumbnail:
            thumbnail_path = output.parent / f"{output.stem}_thumb.jpg"
            export_thumbnail(output, thumbnail_path, timestamp=video_duration / 2)
        
        # Get final output info
        render_time = time.time() - start_time
        output_size = output.stat().st_size
        output_info = get_media_info(output)
        
        # Add to history
        add_to_history({
            "input": str(video),
            "output": str(output),
            "device": device_name,
            "duration": output_info.duration,
            "size": output_size,
            "render_time": render_time,
        })
        
        # Save preset if requested
        if save_as_preset:
            new_preset = Preset(
                name=save_as_preset,
                description=f"Created from render of {video.name}",
                device=device_name,
                fill=fill,
                bg_color=bg_hex,
                shadow=shadow,
                intro=intro.value,
                outro=outro.value,
                quality=quality.value,
            )
            save_preset(new_preset)
            console.print(f"[green]Preset '{save_as_preset}' saved![/]")
        
        # Output result
        if json_output:
            result = {
                "success": True,
                "output": str(output),
                "size": output_size,
                "size_human": format_size(output_size),
                "duration": output_info.duration,
                "render_time": render_time,
                "thumbnail": str(thumbnail_path) if thumbnail_path else None,
            }
            print(json.dumps(result, indent=2))
        else:
            console.print()
            console.print(Panel(
                f"[bold green]Render complete![/]\n\n"
                f"Output: [cyan]{output}[/]\n"
                f"Size: {format_size(output_size)}\n"
                f"Duration: {format_duration(output_info.duration)}\n"
                f"Render time: {render_time:.1f}s",
                title="Success",
            ))
        
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        
        if json_output:
            result = {"success": False, "error": error_msg}
            print(json.dumps(result, indent=2))
        else:
            console.print(f"\n[bold red]FFmpeg Error:[/]")
            console.print(f"[dim]{error_msg}[/]")
        
        raise typer.Exit(1)


# ============================================================================
# Batch Command
# ============================================================================


@app.command()
def batch(
    input_dir: Annotated[Path, typer.Argument(help="Directory containing videos", exists=True)],
    output_dir: Annotated[Optional[Path], typer.Option("--output-dir", "-o", help="Output directory")] = None,
    device: Annotated[str, typer.Option("--device", "-d", help="Device frame")] = DEFAULT_DEVICE,
    pattern: Annotated[str, typer.Option("--pattern", help="File pattern to match")] = "*.mp4",
    preset_name: Annotated[Optional[str], typer.Option("--preset", help="Use a preset")] = None,
    parallel: Annotated[int, typer.Option("--parallel", "-j", help="Parallel jobs", min=1, max=8)] = 1,
    quality: Annotated[Quality, typer.Option("--quality", "-q")] = Quality.MEDIUM,
    hw: Annotated[bool, typer.Option("--hw")] = False,
):
    """
    [bold blue]Batch process[/] multiple videos in a directory.
    
    [dim]Examples:[/]
        dejitech-mockup batch ./recordings/
        dejitech-mockup batch ./videos/ --parallel 4 --preset tiktok
    """
    if output_dir is None:
        output_dir = input_dir / "mockups"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find videos
    videos = list(input_dir.glob(pattern))
    
    if not videos:
        console.print(f"[yellow]No videos found matching '{pattern}' in {input_dir}[/]")
        return
    
    console.print(f"Found [cyan]{len(videos)}[/] videos to process")
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=len(videos))
        
        def process_video(video_path: Path) -> dict:
            output_path = output_dir / f"{video_path.stem}_mockup.mp4"
            
            try:
                # Run render as subprocess to avoid state issues
                cmd = [
                    sys.executable, "-m", "dejitech_mockup",
                    "render", str(video_path),
                    "--device", device,
                    "--output", str(output_path),
                    "--quality", quality.value,
                    "--json",
                ]
                if hw:
                    cmd.append("--hw")
                if preset_name:
                    cmd.extend(["--preset", preset_name])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    return {"success": True, "input": str(video_path), "output": str(output_path)}
                else:
                    return {"success": False, "input": str(video_path), "error": result.stderr}
            except Exception as e:
                return {"success": False, "input": str(video_path), "error": str(e)}
        
        if parallel > 1:
            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = {executor.submit(process_video, v): v for v in videos}
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    progress.advance(task)
        else:
            for video_path in videos:
                result = process_video(video_path)
                results.append(result)
                progress.advance(task)
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    console.print()
    console.print(Panel(
        f"[bold green]Batch complete![/]\n\n"
        f"Processed: {len(videos)}\n"
        f"Successful: {successful}\n"
        f"Failed: {len(videos) - successful}\n"
        f"Output: {output_dir}",
        title="Summary",
    ))


# ============================================================================
# Watch Command
# ============================================================================


@app.command()
def watch(
    input_dir: Annotated[Path, typer.Argument(help="Directory to watch", exists=True)],
    output_dir: Annotated[Optional[Path], typer.Option("--output-dir", "-o")] = None,
    device: Annotated[str, typer.Option("--device", "-d")] = DEFAULT_DEVICE,
    preset_name: Annotated[Optional[str], typer.Option("--preset")] = None,
):
    """
    [bold magenta]Watch[/] a directory and auto-process new videos.
    
    [dim]Example:[/]
        dejitech-mockup watch ./inbox/ --preset tiktok
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        console.print("[red]watchdog not installed.[/] Run: pip install watchdog")
        raise typer.Exit(1)
    
    if output_dir is None:
        output_dir = input_dir / "processed"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    processed_files = set()
    
    class VideoHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            
            path = Path(event.src_path)
            if path.suffix.lower() not in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                return
            
            if str(path) in processed_files:
                return
            
            processed_files.add(str(path))
            console.print(f"[cyan]New video detected:[/] {path.name}")
            
            # Wait for file to finish writing
            time.sleep(2)
            
            output_path = output_dir / f"{path.stem}_mockup.mp4"
            
            cmd = [
                sys.executable, "-m", "dejitech_mockup",
                "render", str(path),
                "--device", device,
                "--output", str(output_path),
            ]
            if preset_name:
                cmd.extend(["--preset", preset_name])
            
            subprocess.run(cmd)
    
    observer = Observer()
    observer.schedule(VideoHandler(), str(input_dir), recursive=False)
    observer.start()
    
    console.print(Panel(
        f"Watching: [cyan]{input_dir}[/]\n"
        f"Output to: [cyan]{output_dir}[/]\n\n"
        f"Press [bold]Ctrl+C[/] to stop",
        title="Watch Mode",
    ))
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
    console.print("[dim]Watch mode stopped.[/]")


# ============================================================================
# Info Command
# ============================================================================


@app.command()
def info(
    file: Annotated[Path, typer.Argument(help="Video or image file", exists=True)],
):
    """
    [bold yellow]Analyze[/] a video or image file.
    """
    try:
        media_info = get_media_info(file)
        
        orientation = "Vertical" if is_vertical(media_info.width, media_info.height) else "Horizontal"
        aspect = f"{media_info.width/media_info.height:.2f}"
        
        table = Table(title=f"Media Info: {file.name}", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        
        table.add_row("Dimensions", f"{media_info.width} x {media_info.height}")
        table.add_row("Orientation", orientation)
        table.add_row("Aspect Ratio", aspect)
        table.add_row("Duration", format_duration(media_info.duration))
        table.add_row("FPS", f"{media_info.fps:.2f}")
        table.add_row("Codec", media_info.codec)
        table.add_row("Has Audio", "Yes" if media_info.has_audio else "No")
        if media_info.bitrate:
            table.add_row("Bitrate", f"{media_info.bitrate // 1000} kbps")
        table.add_row("File Size", format_size(file.stat().st_size))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error analyzing file:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Devices Commands
# ============================================================================


@devices_app.command("list")
def devices_list():
    """List all available device mockup frames."""
    found_devices = discover_devices()
    
    if not found_devices:
        console.print(Panel(
            "No device frames found.\n\n"
            f"Add PNG/JPG images to: [cyan]{ensure_assets_dir()}[/]",
            title="No Devices",
        ))
        return
    
    table = Table(title="Available Device Frames")
    table.add_column("Device Name", style="cyan")
    table.add_column("File")
    table.add_column("Dimensions")
    table.add_column("Category")
    
    for name, info in sorted(found_devices.items()):
        default = " [green](default)[/]" if name == DEFAULT_DEVICE else ""
        category = info.config.category if info.config else "phone"
        table.add_row(
            f"{name}{default}",
            info.path.name,
            f"{info.width}x{info.height}",
            category,
        )
    
    console.print(table)


@devices_app.command("add")
def devices_add(
    image_path: Annotated[Path, typer.Argument(help="Device frame image", exists=True)],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Device name")] = None,
):
    """Add a new device frame to your collection."""
    assets_dir = ensure_assets_dir()
    device_name = name or image_path.stem.lower()
    
    dest_path = assets_dir / f"{device_name}{image_path.suffix}"
    shutil.copy(image_path, dest_path)
    
    console.print(f"[green]Device '{device_name}' added![/] Use with: --device {device_name}")


# ============================================================================
# Preset Commands
# ============================================================================


@preset_app.command("list")
def preset_list():
    """List all available presets."""
    presets = list_presets()
    
    table = Table(title="Available Presets")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Type")
    
    for name, preset in sorted(presets.items()):
        preset_type = "built-in" if name in BUILTIN_PRESETS else "user"
        table.add_row(name, preset.description, preset_type)
    
    console.print(table)


@preset_app.command("show")
def preset_show(name: Annotated[str, typer.Argument(help="Preset name")]):
    """Show details of a preset."""
    preset = get_preset(name)
    
    if not preset:
        console.print(f"[red]Preset '{name}' not found.[/]")
        raise typer.Exit(1)
    
    table = Table(title=f"Preset: {preset.name}", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    
    table.add_row("Description", preset.description)
    table.add_row("Device", preset.device)
    table.add_row("Fill", str(preset.fill))
    table.add_row("Background", preset.bg_color)
    table.add_row("Shadow", "Yes" if preset.shadow else "No")
    table.add_row("Intro", preset.intro)
    table.add_row("Quality", preset.quality)
    
    console.print(table)


@preset_app.command("delete")
def preset_delete(name: Annotated[str, typer.Argument(help="Preset name")]):
    """Delete a user preset."""
    try:
        if delete_preset(name):
            console.print(f"[green]Preset '{name}' deleted.[/]")
        else:
            console.print(f"[yellow]Preset '{name}' not found.[/]")
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)


# ============================================================================
# History Command
# ============================================================================


@app.command()
def history(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of entries")] = 10,
    clear: Annotated[bool, typer.Option("--clear", help="Clear history")] = False,
):
    """Show or clear render history."""
    if clear:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        console.print("[green]History cleared.[/]")
        return
    
    entries = get_history(limit)
    
    if not entries:
        console.print("[dim]No history yet.[/]")
        return
    
    table = Table(title="Recent Renders")
    table.add_column("Time", style="dim")
    table.add_column("Input")
    table.add_column("Device", style="cyan")
    table.add_column("Size")
    table.add_column("Render Time")
    
    for entry in entries:
        ts = datetime.fromisoformat(entry["timestamp"])
        table.add_row(
            ts.strftime("%Y-%m-%d %H:%M"),
            Path(entry["input"]).name,
            entry.get("device", "?"),
            format_size(entry.get("size", 0)),
            f"{entry.get('render_time', 0):.1f}s",
        )
    
    console.print(table)


# ============================================================================
# Interactive Mode (Beautiful TUI)
# ============================================================================

LOGO = """
[bold cyan]
    ██████╗ ███████╗     ██╗██╗████████╗███████╗ ██████╗██╗  ██╗
    ██╔══██╗██╔════╝     ██║██║╚══██╔══╝██╔════╝██╔════╝██║  ██║
    ██║  ██║█████╗       ██║██║   ██║   █████╗  ██║     ███████║
    ██║  ██║██╔══╝  ██   ██║██║   ██║   ██╔══╝  ██║     ██╔══██║
    ██████╔╝███████╗╚█████╔╝██║   ██║   ███████╗╚██████╗██║  ██║
    ╚═════╝ ╚══════╝ ╚════╝ ╚═╝   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝
                    [bold white]M O C K U P[/bold white]
[/bold cyan]
"""

LOGO_SMALL = """[bold cyan]
  ╭─────────────────────────────────────╮
  │     [bold white]DejiTech Mockup[/bold white] [dim]v{version}[/dim]     │
  │   [dim]Professional Device Mockups[/dim]    │
  ╰─────────────────────────────────────╯
[/bold cyan]"""


def show_banner():
    """Display the application banner."""
    import shutil
    term_width = shutil.get_terminal_size().columns
    
    if term_width >= 70:
        console.print(LOGO)
    else:
        console.print(LOGO_SMALL.format(version=__version__))
    
    console.print(f"  [dim]v{__version__} • Type 'q' to quit • 'h' for help[/dim]\n")


def interactive_menu():
    """Show the main interactive menu."""
    from rich.columns import Columns
    
    menu_items = [
        ("1", "Create Mockup", "Render a video onto a device frame"),
        ("2", "Batch Process", "Process multiple videos at once"),
        ("3", "List Devices", "View available device frames"),
        ("4", "Presets", "View and manage presets"),
        ("5", "History", "View recent renders"),
        ("6", "Settings", "Configure defaults"),
        ("q", "Quit", "Exit the application"),
    ]
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=4)
    table.add_column("Action", style="bold white", width=16)
    table.add_column("Description", style="dim")
    
    for key, action, desc in menu_items:
        table.add_row(f"[{key}]", action, desc)
    
    console.print(Panel(table, title="[bold]What would you like to do?[/bold]", border_style="cyan"))


def select_video() -> Optional[Path]:
    """Prompt user to select a video file."""
    console.print("\n[bold cyan]Step 1:[/bold cyan] Select Video File\n")
    
    while True:
        video_path = Prompt.ask(
            "[cyan]>[/cyan] Paste video path (or drag & drop)",
            default=""
        )
        
        if video_path.lower() in ['q', 'quit', 'exit']:
            return None
        
        if video_path.lower() in ['b', 'back']:
            return None
        
        # Clean path (remove quotes if dragged)
        video_path = video_path.strip().strip('"').strip("'")
        
        if not video_path:
            console.print("[yellow]Please enter a video path[/yellow]")
            continue
        
        video = Path(video_path)
        
        if not video.exists():
            console.print(f"[red]File not found:[/red] {video_path}")
            continue
        
        if video.suffix.lower() not in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']:
            console.print(f"[yellow]Warning:[/yellow] Unusual video format: {video.suffix}")
            if not Confirm.ask("Continue anyway?", default=True):
                continue
        
        # Show video info
        try:
            info = get_media_info(video)
            console.print(f"\n  [green]✓[/green] [bold]{video.name}[/bold]")
            console.print(f"    [dim]{info.width}x{info.height} • {format_duration(info.duration)} • {format_size(video.stat().st_size)}[/dim]\n")
        except Exception:
            console.print(f"\n  [green]✓[/green] [bold]{video.name}[/bold]\n")
        
        return video


def select_device() -> Optional[str]:
    """Prompt user to select a device frame."""
    console.print("[bold cyan]Step 2:[/bold cyan] Select Device Frame\n")
    
    devices = discover_devices()
    
    if not devices:
        console.print(Panel(
            f"[red]No device frames found![/red]\n\n"
            f"Add PNG/JPG device frames to:\n"
            f"[cyan]{ensure_assets_dir()}[/cyan]",
            title="Missing Assets"
        ))
        return None
    
    # Show devices in a nice table
    table = Table(show_header=True, box=None)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Device", style="bold")
    table.add_column("Size", style="dim")
    
    device_list = sorted(devices.items())
    for i, (name, info) in enumerate(device_list, 1):
        table.add_row(str(i), name, f"{info.width}x{info.height}")
    
    console.print(table)
    console.print()
    
    while True:
        choice = Prompt.ask(
            "[cyan]>[/cyan] Enter device name or number",
            default=device_list[0][0] if device_list else ""
        )
        
        if choice.lower() in ['q', 'quit', 'exit', 'b', 'back']:
            return None
        
        # Check if it's a number
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(device_list):
                selected = device_list[idx][0]
                console.print(f"\n  [green]✓[/green] Selected: [bold]{selected}[/bold]\n")
                return selected
            else:
                console.print("[red]Invalid number[/red]")
                continue
        
        # Check if it's a device name
        if choice.lower() in devices:
            console.print(f"\n  [green]✓[/green] Selected: [bold]{choice.lower()}[/bold]\n")
            return choice.lower()
        
        console.print(f"[red]Device not found:[/red] {choice}")


def select_effects() -> dict:
    """Prompt user to select effects."""
    console.print("[bold cyan]Step 3:[/bold cyan] Select Effects\n")
    
    effects = {}
    
    # Shadow
    effects['shadow'] = Confirm.ask("  [cyan]•[/cyan] Add drop shadow?", default=True)
    
    # Reflection
    effects['reflection'] = Confirm.ask("  [cyan]•[/cyan] Add reflection?", default=False)
    
    # Intro animation
    if Confirm.ask("  [cyan]•[/cyan] Add intro animation?", default=False):
        intro_choices = ["fade", "zoom", "slide-up", "slide-down", "bounce"]
        console.print(f"    [dim]Options: {', '.join(intro_choices)}[/dim]")
        intro = Prompt.ask("    Intro type", default="fade")
        if intro in intro_choices:
            effects['intro'] = intro
        else:
            effects['intro'] = "fade"
    else:
        effects['intro'] = "none"
    
    # Background
    if Confirm.ask("  [cyan]•[/cyan] Custom background?", default=False):
        bg_choices = ["gradient", "blur", "color", "image"]
        console.print(f"    [dim]Options: {', '.join(bg_choices)}[/dim]")
        bg_type = Prompt.ask("    Background type", default="gradient")
        effects['bg_type'] = bg_type
        
        if bg_type == "gradient":
            effects['bg_gradient'] = Prompt.ask("    Gradient (e.g., #000:#333)", default="#1a1a2e:#16213e")
        elif bg_type == "color":
            effects['bg_color'] = Prompt.ask("    Color (hex)", default="#000000")
        elif bg_type == "blur":
            effects['bg_blur'] = True
    
    console.print()
    return effects


def select_quality() -> dict:
    """Prompt user to select quality settings."""
    console.print("[bold cyan]Step 4:[/bold cyan] Quality & Export\n")
    
    settings = {}
    
    # Quality preset
    quality_options = [
        ("1", "medium", "Balanced quality and size (CRF 23)"),
        ("2", "high", "High quality (CRF 18)"),
        ("3", "ultra", "Best quality (CRF 12)"),
        ("4", "4k", "4K Ultra HD resolution"),
        ("5", "lossless", "Lossless quality (large file)"),
    ]
    
    table = Table(show_header=False, box=None)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Quality", style="bold", width=12)
    table.add_column("Description", style="dim")
    
    for num, name, desc in quality_options:
        table.add_row(f"[{num}]", name, desc)
    
    console.print(table)
    
    choice = Prompt.ask("\n  [cyan]>[/cyan] Select quality", default="2")
    
    if choice == "1":
        settings['quality'] = Quality.MEDIUM
    elif choice == "2":
        settings['quality'] = Quality.HIGH
    elif choice == "3":
        settings['quality'] = Quality.ULTRA
    elif choice == "4":
        settings['quality'] = Quality.ULTRA
        settings['resolution'] = Resolution.UHD
    elif choice == "5":
        settings['quality'] = Quality.LOSSLESS
    else:
        settings['quality'] = Quality.HIGH
    
    console.print(f"\n  [green]✓[/green] Quality: [bold]{settings['quality'].value}[/bold]")
    if 'resolution' in settings:
        console.print(f"  [green]✓[/green] Resolution: [bold]4K (3840x2160)[/bold]")
    
    # Hardware acceleration
    if check_vaapi_available():
        settings['hw'] = Confirm.ask("\n  [cyan]•[/cyan] Use GPU acceleration (faster)?", default=True)
    else:
        settings['hw'] = False
    
    console.print()
    return settings


def show_render_summary(video: Path, device: str, effects: dict, quality: dict) -> bool:
    """Show render summary and confirm."""
    console.print("[bold cyan]Summary:[/bold cyan]\n")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="bold")
    
    table.add_row("Video", video.name)
    table.add_row("Device", device)
    table.add_row("Shadow", "Yes" if effects.get('shadow') else "No")
    table.add_row("Reflection", "Yes" if effects.get('reflection') else "No")
    table.add_row("Intro", effects.get('intro', 'none'))
    table.add_row("Quality", quality.get('quality', Quality.HIGH).value)
    if quality.get('resolution'):
        table.add_row("Resolution", "4K")
    table.add_row("GPU Accel", "Yes" if quality.get('hw') else "No")
    
    output_name = f"{video.stem}_mockup.mp4"
    table.add_row("Output", output_name)
    
    console.print(Panel(table, border_style="cyan"))
    
    return Confirm.ask("\n[bold]Start rendering?[/bold]", default=True)


def run_interactive_render(video: Path, device: str, effects: dict, quality_settings: dict):
    """Execute the render with interactive settings."""
    # Build the render call
    render_kwargs = {
        'video': video,
        'device': device,
        'shadow': effects.get('shadow', False),
        'reflection': effects.get('reflection', False),
        'quality': quality_settings.get('quality', Quality.HIGH),
        'hw': quality_settings.get('hw', False),
    }
    
    if effects.get('intro', 'none') != 'none':
        render_kwargs['intro'] = IntroAnimation(effects['intro'])
    
    if effects.get('bg_gradient'):
        render_kwargs['bg_gradient'] = effects['bg_gradient']
    
    if effects.get('bg_color'):
        render_kwargs['bg_color'] = effects['bg_color']
    
    if effects.get('bg_blur'):
        render_kwargs['bg_blur'] = True
    
    if quality_settings.get('resolution'):
        render_kwargs['resolution'] = quality_settings['resolution']
    
    # Run render
    render(**render_kwargs)


@app.command()
def interactive():
    """Launch interactive TUI wizard."""
    run_interactive_tui()


def run_interactive_tui():
    """Main interactive TUI loop."""
    show_banner()
    
    while True:
        interactive_menu()
        
        choice = Prompt.ask("\n[cyan]>[/cyan] Select option", default="1")
        
        if choice.lower() in ['q', 'quit', 'exit']:
            console.print("\n[dim]Goodbye![/dim]\n")
            break
        
        if choice.lower() in ['h', 'help']:
            console.print(Panel(
                "[bold]Help[/bold]\n\n"
                "• Use numbers or letters to select options\n"
                "• Type 'b' or 'back' to go back\n"
                "• Type 'q' to quit\n"
                "• Drag and drop files to paste their path",
                border_style="cyan"
            ))
            continue
        
        if choice == '1':
            # Create Mockup flow
            console.clear()
            show_banner()
            
            video = select_video()
            if not video:
                continue
            
            device = select_device()
            if not device:
                continue
            
            effects = select_effects()
            quality_settings = select_quality()
            
            if show_render_summary(video, device, effects, quality_settings):
                console.print()
                run_interactive_render(video, device, effects, quality_settings)
                
                console.print("\n[dim]Press Enter to continue...[/dim]")
                input()
            
            console.clear()
            show_banner()
        
        elif choice == '2':
            # Batch process
            console.print("\n[yellow]Batch processing coming soon![/yellow]")
            console.print("[dim]For now, use: dejitech-mockup batch <directory>[/dim]\n")
        
        elif choice == '3':
            # List devices
            console.clear()
            show_banner()
            devices_list()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            console.clear()
            show_banner()
        
        elif choice == '4':
            # Presets
            console.clear()
            show_banner()
            preset_list()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            console.clear()
            show_banner()
        
        elif choice == '5':
            # History
            console.clear()
            show_banner()
            history()
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            console.clear()
            show_banner()
        
        elif choice == '6':
            # Settings
            console.print("\n[yellow]Settings coming soon![/yellow]\n")


# ============================================================================
# Version Command
# ============================================================================


@app.command()
def version():
    """Show version information."""
    console.print(f"[bold cyan]DejiTech Mockup[/] v{__version__}")
    
    # Show system info
    hw_status = "[green]Available[/]" if check_vaapi_available() else "[yellow]Not available[/]"
    
    table = Table(show_header=False, box=None)
    table.add_column("", style="dim")
    table.add_column("")
    table.add_row("VA-API (AMD)", hw_status)
    table.add_row("Config dir", str(CONFIG_DIR))
    table.add_row("Data dir", str(DATA_DIR))
    
    console.print(table)


# ============================================================================
# Callback - Launch interactive by default
# ============================================================================


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version_flag: Annotated[bool, typer.Option("--version", "-V", help="Show version")] = False,
):
    """
    [bold cyan]DejiTech Mockup[/] - Professional device mockup video generator.
    """
    if version_flag:
        version()
        raise typer.Exit()
    
    # If no subcommand, launch interactive TUI
    if ctx.invoked_subcommand is None:
        run_interactive_tui()


# ============================================================================
# Entry Point
# ============================================================================


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
