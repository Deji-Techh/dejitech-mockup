# DejiTech Mockup

<p align="center">
  <strong>Professional device mockup video generator for content creators</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#presets">Presets</a>
</p>

---

A high-performance CLI tool for overlaying screen recordings onto device mockup frames with professional effects, intelligent auto-scaling, and hardware acceleration.

## Features

### Core
- **Intelligent Auto-Scaling** - Automatically detects video orientation and scales to fit perfectly
- **Dynamic Device Discovery** - Drop a PNG in `assets/` and use `--device filename`
- **Hardware Acceleration** - VA-API support for AMD GPUs with `--hw` flag
- **Platform Presets** - Optimized exports for TikTok, YouTube Shorts, Instagram, Discord

### Video Processing
- **Trim** - `--start 00:05 --end 00:30` or `--duration 10`
- **Speed Control** - `--speed 1.5` or `--speed 0.5` for slow-mo
- **Reverse** - `--reverse` for rewind effect
- **Frame Rate** - `--fps 60` to change output FPS
- **Resolution Presets** - `--resolution 1080p` / `4k` / `tiktok` / `instagram-story`
- **Loop** - `--loop` for looping videos/GIFs

### Visual Effects
- **Shadow** - `--shadow` with customizable opacity, blur, offset
- **Reflection** - `--reflection` adds floor reflection
- **Gradient Backgrounds** - `--bg-gradient "#000:#333" --gradient-dir vertical`
- **Image/Video Backgrounds** - `--bg-image bg.jpg` or `--bg-video loop.mp4`
- **Blur Background** - `--bg-blur` uses blurred video as background
- **Corner Radius** - `--corner-radius 20`
- **Border** - `--border "2px #fff"`
- **Rotation** - `--rotate 15` for angled mockups

### Animation
- **Intro** - `--intro fade` / `zoom` / `slide-up` / `slide-down` / `bounce`
- **Outro** - `--outro fade-out` / `zoom-out`
- **Progress Bar** - `--progress-bar` with customizable color

### Branding
- **Logo Overlay** - `--logo logo.png --logo-position bottom-right --logo-scale 0.1`
- **Text Overlay** - `--text "App Demo" --text-position top-center --text-size 48`
- **Watermark** - `--watermark "© 2024" --watermark-opacity 0.5`
- **Call-to-Action** - `--cta "Download Now" --cta-style pill`

### Audio
- **Background Music** - `--music track.mp3 --music-volume 0.3`
- **Mute Original** - `--mute`
- **Voiceover** - `--voiceover narration.mp3`

### Batch & Automation
- **Batch Processing** - `dmockup batch ./videos/ --parallel 4`
- **Watch Mode** - `dmockup watch ./inbox/` auto-processes new files
- **Presets** - `--preset tiktok` or `--save-preset mypreset`
- **History** - `dmockup history` shows recent renders

### Export
- **Multiple Formats** - `--format mp4` / `webm` / `gif` / `mov`
- **Platform Optimization** - `--platform tiktok` auto-configures resolution/codec
- **Size Limits** - `--max-size 25` compresses to target MB
- **Thumbnails** - `--thumbnail` exports poster frame

### Developer Tools
- **Dry Run** - `--dry-run` shows FFmpeg command
- **Preview** - `--preview` renders first 5 seconds only
- **Debug Overlay** - `--debug` shows dimensions on output
- **JSON Output** - `--json` for CI/CD integration
- **Interactive Mode** - `dmockup interactive` launches TUI wizard

## Installation

### From Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/dejitech/dejitech-mockup.git
cd dejitech-mockup

# Install with pip
pip install -e .

# Or install with all optional features
pip install -e ".[all]"
```

### Dependencies

```bash
# Arch Linux
sudo pacman -S ffmpeg python-pip

# For VA-API hardware acceleration (AMD)
sudo pacman -S libva libva-mesa-driver

# For watch mode
pip install watchdog
```

## Quick Start

```bash
# Basic usage (uses default S22 Ultra frame)
dmockup render recording.mp4

# Use a different device
dmockup render recording.mp4 --device iphone15

# Add shadow and fade-in effect
dmockup render recording.mp4 --shadow --intro fade

# Hardware accelerated with TikTok preset
dmockup render recording.mp4 --hw --preset tiktok

# Custom gradient background
dmockup render recording.mp4 --bg-gradient "#1a1a2e:#16213e"

# Full featured example
dmockup render recording.mp4 \
  --device s22 \
  --shadow \
  --intro zoom \
  --bg-gradient "#000:#1a1a2e" \
  --logo logo.png \
  --text "My App Demo" \
  --progress-bar \
  --platform youtube-short \
  --hw
```

## Commands

### `render` - Main rendering command

```bash
dmockup render <VIDEO> [OPTIONS]
```

<details>
<summary><strong>All Options</strong></summary>

**Device & Layout:**
- `-d, --device` - Device frame name (default: s22)
- `-f, --fill` - Fill percentage 0.5-1.0 (default: 0.9)

**Output:**
- `-o, --output` - Output file path
- `--format` - Output format: mp4, webm, gif, mov

**Background:**
- `-bg, --bg-color` - Background color (hex)
- `--bg-image` - Background image path
- `--bg-video` - Background video path
- `--bg-gradient` - Gradient colors (#color1:#color2)
- `--gradient-dir` - vertical, horizontal, diagonal, radial
- `--bg-blur` - Use blurred video as background
- `--blur-strength` - Blur strength 1-50

**Video Processing:**
- `-ss, --start` - Start timestamp
- `-to, --end` - End timestamp
- `-t, --duration` - Duration
- `--speed` - Playback speed 0.25-4.0
- `--reverse` - Reverse playback
- `--fps` - Output frame rate
- `-r, --resolution` - Resolution preset
- `--loop` - Create looping video

**Effects:**
- `--shadow` - Add drop shadow
- `--shadow-opacity` - Shadow opacity 0-1
- `--shadow-blur` - Shadow blur radius
- `--shadow-offset` - Shadow offset pixels
- `--glow` - Add glow effect
- `--reflection` - Add reflection
- `--corner-radius` - Rounded corners
- `--border` - Border (e.g., "2px #fff")
- `--rotate` - Rotation degrees

**Animation:**
- `--intro` - Intro animation type
- `--intro-duration` - Intro duration seconds
- `--outro` - Outro animation type
- `--outro-duration` - Outro duration seconds

**Branding:**
- `--logo` - Logo image path
- `--logo-position` - Logo position
- `--logo-scale` - Logo scale 0.05-0.5
- `--watermark` - Watermark text
- `--text` - Text overlay
- `--text-position` - Text position
- `--text-size` - Text size
- `--cta` - Call-to-action text
- `--progress-bar` - Show progress bar

**Audio:**
- `--music` - Background music file
- `--music-volume` - Music volume 0-1
- `--mute` - Mute original audio
- `--voiceover` - Voiceover audio file

**Quality & Export:**
- `-q, --quality` - low, medium, high, ultra
- `--crf` - Custom CRF 0-51
- `-p, --platform` - Target platform preset
- `--max-size` - Max file size in MB
- `--hw` - Hardware acceleration

**Presets:**
- `--preset` - Use saved preset
- `--save-preset` - Save settings as preset

**Developer:**
- `--dry-run` - Show FFmpeg command only
- `--preview` - Render first 5 seconds
- `--debug` - Show debug overlay
- `-v, --verbose` - Show FFmpeg output
- `--json` - JSON output
- `--thumbnail` - Export thumbnail

</details>

### `batch` - Process multiple videos

```bash
dmockup batch ./videos/ --parallel 4 --preset tiktok
```

### `watch` - Auto-process new files

```bash
dmockup watch ./inbox/ --preset professional
```

### `devices list` - List available devices

```bash
dmockup devices list
```

### `devices add` - Add a new device frame

```bash
dmockup devices add ~/Downloads/pixel9.png --name pixel9
```

### `preset list` - List all presets

```bash
dmockup preset list
```

### `preset show` - Show preset details

```bash
dmockup preset show tiktok
```

### `history` - View render history

```bash
dmockup history --limit 20
```

### `info` - Analyze media file

```bash
dmockup info video.mp4
```

### `interactive` - TUI wizard

```bash
dmockup interactive
```

## Presets

Built-in presets optimized for different use cases:

| Preset | Description |
|--------|-------------|
| `default` | Clean default settings |
| `professional` | Shadow effect, high quality |
| `social-dark` | Dark theme with animations |
| `social-light` | Light theme with shadow |
| `tiktok` | Optimized for TikTok (1080x1920) |
| `youtube-short` | Optimized for YouTube Shorts |
| `instagram-reel` | Gradient background, optimized |
| `instagram-story` | Story format optimized |
| `discord` | Compressed for 25MB limit |
| `minimal` | Clean white background |
| `showcase` | Full effects for app demos |

### Create Custom Presets

```bash
# Save current settings as preset
dmockup render video.mp4 --shadow --intro fade --save-preset my-style

# Use later
dmockup render other.mp4 --preset my-style
```

## Platform Settings

| Platform | Resolution | Max Duration | Max Size |
|----------|------------|--------------|----------|
| TikTok | 1080x1920 | 3 min | 287 MB |
| YouTube Shorts | 1080x1920 | 60s | - |
| Instagram Reel | 1080x1920 | 90s | - |
| Instagram Story | 1080x1920 | 60s | - |
| Discord | 1280x720 | - | 25 MB |
| Twitter | 1280x720 | - | 512 MB |

## Adding Device Frames

1. Add PNG images to `~/.local/share/dejitech-mockup/assets/` or `./assets/`
2. Name files descriptively: `iphone15.png`, `pixel8.png`
3. They're automatically discovered

```bash
# Quick add
dmockup devices add ~/Downloads/device-frame.png --name mydevice

# Use it
dmockup render video.mp4 --device mydevice
```

## Hardware Acceleration

For AMD GPUs with VA-API:

```bash
# Verify VA-API works
vainfo

# Use in renders
dmockup render video.mp4 --hw
```

## Examples

```bash
# Quick social media post
dmockup render demo.mp4 --preset tiktok --hw

# Professional app showcase
dmockup render app-demo.mp4 \
  --shadow \
  --reflection \
  --intro zoom \
  --outro fade-out \
  --logo company-logo.png \
  --text "New Feature Demo" \
  --progress-bar \
  --quality ultra

# Batch process with branding
dmockup batch ./recordings/ \
  --preset professional \
  --parallel 4

# Compressed for Discord
dmockup render clip.mp4 --platform discord --max-size 25

# Debug without rendering
dmockup render test.mp4 --dry-run
```

## License

MIT License - see LICENSE file for details.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/dejitech">DejiTech</a>
</p>
