# Control Panel Guide

## Quick Start

### Option 1: Using the Batch File (Easiest - Windows)

1. **Double-click** `open_control_panel.bat`
2. **Choose your connection method:**
   - **Local Server**: Opens `http://localhost:5000/control`
   - **Cloudflare Tunnel**: You provide the tunnel URL (script adds `/control`)
   - **Manual Entry**: Type the full control URL yourself
3. **Enter your Cloudflare URL** (if applicable)
   - Example: `https://abc-xyz-123.trycloudflare.com`
   - The script automatically adds `/control` to the end
4. **Enter password** (if you set `CONTROL_PASSWORD` environment variable)
5. The control panel opens in your default browser

### Option 2: Direct Browser Access

Simply open your browser and navigate to:

**For localhost:**
```
http://localhost:5000/control
```

**For Cloudflare tunnel:**
```
https://your-tunnel.trycloudflare.com/control
```

**With password:**
```
https://your-tunnel.trycloudflare.com/control?password=YOUR_PASSWORD
```

### Option 3: From Any Device

The control panel is served by your Flask server, so you can access it from any device:

1. Start your server with `start_with_tunnel.bat`
2. Copy the Cloudflare tunnel URL
3. On any device (phone, tablet, laptop), open:
   ```
   https://your-tunnel.trycloudflare.com/control
   ```
4. Add `?password=YOUR_PASSWORD` if needed

## Features

### Real-Time Monitoring
- **Queue Count**: See how many song requests are in the queue
- **Skip Votes**: Monitor current skip votes vs threshold
- **Connection Status**: Shows if you're connected to the server

### Panel Visibility Controls
Toggle what your audience sees:
- ✅ **Show Requests Panel** - Display/hide the song request queue
- ✅ **Show Chat Messages** - Display/hide live chat messages
- ✅ **Show Skip Meter** - Display/hide the skip voting panel

### Quick Actions
- **Clear Queue**: Remove all song requests from the queue
- **Reset Votes**: Reset skip votes back to 0

## Connection Examples

### Localhost (Testing)
```
URL: http://localhost:5000/control
Password: (append ?password=XXX if CONTROL_PASSWORD is set)
```

### Cloudflare Tunnel (Live Streaming)
```
URL: https://abc-xyz-123.trycloudflare.com/control
Password: (append ?password=YOUR_PASSWORD if CONTROL_PASSWORD is set)
```

**Important**: The widget and control panel use the **same base URL**:
- Widget: `https://abc-xyz-123.trycloudflare.com/` (root path)
- Control: `https://abc-xyz-123.trycloudflare.com/control` (control path)

## Troubleshooting

### ❌ "Disconnected" Status
**Problem**: Control panel shows "Disconnected"

**Solutions:**
1. Verify the control panel URL ends with `/control`
2. Make sure `live_widget.py` is running
3. If using Cloudflare, ensure the tunnel is active
4. Try accessing from localhost first: `http://localhost:5000/control`
5. Check browser console (F12) for errors

### ❌ "Clear Queue" or "Reset Votes" Not Working
**Problem**: Buttons don't do anything

**Solutions:**
1. Check connection status - must show "Connected"
2. Verify you're using the correct control URL (should end with `/control`)
3. If using a password, make sure it matches `CONTROL_PASSWORD`
4. Make sure the Flask server (`live_widget.py`) is running
5. Check the browser console (F12) for authorization errors

### ❌ "Access Denied" Message
**Problem**: Can't access control panel

**Solutions:**
1. If accessing remotely, ensure `CONTROL_PASSWORD` is set
2. Add `?password=YOUR_PASSWORD` to the URL
3. If on localhost, this shouldn't happen

### ⚠️ Queue/Votes Not Updating
**Problem**: Numbers don't change when requests/votes come in

**Solutions:**
1. Verify Socket.IO connection (check connection status)
2. Make sure you're connected to the correct server
3. Refresh the page and reconnect
4. Check if the main widget is actually receiving events

## Security Notes

### Local Network Only (Default)
- Control panel only works from `localhost` by default
- Safe for local testing and streaming

### Remote Access (Cloudflare Tunnel)
- **Always set** `CONTROL_PASSWORD` environment variable for remote access
- Example: `set CONTROL_PASSWORD=MySecurePassword123`
- Access via: `https://your-tunnel.trycloudflare.com/control?password=MySecurePassword123`

### Best Practices
- ✅ Use strong passwords for `CONTROL_PASSWORD`
- ✅ Don't share your control panel URL publicly
- ✅ Change password regularly if using remote access
- ❌ Don't hardcode passwords in the HTML file
- ❌ Don't commit passwords to version control

## Advanced Usage

### Opening Control Panel from Command Line (Windows)
```batch
start "" "http://localhost:5000/control"
```
Or for Cloudflare:
```batch
start "" "https://your-tunnel.trycloudflare.com/control?password=YOUR_PASSWORD"
```

### Using with Multiple Devices
1. Set up Cloudflare tunnel on your main PC
2. Copy the tunnel URL (e.g., `https://abc.trycloudflare.com`)
3. On another device (phone, tablet, laptop), open browser
4. Navigate to: `https://abc.trycloudflare.com/control`
5. Add `?password=YOUR_PASSWORD` if needed
6. Control your stream remotely from anywhere!

### Keyboard Shortcuts
Once the page is open, you can use browser shortcuts:
- `F5` - Refresh connection
- `F12` - Open developer console (for debugging)
- `Ctrl+R` - Reload page

## Quick Reference

| Action | What It Does |
|--------|--------------|
| **Clear Queue** | Removes all song requests from the queue |
| **Reset Votes** | Sets skip votes back to 0 |
| **Show Requests** | Toggle visibility of song request panel |
| **Show Chat** | Toggle visibility of chat messages |
| **Show Skip Meter** | Toggle visibility of skip voting panel |

## Support

If you encounter issues:
1. Check the browser console (F12) for errors
2. Verify your server is running (`live_widget.py`)
3. Ensure Cloudflare tunnel is active (if using)
4. Check `logs/` directory for server-side errors

## URLs Summary

Your Flask server serves two pages from the **same base URL**:

| Page | Local URL | Cloudflare URL | Purpose |
|------|-----------|----------------|---------|
| Widget | `http://localhost:5000/` | `https://abc.trycloudflare.com/` | TikTok Studio overlay |
| Control | `http://localhost:5000/control` | `https://abc.trycloudflare.com/control` | Streamer controls |

## Related Files
- `control.html` - Control panel HTML (served by Flask at `/control`)
- `index.html` - Widget HTML (served by Flask at `/`)
- `open_control_panel.bat` - Launcher script (Windows)
- `live_widget.py` - Main Flask server (serves both pages)
- `start_with_tunnel.bat` - Start server with Cloudflare tunnel