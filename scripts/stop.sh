#!/bin/bash

# RAG Knowledge QA System Stop Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "development" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
fi

echo -e "${BLUE}🛑 Stopping RAG Knowledge QA System...${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Compose file: ${COMPOSE_FILE}${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Stop services
echo -e "${BLUE}🔄 Stopping services...${NC}"
docker-compose -f $COMPOSE_FILE down

print_status "Services stopped"

# Option to remove volumes
read -p "Do you want to remove data volumes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠ Removing data volumes...${NC}"
    docker-compose -f $COMPOSE_FILE down -v
    print_status "Data volumes removed"
fi

# Option to remove images
read -p "Do you want to remove Docker images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠ Removing Docker images...${NC}"
    docker-compose -f $COMPOSE_FILE down --rmi all
    print_status "Docker images removed"
fi

# Clean up orphaned containers
echo -e "${BLUE}🧹 Cleaning up orphaned containers...${NC}"
docker-compose -f $COMPOSE_FILE down --remove-orphans

print_status "Cleanup completed"

echo -e "${GREEN}✅ RAG Knowledge QA System stopped successfully!${NC}"