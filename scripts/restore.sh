#!/bin/bash

# RAG Knowledge QA System Restore Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_FILE=$1
ENVIRONMENT=${2:-production}

if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Usage: $0 <backup_file.tar.gz> [environment]${NC}"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}🔄 Starting RAG Knowledge QA System restore...${NC}"
echo -e "${BLUE}Backup file: $BACKUP_FILE${NC}"
echo -e "${BLUE}Environment: $ENVIRONMENT${NC}"

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

# Confirm restore operation
echo -e "${YELLOW}⚠ This will overwrite existing data. Are you sure? (y/N)${NC}"
read -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Restore cancelled.${NC}"
    exit 0
fi

# Stop current system
echo -e "${BLUE}🛑 Stopping current system...${NC}"
./scripts/stop.sh $ENVIRONMENT

print_status "System stopped"

# Extract backup
echo -e "${BLUE}📦 Extracting backup...${NC}"
TEMP_DIR=$(mktemp -d)
tar xzf $BACKUP_FILE -C $TEMP_DIR

BACKUP_NAME=$(basename $BACKUP_FILE .tar.gz)
RESTORE_DIR="$TEMP_DIR/$BACKUP_NAME"

if [ ! -d "$RESTORE_DIR" ]; then
    print_error "Invalid backup file structure"
    rm -rf $TEMP_DIR
    exit 1
fi

print_status "Backup extracted"

# Show backup info
if [ -f "$RESTORE_DIR/backup_info.txt" ]; then
    echo -e "${BLUE}📋 Backup Information:${NC}"
    cat "$RESTORE_DIR/backup_info.txt"
    echo
fi

# Start database service only
echo -e "${BLUE}🗄️ Starting database service...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml up -d postgres-dev
    sleep 10
    
    # Wait for PostgreSQL
    timeout=60
    counter=0
    while ! docker-compose -f docker-compose.dev.yml exec -T postgres-dev pg_isready -U rag_user 2>/dev/null && [ $counter -lt $timeout ]; do
        sleep 1
        counter=$((counter + 1))
    done
else
    docker-compose up -d postgres
    sleep 10
    
    # Wait for PostgreSQL
    timeout=60
    counter=0
    while ! docker-compose exec -T postgres pg_isready -U rag_user 2>/dev/null && [ $counter -lt $timeout ]; do
        sleep 1
        counter=$((counter + 1))
    done
fi

print_status "Database service started"

# Restore database
echo -e "${BLUE}🗄️ Restoring database...${NC}"
if [ -f "$RESTORE_DIR/database.sql" ]; then
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f docker-compose.dev.yml exec -T postgres-dev psql -U rag_user -d rag_db_dev < "$RESTORE_DIR/database.sql"
    else
        docker-compose exec -T postgres psql -U rag_user -d rag_db < "$RESTORE_DIR/database.sql"
    fi
    print_status "Database restored"
else
    print_warning "No database backup found"
fi

# Restore uploaded files
echo -e "${BLUE}📁 Restoring uploaded files...${NC}"
if [ -d "$RESTORE_DIR/uploads" ]; then
    rm -rf uploads
    cp -r "$RESTORE_DIR/uploads" .
    print_status "Uploaded files restored"
else
    print_warning "No uploads backup found"
fi

# Restore configuration files
echo -e "${BLUE}⚙️ Restoring configuration files...${NC}"
if [ -d "$RESTORE_DIR/config" ]; then
    rm -rf config
    cp -r "$RESTORE_DIR/config" .
    print_status "Configuration files restored"
else
    print_warning "No config backup found"
fi

# Restore logs
echo -e "${BLUE}📋 Restoring logs...${NC}"
if [ -d "$RESTORE_DIR/logs" ]; then
    rm -rf logs
    cp -r "$RESTORE_DIR/logs" .
    print_status "Logs restored"
else
    print_warning "No logs backup found"
fi

# Start all services
echo -e "${BLUE}🚀 Starting all services...${NC}"
./scripts/deploy.sh $ENVIRONMENT

# Wait for services to be ready
sleep 30

# Restore vector store data
echo -e "${BLUE}🔢 Restoring vector store data...${NC}"
if [ -f "$RESTORE_DIR/chroma_data.tar.gz" ]; then
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f docker-compose.dev.yml exec -T chroma-dev tar xzf - -C / < "$RESTORE_DIR/chroma_data.tar.gz"
    else
        docker-compose exec -T chroma tar xzf - -C / < "$RESTORE_DIR/chroma_data.tar.gz"
    fi
    print_status "Vector store data restored"
else
    print_warning "No vector store backup found"
fi

# Cleanup
echo -e "${BLUE}🧹 Cleaning up temporary files...${NC}"
rm -rf $TEMP_DIR

print_status "Cleanup completed"

# Restart services to ensure everything is working
echo -e "${BLUE}🔄 Restarting services...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml restart
else
    docker-compose restart
fi

print_status "Services restarted"

# Verify system health
echo -e "${BLUE}🏥 Checking system health...${NC}"
sleep 10

if curl -f http://localhost:8000/health 2>/dev/null; then
    print_status "System health check passed"
else
    print_warning "System health check failed, please check logs"
fi

echo -e "${GREEN}✅ Restore completed successfully!${NC}"
echo -e "${BLUE}System Status:${NC}"

if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml ps
else
    docker-compose ps
fi

echo -e "${GREEN}🔄 RAG Knowledge QA System has been restored!${NC}"