#!/bin/bash

# ==============================================================================
# Gamble Limited - Management Script
# ==============================================================================
# Unified tool for Updates, Configuration, Deployment, and Maintenance.
#
# Features:
# - Smart Git Updates (Safe mode if not a repo)
# - Database Migration Reporting
# - Configuration Management
# - Container Control (Start, Stop, Restart, Logs)
# ==============================================================================

# --- Color Codes ---
C_RESET='\033[0m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_BLUE='\033[1;34m'
C_CYAN='\033[0;36m'
C_MAGENTA='\033[0;35m'
C_BOLD='\033[1m'

# --- Flags & Globals ---
DB_CODE_CHANGED=false
UPDATE_AVAILABLE=false
RECONFIGURE_REQUESTED=false

# --- Helper Functions ---
function print_banner {
    clear
    echo -e "${C_MAGENTA}"
    echo "  ________                ___.   .__           "
    echo " /  _____/_____    _____\_ |__ |  |   ____  "
    echo "/   \  ___\__  \  /     \| __ \|  | _/ __ \ "
    echo "\    \_\  \/ __ \|  Y Y  \ \_\ \  |_\  ___/ "
    echo " \______  (____  /__|_|  /___  /____/\___  >"
    echo "        \/     \/      \/    \/          \/ "
    echo -e "${C_RESET}"
    echo -e "${C_CYAN}       >>> Management Console <<<${C_RESET}"
    echo -e "${C_BLUE}==============================================${C_RESET}"
}

function print_info { echo -e "${C_BLUE}[INFO]${C_RESET} $1"; }
function print_success { echo -e "${C_GREEN}[SUCCESS]${C_RESET} $1"; }
function print_warning { echo -e "${C_YELLOW}[WARNING]${C_RESET} $1"; }
function print_error { echo -e "${C_RED}[ERROR]${C_RESET} $1"; } # Don't exit here to allow menu loop

function check_root {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${C_RED}Error: This script must be run as root.${C_RESET}"
        exit 1
    fi
}

function install_dependencies {
    if ! command -v git &> /dev/null || ! command -v jq &> /dev/null; then
         print_info "Installing dependencies..."
         if command -v apt-get &> /dev/null; then
             apt-get update -y > /dev/null 2>&1
             apt-get install -y curl jq git > /dev/null 2>&1
         else
             print_warning "apt-get not found. Please install 'git' and 'jq' manually."
         fi
    fi
    
    if ! command -v docker &> /dev/null; then
        print_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
    fi
}

# --- Update Logic ---
function check_for_updates {
    if [ ! -d ".git" ]; then
        print_warning "This folder is not a Git repository."
        print_warning "Automatic updates are disabled."
        read -p "Press Enter to continue..."
        return
    fi

    print_info "Checking GitHub for updates..."
    git remote update > /dev/null 2>&1

    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    BASE=$(git merge-base @ @{u})

    if [ "$LOCAL" = "$REMOTE" ]; then
        print_success "Up to date."
        UPDATE_AVAILABLE=false
    elif [ "$LOCAL" = "$BASE" ]; then
        print_success "New version available!"
        UPDATE_AVAILABLE=true
        handle_update
    elif [ "$REMOTE" = "$BASE" ]; then
        print_warning "Local changes detected. Cannot safely update."
        UPDATE_AVAILABLE=false
    else
        print_warning "Branch divergence detected. Cannot automatically update."
        UPDATE_AVAILABLE=false
    fi
    
    # Pause if no update or error
    if [ "$UPDATE_AVAILABLE" = false ]; then
        read -p "Press Enter to continue..."
    fi
}

function handle_update {
    read -p "Download and apply updates? [Y/n]: " OPT
    OPT=${OPT:-Y}
    [[ ! "$OPT" =~ ^[Yy]$ ]] && return

    # Check for DB changes
    CHANGED=$(git diff --name-only HEAD..@{u})
    if echo "$CHANGED" | grep -q "app/core/database.py"; then
        DB_CODE_CHANGED=true
        print_warning "Update includes database changes. Migration logs will be shown."
    fi

    # Auto-stash local changes to prevent conflict errors
    STASHED=false
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Local changes detected. Stashing them to proceed..."
        git stash push -m "Auto-stash by manage.sh"
        STASHED=true
    fi

    if ! git pull; then
        print_error "Git pull failed."
        # Try to restore if we stashed
        [ "$STASHED" = true ] && git stash pop
        return
    fi
    
    if [ "$STASHED" = true ]; then
        print_info "Restoring local changes..."
        # We accept that this might cause a conflict marker in the file
        git stash pop > /dev/null 2>&1
    fi
    
    # Version Bump
    VERSION_FILE="version.txt"
    [ ! -f "$VERSION_FILE" ] && echo "1.0.0" > "$VERSION_FILE"
    CUR_VER=$(cat "$VERSION_FILE")
    
    echo -e "Current Version: ${C_BOLD}$CUR_VER${C_RESET}"
    echo "Update Type: 1) Major  2) Normal  3) Minor  4) Keep Current"
    read -p "Select: " U_TYPE
    
    IFS='.' read -r -a P <<< "$CUR_VER"
    case $U_TYPE in
        1) NEW_VER="$((P[0]+1)).0.0" ;;
        2) NEW_VER="${P[0]}.$((P[1]+1)).0" ;;
        3) NEW_VER="${P[0]}.${P[1]}.$((P[2]+1))" ;;
        *) NEW_VER="$CUR_VER" ;;
    esac
    
    echo "$NEW_VER" > "$VERSION_FILE"
    print_success "Version updated to $NEW_VER"
    read -p "Press Enter to continue..."
}

# --- Configuration ---
function interact_config {
    print_info "Starting Configuration Wizard..."
    
    read -p "Enter SECRET_KEY (leave empty to generate): " SECRET_KEY
    [ -z "$SECRET_KEY" ] && SECRET_KEY=$(openssl rand -hex 32)
    
    while true; do
        read -s -p "Admin Password: " PASS
        echo ""
        [ -n "$PASS" ] && break
    done

    while true; do
        read -p "Server Port [8000]: " PORT
        PORT=${PORT:-8000}
        if [[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ]; then
             break
        else
             print_error "Invalid port. Please enter a number between 1 and 65535."
        fi
    done
    
    read -p "Cloudflare Tunnel Token (optional): " CF_TOKEN
    
    read -p "Enable Nginx Proxy? (y/N): " NGINX_OPT
    
    # Write Files
    echo "SECRET_KEY=${SECRET_KEY}" > .env
    echo "SERVER_PORT=${PORT}" >> .env
    [ -n "$CF_TOKEN" ] && echo "CF_TUNNEL_TOKEN=${CF_TOKEN}" >> .env
    
    # Generate config.json (simplified for brevity, ensuring key fields)
    jq -n --arg port "$PORT" --arg pass "$PASS" \
    '{
      server: {host: "0.0.0.0", port: $port, debug: false, name: "Gamble Limited"},
      security: {admin_username: "admin", admin_password_hash: $pass, secret_key: "from_env"},
      economy: {starting_cash: 1000.0, starting_credits: 500.0, daily_bonus_amount: 100.0, house_cut_percent: 5.0},
      games: {
        slots: {enabled: true, min_bet: 10, max_bet: 1000, payout_rate: 0.95},
        blackjack: {enabled: true, min_bet: 20, max_bet: 2000},
        roulette: {enabled: true, min_bet: 5, max_bet: 5000},
        coinflip: {enabled: true, min_bet: 1, max_bet: 10000}
      },
      gamble_friday: {enabled: true, start_hour: 6, end_hour: 18, timezone: "America/Chicago"},
      logging: {level: "INFO", log_to_file: true}
    }' > config.json
    
    # Nginx handling
    if [[ "$NGINX_OPT" =~ ^[Yy]$ ]]; then
         [ -f "docker-compose.override.yml.template" ] && cp "docker-compose.override.yml.template" "docker-compose.override.yml"
         if [ -f "nginx.conf.template" ]; then
             cp "nginx.conf.template" "nginx.conf"
             sed -i "s/__SERVER_PORT__/${PORT}/g" nginx.conf
         fi
    else
         rm -f docker-compose.override.yml nginx.conf
    fi
    
    ensure_permissions
    print_success "Configuration Saved."
    read -p "Press Enter to continue..."
}

function ensure_permissions {
    mkdir -p data
    chown -R 1000:1000 data
    [ -f config.json ] && chmod 644 config.json
}

# --- Actions ---
function start_app {
    FLAGS="-d"
    if [ "$UPDATE_AVAILABLE" = true ] || [ "$RECONFIGURE_REQUESTED" = true ]; then
         FLAGS="--build -d"
         print_info "Rebuilding containers..."
    fi
    
    ensure_permissions
    docker compose up $FLAGS
    
    if [ "$DB_CODE_CHANGED" = true ]; then
         print_warning "Checking for migrations..."
         sleep 3
         docker compose logs --tail 50 web | grep -iE "transact|migrat|error"
    fi
    
    PORT=$(grep SERVER_PORT .env | cut -d '=' -f2)
    print_success "App running on port ${PORT:-8000}"
    read -p "Press Enter to continue..."
}

function stop_app {
    print_info "Stopping containers..."
    docker compose down
    print_success "Stopped."
    read -p "Press Enter to continue..."
}

function view_logs {
    print_info "Showing logs (Ctrl+C to exit)..."
    docker compose logs -f
    read -p "Logs closed. Press Enter..."
}

function view_status {
    docker compose ps
    read -p "Press Enter to continue..."
}

function reset_data {
    read -p "Are you sure you want to DELETE ALL DATA? [y/N]: " CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
        docker compose down
        rm -f data/casino.db
        print_success "Database deleted."
    else
        print_info "Cancelled."
    fi
    read -p "Press Enter to continue..."
}

# --- Main Menu ---
check_root
install_dependencies

while true; do
    print_banner
    echo "1. Start Application"
    echo "2. Check for Updates"
    echo "3. View Logs"
    echo "4. Show Status"
    echo "5. Stop Application"
    echo "6. Management (Config/Reset)"
    echo "7. Exit"
    echo -e "${C_BLUE}==============================================${C_RESET}"
    read -p "Select Options: " MENU_CHOICE
    
    case $MENU_CHOICE in
        1) start_app ;;
        2) check_for_updates ;;
        3) view_logs ;;
        4) view_status ;;
        5) stop_app ;;
        6) 
           echo "  a) Reconfigure (Run Setup)"
           echo "  b) Factory Reset Data"
           echo "  c) Back"
           read -p "  Select: " SUB_CHOICE
           case $SUB_CHOICE in
               a) RECONFIGURE_REQUESTED=true; interact_config ;;
               b) reset_data ;;
           esac
           ;;
        7) exit 0 ;;
        *) print_error "Invalid option" ; sleep 1 ;;
    esac
done
