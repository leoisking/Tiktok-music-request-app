# TikTok Live Widget - Song Requests & Skip Voting

A professional, real-time overlay widget for TikTok Live streams that displays song requests and skip voting with full mobile optimization.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

### Core Functionality
- 🎵 **Song Request Queue** - Viewers request songs with `!req Song by Artist`
- ⏭️ **Skip Voting System** - Democratic skip voting with `!skip` command
- 💬 **Real-time Updates** - Instant display via WebSocket connections
- 🎨 **Beautiful UI** - Glass morphism design with animations
- 📱 **Mobile Optimized** - Fully responsive for portrait & landscape viewing
- ♿ **Accessible** - WCAG 2.1 compliant with ARIA labels

### Advanced Features
- 🔒 **Rate Limiting** - Prevents spam and abuse
- 👥 **Moderator Controls** - Special commands for stream moderators
- 🎯 **Demo Mode** - Works offline for testing
- 🔄 **Auto-Cleanup** - Memory-efficient with automatic queue management
- 📊 **Professional Logging** - Comprehensive error tracking
- 🛡️ **Security** - CSP headers, input validation, localhost-only control panel

## 🚀 Quick Start

> **💡 For TikTok Studio Users:** TikTok Studio requires HTTPS URLs. See [Cloudflare Tunnel Setup](CLOUDFLARE_TUNNEL_SETUP.md) for hosting instructions.

### Prerequisites
```bash
Python 3.8 or higher
pip (Python package manager)
```

### Installation

1. **Clone or download this repository**

2. **Install dependencies**
```bash
pip install flask flask-socketio TikTokLive
```

3. **Set your chat source**
```bash
# Windows
set CHAT_SOURCE=tiktok
set TIKTOK_USER=yourusername

# Mac/Linux
export CHAT_SOURCE=tiktok
export TIKTOK_USER=yourusername
```

For Twitch:
```bash
# Windows
set CHAT_SOURCE=twitch
set TWITCH_CHANNEL=yourchannel

# Mac/Linux
export CHAT_SOURCE=twitch
export TWITCH_CHANNEL=yourchannel
```

4. **Run the widget**
```bash
python live_widget.py
```

5. **Add to OBS or TikTok Studio**

   **For OBS Studio:**
   - Open OBS Studio
   - Add a "Browser" source
   - URL: `http://127.0.0.1:5000`
   - Width: 400, Height: 800 (or customize)
   - ✅ Check "Shutdown source when not visible"
   - ✅ Check "Refresh browser when scene becomes active"

   **For TikTok Studio:**
   - Follow the [Cloudflare Tunnel Setup Guide](CLOUDFLARE_TUNNEL_SETUP.md)
   - Use the HTTPS tunnel URL in TikTok Studio overlay settings

## 🎮 Commands

### Viewer Commands
| Command | Description | Example |
|---------|-------------|---------|
| `!req [song]` | Request a song | `!req Enter Sandman by Metallica` |
| `!skip` | Vote to skip current song | `!skip` |

### Moderator Commands
| Command | Description |
|---------|-------------|
| `!clear` | Clear all song requests |
| `!reset` | Reset skip votes |
| `!next` | Same as !reset |

### Control Panel
Access at `http://127.0.0.1:5000/control` (localhost only)
- Clear queue
- Reset skip votes
- Toggle panel visibility

## ⚙️ Configuration

### Environment Variables

```bash
# Chat Source
CHAT_SOURCE=tiktok                    # tiktok, twitch, or both

# Required for TikTok mode (CHAT_SOURCE=tiktok/both)
TIKTOK_USER=yourusername              # Your TikTok username

# Required for Twitch mode (CHAT_SOURCE=twitch/both)
TWITCH_CHANNEL=yourchannel            # Twitch channel name (without #)
TWITCH_BOT_USERNAME=yourbotname       # Optional: Twitch account name for authenticated IRC
TWITCH_OAUTH_TOKEN=oauth:xxxxxxxx     # Optional: OAuth token for authenticated IRC

# Moderators (comma-separated)
MOD_LIST=mod1,mod2,mod3               # Users with mod permissions

# Queue Settings
QUEUE_MAX=200                         # Maximum queue size
MAX_REQUEST_LEN=200                   # Max characters per request
MAX_NAME_LEN=50                       # Max username length

# Skip Voting
SKIP_THRESHOLD=10                     # Votes needed to skip

# Rate Limiting
RATE_LIMIT_MAX=5                      # Max actions per window
RATE_LIMIT_WINDOW=30                  # Rate limit window (seconds)

# Chat History
CHAT_HISTORY_MAX=20                   # Max stored messages
CHAT_HISTORY_TTL=60                   # Message lifetime (seconds)

# CORS (for remote access)
ALLOWED_ORIGINS=http://127.0.0.1:5000 # Comma-separated allowed origins

# Debug Mode
LIVE_WIDGET_DEBUG=1                   # Enable verbose logging

# Cloudflare Tunnel / Remote Access
HOST=0.0.0.0                          # Listen on all interfaces
PORT=5000                             # Server port
CONTROL_PASSWORD=your_secure_pass     # Required for remote control panel access
```

### Example Configuration
```bash
# Windows (cmd)
set TIKTOK_USER=midlifedisaster69
set MOD_LIST=admin,helper1,helper2
set SKIP_THRESHOLD=8
set QUEUE_MAX=150

# Mac/Linux (bash)
export TIKTOK_USER=midlifedisaster69
export MOD_LIST=admin,helper1,helper2
export SKIP_THRESHOLD=8
export QUEUE_MAX=150

# For Cloudflare Tunnel
export HOST=0.0.0.0
export ALLOWED_ORIGINS=*
export CONTROL_PASSWORD=MySecurePassword123
```

## 🌐 Cloudflare Tunnel (TikTok Studio)

TikTok Studio requires HTTPS URLs. Host your widget through Cloudflare Tunnel:

### Quick Setup
```bash
# 1. Install cloudflared
winget install Cloudflare.cloudflared

# 2. Configure widget for remote access
export HOST=0.0.0.0
export ALLOWED_ORIGINS=*
export CONTROL_PASSWORD=YourSecurePassword
export TIKTOK_USER=yourusername

# 3. Start widget
python live_widget.py

# 4. Start tunnel (in another terminal)
cloudflared tunnel --url http://localhost:5000
```

You'll get a URL like: `https://random-name.trycloudflare.com`

**Use this URL in TikTok Studio overlay settings!**

📚 **Full Guide:** See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for:
- Named tunnels (permanent URLs)
- Custom domains
- Running as service
- Security best practices
- Troubleshooting

## 📱 Mobile Optimization

The widget is **fully optimized for mobile viewing**:

### Portrait Mode (< 768px)
- ✅ Larger text for readability
- ✅ Bigger touch targets (44px minimum)
- ✅ Optimized spacing and padding
- ✅ Higher contrast for outdoor viewing
- ✅ No performance-heavy animations
- ✅ Responsive font scaling

### Landscape Mode
- ✅ Compact layout for limited height
- ✅ Adjusted proportions
- ✅ Maintained readability

### Small Devices (< 375px)
- ✅ Further optimized for tiny screens
- ✅ Adjusted skip meter size
- ✅ Compressed spacing

### Touch Devices
- ✅ 44px minimum touch targets
- ✅ No hover effects
- ✅ Tap-friendly buttons
- ✅ Disabled text selection on UI elements

## 🎨 Customization

### OBS Browser Source Settings

**Recommended for Desktop Streams:**
- Width: 400px
- Height: 800px
- Custom CSS: (optional)

**Recommended for Mobile/Vertical Streams:**
- Width: 360px
- Height: 640px
- Custom CSS: (optional)

### Custom Styling
Add custom CSS in OBS browser source:
```css
/* Example: Move widget to right side */
.widget-wrapper {
    margin-left: auto;
    max-width: 380px;
}

/* Example: Change panel opacity */
.panel-card {
    background: rgba(8, 8, 8, 0.85) !important;
}

/* Example: Larger text */
.song-name {
    font-size: 16px !important;
}
```

## 🔒 Security Features

- **Content Security Policy** - Restricts resource loading
- **Input Validation** - All user inputs sanitized
- **Rate Limiting** - Prevents spam and abuse
- **Localhost-Only Control** - Admin panel restricted
- **No Sensitive Data Exposure** - Safe error messages
- **Auto-Cleanup** - Prevents memory exhaustion

## 📊 Monitoring & Logs

### Log Levels
- `INFO` - Normal operations (requests, skips, connections)
- `WARNING` - Rate limits, invalid requests
- `ERROR` - Exceptions and failures

### Example Logs
```
2024-01-01 12:00:00 - INFO - Request: Enter Sandman by Metallica (from RockFan42)
2024-01-01 12:00:05 - INFO - SKIP from NightOwl (5/10)
2024-01-01 12:00:10 - WARNING - Rate limited request from SpamUser
2024-01-01 12:00:15 - INFO - SKIP THRESHOLD REACHED! (10/10)
```

### Enable Debug Mode
```bash
export LIVE_WIDGET_DEBUG=1
python live_widget.py
```

## 🐛 Troubleshooting

### Widget Not Showing in OBS
1. Check URL: `http://127.0.0.1:5000`
2. Verify server is running (check console)
3. Try refreshing the browser source
4. Check OBS browser source logs

### Not Connecting to TikTok
```
✓ Normal - Widget waits until you go live
✓ Check console: "Not live yet. Server staying open..."
✓ Server remains accessible even when not live
```

### Rate Limit Errors
Users see: "Rate limited (too many requests)"
- Default: 5 actions per 30 seconds
- Adjust with `RATE_LIMIT_MAX` and `RATE_LIMIT_WINDOW`

### Memory Issues
```bash
# Reduce limits
export QUEUE_MAX=100
export CHAT_HISTORY_MAX=10
```

### Mobile Not Readable
1. Check viewport meta tag is present
2. Clear browser cache
3. Test in browser first: `http://127.0.0.1:5000`
4. Verify responsive styles loaded

## 🔧 Development

### Project Structure
```
flask-tiktok-socket-setup/
├── index.html           # Main widget UI
├── control.html         # Moderator control panel
├── live_widget.py       # Backend server
├── IMPROVEMENTS.md      # Technical documentation
├── QUICK_REFERENCE.md   # User guide
└── README.md           # This file
```

### Running Tests
```bash
# Test without TikTok (demo mode)
python live_widget.py
# Open http://127.0.0.1:5000 after 4 seconds
```

### Contributing
1. Test changes with demo mode
2. Verify mobile responsiveness
3. Check accessibility with screen reader
4. Ensure logs are clear and helpful

## 📈 Performance

### Resource Usage
- **Memory**: ~50-100MB (typical)
- **CPU**: <5% (idle), ~10% (active)
- **Network**: <1 Mbps

### Optimizations
- Auto-cleanup every 10 minutes
- Rate limiter cleanup every 5 minutes
- Efficient data structures
- No animations on mobile
- Memory-bounded queues

## 🌟 What's New in v2.0

### Major Improvements
- ✅ **Fixed HTML layout** - No more broken panels
- ✅ **Mobile responsive** - Optimized for all screen sizes
- ✅ **Better security** - CSP headers, enhanced validation
- ✅ **Accessibility** - WCAG 2.1 compliant
- ✅ **Professional logging** - Structured, timestamped logs
- ✅ **Skip command** - Changed to `!skip` (prevents accidents)
- ✅ **Memory leaks fixed** - Proper cleanup everywhere
- ✅ **Connection feedback** - Visual status banners

### Breaking Changes
- ⚠️ Skip command now requires `!skip` instead of just `skip`

See `IMPROVEMENTS.md` for complete technical details.

## 📚 Additional Documentation

- **[CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)** - Complete Cloudflare Tunnel guide for TikTok Studio
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - Full list of technical improvements
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick tips and common tasks

## 🤝 Support

### Common Issues
1. **"TIKTOK_USER is required"** - Set environment variable
2. **"Access denied"** - Control panel only works on localhost
3. **"Widget file not found"** - Ensure `index.html` exists

### Getting Help
1. Check logs for errors
2. Enable debug mode: `LIVE_WIDGET_DEBUG=1`
3. Review documentation files
4. Test in demo mode first
5. For Cloudflare Tunnel issues, see [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)

## 📄 License

MIT License - Feel free to use and modify for your streams!

## 🎯 Best Practices

### For Streamers
1. ✅ Test widget before going live
2. ✅ Set moderators in `MOD_LIST`
3. ✅ Use reasonable skip threshold (8-15)
4. ✅ Monitor logs during stream
5. ✅ Keep control panel open on second monitor

### For Viewers on Mobile
1. ✅ Portrait mode recommended for best experience
2. ✅ Use good lighting for readability
3. ✅ Zoom if needed (text is responsive)
4. ✅ Commands are simple: `!req` and `!skip`

### For Production (Cloudflare Tunnel)
1. ✅ Use named tunnels (not quick tunnels)
2. ✅ Set strong `CONTROL_PASSWORD`
3. ✅ Set up process manager (systemd/supervisor)
4. ✅ Monitor logs with aggregation tool
5. ✅ Keep cloudflared and packages updated
6. ✅ Consider restricting `ALLOWED_ORIGINS`

## 🚀 Quick Commands Reference

```bash
# Start widget
python live_widget.py

# With custom settings
export TIKTOK_USER=yourname
export SKIP_THRESHOLD=8
python live_widget.py

# For Cloudflare Tunnel
export HOST=0.0.0.0 ALLOWED_ORIGINS=* CONTROL_PASSWORD=MyPass
python live_widget.py
cloudflared tunnel --url http://localhost:5000

# Debug mode
export LIVE_WIDGET_DEBUG=1
python live_widget.py

# Check if running
curl http://127.0.0.1:5000
```

## 🎨 Screenshot

**Main Widget Features:**
- 🎵 Song request queue with animations
- ⏭️ Circular skip meter with progress
- 📊 Live skip counter and progress bar
- 👥 Recent skipper names
- 🔴 Live status indicators
- ⚡ Real-time updates

**Mobile View:**
- Larger, more readable text
- Optimized spacing for touch
- Better contrast for outdoor use
- Responsive to screen size

---

**Made with ❤️ for TikTok Live streamers**

**Version 2.0** | Last Updated: 2024
