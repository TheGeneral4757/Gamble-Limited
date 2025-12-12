# Project Improvements & Roadmap

This document outlines a comprehensive list of improvements, fixes, and new features for the RNG-THING project. Items are categorized by type and sorted from easiest to hardest to implement.

---

## 🚀 Critical Fixes & Architecture (High Priority)

These changes address stability, performance, and best practices.

1.  **Async Database Implementation** (Medium)
    *   **Issue:** The current `sqlite3` driver is synchronous and blocks the FastAPI event loop, which kills performance under load.
    *   **Fix:** Migrate to `aiosqlite` or use an async ORM like **Tortoise ORM** or **SQLAlchemy (Async)**.
    *   **Benefit:** Massive performance boost and non-blocking concurrent request handling.

2.  **Persistent Session Storage** (Medium)
    *   **Issue:** `SESSIONS = {}` in `security.py` is in-memory. If the server restarts or spawns multiple workers (like in production on Linux), users get logged out or sessions desync.
    *   **Fix:** Use a database table for sessions or an external store like Redis.
    *   **Benefit:** Sessions survive restarts and work across multiple worker processes.
    NOTE: Current storeage gets courrupted when the game is updated, make it so as much progress as possible is saved when an update happons, eg, the server checks .db file and adjuss it or itleast copys it to save as much data as possible.

3.  **Centralized Logging** (Easy)
    *   **Issue:** `print()` statements are used for logging.
    *   **Fix:** Implement Python's `logging` module with a configuration in `config.py` (e.g., file rotation, console output, different log levels).
    *   **Benefit:** Better debugging, error tracking, and cleaner console output.

4.  **Configuration Management** (Easy)
    *   **Issue:** `DB_PATH` and `CONFIG_PATH` are hardcoded relative paths.
    *   **Fix:** Use environment variables (via `python-dotenv`) to override config paths, or determine paths relative to the `__file__` location to avoid CWD issues.
    *   **Benefit:** "Run from anywhere" reliability and safer secret management.

---

## 🛡️ Security Improvements

1.  **Rate Limiting** (Easy)
    *   **Add:** Implement `slowapi` or custom middleware to limit requests per minute for game endpoints (e.g., `/games/slots/spin`).
    *   **Why:** Prevents script-based spamming/abuse of the economy.

2.  **Input Validation Sanitization** (Easy)
    *   **Add:** Ensure all user inputs (even usernames) are sanitized to prevent HTML injection if displayed on leaderboards (though Jinja2 auto-escapes, it's good practice).
    *   **Why:** Defense in depth.

3.  **Secure Headers** (Easy)
    *   **Add:** Middleware to add headers like `X-Frame-Options`, `X-Content-Type-Options`, and `Content-Security-Policy`.
    *   **Why:** Protects against clickjacking and XSS.

---

## ✨ New Features

### Easy
1.  **Game History UI:** Create a page showing the user's last 50 games/transactions (API already exists in `db.get_transactions`).
2.  **Daily Bonus:** Add a `/api/economy/daily` endpoint that gives free cash once every 24 hours. Changeable in config.

### Medium
3.  **Leaderboard Page:** A dedicated UI page to show top players by wins, total wagered, etc. (Backend logic exists in `db.get_leaderboard`).
4.  **Admin Dashboard UI:** A proper web interface for the admin to view stats, ban users, or reset balances without using raw SQL or CLI.
5.  **User Profiles:** Users will now sign in with a username and password, and their profile will be saved to the database. Account creation limit will be added for 1 user per real person (enforced by any way needed) New Terms of Service and Privacy Policy will be added to the website. as well. Admin Profile will be hidden when signing in and such, will have to log in in a more secretive way. TOS and Privacy Policy will be left blank for now. Server must check if a username is already taken before allowing a new account to be created.

### Hard
6.  **Real-time Updates (WebSockets):**
    *   **Feature:** Use WebSockets to push balance updates or global "Big Win" announcements to all connected clients instantly.
    *   **Benefit:** Makes the casino feel "live" and multiplayer.
7.  **Chat System:** A global chat room for logged-in users (requires WebSockets).

---

## 🐧 Linux & Web Hosting Preparation Guide (Debian Based)

To run this script on a Linux server (VPS) or host it on the web, follow these steps:

### 1. Environment Setup
Linux file systems are case-sensitive and handle paths differently.
*   **Action:** Ensure all path joins usage `pathlib.Path` (you are already doing this mostly, which is good!).
*   **Action:** Create a `requirements.txt` with locked versions (run `pip freeze > requirements.txt`).

### 2. WSGI/ASGI Server (Gunicorn + Uvicorn)
Do not use `python main.py` in production. It is for development only.
*   **Install:** `pip install gunicorn uvicorn`
*   **Command:** Run the app using Gunicorn as a process manager with Uvicorn workers:
    ```bash
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
    ```
    *   `-w 4`: Runs 4 worker processes (adjust based on CPU cores).
    *   `--bind`: Exposes it to the network.

### 3. Systemd Service (Keep it running)
Create a service file so the bot starts on boot and restarts if it crashes.
*   **File:** `/etc/systemd/system/rngthing.service`
    ```ini
    [Unit]
    Description=RNG-THING Web Server
    After=network.target

    [Service]
    User=www-data
    Group=www-data
    WorkingDirectory=/opt/rng-thing
    ExecStart=/usr/local/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 127.0.0.1:8000
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

### 4. Reverse Proxy (Nginx)
Don't expose Python directly to the internet. Use Nginx to handle SSL (HTTPS) and static files.
*   **Config:**
    ```nginx
    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /static {
            alias /opt/rng-thing/app/static;
        }
    }
    ```

### 5. Docker
Containerize the application to avoid "it works on my machine" issues.
*   **Dockerfile:**
    ```dockerfile
    FROM python:3.10-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
    ```

---

## 🐛 Minor Fixes / Code Quality

1.  **Refactor `api.py`:** Move validation logic (`validate_bet`) and economy logic out of the router and into `app/core/services.py`. The router should only handle HTTP request/response.
2.  **Type Hinting:** Add return types to all functions in `main.py` and routers for better IDE support.
3.  **Error Handling:** Create a global exception handler in `main.py` to catch unhandled errors and return a JSON response instead of a sterile 500 page.


NOTE: Current code/testing is on windows, ensire that it can still be tested on windows as well.