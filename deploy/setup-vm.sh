#!/bin/bash
# ThetaFlow — GCP VM bootstrap script
# Run this once on a fresh Debian/Ubuntu VM:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB/fund-manager-agent/main/deploy/setup-vm.sh | bash
# Or copy it to the VM and run: bash setup-vm.sh

set -e

REPO_URL="https://github.com/chaichatchai13/fund-manager-agent.git"
APP_DIR="/opt/thetaflow"

echo "━━━ 1/6  System update ━━━"
sudo apt-get update -qq && sudo apt-get upgrade -y -qq

echo "━━━ 2/6  Install Docker ━━━"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed — you may need to log out and back in for group changes."
else
    echo "Docker already installed: $(docker --version)"
fi

echo "━━━ 3/6  Install Docker Compose plugin ━━━"
if ! docker compose version &>/dev/null; then
    sudo apt-get install -y docker-compose-plugin
fi
echo "Docker Compose: $(docker compose version)"

echo "━━━ 4/6  Clone repo ━━━"
if [ -d "$APP_DIR/.git" ]; then
    echo "Repo already cloned — pulling latest..."
    git -C "$APP_DIR" pull
else
    sudo git clone "$REPO_URL" "$APP_DIR"
    sudo chown -R "$USER:$USER" "$APP_DIR"
fi

echo "━━━ 5/6  Create .env from example ━━━"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│  IMPORTANT: Edit /opt/thetaflow/.env before continuing  │"
    echo "│  Fill in: SCHWAB_APP_KEY, SCHWAB_APP_SECRET,            │"
    echo "│           ANTHROPIC_API_KEY, DB_PASS, THETAFLOW_DOMAIN, │"
    echo "│           THETAFLOW_PASSWORD, SECRET_KEY                 │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo ""
    echo "Run: nano /opt/thetaflow/.env"
    echo "Then re-run this script to finish setup."
    exit 0
else
    echo ".env already exists — skipping."
fi

echo "━━━ 6/6  Install systemd service ━━━"
sudo cp "$APP_DIR/deploy/thetaflow.service" /etc/systemd/system/thetaflow.service
sudo systemctl daemon-reload
sudo systemctl enable thetaflow
sudo systemctl restart thetaflow

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ThetaFlow is running!"
echo "  Check status: sudo systemctl status thetaflow"
echo "  View logs:    sudo journalctl -u thetaflow -f"
echo "  App logs:     docker compose -f /opt/thetaflow/docker-compose.yml logs -f"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
