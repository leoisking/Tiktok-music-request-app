# Control Panel Quick Start 🎛️

## 🚀 Fastest Way to Open Control Panel

### Step 1: Start Your Server
Double-click `start_with_tunnel.bat` to start the server and Cloudflare tunnel.

### Step 2: Copy the Tunnel URL
Once the tunnel starts, you'll see something like:
```
https://abc-xyz-123.trycloudflare.com
```
**Copy this URL!**

### Step 3: Open Control Panel
Double-click `open_control_panel.bat` and follow the prompts:

```
Choose your connection method:

  1. Local Server (http://localhost:5000/control)
  2. Cloudflare Tunnel URL (I have my tunnel URL)
  3. Manual entry (I'll type the full URL)

Enter your choice (1-3): 2
```

Choose **2**, then paste your tunnel URL when prompted.
The script will automatically add `/control` to your URL.

### Step 4: Enter Password (if needed)
If you set a `CONTROL_PASSWORD`, enter it when prompted. Otherwise, just press Enter.

### Step 5: Control Your Stream! 🎉
The control panel will open in your browser at:
```
https://your-tunnel.trycloudflare.com/control
```

You can now:
- ✅ Clear the song request queue
- ✅ Reset skip votes
- ✅ Toggle panel visibility

---

## 📋 What You Can Do

| Feature | Description |
|---------|-------------|
| **Clear Queue** | Remove all song requests |
| **Reset Votes** | Reset skip votes to 0 |
| **Show/Hide Requests** | Toggle song request panel visibility |
| **Show/Hide Chat** | Toggle chat messages visibility |
| **Show/Hide Skip Meter** | Toggle skip voting panel visibility |
| **Real-time Stats** | See queue count and skip votes live |

---

## 🔧 Connection Methods

### Method 1: Batch File (Recommended)
```batch
open_control_panel.bat
```
Follow the interactive prompts.

### Method 2: Direct Browser Access
Open your browser and go to:
```
http://localhost:5000/control
```
Or for Cloudflare:
```
https://your-tunnel.trycloudflare.com/control?password=YOUR_PASSWORD
```

### Method 3: From Any Device
The control panel is a web page served by your Flask server:
- **Widget**: `https://your-tunnel.trycloudflare.com/`
- **Control**: `https://your-tunnel.trycloudflare.com/control`

Access it from any device with a browser!

---

## 🏠 Local vs Remote

### Local Testing (Localhost)
- **Server URL**: `http://localhost:5000`
- **Password**: Not required (unless you set one)
- **Use Case**: Testing on your computer

### Live Streaming (Cloudflare)
- **Server URL**: Your Cloudflare tunnel URL
- **Password**: Required for security (set `CONTROL_PASSWORD`)
- **Use Case**: Controlling stream from anywhere

---

## ⚠️ Troubleshooting

### "Disconnected" Status
1. ✅ Check if `live_widget.py` is running
2. ✅ Verify your server URL is correct
3. ✅ Ensure Cloudflare tunnel is active
4. ✅ Press F12 to check browser console for errors

### Buttons Don't Work
1. ✅ Must show "Connected" status first
2. ✅ Check you're using the correct server URL
3. ✅ Verify password matches if using one
4. ✅ Make sure you're connecting to the same server as your widget

### Can't Access Control Panel
1. ✅ For remote access, set `CONTROL_PASSWORD` environment variable
2. ✅ Add `?password=YOUR_PASSWORD` to the URL
3. ✅ From localhost, no password needed by default

---

## 🔐 Security Tips

### For Local Use Only
- No password needed
- Control panel only works from your computer
- Perfect for testing

### For Remote Access
```batch
set CONTROL_PASSWORD=MySecurePassword123
start_with_tunnel.bat
```
Then access with:
```
open_control_panel.bat
```
Enter your password when prompted.

**⚠️ Always use a strong password for remote access!**

---

## 💡 Pro Tips

1. **Keep the tunnel URL handy** - Save it in a text file
2. **Use a password manager** - For storing `CONTROL_PASSWORD`
3. **Test locally first** - Before going live on TikTok
4. **Open F12 console** - To see connection status and debug issues
5. **Refresh if stuck** - Press F5 to reconnect

---

## 📱 Mobile Control

Yes! You can control from your phone or any device:

1. Start your server with Cloudflare tunnel
2. Copy the tunnel URL (e.g., `https://abc-xyz.trycloudflare.com`)
3. On your phone's browser, open: `https://abc-xyz.trycloudflare.com/control`
4. Add `?password=YOUR_PASSWORD` if you set a password
5. Control your stream from anywhere!

**The control panel is just a web page - access it from any device!**

---

## 🎬 Typical Workflow

```
1. Double-click: start_with_tunnel.bat
2. Copy Cloudflare URL (e.g., https://abc.trycloudflare.com)
3. Open TikTok Studio
4. Add widget: https://abc.trycloudflare.com/
5. Double-click: open_control_panel.bat
6. Choose option 2, paste URL
7. Control panel opens at: https://abc.trycloudflare.com/control
8. Go live and manage your stream!
```

**Key Point**: Both the widget and control panel are served from the **same Cloudflare URL**:
- Widget: `https://abc.trycloudflare.com/` (root path)
- Control: `https://abc.trycloudflare.com/control` (control path)

---

## 📚 More Help

- **Full Guide**: See `CONTROL_PANEL_GUIDE.md`
- **TikTok Setup**: See `TIKTOK_STUDIO_QUICKSTART.md`
- **Cloudflare Help**: See `CLOUDFLARE_TUNNEL_SETUP.md`
- **Main README**: See `README.md`

---

## ✅ Quick Checklist

Before going live:
- [ ] Server is running (`live_widget.py`)
- [ ] Cloudflare tunnel is active
- [ ] Control panel shows "Connected"
- [ ] Tested Clear Queue button
- [ ] Tested Reset Votes button
- [ ] Visibility toggles work
- [ ] Password is secure (if using remote access)

**You're ready to stream! 🎉**