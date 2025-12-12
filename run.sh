#!/bin/bash

# ==============================================================================
# Gamble Limited - Updater & Launcher Script
# ==============================================================================
# This script manages application updates, versioning, and Docker container
# builds. It integrates with the existing setup logic to provide a seamless
# experience for both first-time installation and subsequent updates.
#
# What it does:
# 1. Checks for remote code updates from the main GitHub branch.
# 2. Suggests a version bump (Major, Normal, Minor/Hotfix) based on changes.
# 3. Allows for custom versioning.
# 4. Prompts for database preservation or reset.
# 5. Rebuilds and relaunches the Docker containers.
# 6. If run for the first time, it performs a full setup.
# ==============================================================================

# --- Color Codes for Output ---
C_RESET='\033[0m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_BLUE='\033[0;34m'
C_CYAN='\033[0;36m'

# --- Helper Functions ---
function print_info {
    echo -e "${C_BLUE}INFO:${C_RESET} $1"
}

function print_success {
    echo -e "${C_GREEN}SUCCESS:${C_RESET} $1"
}

function print_warning {
    echo -e "${C_YELLOW}WARNING:${C_RESET} $1"
}

function print_error {
    echo -e "${C_RED}ERROR:${C_RESET} $1"
    exit 1
}

function check_root {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root. Please use 'sudo'."
    fi
}

function install_dependencies {
    print_info "Updating package lists..."
    if ! apt-get update -y; then
        print_error "Failed to update package lists."
    fi

    print_info "Installing prerequisites: curl, jq, git..."
    if ! apt-get install -y curl jq git; then
        print_error "Failed to install curl, jq, or git."
    fi

    # Check for Docker
    if ! command -v docker &> /dev/null; then
        print_info "Docker not found. Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        if ! sh get-docker.sh; then
            print_error "Docker installation failed."
        fi
        rm get-docker.sh
    else
        print_info "Docker is already installed."
    fi

    # Check for Docker Compose
    if ! docker compose version &> /dev/null; then
        print_info "Docker Compose not found. Installing..."
        if ! apt-get install -y docker-compose-plugin; then
            print_error "Docker Compose installation failed."
        fi
    else
        print_info "Docker Compose is already installed."
    fi
}

# --- Update & Versioning Logic ---
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
        print_warning "You have local changes that are not on the remote. Please stash or commit them."
        UPDATE_AVAILABLE=false # Cannot update safely
    else
        print_warning "The local and remote branches have diverged. Please resolve this manually."
        UPDATE_AVAILABLE=false
    fi

    if [ "$UPDATE_AVAILABLE" = true ]; then
        handle_update
    fi
}

function handle_update {
    print_info "An update is available. Pulling changes from the remote repository..."
    if ! git pull; then
        print_error "Failed to pull updates from the remote repository."
    fi

    # Versioning
    VERSION_FILE="version.txt"
    if [ ! -f "$VERSION_FILE" ]; then
        echo "1.0.0" > "$VERSION_FILE"
    fi
    CURRENT_VERSION=$(cat "$VERSION_FILE")
    print_info "Current version: $CURRENT_VERSION"

    # Suggest update type based on changed files
    CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD)
    SUGGESTED_TYPE="4" # Default to Minor/Hotfix

    if echo "$CHANGED_FILES" | grep -q -e "Dockerfile" -e "docker-compose.yml" -e "requirements.txt"; then
        SUGGESTED_TYPE="1" # Major
    elif echo "$CHANGED_FILES" | grep -q "app/.*\.py"; then
        SUGGESTED_TYPE="2" # Normal
    elif echo "$CHANGED_FILES" | grep -q -e "\.md" -e "\.txt"; then
        SUGGESTED_TYPE="3" # Minor/Hotfix
    fi

    echo "Please select the type of update:"
    echo "  1) Major"
    echo "  2) Normal"
    echo "  3) Minor"
    echo "  4) Hotfix"
    echo "  5) Custom"
    read -p "Enter your choice (Suggested: $SUGGESTED_TYPE): " UPDATE_CHOICE
    UPDATE_CHOICE=${UPDATE_CHOICE:-$SUGGESTED_TYPE}

    # Increment version based on choice
    IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
    MAJOR=${VERSION_PARTS[0]}
    NORMAL=${VERSION_PARTS[1]}
    MINOR=${VERSION_PARTS[2]}

    case $UPDATE_CHOICE in
        1) # Major
            MAJOR=$((MAJOR + 1))
            NORMAL=0
            MINOR=0
            ;;
        2) # Normal
            NORMAL=$((NORMAL + 1))
            MINOR=0
            ;;
        3) # Minor
            MINOR=$((MINOR + 1))
            ;;
        4) # Hotfix
            MINOR=$((MINOR + 1))
            ;;
        5) # Custom
            read -p "Enter the new version number (e.g., 1.2.3): " NEW_VERSION
            if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                print_error "Invalid version format. Please use the format 'major.normal.minor'."
            fi
            echo "$NEW_VERSION" > "$VERSION_FILE"
            print_success "Version updated to $NEW_VERSION"
            return
            ;;
        *)
            print_error "Invalid choice."
            ;;
    esac

    NEW_VERSION="$MAJOR.$NORMAL.$MINOR"
    echo "$NEW_VERSION" > "$VERSION_FILE"
    print_success "Version updated to $NEW_VERSION"
}


# --- Build & Run Logic ---
function prompt_for_build_and_reset {
    if [ "$UPDATE_AVAILABLE" = true ]; then
        read -p "An update has been applied. Rebuild the Docker container now? [Y/n]: " REBUILD_CHOICE
        REBUILD_CHOICE=${REBUILD_CHOICE:-Y}
    else
        read -p "No updates found. Do you want to force a rebuild anyway? [y/N]: " REBUILD_CHOICE
        REBUILD_CHOICE=${REBUILD_CHOICE:-N}
    fi

    if [[ ! "$REBUILD_CHOICE" =~ ^[Yy]$ ]]; then
        print_info "Skipping build process. The script will now exit."
        exit 0
    fi

    # If we are rebuilding, ask about the database
    read -p "Do you want to perform a full reset (delete the database)? This cannot be undone. [y/N]: " RESET_DB
    if [[ "$RESET_DB" =~ ^[Yy]$ ]]; then
        DB_PATH="data/casino.db"
        if [ -f "$DB_PATH" ]; then
            print_warning "Deleting database file at '$DB_PATH'..."
            rm "$DB_PATH"
            print_success "Database reset complete."
        else
            print_warning "Database file '$DB_PATH' not found. Nothing to reset."
        fi
    else
        print_info "Preserving existing database."
    fi
}

function get_user_config {
    print_info "Starting interactive configuration..."

    # SECRET_KEY
    read -p "Enter a SECRET_KEY (leave blank to auto-generate): " SECRET_KEY
    if [ -z "$SECRET_KEY" ]; then
        SECRET_KEY=$(openssl rand -hex 32)
        print_info "Generated a random SECRET_KEY."
    fi

    # Admin Password
    while true; do
        read -p "Enter a password for the admin panel: " ADMIN_PASSWORD
        if [ -n "$ADMIN_PASSWORD" ]; then
            break
        else
            print_warning "Admin password cannot be empty."
        fi
    done

    # Server Port
    read -p "Enter the port to run the server on [8000]: " SERVER_PORT
    SERVER_PORT=${SERVER_PORT:-8000}

    # Cloudflare Tunnel Token
    read -p "Enter your Cloudflare Tunnel Token (optional): " CF_TUNNEL_TOKEN

    # Nginx Proxy
    read -p "Enable Nginx reverse proxy? (y/N): " ENABLE_NGINX
}

function generate_config_files {
    print_info "Generating configuration files..."

    # Create .env file
    echo "# Generated by run.sh on $(date)" > .env
    echo "SECRET_KEY=${SECRET_KEY}" >> .env
    echo "SERVER_PORT=${SERVER_PORT}" >> .env
    if [ -n "$CF_TUNNEL_TOKEN" ]; then
        echo "CF_TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}" >> .env
    fi

    # Create config.json from scratch
    jq -n \
      --argjson port "$SERVER_PORT" \
      --arg pass "$ADMIN_PASSWORD" \
      '
      {
        "server": {
          "host": "0.0.0.0",
          "port": $port,
          "debug": false,
          "name": "Gamble Limited"
        },
        "security": {
          "admin_username": "admin",
          "admin_password_hash": $pass,
          "secret_key": "from_env",
          "admin_login_path": "/admin-portal",
          "house_login_path": "/the-house"
        },
        "economy": {
          "starting_cash": 1000.0,
          "starting_credits": 500.0,
          "base_exchange_rate": 10.0,
          "fluctuation_range": 0.05,
          "daily_bonus_amount": 100.0,
          "daily_bonus_cooldown_hours": 24,
          "daily_cash_amount": 50.0,
          "daily_cash_cooldown_hours": 24,
          "house_cut_percent": 5.0
        },
        "games": {
          "slots": { "enabled": true, "min_bet": 10, "max_bet": 1000, "payout_rate": 0.95 },
          "blackjack": { "enabled": true, "min_bet": 20, "max_bet": 2000 },
          "roulette": { "enabled": true, "min_bet": 5, "max_bet": 5000 },
          "plinko": { "enabled": false, "min_bet": 1, "max_bet": 1000 },
          "coinflip": { "enabled": true, "min_bet": 1, "max_bet": 10000 }
        },
        "gamble_friday": {
          "enabled": true,
          "start_hour": 6,
          "end_hour": 18,
          "timezone": "America/Chicago",
          "winnings_multiplier": 1.5,
          "win_rate_reduction": 0.05,
          "max_bet_multiplier": 3
        },
        "rate_limit": {
          "enabled": true,
          "game_requests": "30/minute",
          "api_requests": "60/minute"
        },
        "logging": {
          "level": "INFO",
          "log_to_file": true
        }
      }
      ' > config.json

    print_success "Successfully created .env and config.json."
}

function configure_nginx {
    if [[ "$ENABLE_NGINX" =~ ^[Yy]$ ]]; then
        print_info "Enabling Nginx reverse proxy..."

        # Create docker-compose.override.yml
        if [ -f "docker-compose.override.yml.template" ]; then
            cp "docker-compose.override.yml.template" "docker-compose.override.yml"
        else
            print_warning "docker-compose.override.yml.template not found."
        fi

        # Create nginx.conf from template
        if [ -f "nginx.conf.template" ]; then
            cp "nginx.conf.template" "nginx.conf"
            # Replace placeholder with user-defined port
            sed -i "s/__SERVER_PORT__/${SERVER_PORT}/g" nginx.conf
            print_success "Nginx has been enabled and configured for port ${SERVER_PORT}."
        else
            print_warning "nginx.conf.template not found. Cannot configure Nginx."
        fi
    else
        print_info "Skipping Nginx setup."
        # Clean up override files if they exist
        [ -f "docker-compose.override.yml" ] && rm "docker-compose.override.yml"
        [ -f "nginx.conf" ] && rm "nginx.conf"
    fi
}

function ensure_permissions {
    print_info "Ensuring correct permissions for data directory..."
    mkdir -p data
    # Set ownership to 1000:1000 (appuser in container)
    chown -R 1000:1000 data
    
    # Also ensure config.json is readable by everyone or specifically user 1000
    if [ -f "config.json" ]; then
        chmod 644 config.json
    fi
}

function run_docker_compose {
    print_info "Building and starting Docker containers..."
    if ! docker compose up --build -d; then
        print_error "Docker Compose failed to build and start."
    fi
    print_success "Docker containers are up and running."
}

function final_summary {
    echo -e "${C_CYAN}=================================================${C_RESET}"
    echo -e "${C_CYAN}          🎉 Setup Complete! 🎉             ${C_RESET}"
    echo -e "${C_CYAN}=================================================${C_RESET}"
    print_success "The Gamble Limited platform has been deployed."

    if [[ "$ENABLE_NGINX" =~ ^[Yy]$ ]]; then
        print_info "Application is accessible at: ${C_YELLOW}http://<your_server_ip>:80${C_RESET}"
    else
        # Fallback to reading from .env if SERVER_PORT is not set
        if [ -z "$SERVER_PORT" ]; then
            if [ -f ".env" ]; then
                SERVER_PORT=$(grep SERVER_PORT .env | cut -d '=' -f2)
            else
                SERVER_PORT="8000" # Default if not found
            fi
        fi
        print_info "Application is accessible at: ${C_YELLOW}http://<your_server_ip>:${SERVER_PORT}${C_RESET}"
    fi

    echo ""
    print_info "Next Steps:"
    echo -e " - To view container logs: ${C_GREEN}docker compose logs -f${C_RESET}"
    echo -e " - To stop the containers: ${C_GREEN}docker compose stop${C_RESET}"
    echo -e " - To stop and remove containers: ${C_GREEN}docker compose down${C_RESET}"
    echo ""
}

# --- Main Execution ---
main() {
    print_info "Starting the updater and launcher script..."
    check_root
    install_dependencies
    check_for_updates
    prompt_for_build_and_reset

    # First-time setup if config files are missing
    if [ ! -f "config.json" ] || [ ! -f ".env" ]; then
        print_warning "Configuration files not found. Running first-time setup..."
        get_user_config
        generate_config_files
        configure_nginx
    else
        print_info "Existing configuration files found. Skipping first-time setup."
    fi

    ensure_permissions
    run_docker_compose

    final_summary
}

main "$@"
