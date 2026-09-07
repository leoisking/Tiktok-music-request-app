# Dual Cloudflare Tunnel Setup Guide 🚀

## Overview

Run **TWO separate Cloudflare tunnels**:
1. **Widget Tunnel** (Port 5000) - For TikTok Studio and viewers
2. **Control Panel Tunnel** (Port 5001) - For you and trusted moderators

```
┌─────────────────────────────────────────┐
│  Main Widget Server (live_widget.py)    │
│  Port: 5000                             │
│  Cloudflare: https://widget-abc.com     │
│  ├─ /        → Widget (TikTok overlay)  │
│  └─ /control → Built-in control (unused)│
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Control Panel Server (control_server.py)│
│  Port: 5001                             │
│  Cloudflare: https://control-xyz.com    │
│  └─ /        → Control Panel            │
│     ↓ Connects to main widget via       │
│       Socket.IO                         │
└─────────────────────────────────────────┘
```

## Why Use Dual Tunnels?

### Benefits
- ✅ **Separate URLs**: Widget and control panel have different URLs
- ✅ **Better Security**: Control URL can be private, widget URL is public
- ✅ **Independent Access**: Control panel won't affect widget performance
- ✅ **Easy Sharing**: Share control URL with moderators/co-streamers
- ✅ **Clean Architecture**: Separation of concerns

### Use Cases
- Share control access with a co-streamer
- Access control panel from phone/tablet remotely
- Keep control panel URL private while widget is public
- Run control panel from a different location

## Quick Start - One Command!

### Easiest Way: Start Everything
```batch
start_everything.bat
```

This will:
1. Start widget server (port 5000)
2. Start widget Cloudflare tunnel
3. Start control panel server (port 5001)
4. Start control panel Cloudflare tunnel
5. Show you both URLs

**You get TWO Cloudflare URLs!**

## Manual Setup (Step by Step)

### Step 1: Start Widget Server with Tunnel
```batch
start_with_tunnel.bat
```

You'll see:
```
https://happy-cloud-123.trycloudflare.com
```
**This is your WIDGET URL** - Copy it!

### Step 2: Start Control Panel with Tunnel
Open a NEW terminal window:
```batch
start_control_with_tunnel.bat
```

When prompted:
```
Widget Server URL: https://happy-cloud-123.trycloudflare.com
```
Paste the URL from Step 1.

You'll see:
```
https://excited-mountain-456.trycloudflare.com
```
**This is your CONTROL PANEL URL** - Copy it!

### Step 3: Use Your URLs

**For TikTok Studio:**
```
https://happy-cloud-123.trycloudflare.com/
```

**For Your Control Panel:**
```
https://excited-mountain-456.trycloudflare.com/
```

**With Password:**
```
https://excited-mountain-456.trycloudflare.com/?password=YOUR_PASSWORD
```

## Configuration

### Environment Variables

```batch
# Widget Server
set TIKTOK_USER=yourname
set PORT=5000
set SKIP_THRESHOLD=10

# Control Panel
set CONTROL_PORT=5001
set CONTROL_PASSWORD=YourSecurePassword123

# Run the script
start_everything.bat
```

### Recommended Settings

**For Security:**
```batch
set CONTROL_PASSWORD=StrongPassword123
```
Always set a password when using Cloudflare tunnels!

**Custom Ports:**
```batch
set PORT=8000
set CONTROL_PORT=8001
```

## URLs Summary

After starting everything, you'll have:

| Service | Local URL | Cloudflare URL | Who Uses It |
|---------|-----------|----------------|-------------|
| **Widget** | `http://localhost:5000/` | `https://abc.trycloudflare.com/` | TikTok Studio, Viewers |
| **Control Panel** | `http://localhost:5001/` | `https://xyz.trycloudflare.com/` | You, Moderators |

## Access Methods

### Widget (TikTok Overlay)
```
Local:      http://localhost:5000/
Cloudflare: https://abc.trycloudflare.com/
```
Add the Cloudflare URL to TikTok Studio.

### Control Panel
```
Local:      http://localhost:5001/
Cloudflare: https://xyz.trycloudflare.com/
With Pass:  https://xyz.trycloudflare.com/?password=YOUR_PASSWORD
```
Open in your browser to control the stream.

## Common Workflows

### Workflow 1: Solo Streamer
```
1. Run: start_everything.bat
2. Copy Widget URL → Add to TikTok Studio
3. Copy Control URL → Open in your browser
4. Go live! 🎉
```

### Workflow 2: Co-Streaming
```
1. Run: start_everything.bat
2. Copy Widget URL → Add to TikTok Studio
3. Copy Control URL → Share with co-streamer
4. Both can control the stream! 🎉
```

### Workflow 3: Mobile Control
```
1. Run: start_everything.bat on PC
2. Copy Widget URL → Add to TikTok Studio
3. Copy Control URL → Open on phone
4. Control stream from anywhere! 🎉
```

## Troubleshooting

### ❌ "Cannot connect to widget server"

**Problem**: Control panel can't reach widget server

**Solutions:**
1. Make sure widget server started first
2. Check the widget URL is correct
3. Wait a few seconds for tunnel to establish
4. Try localhost URL: `http://localhost:5000`

### ❌ "Two tunnels showing same URL"

**Problem**: Both tunnels have same URL (rare)

**Solutions:**
1. Stop both tunnels (Ctrl+C)
2. Restart them one at a time
3. Cloudflare will assign different URLs

### ❌ "Control panel not responding"

**Problem**: Commands don't work

**Solutions:**
1. Check connection status indicator (should be green)
2. Verify widget server is running
3. Check password matches if set
4. Try refreshing the page (F5)

### ❌ "Too many windows open"

**Problem**: Confusing terminal windows

**Solutions:**
1. Use `start_everything.bat` instead
2. Name your windows clearly
3. Check Task Manager for running processes

## Security Best Practices

### DO ✅
- Set `CONTROL_PASSWORD` for remote access
- Use strong passwords (12+ characters)
- Only share control URL with trusted people
- Keep control URL private
- Change password regularly

### DON'T ❌
- Don't share control URL publicly
- Don't use simple passwords like "123456"
- Don't run without password on public WiFi
- Don't share widget and control URLs together

## Advanced: Running on Different Machines

### Widget on PC 1, Control on PC 2

**PC 1 (Widget):**
```batch
start_with_tunnel.bat
Copy widget URL: https://abc.trycloudflare.com
```

**PC 2 (Control Panel):**
```batch
set WIDGET_SERVER_URL=https://abc.trycloudflare.com
start_control_with_tunnel.bat
Copy control URL: https://xyz.trycloudflare.com
```

Now PC 1 runs widget, PC 2 controls it!

## Stopping Everything

### Manual Stop
Press `Ctrl+C` in each terminal window.

### Task Manager
1. Open Task Manager
2. Find processes:
   - `python.exe` (widget)
   - `python.exe` (control)
   - `cloudflared.exe` (tunnels)
3. End all related processes

### Clean Shutdown
Always use `Ctrl+C` for clean shutdown. This ensures:
- Connections close properly
- Logs are saved
- TikTok live disconnects cleanly

## Batch Files Reference

| File | Purpose | When to Use |
|------|---------|-------------|
| `start_everything.bat` | Start both with tunnels | **Recommended** - Easiest! |
| `start_with_tunnel.bat` | Widget only | Testing widget alone |
| `start_control_with_tunnel.bat` | Control only | Separate control setup |
| `start_control_panel.bat` | Control (no tunnel) | Local-only control |

## FAQ

### Q: Do I need two Cloudflare accounts?
**A:** No! Both tunnels use the same Cloudflare account.

### Q: Can I use the same URL for both?
**A:** No, each tunnel gets its own unique URL.

### Q: Do both servers need to run on the same PC?
**A:** No! They can run on different computers.

### Q: What if I only want one tunnel?
**A:** Use `start_with_tunnel.bat` and access control at `/control` endpoint.

### Q: Can I have multiple control panels?
**A:** Yes! The control panel URL can be opened on multiple devices.

### Q: What happens if one tunnel crashes?
**A:** The other keeps running. Restart the crashed one.

### Q: How much bandwidth does this use?
**A:** Minimal. Cloudflare tunnels are very efficient.

## Cost

**Cloudflare Tunnels: 100% FREE** ✨
- No credit card required
- Unlimited tunnels
- No bandwidth limits
- No time limits

## Example Output

When you run `start_everything.bat`, you'll see:

```
========================================
  BOTH SERVICES ARE RUNNING!
========================================

[1] Widget Server: http://localhost:5000
    Cloudflare URL: https://happy-cloud-123.trycloudflare.com
    Purpose: For TikTok Studio overlay

[2] Control Panel: http://localhost:5001
    Cloudflare URL: https://excited-mountain-456.trycloudflare.com
    Purpose: For you to manage the stream

========================================
```

Copy both URLs and you're ready to stream!

## Related Documentation

- `README.md` - Main project documentation
- `CONTROL_SERVER_README.md` - Control server details
- `CLOUDFLARE_TUNNEL_SETUP.md` - Cloudflare setup help
- `TIKTOK_STUDIO_QUICKSTART.md` - TikTok Studio guide

## Support

Having issues? Check:
1. Both servers are running (check Task Manager)
2. Both tunnels are active (check terminal windows)
3. URLs are copied correctly
4. Password is correct (if set)
5. Firewall isn't blocking connections

---

**Ready to stream with dual tunnels? Run `start_everything.bat` and go live! 🎉**