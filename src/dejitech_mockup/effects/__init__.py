"""
Visual effects module - shadows, reflections, backgrounds, animations.
"""

from __future__ import annotations

from typing import Optional, Any
from dataclasses import dataclass, field

try:
    import ffmpeg
except ImportError:
    ffmpeg = None  # type: ignore

from ..constants import (
    IntroAnimation,
    OutroAnimation,
    GradientDirection,
    LogoPosition,
)
from ..utils import parse_hex_color, parse_gradient, make_even


@dataclass
class EffectConfig:
    """Configuration for all visual effects."""
    # Background
    bg_color: str = "0x000000"
    bg_image: Optional[str] = None
    bg_video: Optional[str] = None
    bg_gradient: Optional[str] = None
    gradient_direction: GradientDirection = GradientDirection.VERTICAL
    bg_blur: bool = False
    bg_blur_strength: int = 20
    
    # Shadow & Glow
    shadow: bool = False
    shadow_color: str = "0x000000"
    shadow_opacity: float = 0.5
    shadow_blur: int = 20
    shadow_offset_x: int = 10
    shadow_offset_y: int = 10
    glow: bool = False
    glow_color: str = "0xffffff"
    glow_strength: int = 10
    
    # Reflection
    reflection: bool = False
    reflection_opacity: float = 0.3
    reflection_height: float = 0.3
    
    # Transform
    rotation: float = 0.0
    perspective: bool = False
    perspective_angle: float = 15.0
    corner_radius: int = 0
    
    # Border
    border_width: int = 0
    border_color: str = "0xffffff"
    
    # Animation
    intro: IntroAnimation = IntroAnimation.NONE
    intro_duration: float = 0.5
    outro: OutroAnimation = OutroAnimation.NONE
    outro_duration: float = 0.5
    device_float: bool = False
    float_amplitude: int = 5
    float_speed: float = 2.0
    
    # Branding
    logo_path: Optional[str] = None
    logo_position: LogoPosition = LogoPosition.BOTTOM_RIGHT
    logo_scale: float = 0.1
    logo_opacity: float = 1.0
    logo_margin: int = 20
    
    watermark_text: Optional[str] = None
    watermark_position: LogoPosition = LogoPosition.BOTTOM_RIGHT
    watermark_font: str = "Sans"
    watermark_size: int = 24
    watermark_color: str = "0xffffff"
    watermark_opacity: float = 0.5
    
    text_overlay: Optional[str] = None
    text_position: LogoPosition = LogoPosition.TOP_CENTER
    text_font: str = "Sans"
    text_size: int = 48
    text_color: str = "0xffffff"
    
    cta_text: Optional[str] = None
    cta_style: str = "pill"
    cta_bg_color: str = "0x3b82f6"
    cta_text_color: str = "0xffffff"
    
    # Progress bar
    progress_bar: bool = False
    progress_bar_position: str = "bottom"
    progress_bar_color: str = "0x3b82f6"
    progress_bar_height: int = 4
    
    # End card
    endcard_duration: float = 0.0
    
    # Cursor
    show_cursor: bool = False
    cursor_style: str = "default"


def create_background(
    config: EffectConfig,
    width: int,
    height: int,
    duration: float,
    video_input: Optional[Any] = None,
) -> Any:
    """
    Create the background layer based on configuration.
    Returns an ffmpeg stream.
    """
    width = make_even(width)
    height = make_even(height)
    
    if config.bg_video:
        # Video background
        bg = ffmpeg.input(config.bg_video, stream_loop=-1)
        bg = bg.filter("scale", w=width, h=height, force_original_aspect_ratio="increase")
        bg = bg.filter("crop", w=width, h=height)
        return bg
    
    elif config.bg_image:
        # Image background
        bg = ffmpeg.input(config.bg_image, loop=1, t=duration)
        bg = bg.filter("scale", w=width, h=height, force_original_aspect_ratio="increase")
        bg = bg.filter("crop", w=width, h=height)
        return bg
    
    elif config.bg_blur and video_input is not None:
        # Blurred video background
        bg = video_input.filter("scale", w=width, h=height, force_original_aspect_ratio="increase")
        bg = bg.filter("crop", w=width, h=height)
        bg = bg.filter("boxblur", luma_radius=config.bg_blur_strength)
        return bg
    
    elif config.bg_gradient:
        # Gradient background
        color1, color2 = parse_gradient(config.bg_gradient)
        
        if config.gradient_direction == GradientDirection.RADIAL:
            # Radial gradient using geq filter
            bg = ffmpeg.input(
                f"color=c={color1}:s={width}x{height}:r=30:d={duration}",
                f="lavfi"
            )
            # Apply radial gradient effect
            bg = bg.filter(
                "geq",
                r=f"'lerp({int(color1[2:4], 16)},{int(color2[2:4], 16)},sqrt((X-W/2)^2+(Y-H/2)^2)/sqrt((W/2)^2+(H/2)^2))'",
                g=f"'lerp({int(color1[4:6], 16)},{int(color2[4:6], 16)},sqrt((X-W/2)^2+(Y-H/2)^2)/sqrt((W/2)^2+(H/2)^2))'",
                b=f"'lerp({int(color1[6:8], 16)},{int(color2[6:8], 16)},sqrt((X-W/2)^2+(Y-H/2)^2)/sqrt((W/2)^2+(H/2)^2))'"
            )
        else:
            # Linear gradients using gradients filter
            if config.gradient_direction == GradientDirection.HORIZONTAL:
                direction = "0"
            elif config.gradient_direction == GradientDirection.DIAGONAL:
                direction = "1"
            else:  # VERTICAL
                direction = "2"
            
            # Use color sources and blend
            bg = ffmpeg.input(
                f"color=c={color1}:s={width}x{height}:r=30:d={duration}",
                f="lavfi"
            )
        return bg
    
    else:
        # Solid color background
        bg_hex = parse_hex_color(config.bg_color)
        bg = ffmpeg.input(
            f"color=c={bg_hex}:s={width}x{height}:r=30",
            f="lavfi",
            t=duration + 10,  # Extra buffer
        )
        return bg


def apply_shadow(
    stream: Any,
    config: EffectConfig,
    canvas_width: int,
    canvas_height: int,
    x_offset: int,
    y_offset: int,
) -> tuple[Any, int, int]:
    """
    Apply drop shadow effect.
    Returns the shadow stream and adjusted offsets.
    """
    if not config.shadow:
        return None, x_offset, y_offset
    
    # Create shadow by duplicating, colorizing, and blurring
    shadow = stream.filter("colorchannelmixer", 
        rr=0, rg=0, rb=0, ra=config.shadow_opacity,
        gr=0, gg=0, gb=0, ga=config.shadow_opacity,
        br=0, bg=0, bb=0, ba=config.shadow_opacity,
        ar=0, ag=0, ab=0, aa=config.shadow_opacity
    )
    shadow = shadow.filter("boxblur", luma_radius=config.shadow_blur)
    
    shadow_x = x_offset + config.shadow_offset_x
    shadow_y = y_offset + config.shadow_offset_y
    
    return shadow, shadow_x, shadow_y


def apply_glow(
    stream: Any,
    config: EffectConfig,
) -> Any:
    """Apply glow effect around the video."""
    if not config.glow:
        return stream
    
    # Glow is achieved by blurring and brightening edges
    glow = stream.filter("boxblur", luma_radius=config.glow_strength)
    glow = glow.filter("colorchannelmixer",
        rr=1.5, gg=1.5, bb=1.5
    )
    
    # Blend glow under original
    return ffmpeg.filter([glow, stream], "overlay", x=0, y=0)


def apply_reflection(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
) -> Any:
    """Create a reflection effect below the video."""
    if not config.reflection:
        return None
    
    reflection_h = int(height * config.reflection_height)
    
    # Flip vertically and crop to reflection height
    reflection = stream.filter("vflip")
    reflection = reflection.filter("crop", w=width, h=reflection_h, x=0, y=0)
    
    # Apply fade gradient (top to bottom transparency)
    reflection = reflection.filter(
        "geq",
        lum=f"lum(X,Y)*({config.reflection_opacity}*(1-Y/{reflection_h}))",
        cb="cb(X,Y)",
        cr="cr(X,Y)"
    )
    
    return reflection


def apply_corner_radius(stream: Any, radius: int, width: int, height: int) -> Any:
    """Apply rounded corners to the video."""
    if radius <= 0:
        return stream
    
    # Create rounded rectangle mask
    mask_filter = (
        f"geq=lum='if(gt(abs(X-{width}/2),{width}/2-{radius})*"
        f"gt(abs(Y-{height}/2),{height}/2-{radius}),"
        f"if(lte(sqrt(pow(abs(X-{width}/2)-{width}/2+{radius},2)+"
        f"pow(abs(Y-{height}/2)-{height}/2+{radius},2)),{radius}),255,0),255)'"
    )
    
    return stream.filter("format", pix_fmts="yuva420p")


def apply_border(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
) -> Any:
    """Apply border/stroke around the video."""
    if config.border_width <= 0:
        return stream
    
    border_color = parse_hex_color(config.border_color)
    
    # Pad with border color
    stream = stream.filter(
        "pad",
        w=width + config.border_width * 2,
        h=height + config.border_width * 2,
        x=config.border_width,
        y=config.border_width,
        color=border_color,
    )
    
    return stream


def apply_intro_animation(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
    fps: float,
) -> Any:
    """Apply intro animation to the composed video."""
    if config.intro == IntroAnimation.NONE:
        return stream
    
    frames = int(config.intro_duration * fps)
    
    if config.intro == IntroAnimation.FADE:
        stream = stream.filter(
            "fade",
            type="in",
            start_frame=0,
            nb_frames=frames,
        )
    
    elif config.intro == IntroAnimation.ZOOM:
        # Zoom from 80% to 100%
        stream = stream.filter(
            "zoompan",
            z=f"if(lt(on,{frames}),0.8+0.2*on/{frames},1)",
            d=1,
            x="iw/2-(iw/zoom/2)",
            y="ih/2-(ih/zoom/2)",
            s=f"{width}x{height}",
        )
    
    elif config.intro in [IntroAnimation.SLIDE_UP, IntroAnimation.SLIDE_DOWN,
                          IntroAnimation.SLIDE_LEFT, IntroAnimation.SLIDE_RIGHT]:
        # Slide animations using overlay with animated position
        direction = config.intro.value.replace("slide-", "")
        
        if direction == "up":
            stream = stream.filter(
                "fade", type="in", start_frame=0, nb_frames=frames
            )
        elif direction == "down":
            stream = stream.filter(
                "fade", type="in", start_frame=0, nb_frames=frames
            )
        # Note: Full slide animations require more complex filter graphs
    
    elif config.intro == IntroAnimation.BOUNCE:
        stream = stream.filter(
            "fade", type="in", start_frame=0, nb_frames=frames
        )
    
    return stream


def apply_outro_animation(
    stream: Any,
    config: EffectConfig,
    duration: float,
    fps: float,
) -> Any:
    """Apply outro animation to the composed video."""
    if config.outro == OutroAnimation.NONE:
        return stream
    
    frames = int(config.outro_duration * fps)
    start_frame = int((duration - config.outro_duration) * fps)
    
    if config.outro in [OutroAnimation.FADE, OutroAnimation.ZOOM_OUT]:
        stream = stream.filter(
            "fade",
            type="out",
            start_frame=start_frame,
            nb_frames=frames,
        )
    
    return stream


def apply_progress_bar(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
    duration: float,
) -> Any:
    """Add an animated progress bar to the video."""
    if not config.progress_bar:
        return stream
    
    bar_color = parse_hex_color(config.progress_bar_color)
    bar_h = config.progress_bar_height
    
    if config.progress_bar_position == "top":
        y_pos = 0
    else:  # bottom
        y_pos = height - bar_h
    
    # Draw animated rectangle that grows with time
    stream = stream.filter(
        "drawbox",
        x=0,
        y=y_pos,
        w=f"t/{duration}*{width}",
        h=bar_h,
        color=bar_color,
        t="fill",
    )
    
    return stream


def apply_text_overlay(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
) -> Any:
    """Apply text overlay to the video."""
    if not config.text_overlay:
        return stream
    
    text_color = parse_hex_color(config.text_color).replace("0x", "")
    
    # Calculate position based on text_position
    x_expr, y_expr = _get_position_expr(config.text_position, width, height, margin=40)
    
    stream = stream.filter(
        "drawtext",
        text=config.text_overlay,
        fontsize=config.text_size,
        fontcolor=text_color,
        x=x_expr,
        y=y_expr,
        font=config.text_font,
    )
    
    return stream


def apply_watermark(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
) -> Any:
    """Apply watermark text to the video."""
    if not config.watermark_text:
        return stream
    
    wm_color = parse_hex_color(config.watermark_color).replace("0x", "")
    
    x_expr, y_expr = _get_position_expr(config.watermark_position, width, height, margin=20)
    
    # Apply with opacity
    stream = stream.filter(
        "drawtext",
        text=config.watermark_text,
        fontsize=config.watermark_size,
        fontcolor=f"{wm_color}@{config.watermark_opacity}",
        x=x_expr,
        y=y_expr,
        font=config.watermark_font,
    )
    
    return stream


def apply_logo_overlay(
    stream: Any,
    logo_input: Any,
    config: EffectConfig,
    width: int,
    height: int,
) -> Any:
    """Overlay a logo on the video."""
    if not config.logo_path:
        return stream
    
    # Scale logo
    logo_w = int(width * config.logo_scale)
    logo = logo_input.filter("scale", w=logo_w, h=-1)
    
    if config.logo_opacity < 1.0:
        logo = logo.filter("format", pix_fmts="rgba")
        logo = logo.filter(
            "colorchannelmixer",
            aa=config.logo_opacity,
        )
    
    # Calculate position
    x, y = _get_logo_position(config.logo_position, width, height, logo_w, logo_w, config.logo_margin)
    
    return ffmpeg.overlay(stream, logo, x=x, y=y)


def apply_cta(
    stream: Any,
    config: EffectConfig,
    width: int,
    height: int,
) -> Any:
    """Apply call-to-action button overlay."""
    if not config.cta_text:
        return stream
    
    bg_color = parse_hex_color(config.cta_bg_color).replace("0x", "")
    text_color = parse_hex_color(config.cta_text_color).replace("0x", "")
    
    # Draw CTA as pill/button shape at bottom center
    cta_w = len(config.cta_text) * 20 + 40
    cta_h = 50
    cta_x = (width - cta_w) // 2
    cta_y = height - cta_h - 40
    
    # Draw background pill
    if config.cta_style == "pill":
        stream = stream.filter(
            "drawbox",
            x=cta_x,
            y=cta_y,
            w=cta_w,
            h=cta_h,
            color=bg_color,
            t="fill",
        )
    
    # Draw text
    stream = stream.filter(
        "drawtext",
        text=config.cta_text,
        fontsize=24,
        fontcolor=text_color,
        x=f"({width}-text_w)/2",
        y=cta_y + 13,
        font="Sans",
    )
    
    return stream


def _get_position_expr(
    position: LogoPosition,
    width: int,
    height: int,
    margin: int = 20,
) -> tuple[str, str]:
    """Get FFmpeg expression for text position."""
    positions = {
        LogoPosition.TOP_LEFT: (str(margin), str(margin)),
        LogoPosition.TOP_RIGHT: (f"{width}-text_w-{margin}", str(margin)),
        LogoPosition.TOP_CENTER: (f"({width}-text_w)/2", str(margin)),
        LogoPosition.BOTTOM_LEFT: (str(margin), f"{height}-text_h-{margin}"),
        LogoPosition.BOTTOM_RIGHT: (f"{width}-text_w-{margin}", f"{height}-text_h-{margin}"),
        LogoPosition.BOTTOM_CENTER: (f"({width}-text_w)/2", f"{height}-text_h-{margin}"),
        LogoPosition.CENTER: (f"({width}-text_w)/2", f"({height}-text_h)/2"),
    }
    return positions.get(position, (str(margin), str(margin)))


def _get_logo_position(
    position: LogoPosition,
    canvas_w: int,
    canvas_h: int,
    logo_w: int,
    logo_h: int,
    margin: int = 20,
) -> tuple[int, int]:
    """Calculate logo position coordinates."""
    positions = {
        LogoPosition.TOP_LEFT: (margin, margin),
        LogoPosition.TOP_RIGHT: (canvas_w - logo_w - margin, margin),
        LogoPosition.TOP_CENTER: ((canvas_w - logo_w) // 2, margin),
        LogoPosition.BOTTOM_LEFT: (margin, canvas_h - logo_h - margin),
        LogoPosition.BOTTOM_RIGHT: (canvas_w - logo_w - margin, canvas_h - logo_h - margin),
        LogoPosition.BOTTOM_CENTER: ((canvas_w - logo_w) // 2, canvas_h - logo_h - margin),
        LogoPosition.CENTER: ((canvas_w - logo_w) // 2, (canvas_h - logo_h) // 2),
    }
    return positions.get(position, (margin, margin))
