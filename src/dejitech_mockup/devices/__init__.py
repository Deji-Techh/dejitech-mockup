"""
Device management - discovery, store, and configuration.
"""

from __future__ import annotations

import json
import shutil
import urllib.request
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from ..constants import DATA_DIR, DEVICE_STORE_URL, DEFAULT_DEVICE
from ..utils import get_media_dimensions


@dataclass
class DeviceConfig:
    """Configuration for a device mockup frame."""
    name: str
    file: str
    width: int
    height: int
    screen_x: Optional[int] = None
    screen_y: Optional[int] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    has_notch: bool = False
    color_variant: Optional[str] = None
    category: str = "phone"


@dataclass
class DeviceInfo:
    """Device information with file path."""
    name: str
    path: Path
    width: int
    height: int
    config: Optional[DeviceConfig] = None


def get_assets_dirs() -> list[Path]:
    """Get all possible asset directories in priority order."""
    dirs = []
    
    # Current working directory
    cwd_assets = Path.cwd() / "assets"
    if cwd_assets.exists():
        dirs.append(cwd_assets)
    
    # User data directory
    user_assets = DATA_DIR / "assets"
    if user_assets.exists():
        dirs.append(user_assets)
    
    # Package assets (development)
    pkg_assets = Path(__file__).parent.parent.parent.parent / "assets"
    if pkg_assets.exists():
        dirs.append(pkg_assets)
    
    return dirs


def ensure_assets_dir() -> Path:
    """Ensure the user assets directory exists and return it."""
    user_assets = DATA_DIR / "assets"
    user_assets.mkdir(parents=True, exist_ok=True)
    return user_assets


def discover_devices() -> dict[str, DeviceInfo]:
    """
    Scan all asset directories for available device mockup frames.
    Returns a dict mapping device name to DeviceInfo.
    """
    devices = {}
    
    for assets_dir in get_assets_dirs():
        # Load device configs if available
        configs = _load_device_configs(assets_dir)
        
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            for frame_file in assets_dir.glob(ext):
                device_name = frame_file.stem.lower()
                
                # Skip if already found (priority order)
                if device_name in devices:
                    continue
                
                try:
                    width, height = get_media_dimensions(frame_file)
                    config = configs.get(device_name)
                    
                    devices[device_name] = DeviceInfo(
                        name=device_name,
                        path=frame_file,
                        width=width,
                        height=height,
                        config=config,
                    )
                except Exception:
                    # Skip files that can't be analyzed
                    continue
    
    return devices


def _load_device_configs(assets_dir: Path) -> dict[str, DeviceConfig]:
    """Load device configuration from JSON file if present."""
    config_file = assets_dir / "devices.json"
    configs = {}
    
    if config_file.exists():
        try:
            with open(config_file) as f:
                data = json.load(f)
                for name, cfg in data.items():
                    configs[name.lower()] = DeviceConfig(
                        name=name,
                        **cfg
                    )
        except (json.JSONDecodeError, KeyError):
            pass
    
    return configs


def get_device(name: str) -> Optional[DeviceInfo]:
    """Get a specific device by name."""
    devices = discover_devices()
    return devices.get(name.lower())


def list_device_categories() -> dict[str, list[str]]:
    """Group devices by category."""
    devices = discover_devices()
    categories = {}
    
    for name, info in devices.items():
        category = info.config.category if info.config else "uncategorized"
        if category not in categories:
            categories[category] = []
        categories[category].append(name)
    
    return categories


# ============================================================================
# Device Store (Remote device downloads)
# ============================================================================


@dataclass
class StoreDevice:
    """Device available in the remote store."""
    name: str
    display_name: str
    category: str
    preview_url: str
    download_url: str
    size_bytes: int
    variants: list[str]


def fetch_store_catalog() -> list[StoreDevice]:
    """Fetch the device catalog from the remote store."""
    catalog_url = f"{DEVICE_STORE_URL}/catalog.json"
    
    try:
        with urllib.request.urlopen(catalog_url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return [StoreDevice(**item) for item in data.get("devices", [])]
    except Exception as e:
        raise RuntimeError(f"Failed to fetch device catalog: {e}")


def install_device(device_name: str, variant: Optional[str] = None) -> Path:
    """Download and install a device from the store."""
    catalog = fetch_store_catalog()
    
    device = next((d for d in catalog if d.name.lower() == device_name.lower()), None)
    if not device:
        available = ", ".join(d.name for d in catalog)
        raise ValueError(f"Device '{device_name}' not found in store. Available: {available}")
    
    # Determine download URL
    if variant and variant in device.variants:
        download_url = device.download_url.replace("{variant}", variant)
        filename = f"{device.name}-{variant}.png"
    else:
        download_url = device.download_url.replace("{variant}", "default")
        filename = f"{device.name}.png"
    
    # Download to user assets
    assets_dir = ensure_assets_dir()
    dest_path = assets_dir / filename
    
    try:
        with urllib.request.urlopen(download_url, timeout=30) as response:
            with open(dest_path, "wb") as f:
                f.write(response.read())
    except Exception as e:
        raise RuntimeError(f"Failed to download device: {e}")
    
    return dest_path


def uninstall_device(device_name: str) -> bool:
    """Remove a device from local storage."""
    assets_dir = DATA_DIR / "assets"
    
    for ext in ["png", "jpg", "jpeg", "webp"]:
        device_file = assets_dir / f"{device_name}.{ext}"
        if device_file.exists():
            device_file.unlink()
            return True
    
    return False


def create_device_config(
    device_name: str,
    screen_x: int,
    screen_y: int,
    screen_width: int,
    screen_height: int,
    category: str = "phone",
) -> None:
    """Create or update device configuration with screen coordinates."""
    assets_dir = ensure_assets_dir()
    config_file = assets_dir / "devices.json"
    
    # Load existing configs
    configs = {}
    if config_file.exists():
        with open(config_file) as f:
            configs = json.load(f)
    
    # Get device dimensions
    device = get_device(device_name)
    if not device:
        raise ValueError(f"Device '{device_name}' not found")
    
    # Update config
    configs[device_name] = {
        "file": device.path.name,
        "width": device.width,
        "height": device.height,
        "screen_x": screen_x,
        "screen_y": screen_y,
        "screen_width": screen_width,
        "screen_height": screen_height,
        "category": category,
    }
    
    with open(config_file, "w") as f:
        json.dump(configs, f, indent=2)
