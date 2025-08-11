#!/bin/bash

# RAG Knowledge QA System Deployment Script

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

echo -e "${BLUE}🚀 Starting RAG Knowledge QA System deployment...${NC}"
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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p data logs uploads config nginx/ssl vector_store

print_status "Directories created"

# Set permissions
echo -e "${BLUE}🔐 Setting permissions...${NC}"
chmod +x scripts/*.sh 2>/dev/null || true
chmod 755 data logs uploads config vector_store

print_status "Permissions set"

# Build and start services
echo -e "${BLUE}🏗️ Building and starting services...${NC}"

if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f $COMPOSE_FILE down --remove-orphans
    docker-compose -f $COMPOSE_FILE build --no-cache
    docker-compose -f $COMPOSE_FILE up -d
else
    docker-compose -f $COMPOSE_FILE down --remove-orphans
    docker-compose -f $COMPOSE_FILE build --no-cache
    docker-compose -f $COMPOSE_FILE up -d
fi

print_status "Services started"

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
timeout=60
counter=0
while ! docker-compose -f $COMPOSE_FILE exec -T postgres-dev pg_isready -U rag_user 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 1
    counter=$((counter + 1))
done

if [ $counter -eq $timeout ]; then
    print_error "PostgreSQL failed to start within $timeout seconds"
    exit 1
fi

print_status "PostgreSQL is ready"

# Wait for API service
echo "Waiting for API service..."
timeout=60
counter=0
api_container="rag-knowledge-qa-api"
if [ "$ENVIRONMENT" = "development" ]; then
    api_container="rag-knowledge-qa-api-dev"
fi

while ! curl -f http://localhost:8000/health 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 1
    counter=$((counter + 1))
done

if [ $counter -eq $timeout ]; then
    print_warning "API service health check failed, but continuing..."
else
    print_status "API service is ready"
fi

# Show service status
echo -e "${BLUE}📊 Service Status:${NC}"
docker-compose -f $COMPOSE_FILE ps

# Show logs for debugging
echo -e "${BLUE}📋 Recent logs:${NC}"
docker-compose -f $COMPOSE_FILE logs --tail=10

# Print access information
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}Access Information:${NC}"
echo -e "  • Web Interface: http://localhost"
echo -e "  • API Endpoint: http://localhost:8000"
echo -e "  • API Documentation: http://localhost:8000/docs"
echo -e "  • Health Check: http://localhost:8000/health"

if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "  • PostgreSQL: localhost:5433"
    echo -e "  • Chroma DB: localhost:8002"
    echo -e "  • Redis: localhost:6380"
else
    echo -e "  • PostgreSQL: localhost:5432"
    echo -e "  • Chroma DB: localhost:8001"
    echo -e "  • Redis: localhost:6379"
fi

echo -e "${BLUE}Management Commands:${NC}"
echo -e "  • View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo -e "  • Stop services: docker-compose -f $COMPOSE_FILE down"
echo -e "  • Restart services: docker-compose -f $COMPOSE_FILE restart"
echo -e "  • Update services: ./scripts/deploy.sh $ENVIRONMENT"

echo -e "${GREEN}✨ RAG Knowledge QA System is now running!${NC}"