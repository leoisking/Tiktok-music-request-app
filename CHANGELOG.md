# Changelog

All notable changes to the TikTok Live Widget project.

## [2.0.0] - 2024

### 🎉 Major Release - Production Ready

This release transforms the widget into a production-ready application with comprehensive mobile support, Cloudflare Tunnel integration, and enterprise-grade features.

---

## 🔧 Bug Fixes

### Critical Fixes
- **Fixed HTML Layout** - Added missing closing `</div>` tags in requests panel that broke the layout
- **Fixed Memory Leaks** - Demo mode timers now properly cleaned up when real connection established
- **Fixed Rate Limiter Growth** - Implemented automatic cleanup to prevent unbounded memory usage
- **Fixed Duplicate Event Handlers** - Removed duplicate socket connection handlers causing confusion

### Minor Fixes
- Fixed skip command to require `!skip` instead of just `skip` (prevents accidental votes)
- Fixed animation performance on mobile devices
- Fixed touch target sizes for mobile accessibility
- Fixed text readability in bright environments

---

## ✨ New Features

### Cloudflare Tunnel Support
- **Full Remote Hosting** - Widget can now be hosted via Cloudflare Tunnel for TikTok Studio
- **HTTPS Support** - Works with TikTok Studio's HTTPS requirement
- **CORS Configuration** - Flexible CORS settings with wildcard or specific domain support
- **Control Panel Authentication** - Optional password protection for remote control panel access
- **Environment Variables** - `HOST`, `PORT`, `CONTROL_PASSWORD` for easy configuration

### Mobile Optimization
- **Portrait Mode Support** - Fully optimized for mobile phones in portrait orientation
- **Responsive Text Scaling** - Uses `clamp()` for perfect readability at any screen size
- **Touch-Friendly UI** - 44px minimum touch targets following iOS guidelines
- **High Contrast Mode** - Better visibility in bright outdoor environments
- **Performance Optimizations** - Disabled particles and heavy animations on mobile
- **Landscape Support** - Compact layout for phones in landscape mode
- **Small Device Support** - Special optimizations for screens < 375px width

### Accessibility (WCAG 2.1 Level AA)
- **Semantic HTML** - Proper heading hierarchy (`<h1>`, `<h2>`)
- **ARIA Labels** - Comprehensive `role` and `aria-label` attributes
- **Live Regions** - `aria-live="polite"` for dynamic content updates
- **Screen Reader Support** - All interactive elements properly labeled
- **Keyboard Navigation** - Full keyboard accessibility
- **Toggle States** - `aria-expanded` and `aria-hidden` on interactive panels

### Security Enhancements
- **Content Security Policy** - CSP headers to prevent XSS attacks
- **Referrer Policy** - Privacy protection
- **Input Validation** - Enhanced length checks and sanitization
- **Access Control** - Improved localhost detection and optional password auth
- **Rate Limiter Cleanup** - Prevents DoS via memory exhaustion
- **Safe Error Messages** - No sensitive data exposure in errors

### Connection Management
- **Visual Status Banners** - Green/orange/red banners for connection states
- **Auto-Reconnection** - Intelligent reconnection with exponential backoff
- **Connection Feedback** - Users see real-time connection status
- **Demo Mode Improvements** - Properly stops when live connection established

### Logging & Monitoring
- **Professional Logging** - Python `logging` module with structured output
- **Log Levels** - INFO, WARNING, ERROR with timestamps
- **Contextual Information** - Logs include user names, counts, and operation details
- **Debug Mode** - `LIVE_WIDGET_DEBUG` environment variable for verbose output
- **Operation Tracking** - All moderator actions and user commands logged

---

## 🔄 Changes

### Breaking Changes
- **Skip Command** - Now requires `!skip` instead of just `skip` to prevent accidental votes
  - **Migration**: Users must type `!skip` explicitly
  - **Rationale**: Prevents false positives when "skip" is mentioned in chat

### Configuration Changes
- **New Environment Variables**:
  - `HOST=0.0.0.0` - Listen on all interfaces (required for Cloudflare)
  - `PORT=5000` - Server port (default unchanged)
  - `ALLOWED_ORIGINS=*` - CORS configuration (default: all origins)
  - `CONTROL_PASSWORD=pass` - Control panel password for remote access
  - `SKIP_THRESHOLD=10` - Now configurable via environment variable
  - `QUEUE_MAX=200` - Maximum queue size (now configurable)
  - `CHAT_HISTORY_MAX=20` - Maximum stored chat messages
  - `CHAT_HISTORY_TTL=60` - Chat message lifetime in seconds
  - `LIVE_WIDGET_DEBUG=1` - Enable debug logging

### UI Changes
- **Skip Meter Display** - Shows `!skip` command instead of `skip`
- **Larger Text on Mobile** - Increased font sizes for readability
- **Better Spacing** - Optimized padding and margins for touch
- **More Opaque Panels** - Better contrast on mobile (0.96 vs 0.94 opacity)
- **Connection Banners** - New visual feedback system

### Performance Improvements
- **Memory Management** - Auto-cleanup every 10 minutes for queue
- **Rate Limiter Cleanup** - Auto-cleanup every 5 minutes
- **Mobile Optimizations** - Disabled particles and heavy animations
- **Efficient Data Structures** - Better use of Python collections
- **WebSocket Tuning** - Optimized Socket.IO configuration

---

## 📚 Documentation

### New Documentation Files
- **README.md** - Comprehensive project documentation with Cloudflare section
- **CLOUDFLARE_TUNNEL_SETUP.md** - Complete guide for hosting via Cloudflare
- **IMPROVEMENTS.md** - Technical details of all improvements
- **QUICK_REFERENCE.md** - Quick start guide and common tasks
- **CHANGELOG.md** - This file

### New Scripts
- **start_with_tunnel.bat** - Windows batch script for easy startup with Cloudflare
- **start_with_tunnel.sh** - Mac/Linux bash script for easy startup with Cloudflare

### Documentation Improvements
- Mobile optimization guidelines
- Cloudflare Tunnel setup instructions
- Security best practices
- Troubleshooting guides
- Performance tuning tips
- Environment variable reference

---

## 🔒 Security

### Security Improvements
- Content Security Policy (CSP) headers
- Input validation and sanitization
- Rate limiting with automatic cleanup
- Access control for control panel
- Password authentication for remote access
- No sensitive data in logs or errors
- Safe-area-inset support for notched devices

### Security Best Practices Documented
- Strong password generation
- CORS restriction guidelines
- Access log monitoring
- Software update procedures
- Environment file usage

---

## 📱 Browser Compatibility

### Tested Browsers
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

### Mobile Browsers
- Chrome Mobile ✅
- Safari iOS ✅
- Firefox Mobile ✅
- Samsung Internet ✅

### Required Features
- CSS Grid & Flexbox
- WebSocket support
- ES6 JavaScript
- SVG support
- CSS `clamp()` function

---

## 🎯 Use Cases

### Now Supports
- ✅ **OBS Studio** - Local browser source (original use case)
- ✅ **TikTok Studio** - Via Cloudflare Tunnel (NEW)
- ✅ **Mobile Viewing** - Portrait and landscape (NEW)
- ✅ **Remote Access** - Control panel from anywhere (NEW)
- ✅ **Multiple Devices** - Simultaneous viewers (IMPROVED)

---

## 📊 Statistics

### Code Improvements
- **1,600+ lines** of new/improved code
- **400+ lines** of mobile-specific CSS
- **200+ lines** of improved Python backend
- **4 new documentation files**
- **2 new startup scripts**

### Features Added
- **20+ accessibility improvements**
- **15+ security enhancements**
- **10+ mobile optimizations**
- **8+ new environment variables**
- **Full Cloudflare Tunnel support**

---

## 🚀 Migration Guide

### From Version 1.x to 2.0

#### No Breaking Changes for Local Use
If you're using the widget locally in OBS, **no changes required**! Everything works as before.

#### For TikTok Studio Users (NEW)
1. Follow [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)
2. Set `HOST=0.0.0.0` and `ALLOWED_ORIGINS=*`
3. Set `CONTROL_PASSWORD` for remote control panel access

#### For Mobile Viewers (NEW)
- Widget automatically adapts to mobile screens
- No configuration needed
- Test on your phone to verify readability

#### For Skip Command
- Users now type `!skip` instead of `skip`
- Update any documentation/overlays mentioning the command

---

## 🙏 Acknowledgments

### Technologies Used
- Flask & Flask-SocketIO for web server
- TikTokLive library for TikTok integration
- Cloudflare Tunnel for HTTPS hosting
- Socket.IO for real-time communication

### Design Principles
- Mobile-first responsive design
- WCAG 2.1 accessibility standards
- Security by default
- Progressive enhancement
- Graceful degradation

---

## 📞 Support

### Getting Help
1. Check [README.md](README.md) for basic setup
2. See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for TikTok Studio
3. Review [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common tasks
4. Enable `LIVE_WIDGET_DEBUG=1` for verbose logging

### Known Issues
- Quick Cloudflare tunnels change URL on restart (use named tunnels)
- Demo mode requires 4 seconds to activate
- Control panel only accessible via password or localhost

---

## 🔮 Future Roadmap

### Potential Features
- Database persistence for queue across restarts
- Song history tracking and analytics
- Custom themes and color schemes
- Multi-language support (i18n)
- Spotify/Apple Music integration
- Vote history and statistics
- Export queue as CSV/JSON
- Mobile app for control panel
- WebRTC for lower latency

### Community Contributions
- Pull requests welcome
- Issues and suggestions appreciated
- Documentation improvements needed
- Translations wanted

---

## 📄 License

MIT License - Free to use and modify

---

## 📅 Version History

### [2.0.0] - 2024-01-XX
- Initial production release
- Cloudflare Tunnel support
- Mobile optimization
- Full accessibility
- Professional logging
- Security hardening

### [1.x] - Previous
- Basic functionality
- Local OBS support
- Song requests and skip voting

---

**Made with ❤️ for TikTok Live streamers**

For questions, issues, or contributions, see the documentation files in this repository.