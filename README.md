# 🎰 Gamble Limited - Casino Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

A full-featured, self-hosted casino gaming platform built with Python and FastAPI. Features multiple games with dynamic odds, real-time updates via WebSockets, a complete user and admin management system, and a dynamic in-game economy.

---

## ⚡ Quickstart: Run Locally

### Prerequisites
- Python 3.10+
- `pip` for installing dependencies

### Installation & Setup
From your terminal, run the following commands to clone the repository, set up the environment, and start the development server:

```bash
# Clone the repository and navigate into it
git clone https://github.com/yourusername/RNG-THING.git
cd RNG-THING

# Run setup script (creates venv, installs deps, generates .env)
bash scripts/setup_dev.sh

# Activate the virtual environment
source venv/bin/activate

# Create a test user (testuser / password)
python scripts/create_test_user.py

# Run the server
python -m app.main
```

After the server starts, you can **login** at [http://localhost:8000](http://localhost:8000) with:
-   **Username:** `testuser`
-   **Password:** `password`

---

## ✨ Features

### 🎮 Games Included
| Game | Description | Dynamic Odds Control |
|------|-------------|----------------------|
| **🎰 Slots** | 3-reel slot machine with configurable symbol weights and payouts. | Yes |
| **🃏 Blackjack** | Classic 21 - Hit, Stand, Double Down. | No |
| **🎡 Roulette** | European style - Red/Black, Odd/Even, Dozens, Straight bets. | Yes |
| **📍 Plinko** | Ball drop with configurable center bias and peg multipliers. | Yes |
| **🪙 Coinflip** | 50/50 heads or tails with adjustable player odds. | Yes |
| **🎉 Gamble Friday** | Special high-stakes event, configurable and testable. | Yes |

### 🚀 Real-time Features (WebSockets)
- **Live Global Chat:** A chat room for all connected players.
- **Instant Balance Updates:** Your balance updates in real-time after every game.
- **Big Win Announcements:** Major wins are announced globally to all players.

### 👤 User System
- **Simple Login:** Username and passsord based login for players.
- **Persistent Balances:** Cash and Credits are stored in a SQLite database.
- **Secure Session Management:** Uses secure, cookie-based sessions.

### 🔐 Admin Panel
- **Password-Protected:** Secure admin panel at a configurable path.
- **User Management:** View all users, grant funds, reset balances, or delete users.
- **Platform Statistics:** See totals for users, games played, and amounts wagered.
- **Leaderboard:** View the top players by winnings.
- **Live Odds Configuration:** Modify game odds in real-time by editing `ODDS-CHANGER.json`.
- **Data Management:** Clear all platform data with a single click.

### 💱 Economy
- **Dual Currency:** In-game economy with Cash ($) and Credits (CR).
- **Dynamic Exchange Rates:** The exchange rate between Cash and Credits fluctuates automatically.
- **Starting Balance:** New users start with a configurable amount of both currencies.

---

## 🛠️ Developer Utilities

### WebSocket Logging Verification
The project includes a utility script to help verify that WebSocket connections, disconnections, and messages are being logged correctly. This is useful when working on features related to real-time events or debugging the logging setup.

To run the script, first ensure the main application server is running in a separate terminal:
```bash
# In terminal 1:
python -m app.main
```

Then, in a second terminal, run the verification script:
```bash
# In terminal 2 (with venv activated):
python scripts/verify_ws_logging.py
```
The script will connect to the WebSocket, send a ping, receive a pong, and then disconnect. You should see corresponding log entries in the output of the main application server.

---

## 🧪 Testing

The project includes a custom test suite to verify core functionality, including database operations, game logic, and configuration loading.

To run the tests, execute the following command from the root of the repository:
```bash
python -m tests.test_all
```
The test script will output the results to the console. All tests should pass before committing code.

---

## 🐳 Docker Deployment (Recommended for Production)

This guide is for Debian-based Linux distributions like Ubuntu.

### 1. Install Docker and Docker Compose
If you don't have Docker installed, you can use the official convenience script:
```bash
# Download and run the Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin -y
```

### 2. Prepare the Environment
Create a `.env` file for your production configuration.
```bash
cp .env.example .env
```
**Important:** You must change the `SECRET_KEY` in your `.env` file to a long, random string for security.

### 3. Build and Run with Docker Compose
Use the provided `docker-compose.yml` file to build and run the application in a detached container.
```bash
sudo docker-compose up --build -d
```
Your casino platform is now running on port 8000.

### 4. Managing the Container
- **View logs:** `sudo docker-compose logs -f`
- **Stop the container:** `sudo docker-compose stop`
- **Start the container:** `sudo docker-compose start`
- **Stop and remove the container:** `sudo docker-compose down`

---

## 🛠️ Production Management (`manage.sh`)

For production environments, the `manage.sh` script is the recommended tool for managing the application lifecycle. It provides a simple, menu-driven interface for common administrative tasks.

**Key Features:**
- **Automated Setup:** Installs required dependencies like Docker, `jq`, and `git`.
- **Guided Configuration:** Interactive prompts for setting up your `.env` and `config.json` files.
- **Application Lifecycle:** Start, stop, and view logs for your application containers.
- **Automatic Updates:** Safely pulls the latest changes from the Git repository.
- **Data Management:** Perform a factory reset to clear all user data.

### Usage
The script must be run as root.

```bash
sudo bash manage.sh
```

---

## ⚙️ Configuration

The application's configuration is managed through a combination of environment variables and JSON files, allowing for both security and flexibility.

-   **.env:** The primary method for configuring secure and environment-specific settings. It overrides any values in `config.json`. A template is provided in `.env.example`.
-   **config.json:** Contains the base configuration for game settings, economy parameters, and admin credentials.
-   **ODDS-CHANGER.json:** Allows for real-time modification of game odds without restarting the server.

### Changing the Admin Password
To set or change the admin password, modify the `admin_password_hash` in `config.json` with a plain-text password. The server will automatically hash it on the first startup.

---

## 📁 Project Structure
```
RNG-THING/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration loader
│   ├── core/                # Core logic (DB, economy, games)
│   ├── routers/             # API and page routers
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS/JS files
├── data/
│   └── casino.db            # SQLite database (auto-created)
├── .env.example             # Environment variable template
├── config.json              # Main configuration
├── ODDS-CHANGER.json        # Dynamic game odds
├── docker-compose.yml       # Docker Compose file
├── Dockerfile               # Docker build file
└── requirements.txt         # Python dependencies
```

---

## 🛠️ API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Logs in a user. |
| POST | `/auth/register` | Creates a new user account. |
| POST | `/auth/admin-login` | Logs in an admin. |
| GET | `/logout` | Logs out the current user. |

### Economy
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/economy/rate` | Gets the current currency exchange rate. |
| GET | `/api/economy/balance` | Retrieves the user's balance.
| POST | `/api/economy/exchange` | Exchanges currency. |
| GET | `/api/economy/transactions` | Gets the user's transaction history. |
| POST | `/api/economy/daily` | Claims the daily bonus. |

### Games
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/games/slots/spin` | Spins the slot machine. |
| POST | `/api/games/blackjack/deal` | Deals a new hand of Blackjack. |
| POST | `/api/games/blackjack/hit` | Hits in the current Blackjack game. |
| POST | `/api/games/blackjack/stand`| Stands in the current Blackjack game. |
| POST | `/api/games/roulette/spin` | Spins the roulette wheel. |
| POST | `/api/games/plinko/drop` | Drops a ball in the Plinko machine. |
| POST | `/api/games/coinflip/flip`| Flips a coin. |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/api/reset-user` | Resets a user's balance. |
| POST | `/admin/api/delete-user` | Deletes a user. |
| POST | `/admin/api/grant-funds` | Grants funds to a user. |
| POST | `/admin/api/clear-all` | Clears all data. |
| POST | `/admin/api/change-password` | Changes the admin password. |

---

## 🚀 Deployment (Production)

While Docker is the recommended method for deployment, you can also run the application directly on a server. For exposing your application to the internet, we strongly recommend using a reverse proxy like Nginx and placing it behind Cloudflare for security and performance.

### Non-Docker Deployment
For running the application without Docker, you will need:
- A process manager like `gunicorn` to handle the application workers.
- A `systemd` service to ensure the application runs continuously and restarts on failure.
- An Nginx reverse proxy to handle incoming traffic and SSL.

### Cloudflare
Using Cloudflare provides SSL, DDoS protection, and caching. You can connect your server to Cloudflare using:
- **Cloudflare Tunnels (Recommended):** A secure way to expose your server without opening firewall ports.
- **Traditional DNS with Nginx:** Pointing your domain to your server's IP and using Nginx to handle SSL.

**For detailed, step-by-step instructions on setting up Nginx, systemd, and Cloudflare, please refer to the `CLOUDFLARE.md` file in this repository.**

---

## 🤝 Contributing

1.  Fork the repository
2.  Create a feature branch (`git checkout -b feature/amazing`)
3.  Commit changes (`git commit -m 'Add amazing feature'`)
4.  Push to branch (`git push origin feature/amazing`)
5.  Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

**⚠️ Disclaimer**: This is a fictional casino for entertainment purposes only. No real money gambling is involved.
