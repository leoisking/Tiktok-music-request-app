# TikTok Live Widget - Setup Options Guide 🎯

## Choose Your Setup

You have **THREE** different ways to set up the control panel. Pick the one that fits your needs!

---

## Option 1: Built-in Control Panel (Simplest)

### How It Works
One server, one Cloudflare URL, two routes.

```
Cloudflare: https://your-tunnel.trycloudflare.com
├─ /        → Widget (for TikTok)
└─ /control → Control Panel (for you)
```

### Quick Start
```batch
start_with_tunnel.bat
```

### Access URLs
```
Widget:  https://your-tunnel.trycloudflare.com/
Control: https://your-tunnel.trycloudflare.com/control
```

### Pros ✅
- Easiest setup
- One server to manage
- One Cloudflare URL
- Works out of the box

### Cons ❌
- Control panel exposed to internet
- Must use password for security
- Same URL for everything

### Best For
- Solo streamers
- Quick setup
- Testing
- Simple use cases

### Files Used
- `start_with_tunnel.bat`
- `live_widget.py`
- `index.html` (widget)
- `control.html` (control)

---

## Option 2: Local Control Panel (Most Secure)

### How It Works
Main widget on Cloudflare, control panel runs locally.

```
Cloudflare: https://your-tunnel.trycloudflare.com/ (Widget)
    ↕ Socket.IO
Localhost: http://localhost:5001/ (Control Panel)
```

### Quick Start
```batch
REM Terminal 1:
start_with_tunnel.bat

REM Terminal 2:
start_control_panel.bat
```

When prompted, enter your Cloudflare URL.

### Access URLs
```
Widget:  https://your-tunnel.trycloudflare.com/
Control: http://localhost:5001/
```

### Pros ✅
- Control panel not exposed to internet
- Most secure option
- Separate concerns
- Can run on different ports

### Cons ❌
- Need to run two servers
- Control panel only on your PC
- Can't share control access easily

### Best For
- Security-conscious streamers
- Local-only control
- When you don't need remote access
- Development/testing

### Files Used
- `start_with_tunnel.bat` (widget)
- `start_control_panel.bat` (control)
- `live_widget.py` (widget server)
- `control_server.py` (control server)

---

## Option 3: Dual Cloudflare Tunnels (Most Flexible)

### How It Works
Two servers, two Cloudflare URLs, complete independence.

```
Cloudflare 1: https://widget-abc.trycloudflare.com/ (Widget)
    ↕ Socket.IO
Cloudflare 2: https://control-xyz.trycloudflare.com/ (Control)
```

### Quick Start
```batch
start_everything.bat
```

Or manually:
```batch
REM Terminal 1:
start_with_tunnel.bat

REM Terminal 2:
start_control_with_tunnel.bat
```

### Access URLs
```
Widget:  https://widget-abc.trycloudflare.com/
Control: https://control-xyz.trycloudflare.com/
```

### Pros ✅
- Separate URLs for widget and control
- Share control URL with co-streamers
- Access control from anywhere
- Most flexible setup
- Professional architecture

### Cons ❌
- Two Cloudflare URLs to manage
- Two servers to monitor
- Slightly more complex setup

### Best For
- Co-streaming with others
- Remote control access
- Professional setups
- When you need to share control
- Mobile control access

### Files Used
- `start_everything.bat` (both)
- `start_with_tunnel.bat` (widget only)
- `start_control_with_tunnel.bat` (control only)
- `live_widget.py` (widget server)
- `control_server.py` (control server)

---

## Quick Comparison Table

| Feature | Built-in | Local | Dual Tunnel |
|---------|----------|-------|-------------|
| **Servers** | 1 | 2 | 2 |
| **Cloudflare URLs** | 1 | 1 | 2 |
| **Setup Difficulty** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐ Medium |
| **Security** | ⭐⭐ Medium | ⭐⭐⭐ High | ⭐⭐ Medium |
| **Remote Control** | ✅ Yes | ❌ No | ✅ Yes |
| **Share Control** | ✅ Yes | ❌ No | ✅ Yes |
| **Mobile Access** | ✅ Yes | ❌ No | ✅ Yes |
| **Internet Required** | ✅ Yes | ⚠️ Widget only | ✅ Yes |
| **Best For** | Beginners | Security | Flexibility |

---

## Decision Flow Chart

```
START: Choose Your Setup
│
├─ Do you need to share control with others?
│  ├─ YES → Option 3: Dual Tunnels
│  └─ NO → Continue
│
├─ Do you need mobile/remote control access?
│  ├─ YES → Option 3: Dual Tunnels
│  └─ NO → Continue
│
├─ Is security your top priority?
│  ├─ YES → Option 2: Local Control
│  └─ NO → Continue
│
└─ Want the simplest setup?
   └─ YES → Option 1: Built-in
```

---

## Detailed Setup Instructions

### Option 1: Built-in Control Panel

1. **Start the server:**
   ```batch
   start_with_tunnel.bat
   ```

2. **Copy the Cloudflare URL:**
   ```
   https://happy-cloud-123.trycloudflare.com
   ```

3. **For TikTok Studio:**
   ```
   https://happy-cloud-123.trycloudflare.com/
   ```

4. **For Control Panel:**
   ```
   https://happy-cloud-123.trycloudflare.com/control
   ```

5. **If you set a password:**
   ```
   https://happy-cloud-123.trycloudflare.com/control?password=YOUR_PASSWORD
   ```

---

### Option 2: Local Control Panel

1. **Start widget server:**
   ```batch
   start_with_tunnel.bat
   ```
   Copy the Cloudflare URL.

2. **Start control panel:**
   ```batch
   start_control_panel.bat
   ```

3. **When prompted, choose option 2 (Cloudflare)**

4. **Paste the Cloudflare URL from step 1**

5. **Access control panel:**
   ```
   http://localhost:5001/
   ```

6. **For TikTok Studio:**
   ```
   https://your-cloudflare-url.com/
   ```

---

### Option 3: Dual Cloudflare Tunnels

1. **Start everything:**
   ```batch
   start_everything.bat
   ```

2. **Follow the prompts for configuration**

3. **You'll see TWO Cloudflare URLs:**
   ```
   Widget:  https://abc-123.trycloudflare.com
   Control: https://xyz-456.trycloudflare.com
   ```

4. **For TikTok Studio (Widget URL):**
   ```
   https://abc-123.trycloudflare.com/
   ```

5. **For Control Panel (Control URL):**
   ```
   https://xyz-456.trycloudflare.com/
   ```

6. **With password:**
   ```
   https://xyz-456.trycloudflare.com/?password=YOUR_PASSWORD
   ```

---

## Configuration Tips

### Setting Environment Variables

**Before starting any batch file:**

```batch
REM TikTok username (required)
set TIKTOK_USER=yourname

REM Password for control panel (recommended)
set CONTROL_PASSWORD=YourSecurePassword123

REM Widget server port (default: 5000)
set PORT=5000

REM Control panel port (default: 5001)
set CONTROL_PORT=5001

REM Skip vote threshold (default: 10)
set SKIP_THRESHOLD=10
```

### Recommended Settings

**For Solo Streaming:**
```batch
set TIKTOK_USER=yourname
set CONTROL_PASSWORD=MyPassword123
start_with_tunnel.bat
```

**For Co-Streaming:**
```batch
set TIKTOK_USER=yourname
set CONTROL_PASSWORD=SharedPassword123
start_everything.bat
```

**For Testing Locally:**
```batch
set TIKTOK_USER=yourname
python live_widget.py
```
Access: `http://localhost:5000/`

---

## Switching Between Options

### From Built-in to Local
1. Stop `start_with_tunnel.bat` (Ctrl+C)
2. Restart with `start_with_tunnel.bat`
3. Open new terminal: `start_control_panel.bat`
4. Enter the Cloudflare URL when prompted

### From Local to Dual Tunnel
1. Stop both servers (Ctrl+C in both terminals)
2. Run `start_everything.bat`
3. You'll get two Cloudflare URLs

### From Dual to Built-in
1. Stop `start_everything.bat` (Ctrl+C)
2. Run `start_with_tunnel.bat` only
3. Use the `/control` endpoint

---

## Troubleshooting

### Can't decide which option?
- **Start with Option 1** (Built-in) - easiest to try
- **Upgrade to Option 2** if you want more security
- **Use Option 3** if you need to share control

### Something not working?
1. Check if servers are running (Task Manager)
2. Verify Cloudflare URLs are correct
3. Make sure password matches (if set)
4. Try restarting the servers
5. Check firewall settings

### Need to change options?
- Just stop the current setup (Ctrl+C)
- Run the new batch file
- No files need to be edited!

---

## File Reference

| Batch File | What It Does | Option |
|------------|--------------|--------|
| `start_with_tunnel.bat` | Widget with Cloudflare | 1, 2 |
| `start_control_panel.bat` | Local control (no tunnel) | 2 |
| `start_control_with_tunnel.bat` | Control with Cloudflare | 3 |
| `start_everything.bat` | Both with Cloudflare | 3 |
| `open_control_panel.bat` | Helper to open control | 1, 3 |

---

## Security Recommendations

### Always Set Password For:
- ✅ Remote access (Cloudflare)
- ✅ Shared control access
- ✅ Public streaming

### Password Optional For:
- ⚠️ Local testing
- ⚠️ Solo streaming (if you trust your network)

### Never:
- ❌ Use simple passwords like "123456"
- ❌ Share control URL publicly
- ❌ Leave control panel open on public WiFi without password

---

## Next Steps

1. **Choose your option** (1, 2, or 3)
2. **Read the detailed guide** for that option
3. **Run the batch file**
4. **Test everything** before going live
5. **Go live on TikTok!** 🎉

## Additional Resources

- `README.md` - Main documentation
- `TIKTOK_STUDIO_QUICKSTART.md` - TikTok setup
- `CLOUDFLARE_TUNNEL_SETUP.md` - Cloudflare help
- `CONTROL_PANEL_GUIDE.md` - Control panel features
- `DUAL_TUNNEL_SETUP.md` - Dual tunnel details
- `CONTROL_SERVER_README.md` - Control server info

---

**Still confused? Start with Option 1 - you can always switch later!** 🚀