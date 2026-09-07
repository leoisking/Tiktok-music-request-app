# URL Guide - How Your Setup Works 🌐

## The Simple Truth

**You get ONE Cloudflare URL that serves BOTH pages!**

```
🌍 Cloudflare Tunnel URL: https://abc-xyz-123.trycloudflare.com

   ├── / (root)           → Widget (index.html)
   │                         ↳ For TikTok Studio overlay
   │
   └── /control           → Control Panel (control.html)
                             ↳ For you to manage the stream
```

---

## Visual Guide

### Your Flask Server Structure

```
┌─────────────────────────────────────────────────┐
│  Flask Server (live_widget.py)                  │
│  Running on: localhost:5000                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  Route: /          →  index.html                │
│  (Widget Page)        - Song requests           │
│                       - Skip voting             │
│                       - Live chat               │
│                                                 │
│  Route: /control   →  control.html              │
│  (Control Panel)      - Clear queue             │
│                       - Reset votes             │
│                       - Toggle panels           │
│                                                 │
└─────────────────────────────────────────────────┘
         │
         │ Cloudflare Tunnel
         ▼
┌─────────────────────────────────────────────────┐
│  Public URL: https://abc.trycloudflare.com      │
│                                                 │
│  /        → Widget (for viewers/TikTok)         │
│  /control → Control Panel (for you)             │
└─────────────────────────────────────────────────┘
```

---

## Step-by-Step Usage

### 1. Start Your Server
```batch
start_with_tunnel.bat
```

You'll see output like:
```
[START] Starting Cloudflare Tunnel...

https://abc-xyz-123.trycloudflare.com

Copy this URL! ☝️
```

### 2. Two URLs to Know

From that ONE Cloudflare URL, you have TWO pages:

#### 📺 Widget (for TikTok Studio)
```
https://abc-xyz-123.trycloudflare.com/
```
- Add THIS to TikTok Studio as a custom overlay
- Your viewers will see the song requests and voting

#### 🎛️ Control Panel (for YOU)
```
https://abc-xyz-123.trycloudflare.com/control
```
- Open THIS in your browser to manage the stream
- Clear queue, reset votes, toggle panels

---

## Quick Reference Table

| What | URL | Who Uses It |
|------|-----|-------------|
| **Widget** | `https://YOUR-TUNNEL.trycloudflare.com/` | TikTok Studio, Viewers |
| **Control** | `https://YOUR-TUNNEL.trycloudflare.com/control` | You (the streamer) |
| **Local Widget** | `http://localhost:5000/` | Testing only |
| **Local Control** | `http://localhost:5000/control` | Testing only |

---

## Using the Batch File

### What `open_control_panel.bat` Does:

```
1. You: "I want to open the control panel"
2. Script: "Local or Cloudflare?"
3. You: "Cloudflare"
4. Script: "What's your tunnel URL?"
5. You: "https://abc-xyz-123.trycloudflare.com"
6. Script: *adds /control automatically*
7. Opens: https://abc-xyz-123.trycloudflare.com/control
```

**You provide the BASE URL, the script adds `/control`!**

---

## Common Mistakes ❌ vs Correct ✅

### Mistake 1: Wrong URL for TikTok Studio
❌ `https://abc.trycloudflare.com/control`
✅ `https://abc.trycloudflare.com/`

### Mistake 2: Wrong URL for Control Panel
❌ `https://abc.trycloudflare.com/`
✅ `https://abc.trycloudflare.com/control`

### Mistake 3: Trying to open local file
❌ `file:///G:/path/to/control.html`
✅ `http://localhost:5000/control` or `https://abc.trycloudflare.com/control`

### Mistake 4: Thinking you need two Cloudflare URLs
❌ "I need one tunnel for widget and one for control"
✅ "I need ONE tunnel URL with TWO routes"

---

## Password Authentication

If you set `CONTROL_PASSWORD=MySecure123`:

```
Widget (no password needed):
https://abc.trycloudflare.com/

Control Panel (password required):
https://abc.trycloudflare.com/control?password=MySecure123
```

---

## Example Workflow

### Day of Your Stream:

```
1. Run: start_with_tunnel.bat
   → Server starts
   → Cloudflare tunnel starts
   → You see: https://happy-cloud-123.trycloudflare.com

2. In TikTok Studio:
   → Add overlay URL: https://happy-cloud-123.trycloudflare.com/
   
3. Run: open_control_panel.bat
   → Choose: "2" (Cloudflare)
   → Paste: https://happy-cloud-123.trycloudflare.com
   → Script opens: https://happy-cloud-123.trycloudflare.com/control
   
4. Go Live! 🎉
   → Viewers see widget at "/"
   → You control it at "/control"
```

---

## Testing Locally (Before Going Live)

```
1. Run: start_with_tunnel.bat
   (or just: python live_widget.py)

2. Open Widget:
   http://localhost:5000/
   
3. Open Control Panel:
   http://localhost:5000/control
   
4. Test buttons and features
   
5. When ready, use the Cloudflare URLs for real streaming
```

---

## Troubleshooting

### "I can't access the control panel"
- Are you using `/control` at the end of the URL?
- Is your server running?
- If remote, did you add `?password=YOUR_PASSWORD`?

### "The widget and control panel don't sync"
- Are they using the SAME base URL?
- Both should be from: `https://abc.trycloudflare.com`
- Check connection status (green = connected)

### "TikTok Studio says invalid URL"
- Make sure you're using the ROOT path: `https://abc.trycloudflare.com/`
- NOT the control path: `https://abc.trycloudflare.com/control`

---

## Remember! 🧠

```
ONE Cloudflare URL → TWO different pages

Base: https://abc.trycloudflare.com
  ├── /         (for TikTok/viewers)
  └── /control  (for you)

Same server, different routes!
```

---

## Need Help?

1. Check connection status in control panel (green = good)
2. Open browser console (F12) to see errors
3. Verify URLs end with correct path
4. Make sure server is running
5. Read `CONTROL_PANEL_QUICKSTART.md` for detailed steps