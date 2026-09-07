# TikTok Studio Quick Start Guide

The fastest way to get your widget running in TikTok Studio.

## 🎯 What You Need

- ✅ Windows/Mac/Linux computer
- ✅ Python 3.8+ installed
- ✅ TikTok account
- ✅ 10 minutes

## 🚀 5-Minute Setup

### Step 1: Install Cloudflared

**Windows:**
```powershell
winget install Cloudflare.cloudflared
```

**Mac:**
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux:**
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### Step 2: Install Python Packages

```bash
pip install flask flask-socketio TikTokLive
```

### Step 3: Configure Your Settings

**Windows (cmd):**
```batch
set TIKTOK_USER=yourusername
set HOST=0.0.0.0
set ALLOWED_ORIGINS=*
set CONTROL_PASSWORD=MySecurePassword123
```

**Mac/Linux (bash):**
```bash
export TIKTOK_USER=yourusername
export HOST=0.0.0.0
export ALLOWED_ORIGINS=*
export CONTROL_PASSWORD=MySecurePassword123
```

### Step 4: Start the Widget

Open **Terminal/Command Prompt 1:**
```bash
cd flask-tiktok-socket-setup
python live_widget.py
```

You should see:
```
🚀 Server LIVE at http://0.0.0.0:5000
🌐 Accessible from network (for Cloudflare tunnel)
🔐 Control panel password: SET
```

### Step 5: Start Cloudflare Tunnel

Open **Terminal/Command Prompt 2:**
```bash
cloudflared tunnel --url http://localhost:5000
```

You'll see output like:
```
Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
https://random-words-1234.trycloudflare.com
```

**📋 COPY THAT URL!** You'll need it for TikTok Studio.

### Step 6: Add to TikTok Studio

1. Open **TikTok Studio**
2. Go to **Settings** → **Overlay** (or **Browser Source**)
3. **Add New Overlay/Browser**
4. **URL:** Paste your tunnel URL: `https://random-words-1234.trycloudflare.com`
5. **Width:** `400` (or `360` for mobile-optimized)
6. **Height:** `800` (or `640` for mobile-optimized)
7. **✅ Click Save/Apply**

### Step 7: Test It!

Open your tunnel URL in a browser to test:
```
https://random-words-1234.trycloudflare.com
```

You should see:
- 🎵 Song Requests panel
- ⏭️ Skip Meter panel
- Beautiful glass morphism design

## 🎮 Commands

Tell your viewers:

- **Request a song:** Type `!req Song Name by Artist` in chat
- **Vote to skip:** Type `!skip` in chat

**Moderators only:**
- `!clear` - Clear all requests
- `!reset` or `!next` - Reset skip votes

## 🎛️ Control Panel

Access your control panel remotely:
```
https://random-words-1234.trycloudflare.com/control?password=MySecurePassword123
```

Features:
- Clear queue button
- Reset skip votes button
- Toggle panel visibility (requests/chat/voting)

## ⚙️ Optional: Use Easy Startup Scripts

Instead of manual steps, use the provided scripts:

**Windows:**
```batch
start_with_tunnel.bat
```

**Mac/Linux:**
```bash
chmod +x start_with_tunnel.sh
./start_with_tunnel.sh
```

These scripts will:
- ✅ Check if everything is installed
- ✅ Prompt for your TikTok username
- ✅ Start the widget
- ✅ Start the Cloudflare tunnel
- ✅ Show you the URL to use

## 📱 Mobile Optimization

Your widget is **automatically optimized** for:
- Portrait mode phones
- Landscape mode phones
- Tablets
- Small screens (< 375px)
- Touch devices

Features:
- ✅ Larger text (readable from across the room)
- ✅ Better contrast (works in bright light)
- ✅ Touch-friendly buttons (44px minimum)
- ✅ Responsive layout (adapts to any screen)

## 🔒 Important Security Notes

### 1. Use a Strong Password
```bash
# Generate a secure password
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then set it:
```bash
export CONTROL_PASSWORD=the_generated_password
```

### 2. Keep Your Tunnel URL Private
Your tunnel URL is public, but:
- Only you have the control panel password
- Rate limiting prevents spam
- Input validation prevents attacks

### 3. For Production, Use Named Tunnels
Quick tunnels change URL every restart. For permanent URL:
```bash
cloudflared tunnel login
cloudflared tunnel create tiktok-widget
cloudflared tunnel run tiktok-widget
```

See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for details.

## 🐛 Troubleshooting

### "cloudflared not found"
Install cloudflared first (see Step 1)

### "Python not found"
Install Python from https://www.python.org/downloads/

### Widget not showing in TikTok Studio
1. Make sure URL is HTTPS (starts with `https://`)
2. Check if tunnel is still running
3. Test URL in browser first
4. Try refreshing TikTok Studio
5. Check dimensions (try 400x800)

### Can't access control panel
Make sure to add `?password=YourPassword` to the URL:
```
https://your-url.trycloudflare.com/control?password=MySecurePassword123
```

### Connection lost
Both terminals must stay open:
- Terminal 1: Widget (python live_widget.py)
- Terminal 2: Tunnel (cloudflared tunnel...)

If either closes, restart it.

### Mobile viewers can't read text
The widget auto-adapts! If still hard to read:
1. Test URL on phone browser first
2. Check TikTok Studio dimensions match recommendation
3. Verify tunnel is using correct URL
4. Try portrait mode (better for mobile)

## 💡 Pro Tips

### 1. Keep Everything Running
Use process managers to auto-restart:
- **Windows:** NSSM or Task Scheduler
- **Linux/Mac:** systemd service
- See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for setup

### 2. Monitor Logs
Keep widget terminal visible to see:
- Song requests coming in
- Skip votes counting up
- Rate limit warnings
- Connection issues

### 3. Test Before Going Live
1. Start everything
2. Open widget in browser
3. Test with demo mode (it auto-starts after 4 seconds)
4. Verify in TikTok Studio
5. Then go live on TikTok

### 4. Bookmark Control Panel
Save this link with your password:
```
https://your-url.trycloudflare.com/control?password=YourPassword
```

### 5. Mobile-Optimized Dimensions
For streams primarily viewed on mobile:
- Width: 360px (instead of 400px)
- Height: 640px (instead of 800px)

## 📊 Configuration Options

Customize your widget with environment variables:

```bash
# Basic (required)
TIKTOK_USER=yourusername

# Remote access (required for Cloudflare)
HOST=0.0.0.0
ALLOWED_ORIGINS=*
CONTROL_PASSWORD=YourSecurePassword

# Customization (optional)
SKIP_THRESHOLD=10          # Votes needed to skip (default: 10)
QUEUE_MAX=200              # Max song requests (default: 200)
RATE_LIMIT_MAX=5           # Max actions per window (default: 5)
RATE_LIMIT_WINDOW=30       # Rate limit window in seconds (default: 30)

# Moderators (optional)
MOD_LIST=mod1,mod2,mod3    # Comma-separated list

# Debug (optional)
LIVE_WIDGET_DEBUG=1        # Verbose logging
```

## 🎨 Customization

### Change Skip Threshold
```bash
export SKIP_THRESHOLD=8    # Need 8 votes instead of 10
```

### Reduce Queue Size
```bash
export QUEUE_MAX=100       # Only show 100 requests max
```

### Add More Moderators
```bash
export MOD_LIST=admin,helper1,helper2,friend
```

## 📚 Next Steps

Once everything works:

1. **Read Full Docs:**
   - [README.md](README.md) - Complete feature list
   - [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) - Advanced tunnel setup
   - [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Tips and tricks

2. **Set Up Named Tunnel:**
   - Get permanent URL (doesn't change)
   - Optional custom domain
   - Auto-start on boot

3. **Optimize for Your Stream:**
   - Adjust skip threshold
   - Set moderators
   - Customize dimensions
   - Test mobile readability

## ✅ Pre-Stream Checklist

Before going live:

- [ ] Widget running (`python live_widget.py`)
- [ ] Tunnel running (`cloudflared tunnel...`)
- [ ] URL copied and tested in browser
- [ ] Added to TikTok Studio overlay
- [ ] Control panel accessible with password
- [ ] Tested on mobile device
- [ ] Commands explained to viewers
- [ ] Moderators added to `MOD_LIST`
- [ ] Both terminals kept open

## 🆘 Still Having Issues?

1. **Check logs** - Look at widget terminal for errors
2. **Enable debug mode** - `export LIVE_WIDGET_DEBUG=1`
3. **Test step-by-step**:
   - Widget works locally? (http://localhost:5000)
   - Tunnel running? (check terminal 2)
   - URL works in browser? (open in Chrome)
   - TikTok Studio shows it? (check overlay settings)
4. **Review documentation** - Full guides available
5. **Restart everything** - Close terminals and start fresh

## 🎉 You're Ready!

Once you see your widget in TikTok Studio:

1. Tell viewers the commands: `!req` and `!skip`
2. Keep control panel open on second monitor
3. Monitor widget terminal for activity
4. Enjoy your interactive stream!

---

**Quick Command Reference:**

```bash
# Terminal 1: Widget
export TIKTOK_USER=yourname HOST=0.0.0.0 ALLOWED_ORIGINS=* CONTROL_PASSWORD=MyPass
python live_widget.py

# Terminal 2: Tunnel
cloudflared tunnel --url http://localhost:5000

# TikTok Studio: Use the https://... URL from Terminal 2
```

---

**Made for TikTok Studio streamers | Version 2.0 | 2024**

For detailed setup, see [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)