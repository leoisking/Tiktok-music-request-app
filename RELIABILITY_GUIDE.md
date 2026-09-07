# TikTok Widget Reliability Guide 🛡️

## What Was Fixed

Your widget was stopping because of several issues that have now been resolved:

### 1. **Silent Connection Failures**
- **Problem**: Widget would disconnect from TikTok but you couldn't see it
- **Fix**: Added comprehensive logging with immediate flushing
- **Fix**: All output now visible in real-time
- **Fix**: Health monitoring system detects stale connections

### 2. **No Auto-Recovery**
- **Problem**: When TikTok connection dropped, widget stayed disconnected
- **Fix**: Automatic reconnection with exponential backoff
- **Fix**: Recreates client after multiple failures
- **Fix**: Auto-restart capability in launcher

### 3. **Rate Limiting Issues**
- **Problem**: TikTok would rate limit and widget would hang
- **Fix**: Intelligent retry with increasing delays when rate limited
- **Fix**: Detects rate limit errors and backs off appropriately

### 4. **Stale Connections**
- **Problem**: Connected but not receiving events (zombie connection)
- **Fix**: Health monitor checks for activity every 60 seconds
- **Fix**: Force disconnect after 15 minutes of no events
- **Fix**: Automatic reconnection after forced disconnect

### 5. **Resource Leaks**
- **Problem**: Large queues or memory leaks could cause slowdowns
- **Fix**: Periodic cleanup of old requests and rate limiter data
- **Fix**: Queue size limits enforced (default 200)
- **Fix**: Stale request removal (older than 24 hours)

### 6. **Error Handling**
- **Problem**: Single error could crash entire comment handler
- **Fix**: Comprehensive try-catch blocks
- **Fix**: Errors logged but don't stop processing
- **Fix**: System messages notify of errors

---

## New Features

### ✅ Connection Health Monitoring
- Tracks time since last TikTok event
- Warns after 2 minutes of silence
- Alerts after 5 minutes of silence
- Force reconnects after 15 minutes

### ✅ Automatic Reconnection
- Retries connection every 15 seconds initially
- Backs off to 120 seconds if rate limited
- Creates fresh client every 10 failed attempts
- Never stops trying to reconnect

### ✅ Smart Error Detection
- Detects when user is not live
- Detects rate limiting from TikTok
- Detects network timeouts
- Adjusts retry strategy based on error type

### ✅ Queue Overflow Protection
- Warns at 90% capacity (180/200)
- Logs when requests are dropped
- Shows which requests were removed
- Broadcasts system messages

### ✅ Real-Time Monitoring
- All activity visible in console
- Connection attempts logged
- Health checks every minute
- Cleanup operations logged

---

## How to Use the Robust Launcher

### Quick Start

```batch
start_robust.bat
```

This launches **4 windows**:

1. **Main Control** - Instructions and controls
2. **Widget Server** - Live activity (auto-restarts if crashes)
3. **Cloudflare Tunnel** - Your public URL
4. **Health Monitor** - Connection status checks

### What Each Window Does

#### Widget Server Window
```
Shows:
- [ATTEMPT X] Connecting to TikTok Live...
- REQUEST from [user]: Song Name
- SKIP from [user] (3/10)
- [HEALTH] Last event was 120s ago
- [CLEANUP] Pruned X stale requests

Auto-restarts if:
- Python crashes
- Widget exits unexpectedly
```

#### Cloudflare Tunnel Window
```
Shows:
- Your https://...trycloudflare.com URL
- Connection status
- Traffic logs

Copy this URL to TikTok Studio!
```

#### Health Monitor Window
```
Shows every 30 seconds:
- [OK] Widget responding
- [WARNING] Widget not responding

Will alert if widget becomes unresponsive
```

---

## Configuration Options

Set before running `start_robust.bat`:

### TikTok Connection
```batch
set TIKTOK_USER=yourname
```

### Rate Limiting (prevent spam)
```batch
set RATE_LIMIT_MAX=10          # Commands per window
set RATE_LIMIT_WINDOW=60       # Window in seconds
```
Default: 10 commands per 60 seconds per user

### Queue Size
```batch
set QUEUE_MAX=200              # Max songs in queue
```
Default: 200 songs

### Skip Threshold
```batch
set SKIP_THRESHOLD=5           # Votes needed to skip
```
Default: 5 votes

### Example Configuration
```batch
set TIKTOK_USER=yourname
set SKIP_THRESHOLD=3
set RATE_LIMIT_MAX=15
set QUEUE_MAX=300
start_robust.bat
```

---

## Monitoring Your Stream

### What to Watch

#### Widget Server Window - Normal Operation
```
✅ [ATTEMPT 1] Connecting to TikTok Live for user: yourname
✅ [HEALTH] Last event was 45s ago
✅ REQUEST from User123: Song Name - Artist
✅ SKIP from User456 (2/5)
```

#### Widget Server Window - Warning Signs
```
⚠️ [HEALTH] No events for 300s - connection may be dead
⚠️ Queue is 180/200 - nearly full!
⚠️ Rate limited by TikTok - backing off
⚠️ Connection error: timeout
```

#### Widget Server Window - Auto-Recovery
```
🔄 [ATTEMPT 5] Connecting to TikTok Live...
🔄 Creating fresh TikTok client after multiple retries
🔄 Connection ended after 3600s. Reconnecting...
```

### Log Files

All activity is logged to `logs\widget_[date].log`

**View recent activity:**
```batch
powershell "Get-Content logs\widget_20260209.log -Tail 50"
```

**Search for errors:**
```batch
type logs\widget_20260209.log | findstr /C:"ERROR" /C:"WARNING"
```

**Check connection attempts:**
```batch
type logs\widget_20260209.log | findstr /C:"ATTEMPT" /C:"Connecting"
```

---

## Troubleshooting

### Widget Stops Responding

**Symptoms:**
- No new requests appearing
- Health monitor shows warnings
- TikTok comments not being processed

**Solutions:**
1. **Check Widget Server window** - Look for error messages
2. **Check if you're still live** - Widget only works during live streams
3. **Wait 60 seconds** - Health monitor will detect and force reconnect
4. **Restart** - Close main control window, restart `start_robust.bat`

### Rate Limited by TikTok

**Symptoms:**
- Widget says "Rate limited by TikTok - backing off"
- Retry delays getting longer (30s, 60s, 120s)

**Solutions:**
1. **Wait** - Widget will automatically retry with increasing delays
2. **Change account** - TikTok may have flagged your account
3. **Reduce activity** - Too many API requests can trigger limits

### Queue Full

**Symptoms:**
- "Queue full (200) - oldest requests removed"
- Requests being dropped

**Solutions:**
1. **Increase queue size:**
   ```batch
   set QUEUE_MAX=500
   start_robust.bat
   ```

2. **Clear queue manually:**
   - Open control panel: `http://localhost:5000/control`
   - Click "Clear Queue"

3. **Enable auto-cleanup:**
   - Already enabled! Old requests (24+ hours) auto-removed

### Connection Keeps Dropping

**Symptoms:**
- Constant "Connecting to TikTok Live..." messages
- Never stays connected long

**Possible Causes:**
1. **Not live on TikTok** - Widget can only connect when streaming
2. **Network issues** - Unstable internet connection
3. **TikTok API issues** - TikTok servers having problems
4. **Account restricted** - TikTok may have limited your account

**Solutions:**
1. Check your TikTok stream is actually live
2. Check your internet connection
3. Wait and retry - TikTok API issues usually resolve quickly
4. Try different network/VPN if account seems blocked

### Python/Widget Crashes

**Symptoms:**
- Widget Server window closes unexpectedly
- "Widget stopped! Restarting..." message

**What Happens:**
- `start_robust.bat` auto-restarts the widget
- Usually back up in 5 seconds
- Cloudflare tunnel stays connected

**If Crashes Repeatedly:**
1. Check logs for error pattern
2. Update Python packages:
   ```batch
   pip install --upgrade flask flask-socketio TikTokLive
   ```
3. Check system resources (RAM, CPU)

---

## Best Practices

### Before Going Live

✅ **Test everything locally first**
```batch
1. Start widget with start_robust.bat
2. Open http://localhost:5000 - should load
3. Test with demo mode if available
4. Verify all 4 windows are open
```

✅ **Check configuration**
- Skip threshold appropriate for your audience size
- Rate limits not too strict
- Queue size sufficient for stream length

✅ **Monitor for 5 minutes**
- Watch for any error messages
- Verify health checks running
- Confirm auto-restart works (close widget window to test)

### During Stream

✅ **Keep all windows visible** (or accessible)
- Don't minimize the main control window
- Widget Server shows live activity
- Health Monitor shows status

✅ **Watch for warnings**
- Health monitor alerts
- Rate limit messages
- Queue overflow warnings

✅ **Have backup plan**
- Know how to restart quickly
- Keep Cloudflare URL saved
- Have control panel bookmarked

### After Stream

✅ **Clean shutdown**
- Close main control window (closes all)
- Or press Ctrl+C in main window

✅ **Review logs**
- Check for any issues that occurred
- Note any patterns in disconnections
- Adjust settings if needed

✅ **Clear old data** (optional)
```batch
# Clear queue for next stream
# Open control panel and click "Clear Queue"
```

---

## Performance Tips

### For Long Streams (3+ hours)

1. **Increase cleanup frequency:**
   - Automatic cleanup every 10 minutes
   - Removes stale requests and rate limiter data

2. **Monitor queue size:**
   - Check periodically: `Queue is X/200`
   - Clear if needed via control panel

3. **Watch memory usage:**
   - Normal: 20-50MB RAM
   - High: 100MB+ (may need restart)

### For High-Activity Streams

1. **Adjust rate limits:**
   ```batch
   set RATE_LIMIT_MAX=15
   set RATE_LIMIT_WINDOW=60
   ```

2. **Increase queue size:**
   ```batch
   set QUEUE_MAX=500
   ```

3. **Monitor connection health:**
   - Should see events every 1-2 minutes
   - If quiet for 5+ minutes, connection may be stale

### For Low-Activity Streams

1. **Normal to see:**
   - "Last event was 300s ago"
   - Long periods between requests

2. **Health monitor will:**
   - Check connection is alive
   - Force reconnect if truly dead
   - Show warnings but keep running

---

## Emergency Recovery

### Widget Completely Dead

```batch
# Kill everything
taskkill /F /IM python.exe
taskkill /F /IM cloudflared.exe

# Wait 5 seconds
timeout /t 5

# Restart
start_robust.bat
```

### Can't Connect to TikTok

```batch
# Check username is correct
echo %TIKTOK_USER%

# Try manual connection
python live_widget.py

# Watch for specific error message
# If "not found" - username wrong
# If "not live" - you're not streaming
# If "rate limit" - wait 5 minutes and retry
```

### Cloudflare URL Changed

```batch
# Don't restart widget!
# Just restart cloudflare tunnel:

# Open new terminal
cloudflared tunnel --url http://localhost:5000

# Copy new URL
# Update in TikTok Studio
# Widget keeps running without interruption
```

---

## Technical Details

### Connection Health Monitoring

- **Check interval**: 60 seconds
- **Warning threshold**: 120 seconds no events
- **Critical threshold**: 300 seconds (5 minutes)
- **Force disconnect**: 3 consecutive critical checks (15 minutes)

### Reconnection Logic

- **Initial retry**: 15 seconds
- **Max retry delay**: 120 seconds
- **Backoff multiplier**: 1.5x on timeout, 2x on rate limit
- **Client refresh**: Every 10 failed attempts

### Resource Cleanup

- **Cleanup interval**: 600 seconds (10 minutes)
- **Stale request age**: 86400 seconds (24 hours)
- **Rate limiter cleanup**: Same as main cleanup
- **Chat history TTL**: 3600 seconds (1 hour)

### Queue Management

- **Default max**: 200 songs
- **Warning threshold**: 90% (180 songs)
- **Overflow behavior**: Drop oldest, keep newest
- **Logging**: All drops logged with details

---

## Files Reference

| File | Purpose |
|------|---------|
| `live_widget.py` | Main widget server with all improvements |
| `start_robust.bat` | Recommended launcher with monitoring |
| `start_simple.bat` | Basic launcher without monitoring |
| `watchdog.bat` | Standalone monitor (optional) |
| `logs\widget_*.log` | Activity logs by date |

---

## Summary

Your widget now has:

✅ **Auto-reconnection** - Never stops trying to connect
✅ **Health monitoring** - Detects and recovers from stale connections
✅ **Error recovery** - Handles errors gracefully without crashes
✅ **Auto-restart** - Restarts if it crashes
✅ **Smart retry** - Backs off when rate limited
✅ **Resource management** - Cleans up old data automatically
✅ **Real-time visibility** - See everything as it happens
✅ **Comprehensive logging** - Full activity history

**Use `start_robust.bat` for the most reliable experience!** 🚀

---

## Support

If issues persist:

1. **Check logs** - `logs\widget_[date].log`
2. **Look for patterns** - Same error repeatedly?
3. **Test connection** - `curl http://localhost:5000`
4. **Verify TikTok live** - Make sure you're actually streaming
5. **Update packages** - `pip install --upgrade TikTokLive`

The widget is now much more resilient and should stay running throughout your entire stream! 🎉