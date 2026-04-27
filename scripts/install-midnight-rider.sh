#!/bin/bash
#
# Midnight Rider — Automatic Installation Script
# Usage: bash scripts/install-midnight-rider.sh
#
# Installs complete stack from scratch:
#   • Docker + Docker Compose
#   • Signal K server (native systemd)
#   • InfluxDB (Docker)
#   • Grafana (Docker)
#   • Python 3.11 + dependencies
#   • Node.js + npm
#   • Configuration files
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Midnight Rider — Automatic Installation Script        ║${NC}"
echo -e "${BLUE}║              J/30 Navigation System Setup                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
  exit 1
fi

echo -e "${YELLOW}📋 Pre-flight checks...${NC}"

# Check OS
if ! grep -q "Raspberry\|Debian\|Ubuntu" /etc/os-release; then
  echo -e "${RED}❌ Unsupported OS (requires Debian/Ubuntu/RPi OS)${NC}"
  exit 1
fi

echo -e "${GREEN}✅ OS: Debian-based${NC}"

# Detect package manager
if command -v apt-get &> /dev/null; then
  PKG_MANAGER="apt-get"
elif command -v apt &> /dev/null; then
  PKG_MANAGER="apt"
else
  echo -e "${RED}❌ apt-get/apt not found${NC}"
  exit 1
fi

echo ""
echo -e "${BLUE}🔧 Phase 1: System Updates${NC}"
$PKG_MANAGER update -y
$PKG_MANAGER upgrade -y

echo ""
echo -e "${BLUE}🐳 Phase 2: Docker Installation${NC}"

if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  bash get-docker.sh
  rm get-docker.sh
  
  # Add current user to docker group
  usermod -aG docker $SUDO_USER
  echo -e "${GREEN}✅ Docker installed${NC}"
else
  echo -e "${GREEN}✅ Docker already installed${NC}"
fi

# Docker Compose
if ! command -v docker-compose &> /dev/null; then
  echo "Installing Docker Compose..."
  curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  echo -e "${GREEN}✅ Docker Compose installed${NC}"
else
  echo -e "${GREEN}✅ Docker Compose already installed${NC}"
fi

echo ""
echo -e "${BLUE}🟢 Phase 3: Node.js & npm${NC}"

if ! command -v node &> /dev/null; then
  echo "Installing Node.js 18..."
  curl -sL https://deb.nodesource.com/setup_18.x | bash -
  $PKG_MANAGER install -y nodejs
  echo -e "${GREEN}✅ Node.js installed${NC}"
else
  echo -e "${GREEN}✅ Node.js already installed${NC}"
fi

echo ""
echo -e "${BLUE}🐍 Phase 4: Python 3.11${NC}"

if ! command -v python3.11 &> /dev/null; then
  echo "Installing Python 3.11..."
  $PKG_MANAGER install -y python3.11 python3.11-venv python3.11-dev
  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
  echo -e "${GREEN}✅ Python 3.11 installed${NC}"
else
  echo -e "${GREEN}✅ Python 3.11 already installed${NC}"
fi

# Python dependencies
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install influxdb-client twilio bleak pyyaml requests

echo ""
echo -e "${BLUE}⛵ Phase 5: Signal K Server${NC}"

if ! command -v signalk-server &> /dev/null; then
  echo "Installing Signal K server..."
  npm install -g @signalk/server
  echo -e "${GREEN}✅ Signal K installed${NC}"
else
  echo -e "${GREEN}✅ Signal K already installed${NC}"
fi

echo ""
echo -e "${BLUE}📦 Phase 6: Docker Services (InfluxDB + Grafana)${NC}"

if [ -f "docker-compose.yml" ]; then
  echo "Starting Docker services..."
  docker-compose down 2>/dev/null || true
  docker-compose up -d influxdb grafana
  sleep 10
  echo -e "${GREEN}✅ Docker services running${NC}"
else
  echo -e "${YELLOW}⚠️  docker-compose.yml not found (skipping)${NC}"
fi

echo ""
echo -e "${BLUE}📝 Phase 7: Configuration Files${NC}"

# Create .env.local if not exists
if [ ! -f ".env.local" ]; then
  echo "Creating .env.local from template..."
  if [ -f ".env.example" ]; then
    cp .env.example .env.local
    chmod 600 .env.local
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env.local with your credentials${NC}"
    echo -e "${YELLOW}   • INFLUX_TOKEN${NC}"
    echo -e "${YELLOW}   • GRAFANA_TOKEN${NC}"
    echo -e "${YELLOW}   • WHATSAPP credentials (if using reporter)${NC}"
  fi
else
  echo -e "${GREEN}✅ .env.local exists${NC}"
fi

echo ""
echo -e "${BLUE}✅ Phase 8: Signal K Service${NC}"

# Create systemd service for Signal K
if [ ! -f "/etc/systemd/system/signalk.service" ]; then
  echo "Creating Signal K systemd service..."
  cat > /etc/systemd/system/signalk.service << 'EOF'
[Unit]
Description=Signal K Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$HOME/.signalk
ExecStart=/usr/local/bin/signalk-server -c $HOME/.signalk
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
  
  # Replace variables
  sed -i "s/\$SUDO_USER/$SUDO_USER/g" /etc/systemd/system/signalk.service
  sed -i "s|\$HOME|$(eval echo ~$SUDO_USER)|g" /etc/systemd/system/signalk.service
  
  systemctl daemon-reload
  systemctl enable signalk
  systemctl start signalk
  
  echo -e "${GREEN}✅ Signal K service created and started${NC}"
else
  echo -e "${GREEN}✅ Signal K service already exists${NC}"
fi

echo ""
echo -e "${BLUE}🎯 Phase 9: Verification${NC}"

echo ""
echo "Service status:"
echo -n "  Docker: "
docker --version 2>/dev/null | cut -d' ' -f3 && echo -e "${GREEN}✅${NC}" || echo -e "${RED}❌${NC}"

echo -n "  InfluxDB: "
curl -s http://localhost:8086/health | grep -q "ok" && echo -e "${GREEN}✅${NC}" || echo -e "${YELLOW}⏳ Starting...${NC}"

echo -n "  Grafana: "
curl -s http://localhost:3001/api/health | grep -q "ok" && echo -e "${GREEN}✅${NC}" || echo -e "${YELLOW}⏳ Starting...${NC}"

echo -n "  Signal K: "
systemctl is-active signalk > /dev/null && echo -e "${GREEN}✅${NC}" || echo -e "${RED}❌${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Installation Complete! ✅                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

echo ""
echo -e "${BLUE}📝 NEXT STEPS:${NC}"
echo "  1. Edit .env.local with your credentials"
echo "  2. Configure Signal K plugins"
echo "  3. Import Grafana dashboards"
echo "  4. Test: http://localhost:3001 (Grafana)"
echo "           http://localhost:3000 (Signal K)"
echo "           http://localhost:8086 (InfluxDB)"
echo ""
echo -e "${BLUE}🚀 Ready to sail!${NC} ⛵"
