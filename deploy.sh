#!/bin/bash

# Simple deployment script for Solar Analyzer Pro
# This script helps deploy the application using Docker Compose

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
DEV_COMPOSE_FILE="docker-compose.dev.yml"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Solar Analyzer Pro - Deployment${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Use 'docker compose' or 'docker-compose' depending on what's available
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Parse command line arguments
MODE=${1:-production}

if [ "$MODE" = "dev" ] || [ "$MODE" = "development" ]; then
    COMPOSE_FILE=$DEV_COMPOSE_FILE
    echo -e "${YELLOW}📦 Deploying in DEVELOPMENT mode${NC}"
    echo -e "${YELLOW}Using: $DEV_COMPOSE_FILE${NC}"
elif [ "$MODE" = "prod" ] || [ "$MODE" = "production" ]; then
    echo -e "${GREEN}🚀 Deploying in PRODUCTION mode${NC}"
    echo -e "${GREEN}Using: $COMPOSE_FILE${NC}"
else
    echo -e "${RED}❌ Invalid mode: $MODE${NC}"
    echo -e "Usage: $0 [production|dev]"
    exit 1
fi

echo ""

# Stop and remove existing containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
$COMPOSE_CMD -f $COMPOSE_FILE down 2>/dev/null || true

# Build the image
echo -e "${BLUE}🔨 Building Docker image...${NC}"
$COMPOSE_CMD -f $COMPOSE_FILE build

# Start the containers
echo -e "${BLUE}🚀 Starting containers...${NC}"
$COMPOSE_CMD -f $COMPOSE_FILE up -d

# Wait for the application to be ready
echo -e "${BLUE}⏳ Waiting for application to be ready...${NC}"
sleep 5

# Check health
echo -e "${BLUE}🏥 Checking application health...${NC}"
if curl -f -s http://localhost:8000/ > /dev/null; then
    echo -e "${GREEN}✅ Application is healthy and running!${NC}"
else
    echo -e "${YELLOW}⚠️  Application is starting... (health check pending)${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Deployment completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${GREEN}🌍 Application URL: ${NC}http://localhost:8000"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  View logs:      ${COMPOSE_CMD} -f ${COMPOSE_FILE} logs -f"
echo -e "  Stop:           ${COMPOSE_CMD} -f ${COMPOSE_FILE} down"
echo -e "  Restart:        ${COMPOSE_CMD} -f ${COMPOSE_FILE} restart"
echo -e "  Status:         ${COMPOSE_CMD} -f ${COMPOSE_FILE} ps"
echo ""

# Show logs for a few seconds
echo -e "${BLUE}📋 Recent logs:${NC}"
$COMPOSE_CMD -f $COMPOSE_FILE logs --tail=20
