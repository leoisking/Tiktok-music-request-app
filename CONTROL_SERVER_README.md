# Standalone Control Panel Server 🎛️

## What Is This?

A **separate control panel server** that runs independently from your main widget server!

```
┌─────────────────────────────────────┐
│  Main Widget Server (live_widget.py)│
│  Port: 5000                         │
│  Cloudflare Tunnel: YOUR-URL.com    │
│  ├─ / → Widget (for TikTok)         │
│  └─ /control → Control Panel        │
└─────────────────────────────────────┘
         ▲
         │ Socket.IO Connection
         │
┌─────────────────────────────────────┐
│  Control Panel Server               │
│  (control_server.py)                │
│  Port: 5001                         │
│  Local Only: http://localhost:5001  │
│  ├─ Connects to main server         │
│  ├─ Relays commands                 │
│  └─ Receives updates                │
└─────────────────────────────────────┘
```

## Why Use This?

### Problem
- Your main widget is on Cloudflare (for TikTok Studio)
- You want a local-only control panel (not exposed to internet)
- You don't want to access `/control` through Cloudflare

### Solution
- Main widget stays on port 5000 + Cloudflare (for viewers)
- Control panel runs on port 5001 locally (just for you)
- They communicate via Socket.IO

## Quick Start

### Step 1: Start Your Main Widget Server
```batch
start_with_tunnel.bat
```

This starts on port 5000 and creates a Cloudflare tunnel.

### Step 2: Start Control Panel Server
```batch
start_control_panel.bat
```

Follow the prompts:
- If main widget is on Cloudflare, enter the URL
- If main widget is local, just press Enter
- Set a password if you want

### Step 3: Open Control Panel
Open your browser to:
```
http://localhost:5001
```

Done! 🎉

## How It Works

### Architecture

```
TikTok Studio
    ↓
https://your-tunnel.trycloudflare.com/  (Widget)
    ↓
live_widget.py (Port 5000)
    ↑
    │ Socket.IO
    ↓
control_server.py (Port 5001)
    ↑
    │ Browser
    ↓
You (http://localhost:5001)
```

### Communication Flow

1. **Control Panel → Control Server**: You click "Clear Queue"
2. **Control Server → Main Server**: Forwards the command via Socket.IO
3. **Main Server**: Processes the command, clears queue
4. **Main Server → Control Server**: Sends update back
5. **Control Server → Control Panel**: Updates your browser

## Features

### ✅ What Works
- Clear Queue button
- Reset Votes button
- Toggle panel visibility
- Real-time queue count
- Real-time skip votes
- Connection status indicator

### ✅ Benefits
- **Secure**: Control panel not exposed to internet
- **Separate**: Main widget stays on Cloudflare
- **Simple**: Just access localhost:5001
- **Reliable**: Direct connection to main server

## Configuration

### Environment Variables

```batch
# Control panel port (default: 5001)
set CONTROL_PORT=5001

# Main widget server URL
set WIDGET_SERVER_URL=http://localhost:5000
# OR for Cloudflare:
set WIDGET_SERVER_URL=https://your-tunnel.trycloudflare.com

# Optional password protection
set CONTROL_PASSWORD=YourSecurePassword123
```

### Example Configurations

#### Local Testing
```batch
set CONTROL_PORT=5001
set WIDGET_SERVER_URL=http://localhost:5000
start_control_panel.bat
```

#### Cloudflare Production
```batch
set CONTROL_PORT=5001
set WIDGET_SERVER_URL=https://abc-xyz.trycloudflare.com
set CONTROL_PASSWORD=MySecretPassword
start_control_panel.bat
```

## Usage

### Starting Both Servers

**Terminal 1:**
```batch
start_with_tunnel.bat
```
Copy the Cloudflare URL.

**Terminal 2:**
```batch
start_control_panel.bat
```
Paste the Cloudflare URL when prompted.

**Browser:**
```
http://localhost:5001
```

### Stopping Servers

Press `Ctrl+C` in each terminal window.

## Troubleshooting

### ❌ "Not connected to widget server"

**Problem**: Control panel can't reach main widget

**Solutions:**
1. Check if `live_widget.py` is running
2. Verify `WIDGET_SERVER_URL` is correct
3. For Cloudflare, make sure tunnel is active
4. Check firewalls aren't blocking connections

### ❌ "Port 5001 already in use"

**Problem**: Something is using port 5001

**Solutions:**
1. Change port: `set CONTROL_PORT=5002`
2. Find and stop the other process
3. Restart your computer

### ❌ "Cannot clear queue / reset votes"

**Problem**: Commands aren't working

**Solutions:**
1. Check connection status (should be green)
2. Verify widget server is running
3. If password is set, make sure it matches
4. Check browser console (F12) for errors

### ❌ "Control panel shows old data"

**Problem**: Not receiving updates

**Solutions:**
1. Refresh the page (F5)
2. Check connection indicator
3. Restart control panel server
4. Check main widget server logs

## Advanced Usage

### Running on Different Computer

You can run the control panel on a different computer on your LAN:

**On Widget Server Computer:**
```batch
# Find your IP address
ipconfig
# Look for IPv4 Address (e.g., 192.168.1.100)
```

**On Control Panel Computer:**
```batch
set WIDGET_SERVER_URL=http://192.168.1.100:5000
start_control_panel.bat
```

Open: `http://localhost:5001`

### Multiple Control Panels

You can have multiple control panel windows open:
- One on your streaming PC
- One on your phone/tablet (via LAN)
- One on another computer

All will receive the same updates!

### Custom Port

```batch
set CONTROL_PORT=8080
python control_server.py
```

Then access: `http://localhost:8080`

## Security

### Local Network Only (Default)
- Control panel binds to `0.0.0.0` but only accessible on LAN
- No internet exposure
- Safe for streaming setup

### Password Protection
```batch
set CONTROL_PASSWORD=StrongPassword123
start_control_panel.bat
```

The server validates all commands against this password.

### Best Practices
- ✅ Use password for extra protection
- ✅ Only expose main widget (5000) to internet
- ✅ Keep control panel (5001) local only
- ❌ Don't expose port 5001 to internet
- ❌ Don't use simple passwords like "123456"

## Files

| File | Purpose |
|------|---------|
| `control_server.py` | Main control panel server |
| `start_control_panel.bat` | Launcher script |
| `control.html` | Control panel UI (served by server) |
| `live_widget.py` | Main widget server (port 5000) |

## Comparison: Built-in vs Standalone

### Built-in Control Panel
```
URL: https://your-tunnel.trycloudflare.com/control
Pros: No extra setup, same server
Cons: Exposed to internet, requires password
```

### Standalone Control Panel (This)
```
URL: http://localhost:5001
Pros: Local only, more secure, separate concerns
Cons: Need to run two servers
```

## Commands Reference

### Start Control Panel Server
```batch
start_control_panel.bat
```

### Start with Custom Settings
```batch
set CONTROL_PORT=5002
set WIDGET_SERVER_URL=https://your-tunnel.com
set CONTROL_PASSWORD=secret
python control_server.py
```

### Check If Running
```batch
curl http://localhost:5001
```

### View Logs
Check console output in the terminal window.

## FAQ

### Q: Do I need this if I'm using the built-in control panel?
**A:** No, this is optional. Use it if you want a local-only control panel.

### Q: Can I use both at the same time?
**A:** Yes! You can access both:
- `https://your-tunnel.com/control` (built-in)
- `http://localhost:5001` (standalone)

### Q: Does this work without Cloudflare?
**A:** Yes! Set `WIDGET_SERVER_URL=http://localhost:5000`

### Q: Can I access this from my phone?
**A:** Yes, if on same WiFi:
1. Find your PC's IP (e.g., 192.168.1.100)
2. Open: `http://192.168.1.100:5001` on phone

### Q: What if the widget server restarts?
**A:** Control panel automatically reconnects!

## Support

If you have issues:
1. Check both servers are running
2. Verify URLs in configuration
3. Check browser console (F12)
4. Look at terminal logs
5. Try restarting both servers

## Related Documentation
- `README.md` - Main widget documentation
- `CONTROL_PANEL_GUIDE.md` - Built-in control panel
- `TIKTOK_STUDIO_QUICKSTART.md` - TikTok setup
- `CLOUDFLARE_TUNNEL_SETUP.md` - Cloudflare help

---

**Remember**: This is for local control only. Your viewers still see the widget through Cloudflare! 🎉