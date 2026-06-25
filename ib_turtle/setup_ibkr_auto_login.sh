#!/bin/bash

# ==============================================================================
# IBKR AUTOMATED HEADLESS LOGIN SETUP SCRIPT
# ==============================================================================

# Stop on error
set -e

# Visual formatting helper
print_msg() {
    echo -e "\033[1;34m==>\033[0m \033[1m$1\033[0m"
}

print_success() {
    echo -e "\033[1;32m==>\033[0m \033[1;32m$1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m==>\033[0m \033[1;33m$1\033[0m"
}

# 1. Check Docker installation
print_msg "Checking Docker installation..."
OS_TYPE=$(uname)

if ! command -v docker &> /dev/null; then
    print_warning "Docker is not installed."
    echo "Attempting to install Docker automatically..."
    
    if [ "$OS_TYPE" = "Darwin" ]; then
        if command -v brew &> /dev/null; then
            echo "Installing Docker Desktop via Homebrew Cask..."
            brew install --cask docker
        else
            print_warning "Homebrew is not installed. Cannot automate Docker installation on macOS."
            echo "Please install Homebrew first, or download Docker Desktop from: https://www.docker.com/products/docker-desktop/"
            exit 1
        fi
    elif [ "$OS_TYPE" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            echo "Installing Docker and Docker Compose via apt-get (requires sudo)..."
            sudo apt-get update
            sudo apt-get install -y docker.io docker-compose-v2
            # Add current user to docker group so they don't need sudo for docker commands
            sudo usermod -aG docker $USER || true
            echo "Note: You may need to log out and log back in for docker group membership to take effect."
        elif command -v dnf &> /dev/null; then
            echo "Installing Docker via dnf (requires sudo)..."
            sudo dnf install -y docker docker-compose-plugin
            sudo systemctl enable --now docker
        else
            print_warning "Unsupported package manager. Please install Docker manually."
            echo "See: https://docs.docker.com/engine/install/"
            exit 1
        fi
    else
        print_warning "Unsupported OS. Please install Docker manually."
        exit 1
    fi
fi

if ! docker info &> /dev/null; then
    print_warning "Docker daemon is not running. Attempting to start it..."
    if [ "$OS_TYPE" = "Darwin" ]; then
        echo "Opening Docker Desktop..."
        open -a Docker
        echo "Waiting for Docker daemon to start (up to 30 seconds)..."
        for i in {1..30}; do
            if docker info &> /dev/null; then
                break
            fi
            sleep 1
        done
    elif [ "$OS_TYPE" = "Linux" ]; then
        echo "Starting Docker service (requires sudo)..."
        sudo systemctl start docker || sudo service docker start
    fi
fi

if ! docker info &> /dev/null; then
    print_warning "Could not start Docker daemon automatically. Please start Docker manually and rerun this script."
    exit 1
fi

print_success "Docker is running."

# 1.5 Install Python dependencies from pip
print_msg "Checking and installing Python dependencies from pip..."
PIP_CMD=""
if command -v pip &> /dev/null; then
    PIP_CMD="pip"
elif command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
fi

if [ -n "$PIP_CMD" ]; then
    echo "Using $PIP_CMD to install required libraries..."
    $PIP_CMD install ib-insync pandas numpy pytz
    print_success "Python dependencies successfully installed/updated."
else
    print_warning "pip is not installed. Skipping python library installation."
    echo "Please install pip and run: pip install ib-insync pandas numpy pytz"
fi

# 2. Collect Credentials securely
echo ""
print_msg "Please enter your IBKR Paper Trading credentials."
echo "Note: This script only configures paper trading (port 4002)."
echo ""

read -p "Enter IBKR Paper Username: " ib_username

# Read password securely (without echoing characters)
unset ib_password
prompt="Enter IBKR Paper Password: "
while IFS= read -p "$prompt" -r -s -n 1 char; do
    if [[ $char == $'\0' || $char == $'\n' ]]; then
        break
    fi
    if [[ $char == $'\177' ]]; then # Handle backspace
        if [ ${#ib_password} -gt 0 ]; then
            ib_password="${ib_password%?}"
            echo -ne "\b \b"
        fi
    else
        ib_password+="$char"
        echo -n "*"
    fi
done
echo ""

if [ -z "$ib_username" ] || [ -z "$ib_password" ]; then
    print_warning "Username or password cannot be empty. Aborting setup."
    exit 1
fi

# 3. Create Gateway Setup Directory
TARGET_DIR="$HOME/ib_gateway_docker"
print_msg "Creating gateway setup directory at $TARGET_DIR..."
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# 4. Generate docker-compose.yml
print_msg "Generating docker-compose.yml..."
cat <<EOF > docker-compose.yml
version: '3.8'

services:
  ib-gateway:
    image: mvance/ib-gateway:latest
    container_name: ib-gateway-headless
    restart: always
    ports:
      - "4002:4002"  # API Port (Paper Account)
    environment:
      - TWS_USERID=${ib_username}
      - TWS_PASSWORD=${ib_password}
      - TRADING_MODE=paper
      - TWS_PORT=4002
EOF

# 5. Start the Docker container
print_msg "Spinning up the automated headless IB Gateway container..."
docker compose up -d

# 6. Verify Container Status
print_msg "Verifying container status..."
sleep 3
if [ "$(docker inspect -f '{{.State.Running}}' ib-gateway-headless)" = "true" ]; then
    print_success "IBKR Headless Gateway is successfully running in the background."
else
    print_warning "Container is not running. Printing container logs:"
    docker logs ib-gateway-headless
    exit 1
fi

# 7. Print instructions
echo ""
echo "=============================================================================="
print_success "SETUP COMPLETE - Headless IBKR Gateway is Online!"
echo "=============================================================================="
echo "1. The gateway is running on port 4002 (API Port for paper trading)."
echo "2. Your Python trading bots can now connect to localhost:4002 without TWS open."
echo "3. The gateway will run 24/7, handling daily restarts and logins automatically."
echo ""
echo "Useful Commands:"
echo "  - View live logs:      docker logs -f ib-gateway-headless"
echo "  - Stop the gateway:    cd $TARGET_DIR && docker compose down"
echo "  - Restart the gateway: cd $TARGET_DIR && docker compose restart"
echo "=============================================================================="
echo ""
