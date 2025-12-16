#!/bin/bash
# ==============================================================================
# Gamble Limited - Development Setup Script
# ==============================================================================
# This script automates the setup of a local development environment.
#
# It performs the following actions:
#   1. Checks for Python 3.
#   2. Creates a Python virtual environment (`venv`).
#   3. Installs dependencies from `requirements.txt`.
#   4. Creates a `.env` file from `.env.example`.
#   5. Generates a unique SECRET_KEY for the `.env` file.
# ==============================================================================

# --- Color Codes ---
C_RESET='\033[0m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_BLUE='\033[1;34m'
C_CYAN='\033[0;36m'

# --- Helper Functions ---
function print_info { echo -e "${C_BLUE}[INFO]${C_RESET} $1"; }
function print_success { echo -e "${C_GREEN}[SUCCESS]${C_RESET} $1"; }
function print_warning { echo -e "${C_YELLOW}[WARNING]${C_RESET} $1"; }

# 1. Check for Python 3
print_info "Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    print_warning "Python 3 is not installed. Please install it to continue."
    exit 1
fi

# 2. Create a virtual environment
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
else
    print_info "Virtual environment already exists."
fi

# 3. Install dependencies
print_info "Installing dependencies from requirements.txt..."
source venv/bin/activate
pip install -r requirements.txt

# 4. Create .env file
if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    cp .env.example .env
else
    print_info ".env file already exists."
fi

# 5. Generate SECRET_KEY
print_info "Generating a new SECRET_KEY..."
SECRET_KEY=$(openssl rand -hex 32)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS requires a backup extension for sed -i
    sed -i '' "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
else
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
fi

print_success "Development environment setup is complete."
echo -e "${C_CYAN}To activate the virtual environment, run:${C_RESET}"
echo "source venv/bin/activate"
