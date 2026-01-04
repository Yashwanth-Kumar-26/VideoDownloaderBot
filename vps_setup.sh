#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting VideoDownloaderBot Setup for DigitalOcean/VPS...${NC}"

# 1. Update System
echo -e "${BLUE}🔄 Updating system packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y git curl python3 python3-pip

# 2. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo -e "${BLUE}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo -e "${GREEN}✅ Docker is already installed.${NC}"
fi

# 3. Clone Repository
REPO_DIR="VideoDownloaderBot"
REPO_URL="https://github.com/Yashwanth-Kumar-26/VideoDownloaderBot.git"

if [ -d "$REPO_DIR" ]; then
    echo -e "${BLUE}📂 Directory $REPO_DIR exists. Pulling latest changes...${NC}"
    cd "$REPO_DIR"
    git pull origin main
else
    echo -e "${BLUE}📂 Cloning repository...${NC}"
    git clone "$REPO_URL"
    cd "$REPO_DIR"
fi

# 4. Environment Setup (.env)
if [ ! -f .env ]; then
    echo -e "${RED}⚠️ .env file missing! Let's create it.${NC}"
    cp .env.example .env
    
    echo -e "${GREEN}📝 Please enter your configuration below:${NC}"
    
    read -p "Enter Downloader Bot Token: " BOT_TOKEN
    sed -i "s/BOT_TOKEN=.*/BOT_TOKEN=$BOT_TOKEN/" .env
    
    read -p "Enter Admin Bot Token: " ADMIN_BOT_TOKEN
    sed -i "s/ADMIN_BOT_TOKEN=.*/ADMIN_BOT_TOKEN=$ADMIN_BOT_TOKEN/" .env
    
    read -p "Enter Admin User IDs (comma separated): " ADMIN_IDS
    sed -i "s/ADMIN_USER_IDS=.*/ADMIN_USER_IDS=$ADMIN_IDS/" .env
    
    echo -e "${GREEN}✅ .env file created!${NC}"
else
    echo -e "${GREEN}✅ .env file found.${NC}"
fi

# 5. Run Deployment
echo -e "${BLUE}🚀 Launching Deployment Script...${NC}"
python3 deploy.py

echo -e "${GREEN}🎉 Setup Complete! Your bot is running.${NC}"
echo -e "${BLUE}📜 Check logs with: docker logs -f telegram-downloader-container${NC}"
