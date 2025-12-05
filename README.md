# 🎰 Gamble Limited - Casino Platform

A full-featured casino gaming platform built with Python FastAPI. Features multiple games, user accounts, admin management, and dynamic economy.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🎮 Games
| Game | Description | Odds |
|------|-------------|------|
| **🎰 Slots** | 3-reel slot machine with symbols (🍒🍋🍊🔔⭐💎) | RTP ~95% |
| **🃏 Blackjack** | Classic 21 - Hit, Stand, Double Down | House edge ~2% |
| **🎡 Roulette** | European style - Red/Black, Odd/Even, Dozens, Straight | Standard odds |
| **📍 Plinko** | Ball drop through pegs with multiplier slots | House edge ~15% |
| **🪙 Coinflip** | 50/50 heads or tails | 1.95x payout |

### 👤 User System
- **Username-based login** - No password required for players
- **Create new accounts** instantly
- **Persistent balances** - Cash and Credits tracked in SQLite
- **Session management** via cookies

### 🔐 Admin Features
- **Password-protected admin panel** (`/admin`)
- **Infinite funds** for admin accounts
- **User management**:
  - View all users with stats
  - Grant cash/credits to any user
  - Reset user balances to default
  - Delete users permanently
  - Clear all platform data
- **Platform statistics**: Total users, games played, wagered amounts
- **Leaderboard**: Top players by winnings
- **Game breakdown**: Per-game statistics
- **Change admin password**

### 💱 Economy
- **Dual currency**: Cash ($) and Credits (CR)
- **Dynamic exchange rates**: Fluctuate ±5% every 30 seconds
- **Conversion penalty**: Frequent converters get worse rates (up to 15%)
- **Starting balance**: $1000 cash + 500 credits

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/RNG-THING.git
cd RNG-THING

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m app.main
```

The server will start at **http://localhost:8000**

### First Login
1. Visit `http://localhost:8000` (redirects to `/auth`)
2. Click **"New Player"** tab
3. Enter a username (3+ characters)
4. Click **"Create Account"**
5. Start playing!

### Admin Access
1. Click **"🔐 Admin"** tab on login page
2. Enter admin password (default: `admin123`)
3. Access full admin panel at `/admin`

## 📁 Project Structure

```
RNG-THING/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration loader
│   ├── core/
│   │   ├── database.py      # SQLite database wrapper
│   │   ├── economy.py       # Currency exchange system
│   │   ├── rng.py           # Random number generation
│   │   └── games/
│   │       ├── slots.py     # Slot machine logic
│   │       ├── blackjack.py # Blackjack game logic
│   │       ├── roulette.py  # Roulette game logic
│   │       ├── plinko.py    # Plinko game logic
│   │       └── coinflip.py  # Coinflip game logic
│   ├── routers/
│   │   ├── pages.py         # HTML page routes
│   │   ├── api.py           # Game API endpoints
│   │   ├── auth.py          # Authentication routes
│   │   └── admin.py         # Admin panel routes
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html        # Base layout
│   │   ├── index.html       # Home page
│   │   ├── login.html       # Auth page
│   │   ├── admin.html       # Admin panel
│   │   ├── exchange.html    # Currency exchange
│   │   └── [game].html      # Game pages
│   └── static/
│       ├── css/style.css    # Main stylesheet
│       └── js/main.js       # Client JavaScript
├── data/
│   └── casino.db            # SQLite database (auto-created)
├── config.json              # Server configuration
├── requirements.txt         # Python dependencies
└── README.md
```

## ⚙️ Configuration

Edit `config.json` to customize:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": true,
    "name": "Gamble Limited"
  },
  "security": {
    "admin_username": "admin",
    "admin_password_hash": "YOUR_BCRYPT_HASH",
    "secret_key": "CHANGE_THIS_IN_PRODUCTION"
  },
  "economy": {
    "starting_cash": 1000.0,
    "starting_credits": 500.0,
    "base_exchange_rate": 10.0,
    "fluctuation_range": 0.05
  },
  "games": {
    "slots": { "min_bet": 10, "max_bet": 1000 },
    "blackjack": { "min_bet": 20, "max_bet": 2000 },
    "roulette": { "min_bet": 5, "max_bet": 5000 },
    "plinko": { "min_bet": 1, "max_bet": 1000 },
    "coinflip": { "min_bet": 1, "max_bet": 10000 }
  }
}
```

### Changing Admin Password
You can set a plain text password in `config.json` - it will be automatically hashed on first server start:

```json
"admin_password_hash": "YourNewPassword123"
```

Or change it from the admin panel.

## 🛠️ API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth` | Login/register page |
| POST | `/auth/login` | User login |
| POST | `/auth/register` | Create new user |
| POST | `/auth/admin-login` | Admin login |
| GET | `/logout` | Logout |

### Games
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/games/slots/spin` | Spin slot machine |
| POST | `/api/games/blackjack/deal` | Start blackjack hand |
| POST | `/api/games/blackjack/action` | Hit/Stand/Double |
| POST | `/api/games/roulette/spin` | Spin roulette wheel |
| POST | `/api/games/plinko/drop` | Drop plinko ball |
| POST | `/api/games/coinflip/flip` | Flip coin |

### Economy
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/economy/balance` | Get user balance |
| GET | `/api/economy/rate` | Get exchange rate |
| POST | `/api/economy/exchange` | Convert currency |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin` | Admin panel |
| POST | `/admin/api/reset-user` | Reset user balance |
| POST | `/admin/api/delete-user` | Delete user |
| POST | `/admin/api/grant-funds` | Grant cash/credits |
| POST | `/admin/api/clear-all` | Clear all data |
| POST | `/admin/api/change-password` | Change admin password |

## 🔒 Security Notes

- Admin passwords are hashed with **bcrypt**
- Session cookies expire after 1 year (user) / 1 hour (admin)
- No sensitive data stored in plaintext
- Rate limiting recommended for production

## 📝 Dependencies

```
fastapi>=0.100.0
uvicorn>=0.23.0
jinja2>=3.1.0
python-multipart>=0.0.6
pydantic>=2.0.0
bcrypt>=4.0.0
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

---

**⚠️ Disclaimer**: This is a fictional casino for entertainment purposes only. No real money gambling is involved.
