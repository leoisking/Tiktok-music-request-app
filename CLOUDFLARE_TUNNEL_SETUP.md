# Cloudflare Tunnel Setup Guide

Complete guide for hosting your TikTok Live Widget through Cloudflare Tunnel for use with TikTok Studio.

## 🎯 Why Cloudflare Tunnel?

TikTok Studio requires HTTPS URLs and doesn't accept `localhost`. Cloudflare Tunnel provides:
- ✅ Free HTTPS URL for your widget
- ✅ No port forwarding needed
- ✅ Secure encrypted connection
- ✅ Works with TikTok Studio perfectly
- ✅ No need for public IP or domain

## 📋 Prerequisites

1. **Cloudflare Account** (free) - [Sign up here](https://dash.cloudflare.com/sign-up)
2. **Python 3.8+** installed
3. **Widget files** (this project)

## 🚀 Quick Start

### Step 1: Install Cloudflare Tunnel (cloudflared)

**Windows:**
```powershell
# Download from: https://github.com/cloudflare/cloudflared/releases
# Or use winget:
winget install --id Cloudflare.cloudflared
```

**Mac:**
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux:**
```bash
# Debian/Ubuntu
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Or using package manager
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-archive-keyring.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-archive-keyring.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared
```

### Step 2: Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser window. Log in and select your domain (or use the free tunnel domain).

### Step 3: Configure Widget for Remote Access

**Set environment variables:**

```bash
# Windows (cmd)
set HOST=0.0.0.0
set PORT=5000
set ALLOWED_ORIGINS=*
set CONTROL_PASSWORD=your_secure_password_here
set TIKTOK_USER=yourusername

# Mac/Linux (bash)
export HOST=0.0.0.0
export PORT=5000
export ALLOWED_ORIGINS=*
export CONTROL_PASSWORD=your_secure_password_here
export TIKTOK_USER=yourusername
```

**Or create a `.env` file:**
```env
HOST=0.0.0.0
PORT=5000
ALLOWED_ORIGINS=*
CONTROL_PASSWORD=MySecurePassword123
TIKTOK_USER=yourusername
MOD_LIST=mod1,mod2,mod3
SKIP_THRESHOLD=10
```

### Step 4: Start Your Widget

```bash
python live_widget.py
```

You should see:
```
🚀 Server LIVE at http://0.0.0.0:5000
🌐 Accessible from network (for Cloudflare tunnel)
🔐 Control panel password: SET
🌍 CORS: All origins allowed (Cloudflare tunnel mode)
```

### Step 5: Create and Run Cloudflare Tunnel

**Option A: Quick Tunnel (No Configuration)**
```bash
cloudflared tunnel --url http://localhost:5000
```

You'll get a URL like: `https://random-name.trycloudflare.com`

⚠️ **Note:** Quick tunnels change URL each time. Use Option B for permanent URL.

**Option B: Named Tunnel (Recommended)**

1. **Create a tunnel:**
```bash
cloudflared tunnel create tiktok-widget
```

2. **Note the Tunnel ID** from the output

3. **Create config file** (`~/.cloudflared/config.yml` or `C:\Users\YourName\.cloudflared\config.yml`):
```yaml
tunnel: tiktok-widget
credentials-file: C:\Users\YourName\.cloudflared\<TUNNEL-ID>.json

ingress:
  - hostname: your-widget.yourname.com
    service: http://localhost:5000
  - service: http_status:404
```

**Or without custom domain (free .trycloudflare.com subdomain):**
```yaml
tunnel: tiktok-widget
credentials-file: /path/to/.cloudflared/<TUNNEL-ID>.json

ingress:
  - service: http://localhost:5000
```

4. **Route DNS (if using custom domain):**
```bash
cloudflared tunnel route dns tiktok-widget your-widget.yourname.com
```

5. **Run the tunnel:**
```bash
cloudflared tunnel run tiktok-widget
```

### Step 6: Use in TikTok Studio

1. Open TikTok Studio
2. Go to Overlay/Browser settings
3. Add your tunnel URL: `https://your-tunnel-url.trycloudflare.com`
4. Set dimensions (recommended: 400x800 or 360x640)
5. ✅ Done! Widget now works in TikTok Studio

## 🎮 Accessing Control Panel Remotely

With Cloudflare tunnel, access your control panel:

```
https://your-tunnel-url.trycloudflare.com/control?password=your_secure_password_here
```

**Security Note:** Always set a strong `CONTROL_PASSWORD` when using remote access!

## 🔧 Advanced Configuration

### Custom Domain Setup

If you have a domain in Cloudflare:

1. **Point DNS to tunnel:**
```bash
cloudflared tunnel route dns tiktok-widget widget.yourdomain.com
```

2. **Update config.yml:**
```yaml
tunnel: tiktok-widget
credentials-file: /path/to/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: widget.yourdomain.com
    service: http://localhost:5000
    originRequest:
      noTLSVerify: true
  - service: http_status:404
```

### Multiple Services

Host multiple things through one tunnel:

```yaml
tunnel: tiktok-widget
credentials-file: /path/to/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: widget.yourdomain.com
    service: http://localhost:5000
  - hostname: control.yourdomain.com
    service: http://localhost:5000
    path: /control
  - service: http_status:404
```

### CORS for Specific Domains

Instead of allowing all origins:

```bash
# Allow only your tunnel URL
export ALLOWED_ORIGINS=https://your-tunnel.trycloudflare.com,https://widget.yourdomain.com
```

## 🏃 Running as Service

### Windows (as Service)

**Create service script (`run_widget.bat`):**
```batch
@echo off
cd /d "C:\path\to\flask-tiktok-socket-setup"
set HOST=0.0.0.0
set PORT=5000
set ALLOWED_ORIGINS=*
set CONTROL_PASSWORD=YourPassword
set TIKTOK_USER=yourusername
python live_widget.py
```

**Install as Windows Service with NSSM:**
1. Download [NSSM](https://nssm.cc/download)
2. `nssm install TikTokWidget "C:\path\to\run_widget.bat"`

### Linux (systemd)

**Widget service (`/etc/systemd/system/tiktok-widget.service`):**
```ini
[Unit]
Description=TikTok Live Widget
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/flask-tiktok-socket-setup
Environment="HOST=0.0.0.0"
Environment="PORT=5000"
Environment="ALLOWED_ORIGINS=*"
Environment="CONTROL_PASSWORD=YourPassword"
Environment="TIKTOK_USER=yourusername"
ExecStart=/usr/bin/python3 /path/to/flask-tiktok-socket-setup/live_widget.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Cloudflare Tunnel service (`/etc/systemd/system/cloudflared.service`):**
```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=yourusername
ExecStart=/usr/local/bin/cloudflared tunnel run tiktok-widget
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tiktok-widget
sudo systemctl enable cloudflared
sudo systemctl start tiktok-widget
sudo systemctl start cloudflared
```

## 📱 Mobile Testing

Your widget is now accessible from any device:

1. **On your phone**, visit: `https://your-tunnel.trycloudflare.com`
2. Test readability and responsiveness
3. Check all commands work (`!req`, `!skip`)
4. Verify skip meter displays correctly

## 🔒 Security Best Practices

### 1. Strong Control Password
```bash
# Generate secure password
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Restrict CORS (Production)
```bash
# Only allow your specific tunnel
export ALLOWED_ORIGINS=https://your-tunnel.trycloudflare.com
```

### 3. Monitor Access Logs
```bash
# Watch for unauthorized access attempts
python live_widget.py | grep "WARNING"
```

### 4. Keep Software Updated
```bash
# Update cloudflared regularly
cloudflared update

# Update Python packages
pip install --upgrade flask flask-socketio TikTokLive
```

### 5. Use Environment Files
Don't hardcode passwords! Use `.env` files or environment variables.

## 🐛 Troubleshooting

### Tunnel Not Connecting

**Check tunnel status:**
```bash
cloudflared tunnel list
cloudflared tunnel info tiktok-widget
```

**Check if service is running:**
```bash
# Windows
tasklist | findstr cloudflared

# Mac/Linux
ps aux | grep cloudflared
```

### Widget Not Accessible

**Verify widget is running:**
```bash
curl http://localhost:5000
```

**Check tunnel config:**
```bash
cloudflared tunnel info tiktok-widget
```

**Check logs:**
```bash
# Widget logs
python live_widget.py

# Cloudflared logs
cloudflared tunnel run tiktok-widget --loglevel debug
```

### WebSocket Connection Issues

**Check CORS settings:**
```bash
# Should see in widget logs:
🌍 CORS: All origins allowed (Cloudflare tunnel mode)
```

**Test WebSocket:**
Open browser console on widget page:
```javascript
// Should see:
✅ Connected to server
```

### TikTok Studio Not Loading Widget

1. **Check URL is HTTPS**: `https://` not `http://`
2. **Test in browser first**: Open URL in Chrome/Firefox
3. **Check dimensions**: Try 400x800 or 360x640
4. **Clear TikTok Studio cache**: Restart TikTok Studio
5. **Check Cloudflare tunnel is running**

### Control Panel Not Accessible

**Check password parameter:**
```
https://your-tunnel.trycloudflare.com/control?password=YourPassword
```

**Check logs for access attempts:**
```bash
python live_widget.py | grep "Control page"
```

## 📊 Performance Optimization

### For Cloudflare Tunnel

**Optimize config.yml:**
```yaml
tunnel: tiktok-widget
credentials-file: /path/to/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: your-widget.yourname.com
    service: http://localhost:5000
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false
      keepAliveTimeout: 90s
      keepAliveConnections: 10
  - service: http_status:404
```

### For Widget

**Reduce queue limits for faster responses:**
```bash
export QUEUE_MAX=100
export CHAT_HISTORY_MAX=10
```

## 🎯 Quick Reference

### Start Everything

**Terminal 1 - Widget:**
```bash
export HOST=0.0.0.0 PORT=5000 ALLOWED_ORIGINS=* CONTROL_PASSWORD=MyPass TIKTOK_USER=myname
python live_widget.py
```

**Terminal 2 - Tunnel:**
```bash
cloudflared tunnel run tiktok-widget
```

**URLs:**
- Widget: `https://your-tunnel.trycloudflare.com`
- Control: `https://your-tunnel.trycloudflare.com/control?password=MyPass`

### Stop Everything

```bash
# Ctrl+C in both terminals

# Or if running as service:
sudo systemctl stop tiktok-widget cloudflared
```

## 📚 Additional Resources

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [TikTok Studio Guide](https://www.tiktok.com/studio)
- [Widget Documentation](README.md)

## 💡 Pro Tips

1. **Use Named Tunnels**: More reliable than quick tunnels
2. **Bookmark Control Panel**: Add `?password=` to URL for quick access
3. **Monitor Logs**: Keep terminal open to see requests/skips
4. **Test Before Going Live**: Always test tunnel before streaming
5. **Keep Tunnel Running**: Use systemd/nssm for auto-restart

## ✅ Checklist

Before going live:
- [ ] Widget running on 0.0.0.0:5000
- [ ] Cloudflare tunnel running
- [ ] HTTPS URL accessible in browser
- [ ] Control panel accessible with password
- [ ] Tested in TikTok Studio overlay
- [ ] Commands work (!req, !skip)
- [ ] Mobile view is readable
- [ ] Logs show no errors

---

**You're ready to stream! 🎉**

For issues or questions, check the [README.md](README.md) or [TROUBLESHOOTING.md](TROUBLESHOOTING.md).