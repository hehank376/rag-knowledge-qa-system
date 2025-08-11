#!/bin/bash

# RAG Knowledge QA System Backup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="rag_backup_${TIMESTAMP}"
ENVIRONMENT=${1:-production}

echo -e "${BLUE}💾 Starting RAG Knowledge QA System backup...${NC}"
echo -e "${BLUE}Backup name: ${BACKUP_NAME}${NC}"

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

# Create backup directory
mkdir -p $BACKUP_DIR/$BACKUP_NAME

print_status "Backup directory created"

# Backup PostgreSQL database
echo -e "${BLUE}🗄️ Backing up PostgreSQL database...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml exec -T postgres-dev pg_dump -U rag_user rag_db_dev > $BACKUP_DIR/$BACKUP_NAME/database.sql
else
    docker-compose exec -T postgres pg_dump -U rag_user rag_db > $BACKUP_DIR/$BACKUP_NAME/database.sql
fi

print_status "Database backup completed"

# Backup uploaded files
echo -e "${BLUE}📁 Backing up uploaded files...${NC}"
if [ -d "uploads" ]; then
    cp -r uploads $BACKUP_DIR/$BACKUP_NAME/
    print_status "Uploaded files backup completed"
else
    print_warning "No uploads directory found"
fi

# Backup configuration files
echo -e "${BLUE}⚙️ Backing up configuration files...${NC}"
if [ -d "config" ]; then
    cp -r config $BACKUP_DIR/$BACKUP_NAME/
    print_status "Configuration files backup completed"
else
    print_warning "No config directory found"
fi

# Backup vector store data
echo -e "${BLUE}🔢 Backing up vector store data...${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.dev.yml exec -T chroma-dev tar czf - /chroma/chroma > $BACKUP_DIR/$BACKUP_NAME/chroma_data.tar.gz
else
    docker-compose exec -T chroma tar czf - /chroma/chroma > $BACKUP_DIR/$BACKUP_NAME/chroma_data.tar.gz
fi

print_status "Vector store backup completed"

# Backup logs
echo -e "${BLUE}📋 Backing up logs...${NC}"
if [ -d "logs" ]; then
    cp -r logs $BACKUP_DIR/$BACKUP_NAME/
    print_status "Logs backup completed"
else
    print_warning "No logs directory found"
fi

# Create backup metadata
echo -e "${BLUE}📝 Creating backup metadata...${NC}"
cat > $BACKUP_DIR/$BACKUP_NAME/backup_info.txt << EOF
RAG Knowledge QA System Backup
==============================
Backup Date: $(date)
Environment: $ENVIRONMENT
Backup Name: $BACKUP_NAME
System Info: $(uname -a)

Contents:
- database.sql: PostgreSQL database dump
- uploads/: Uploaded document files
- config/: Configuration files
- chroma_data.tar.gz: Vector store data
- logs/: System logs

Restore Instructions:
1. Stop the current system: ./scripts/stop.sh $ENVIRONMENT
2. Restore database: docker-compose exec -T postgres psql -U rag_user -d rag_db < database.sql
3. Restore files: cp -r uploads/* ../uploads/
4. Restore config: cp -r config/* ../config/
5. Restore vector data: docker-compose exec -T chroma tar xzf - -C / < chroma_data.tar.gz
6. Start system: ./scripts/deploy.sh $ENVIRONMENT
EOF

print_status "Backup metadata created"

# Compress backup
echo -e "${BLUE}🗜️ Compressing backup...${NC}"
cd $BACKUP_DIR
tar czf ${BACKUP_NAME}.tar.gz $BACKUP_NAME
rm -rf $BACKUP_NAME
cd ..

print_status "Backup compressed"

# Calculate backup size
BACKUP_SIZE=$(du -h $BACKUP_DIR/${BACKUP_NAME}.tar.gz | cut -f1)

echo -e "${GREEN}✅ Backup completed successfully!${NC}"
echo -e "${BLUE}Backup Details:${NC}"
echo -e "  • Location: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo -e "  • Size: $BACKUP_SIZE"
echo -e "  • Timestamp: $TIMESTAMP"

echo -e "${BLUE}Restore Command:${NC}"
echo -e "  ./scripts/restore.sh $BACKUP_DIR/${BACKUP_NAME}.tar.gz"

# Clean up old backups (keep last 7 days)
echo -e "${BLUE}🧹 Cleaning up old backups...${NC}"
find $BACKUP_DIR -name "rag_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true

print_status "Old backups cleaned up"

echo -e "${GREEN}💾 Backup process completed!${NC}"