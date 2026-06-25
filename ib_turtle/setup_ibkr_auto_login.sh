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
if ! command -v docker &> /dev/null; then
    print_warning "Docker is not installed or not in your PATH."
    echo "Please download and install Docker Desktop for Mac from: https://www.docker.com/products/docker-desktop/"
    echo "After installing, start Docker Desktop and run this script again."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_warning "Docker daemon is not running."
    echo "Please start your Docker Desktop application and run this script again."
    exit 1
fi

print_success "Docker is running."

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
