#!/bin/bash

# ==============================================================================
# Gamble Limited - Management Script (manage.sh)
# ==============================================================================
# Replaces run.sh and build.sh.
# Unified tool for Updates, Construction/Configuration, and Deployment.
#
# Features:
# 1. Checks for updates from GitHub.
# 2. Handles versioning (Major/Normal/Minor/Hotfix).
# 3. Detects database schema changes and reports migrations.
# 4. First-time setup & "Force Reconfigure" option.
# 5. Database retention management.
# 6. Builds and runs Docker containers.
# ==============================================================================

# --- Color Codes ---
C_RESET='\033[0m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_BLUE='\033[0;34m'
C_CYAN='\033[0;36m'

# --- Flags & Globals ---
DB_CODE_CHANGED=false
UPDATE_AVAILABLE=false
RECONFIGURE_REQUESTED=false
SERVER_PORT=8000

# --- Helper Functions ---
function print_info { echo -e "${C_BLUE}INFO:${C_RESET} $1"; }
function print_success { echo -e "${C_GREEN}SUCCESS:${C_RESET} $1"; }
function print_warning { echo -e "${C_YELLOW}WARNING:${C_RESET} $1"; }
function print_error { echo -e "${C_RED}ERROR:${C_RESET} $1"; exit 1; }

function check_root {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root. Please use 'sudo'."
    fi
}

function install_dependencies {
    print_info "Checking dependencies..."
    if ! command -v apt-get &> /dev/null; then
        # Check if we are on a non-apt system (e.g. user on Windows Git Bash might just skip this part gracefully or fail)
        print_warning "apt-get not found. Skipping dependency install (assuming non-Debian env or already set up)."
        return
    fi
    
    apt-get update -y > /dev/null 2>&1
    if ! command -v curl &> /dev/null || ! command -v jq &> /dev/null || ! command -v git &> /dev/null; then
        print_info "Installing curl, jq, git..."
        apt-get install -y curl jq git
    fi

    # Docker Check
    if ! command -v docker &> /dev/null; then
        print_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
    fi
    
    # Docker Compose Check
    if ! docker compose version &> /dev/null; then
         print_info "Installing Docker Compose..."
         apt-get install -y docker-compose-plugin
    fi
}

# --- Update & Versioning ---
function check_for_updates {
    print_info "Checking for updates..."
    git remote update > /dev/null 2>&1

    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    BASE=$(git merge-base @ @{u})

    if [ $LOCAL = $REMOTE ]; then
        print_success "Application is up-to-date."
        UPDATE_AVAILABLE=false
    elif [ $LOCAL = $BASE ]; then
        print_success "Update available."
        UPDATE_AVAILABLE=true
    elif [ $REMOTE = $BASE ]; then
        print_warning "Local changes detected. Stash or commit them to update properly."
        UPDATE_AVAILABLE=false
    else
        print_warning "Diverged branches. Resolve manually."
        UPDATE_AVAILABLE=false
    fi

    if [ "$UPDATE_AVAILABLE" = true ]; then
        handle_update
    fi
}

function handle_update {
    print_info "Downloading updates..."
    
    # Check what files changed before pulling
    CHANGED_FILES=$(git diff --name-only HEAD..@{u})
    
    if echo "$CHANGED_FILES" | grep -q "app/core/database.py"; then
        DB_CODE_CHANGED=true
        print_warning "Database logic changes detected. Migration might occur."
    fi

    if ! git pull; then
        print_error "git pull failed."
    fi

    # Versioning
    VERSION_FILE="version.txt"
    [ ! -f "$VERSION_FILE" ] && echo "1.0.0" > "$VERSION_FILE"
    CURRENT_VERSION=$(cat "$VERSION_FILE")
    
    print_info "Current Version: $CURRENT_VERSION"
    
    SUGGESTED_TYPE="4" # Hotfix default
    if echo "$CHANGED_FILES" | grep -q -e "Dockerfile" -e "docker-compose.yml"; then
        SUGGESTED_TYPE="1" # Major
    elif echo "$CHANGED_FILES" | grep -q "app/"; then
        SUGGESTED_TYPE="2" # Normal
    fi

    echo "Select Update Type (Suggested: $SUGGESTED_TYPE):"
    echo "  1) Major  2) Normal  3) Minor  4) Hotfix  5) Custom"
    read -p "Choice: " U_CHOICE
    U_CHOICE=${U_CHOICE:-$SUGGESTED_TYPE}

    IFS='.' read -r -a PARTS <<< "$CURRENT_VERSION"
    MAJOR=${PARTS[0]}; NORMAL=${PARTS[1]}; MINOR=${PARTS[2]}

    case $U_CHOICE in
        1) MAJOR=$((MAJOR+1)); NORMAL=0; MINOR=0 ;;
        2) NORMAL=$((NORMAL+1)); MINOR=0 ;;
        3) MINOR=$((MINOR+1)) ;;
        4) MINOR=$((MINOR+1)) ;;
        5) 
           read -p "Enter new version: " NEW_VERSION
           echo "$NEW_VERSION" > "$VERSION_FILE"
           print_success "Updated to $NEW_VERSION"
           return 
           ;;
    esac

    NEW_VERSION="$MAJOR.$NORMAL.$MINOR"
    echo "$NEW_VERSION" > "$VERSION_FILE"
    print_success "Updated to $NEW_VERSION"
}

# --- Configuration ---
function interact_config {
    print_info "--- Configuration ---"
    
    read -p "Enter SECRET_KEY (leave empty to generate): " SECRET_KEY
    if [ -z "$SECRET_KEY" ]; then
        SECRET_KEY=$(openssl rand -hex 32)
        print_info "Generated key."
    fi

    while true; do
        read -p "Enter Admin Password: " ADMIN_PASSWORD
        [ -n "$ADMIN_PASSWORD" ] && break
    done

    read -p "Server Port [8000]: " SERVER_PORT
    SERVER_PORT=${SERVER_PORT:-8000}

    read -p "Cloudflare Tunnel Token (optional): " CF_TUNNEL_TOKEN
    read -p "Enable Nginx Proxy? (y/N): " ENABLE_NGINX

    # Generate files
    echo "SECRET_KEY=${SECRET_KEY}" > .env
    echo "SERVER_PORT=${SERVER_PORT}" >> .env
    [ -n "$CF_TUNNEL_TOKEN" ] && echo "CF_TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}" >> .env

    jq -n \
      --argjson port "$SERVER_PORT" \
      --arg pass "$ADMIN_PASSWORD" \
      '{
        "server": { "host": "0.0.0.0", "port": $port, "debug": false, "name": "Gamble Limited" },
        "security": { "admin_username": "admin", "admin_password_hash": $pass, "secret_key": "from_env", "admin_login_path": "/admin-portal", "house_login_path": "/the-house" },
        "economy": { "starting_cash": 1000.0, "starting_credits": 500.0, "base_exchange_rate": 10.0, "fluctuation_range": 0.05, "daily_bonus_amount": 100.0, "daily_bonus_cooldown_hours": 24, "daily_cash_amount": 50.0, "daily_cash_cooldown_hours": 24, "house_cut_percent": 5.0 },
        "games": {
          "slots": { "enabled": true, "min_bet": 10, "max_bet": 1000, "payout_rate": 0.95 },
          "blackjack": { "enabled": true, "min_bet": 20, "max_bet": 2000 },
          "roulette": { "enabled": true, "min_bet": 5, "max_bet": 5000 },
          "plinko": { "enabled": false, "min_bet": 1, "max_bet": 1000 },
          "coinflip": { "enabled": true, "min_bet": 1, "max_bet": 10000 }
        },
        "gamble_friday": { "enabled": true, "start_hour": 6, "end_hour": 18, "timezone": "America/Chicago", "winnings_multiplier": 1.5, "win_rate_reduction": 0.05, "max_bet_multiplier": 3 },
        "rate_limit": { "enabled": true, "game_requests": "30/minute", "api_requests": "60/minute" },
        "logging": { "level": "INFO", "log_to_file": true }
      }' > config.json

    if [[ "$ENABLE_NGINX" =~ ^[Yy]$ ]]; then
        [ -f "docker-compose.override.yml.template" ] && cp "docker-compose.override.yml.template" "docker-compose.override.yml"
        if [ -f "nginx.conf.template" ]; then
             cp "nginx.conf.template" "nginx.conf"
             sed -i "s/__SERVER_PORT__/${SERVER_PORT}/g" nginx.conf
        fi
        print_success "Configuration complete (Nginx enabled)."
    else
        [ -f "docker-compose.override.yml" ] && rm "docker-compose.override.yml"
        [ -f "nginx.conf" ] && rm "nginx.conf"
        print_success "Configuration complete."
    fi
}

function ensure_permissions {
    print_info "Fixing permissions..."
    mkdir -p data
    chown -R 1000:1000 data
    [ -f "config.json" ] && chmod 644 config.json
}

# --- Build & Runtime ---
function db_report {
    # Check if we should report DB changes
    if [ "$DB_CODE_CHANGED" = true ]; then
        print_warning "Database code was updated. Fetching migration logs..."
        sleep 5 # Wait a bit for container startup
        
        echo -e "${C_CYAN}--- Database Migration Report ---${C_RESET}"
        if docker compose logs --tail 200 web | grep -iE "transact|migrat|error|column"; then
             echo -e "${C_CYAN}----------------------------------${C_RESET}"
        else
             print_info "No explicit migration logs found (might have been silent or successful)."
        fi
    fi
}

function run_app {
    print_info "Starting containers..."
    
    # Check for rebuild need
    if [ "$UPDATE_AVAILABLE" = true ] || [ "$RECONFIGURE_REQUESTED" = true ]; then
         read -p "Rebuild containers? [Y/n]: " BUILD_OPT
         BUILD_OPT=${BUILD_OPT:-Y}
         
         if [[ "$BUILD_OPT" =~ ^[Yy]$ ]]; then
             read -p "RESET DATABASE? (Dangerous!) [y/N]: " RESET_DB
             if [[ "$RESET_DB" =~ ^[Yy]$ ]]; then
                 rm -f data/casino.db
                 print_warning "Database deleted."
             fi
             
             docker compose up --build -d
         else
             docker compose up -d
         fi
    else
         docker compose up -d
    fi
    
    db_report
    
    # Final port check
    if [ -f ".env" ]; then
        PORT=$(grep SERVER_PORT .env | cut -d '=' -f2)
        PORT=${PORT:-8000}
        print_success "Running at http://localhost:$PORT"
    fi
}

# --- Main Menu ---
function show_menu {
    echo -e "${C_CYAN}--- Gamble Limited Manager ---${C_RESET}"
    echo "1. Start Application (Normal)"
    echo "2. Check for Updates & Start"
    echo "3. Reconfigure (Reset Config) & Start"
    echo "4. Exit"
    read -p "Select [1-4]: " CHOICE
    
    case $CHOICE in
        1) 
           ensure_permissions
           run_app 
           ;;
        2) 
           check_for_updates 
           ensure_permissions
           run_app 
           ;;
        3) 
           RECONFIGURE_REQUESTED=true
           interact_config 
           ensure_permissions
           run_app 
           ;;
        4) exit 0 ;;
        *) run_app ;;
    esac
}

# --- Entry Point ---
check_root
install_dependencies

# If run with args (e.g. from cron or CI), default to update check
if [ $# -gt 0 ]; then
    check_for_updates
    ensure_permissions
    run_app
else
    show_menu
fi
