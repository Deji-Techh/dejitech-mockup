"""
Preset management - save, load, and apply rendering presets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime

from ..constants import (
    PRESETS_DIR,
    Quality,
    Platform,
    ExportFormat,
    IntroAnimation,
    OutroAnimation,
    LogoPosition,
    GradientDirection,
)


@dataclass
class Preset:
    """Complete rendering preset configuration."""
    name: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Device
    device: str = "s22"
    fill: float = 0.90
    
    # Background
    bg_color: str = "0x000000"
    bg_image: Optional[str] = None
    bg_video: Optional[str] = None
    bg_gradient: Optional[str] = None
    gradient_direction: str = "vertical"
    bg_blur: bool = False
    bg_blur_strength: int = 20
    
    # Effects
    shadow: bool = False
    shadow_color: str = "0x000000"
    shadow_opacity: float = 0.5
    shadow_blur: int = 20
    shadow_offset_x: int = 10
    shadow_offset_y: int = 10
    
    reflection: bool = False
    reflection_opacity: float = 0.3
    
    corner_radius: int = 0
    border_width: int = 0
    border_color: str = "0xffffff"
    
    rotation: float = 0.0
    
    # Animation
    intro: str = "none"
    intro_duration: float = 0.5
    outro: str = "none"
    outro_duration: float = 0.5
    
    # Branding
    logo_path: Optional[str] = None
    logo_position: str = "bottom-right"
    logo_scale: float = 0.1
    logo_opacity: float = 1.0
    
    watermark_text: Optional[str] = None
    watermark_position: str = "bottom-right"
    watermark_font: str = "Sans"
    watermark_size: int = 24
    watermark_color: str = "0xffffff"
    watermark_opacity: float = 0.5
    
    text_overlay: Optional[str] = None
    text_position: str = "top-center"
    text_font: str = "Sans"
    text_size: int = 48
    text_color: str = "0xffffff"
    
    progress_bar: bool = False
    progress_bar_color: str = "0x3b82f6"
    
    # Export
    quality: str = "medium"
    format: str = "mp4"
    platform: Optional[str] = None
    hw_accel: bool = False


# Built-in presets
BUILTIN_PRESETS = {
    "default": Preset(
        name="default",
        description="Clean default settings",
    ),
    "professional": Preset(
        name="professional",
        description="Professional look with shadow",
        shadow=True,
        shadow_blur=25,
        shadow_opacity=0.4,
        quality="high",
    ),
    "social-dark": Preset(
        name="social-dark",
        description="Dark theme for social media",
        bg_color="0x0d1117",
        shadow=True,
        intro="fade",
        outro="fade-out",
        quality="high",
    ),
    "social-light": Preset(
        name="social-light",
        description="Light theme for social media",
        bg_color="0xf5f5f5",
        shadow=True,
        shadow_color="0x888888",
        quality="high",
    ),
    "tiktok": Preset(
        name="tiktok",
        description="Optimized for TikTok",
        bg_gradient="0x000000:0x1a1a2e",
        gradient_direction="vertical",
        intro="zoom",
        platform="tiktok",
    ),
    "youtube-short": Preset(
        name="youtube-short",
        description="Optimized for YouTube Shorts",
        shadow=True,
        intro="fade",
        platform="youtube-short",
        quality="high",
    ),
    "instagram-reel": Preset(
        name="instagram-reel",
        description="Optimized for Instagram Reels",
        bg_gradient="0x833ab4:0xfd1d1d",
        gradient_direction="diagonal",
        platform="instagram-reel",
    ),
    "minimal": Preset(
        name="minimal",
        description="Clean minimal look",
        bg_color="0xffffff",
        fill=0.85,
    ),
    "showcase": Preset(
        name="showcase",
        description="App showcase with branding",
        shadow=True,
        reflection=True,
        intro="slide-up",
        outro="fade-out",
        progress_bar=True,
        quality="ultra",
    ),
    "discord": Preset(
        name="discord",
        description="Optimized for Discord (25MB limit)",
        platform="discord",
        quality="medium",
    ),
}


def ensure_presets_dir() -> Path:
    """Ensure the presets directory exists."""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return PRESETS_DIR


def list_presets() -> dict[str, Preset]:
    """List all available presets (builtin + user)."""
    presets = dict(BUILTIN_PRESETS)
    
    # Load user presets
    presets_dir = PRESETS_DIR
    if presets_dir.exists():
        for preset_file in presets_dir.glob("*.json"):
            try:
                with open(preset_file) as f:
                    data = json.load(f)
                    preset = Preset(**data)
                    presets[preset.name] = preset
            except (json.JSONDecodeError, TypeError):
                continue
    
    return presets


def get_preset(name: str) -> Optional[Preset]:
    """Get a preset by name."""
    presets = list_presets()
    return presets.get(name.lower())


def save_preset(preset: Preset) -> Path:
    """Save a user preset."""
    presets_dir = ensure_presets_dir()
    preset_path = presets_dir / f"{preset.name.lower()}.json"
    
    with open(preset_path, "w") as f:
        json.dump(asdict(preset), f, indent=2)
    
    return preset_path


def delete_preset(name: str) -> bool:
    """Delete a user preset."""
    if name.lower() in BUILTIN_PRESETS:
        raise ValueError(f"Cannot delete built-in preset: {name}")
    
    preset_path = PRESETS_DIR / f"{name.lower()}.json"
    if preset_path.exists():
        preset_path.unlink()
        return True
    return False


def export_preset(name: str, output_path: Path) -> Path:
    """Export a preset to a file."""
    preset = get_preset(name)
    if not preset:
        raise ValueError(f"Preset not found: {name}")
    
    with open(output_path, "w") as f:
        json.dump(asdict(preset), f, indent=2)
    
    return output_path


def import_preset(preset_path: Path, new_name: Optional[str] = None) -> Preset:
    """Import a preset from a file."""
    with open(preset_path) as f:
        data = json.load(f)
    
    if new_name:
        data["name"] = new_name
    
    preset = Preset(**data)
    save_preset(preset)
    return preset


def preset_to_args(preset: Preset) -> dict[str, Any]:
    """Convert a preset to CLI argument dictionary."""
    args = {}
    
    # Map preset fields to CLI args
    if preset.device != "s22":
        args["device"] = preset.device
    if preset.fill != 0.90:
        args["fill"] = preset.fill
    if preset.bg_color != "0x000000":
        args["bg_color"] = preset.bg_color
    if preset.bg_image:
        args["bg_image"] = preset.bg_image
    if preset.bg_video:
        args["bg_video"] = preset.bg_video
    if preset.bg_gradient:
        args["bg_gradient"] = preset.bg_gradient
    if preset.bg_blur:
        args["bg_blur"] = True
    if preset.shadow:
        args["shadow"] = True
    if preset.reflection:
        args["reflection"] = True
    if preset.intro != "none":
        args["intro"] = preset.intro
    if preset.outro != "none":
        args["outro"] = preset.outro
    if preset.logo_path:
        args["logo"] = preset.logo_path
    if preset.watermark_text:
        args["watermark"] = preset.watermark_text
    if preset.progress_bar:
        args["progress_bar"] = True
    if preset.quality != "medium":
        args["quality"] = preset.quality
    if preset.platform:
        args["platform"] = preset.platform
    if preset.hw_accel:
        args["hw"] = True
    
    return args
