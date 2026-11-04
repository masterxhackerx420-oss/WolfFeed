# WolfFeed

**Portable local social feed** inspired by Facebook.  
Python (Flask) + HTML + CSS + JavaScript. No cloud, no tracking — runs entirely on your machine.

[![Download](https://img.shields.io/badge/Download-ZIP-blue?style=for-the-badge)](https://github.com/masterxhackerx420-oss/WolfFeed/archive/refs/heads/main.zip)

## Features
- User registration & login (local SQLite)
- Create posts, like, and comment
- Live-updating feed (auto-refreshes every 5 seconds)
- Multiple modes: Classic, Live, Stories, Groups
- Dark / light theme toggle
- Fully portable — just download and run

## Quick Start

### Download
Click the button above or use the green **Code → Download ZIP** button on this page.

### Run
1. Extract the folder
2. **Windows**: Double-click `run.bat`
3. **Linux / Mac**:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
4. Open http://127.0.0.1:5000

Requires Python 3.8+.

Data is stored in `wolffeed.db` in the same folder. Delete the file to reset everything.

## Modes
- **Classic** — Standard chronological feed
- **Live** — Emphasizes recent activity
- **Stories** — Short-form style posts
- **Groups** — Filtered group-style view

## License
MIT

Built for DebianGang / WolfSec style local tools.
