# DejiTech Mockup - Project Structure

```
dejitech-mockup/
├── pyproject.toml                    # Build config, dependencies, CLI entry points
├── README.md                         # User documentation
├── LICENSE                           # MIT License
├── project_structure.md              # This file
│
├── assets/                           # Device frame mockups (auto-discovered)
│   ├── s22.png                       # Samsung S22 Ultra (default)
│   ├── iphone15.png                  # Example: iPhone 15
│   └── devices.json                  # Optional: device screen coordinates
│
└── src/
    └── dejitech_mockup/              # Main package
        ├── __init__.py               # Package exports
        ├── main.py                   # CLI commands (Typer app)
        ├── constants.py              # Enums, defaults, platform settings
        │
        ├── utils/
        │   └── __init__.py           # Media analysis, color parsing, calculations
        │
        ├── effects/
        │   └── __init__.py           # Visual effects, animations, branding
        │
        ├── devices/
        │   └── __init__.py           # Device discovery, store, configuration
        │
        ├── exporters/
        │   └── __init__.py           # Export formats, platforms, compression
        │
        └── presets/
            └── __init__.py           # Preset management, built-in presets
```

## Module Responsibilities

### `constants.py`
- Version info
- Default values
- Enums (Quality, Platform, Resolution, etc.)
- Platform-specific settings (TikTok, YouTube, Instagram, etc.)

### `utils/`
- `get_media_info()` - FFprobe wrapper
- `parse_hex_color()` - Color format conversion
- `calculate_scaling()` - Auto-fit algorithm
- `parse_timestamp()` - Time string parsing
- Hardware detection (VA-API, NVENC)

### `effects/`
- `EffectConfig` dataclass - All effect settings
- `create_background()` - Solid/gradient/image/video/blur backgrounds
- `apply_shadow()` - Drop shadow generation
- `apply_reflection()` - Floor reflection effect
- `apply_intro_animation()` / `apply_outro_animation()`
- `apply_text_overlay()` / `apply_watermark()` / `apply_logo_overlay()`
- `apply_progress_bar()` / `apply_cta()`

### `devices/`
- `discover_devices()` - Scan assets directories
- `DeviceInfo` / `DeviceConfig` dataclasses
- `install_device()` / `uninstall_device()` - Store management
- `create_device_config()` - Custom screen coordinates

### `exporters/`
- `ExportConfig` / `ExportResult` dataclasses
- `export_video()` - Main export function
- Format-specific: `_export_mp4()`, `_export_webm()`, `_export_gif()`
- `export_thumbnail()` / `export_sprites()`
- `compress_to_size()` - Target file size compression
- Upload integrations (S3, Cloudinary)

### `presets/`
- `Preset` dataclass
- `BUILTIN_PRESETS` dictionary
- `list_presets()` / `get_preset()` / `save_preset()` / `delete_preset()`
- `preset_to_args()` - Convert preset to CLI args

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLI Input (main.py)                        │
│  render video.mp4 --device s22 --shadow --preset tiktok --hw     │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      1. Load Preset (if any)                      │
│                         presets/__init__.py                       │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      2. Discover Device Frame                     │
│                        devices/__init__.py                        │
│                    └─ Scan assets/ directories                    │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      3. Analyze Media (ffprobe)                   │
│                         utils/__init__.py                         │
│         └─ get_media_info() → dimensions, duration, fps          │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      4. Calculate Layout                          │
│                         utils/__init__.py                         │
│         └─ calculate_scaling() → scaled size, x/y offsets        │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      5. Build Effect Config                       │
│                        effects/__init__.py                        │
│               └─ EffectConfig with all visual settings           │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    6. Build FFmpeg Filter Graph                   │
│                           main.py                                 │
│                                                                   │
│   ┌─────────────┐                                                │
│   │ Background  │──┐                                             │
│   │   Layer     │  │                                             │
│   └─────────────┘  │                                             │
│                    ▼                                             │
│   ┌─────────────┐  ┌──────────────────┐                         │
│   │   Shadow    │──│    Overlay       │──┐                      │
│   │   (opt)     │  └──────────────────┘  │                      │
│   └─────────────┘                        ▼                      │
│                    ┌─────────────────┐  ┌──────────────────┐    │
│                    │  Scaled Video   │──│    Overlay       │──┐ │
│                    └─────────────────┘  └──────────────────┘  │ │
│                                                               ▼ │
│                    ┌─────────────────┐  ┌──────────────────┐   ││
│                    │  Device Frame   │──│    Overlay       │───┘│
│                    └─────────────────┘  └──────────────────┘    │
│                                                   │              │
│                                                   ▼              │
│                    ┌──────────────────────────────────────┐     │
│                    │  Post-processing (text, logo, etc)  │     │
│                    └──────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      7. Execute & Encode                          │
│                       exporters/__init__.py                       │
│         └─ libx264 (SW) or h264_vaapi (HW) encoding              │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      8. Post-processing                           │
│              └─ Compress to size, extract thumbnail               │
│              └─ Add to history, save preset                       │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                            Output Video
```

## CLI Commands Tree

```
dmockup
├── render          # Main rendering command (default)
├── batch           # Process multiple videos
├── watch           # Auto-process new files
├── info            # Analyze media file
├── history         # View/clear render history
├── interactive     # TUI wizard
├── version         # Show version info
│
├── devices/
│   ├── list        # List available device frames
│   └── add         # Add new device frame
│
├── preset/
│   ├── list        # List all presets
│   ├── show        # Show preset details
│   └── delete      # Delete user preset
│
└── store/          # (Future) Remote device downloads
    ├── list
    ├── install
    └── uninstall
```

## Configuration Files

```
~/.config/dejitech-mockup/
├── presets/                  # User-saved presets
│   └── my-preset.json

~/.local/share/dejitech-mockup/
├── assets/                   # User device frames
│   ├── custom-device.png
│   └── devices.json          # Screen coordinate configs
└── history.json              # Render history

~/.cache/dejitech-mockup/     # Temporary files
```

## Key Design Decisions

1. **Modular Architecture**: Separated concerns into distinct modules for maintainability

2. **No Hardcoded Coordinates**: All positioning calculated from ffprobe analysis

3. **Preset System**: Built-in + user presets reduce repetitive CLI flags

4. **Platform Awareness**: Pre-configured settings for TikTok, YouTube, Instagram, etc.

5. **Progressive Enhancement**: Core features work without optional deps (watchdog, boto3)

6. **FFmpeg Filter Graph**: Efficient single-pass composition using overlay filters

7. **Hardware Abstraction**: Automatic fallback from VA-API to software encoding

8. **Rich CLI**: Beautiful terminal output with progress, tables, and panels
