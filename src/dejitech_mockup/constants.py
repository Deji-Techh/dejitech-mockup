"""
DejiTech Mockup - Core constants and configuration.
"""

from pathlib import Path
from enum import Enum

# ============================================================================
# Version
# ============================================================================

__version__ = "2.1.3"

# ============================================================================
# Defaults
# ============================================================================

DEFAULT_DEVICE = "s22"
DEFAULT_BG_COLOR = "0x000000"
DEFAULT_CRF = 18  # Higher quality default
DEFAULT_FILL_PERCENT = 0.98  # Fill almost entire mockup
DEFAULT_FPS = 30
DEFAULT_AUDIO_BITRATE = "256k"

# ============================================================================
# Paths
# ============================================================================

APP_NAME = "dejitech-mockup"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
DATA_DIR = Path.home() / ".local" / "share" / APP_NAME
CACHE_DIR = Path.home() / ".cache" / APP_NAME
PRESETS_DIR = CONFIG_DIR / "presets"
HISTORY_FILE = DATA_DIR / "history.json"
DEVICE_STORE_URL = "https://raw.githubusercontent.com/dejitech/mockup-devices/main"

# ============================================================================
# Enums
# ============================================================================


class Quality(str, Enum):
    """Video quality presets mapped to CRF values."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    LOSSLESS = "lossless"


class Resolution(str, Enum):
    """Common resolution presets."""
    SD = "480p"
    HD = "720p"
    FHD = "1080p"
    QHD = "1440p"
    UHD = "4k"
    UHD_PLUS = "5k"
    INSTAGRAM_STORY = "instagram-story"
    INSTAGRAM_REEL = "instagram-reel"
    TIKTOK = "tiktok"
    YOUTUBE_SHORT = "youtube-short"
    TWITTER = "twitter"


class Platform(str, Enum):
    """Export platform presets."""
    YOUTUBE = "youtube"
    YOUTUBE_SHORT = "youtube-short"
    TIKTOK = "tiktok"
    INSTAGRAM_STORY = "instagram-story"
    INSTAGRAM_REEL = "instagram-reel"
    INSTAGRAM_POST = "instagram-post"
    TWITTER = "twitter"
    DISCORD = "discord"
    LINKEDIN = "linkedin"


class IntroAnimation(str, Enum):
    """Intro animation types."""
    NONE = "none"
    FADE = "fade"
    SLIDE_UP = "slide-up"
    SLIDE_DOWN = "slide-down"
    SLIDE_LEFT = "slide-left"
    SLIDE_RIGHT = "slide-right"
    ZOOM = "zoom"
    BOUNCE = "bounce"
    ROTATE = "rotate"


class OutroAnimation(str, Enum):
    """Outro animation types."""
    NONE = "none"
    FADE = "fade-out"
    SLIDE_UP = "slide-up"
    SLIDE_DOWN = "slide-down"
    ZOOM_OUT = "zoom-out"


class ExportFormat(str, Enum):
    """Export format types."""
    MP4 = "mp4"
    WEBM = "webm"
    GIF = "gif"
    MOV = "mov"
    AVI = "avi"


class LogoPosition(str, Enum):
    """Logo/watermark position options."""
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    TOP_CENTER = "top-center"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    BOTTOM_CENTER = "bottom-center"
    CENTER = "center"


class GradientDirection(str, Enum):
    """Gradient direction presets."""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    DIAGONAL = "diagonal"
    RADIAL = "radial"


# ============================================================================
# Mappings
# ============================================================================

QUALITY_CRF_MAP = {
    Quality.LOW: 28,
    Quality.MEDIUM: 23,
    Quality.HIGH: 18,
    Quality.ULTRA: 12,
    Quality.LOSSLESS: 0,
}

RESOLUTION_MAP = {
    Resolution.SD: (854, 480),
    Resolution.HD: (1280, 720),
    Resolution.FHD: (1920, 1080),
    Resolution.QHD: (2560, 1440),
    Resolution.UHD: (3840, 2160),
    Resolution.UHD_PLUS: (5120, 2880),
    Resolution.INSTAGRAM_STORY: (1080, 1920),
    Resolution.INSTAGRAM_REEL: (1080, 1920),
    Resolution.TIKTOK: (1080, 1920),
    Resolution.YOUTUBE_SHORT: (1080, 1920),
    Resolution.TWITTER: (1280, 720),
}

PLATFORM_SETTINGS = {
    Platform.YOUTUBE: {
        "resolution": (1920, 1080),
        "fps": 30,
        "max_bitrate": "20M",
        "codec": "libx264",
        "audio_bitrate": "320k",
    },
    Platform.YOUTUBE_SHORT: {
        "resolution": (1080, 1920),
        "fps": 30,
        "max_bitrate": "15M",
        "codec": "libx264",
        "audio_bitrate": "256k",
        "max_duration": 60,
    },
    Platform.TIKTOK: {
        "resolution": (1080, 1920),
        "fps": 30,
        "max_bitrate": "10M",
        "codec": "libx264",
        "audio_bitrate": "192k",
        "max_duration": 180,
        "max_size_mb": 287,
    },
    Platform.INSTAGRAM_STORY: {
        "resolution": (1080, 1920),
        "fps": 30,
        "max_bitrate": "8M",
        "codec": "libx264",
        "audio_bitrate": "128k",
        "max_duration": 60,
    },
    Platform.INSTAGRAM_REEL: {
        "resolution": (1080, 1920),
        "fps": 30,
        "max_bitrate": "10M",
        "codec": "libx264",
        "audio_bitrate": "192k",
        "max_duration": 90,
    },
    Platform.INSTAGRAM_POST: {
        "resolution": (1080, 1080),
        "fps": 30,
        "max_bitrate": "8M",
        "codec": "libx264",
        "audio_bitrate": "128k",
        "max_duration": 60,
    },
    Platform.TWITTER: {
        "resolution": (1280, 720),
        "fps": 30,
        "max_bitrate": "5M",
        "codec": "libx264",
        "audio_bitrate": "128k",
        "max_size_mb": 512,
    },
    Platform.DISCORD: {
        "resolution": (1280, 720),
        "fps": 30,
        "max_bitrate": "4M",
        "codec": "libx264",
        "audio_bitrate": "128k",
        "max_size_mb": 25,
    },
    Platform.LINKEDIN: {
        "resolution": (1920, 1080),
        "fps": 30,
        "max_bitrate": "10M",
        "codec": "libx264",
        "audio_bitrate": "192k",
        "max_duration": 600,
    },
}
