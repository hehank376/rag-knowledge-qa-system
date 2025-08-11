#!/bin/bash

# RAG Knowledge QA System Deployment Test Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing RAG Knowledge QA System Deployment...${NC}"

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

# Test Docker installation
echo -e "${BLUE}🐳 Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    print_status "Docker is installed: $DOCKER_VERSION"
else
    print_error "Docker is not installed"
    exit 1
fi

# Test Docker Compose installation
echo -e "${BLUE}🐙 Checking Docker Compose installation...${NC}"
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    print_status "Docker Compose is installed: $COMPOSE_VERSION"
else
    print_error "Docker Compose is not installed"
    exit 1
fi

# Test Docker daemon
echo -e "${BLUE}🔧 Checking Docker daemon...${NC}"
if docker info &> /dev/null; then
    print_status "Docker daemon is running"
else
    print_error "Docker daemon is not running"
    exit 1
fi

# Check required files
echo -e "${BLUE}📁 Checking required files...${NC}"
required_files=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "requirements.txt"
    "scripts/deploy.sh"
    "scripts/stop.sh"
    "nginx/nginx.conf"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "Found: $file"
    else
        print_error "Missing: $file"
        exit 1
    fi
done

# Test environment file
echo -e "${BLUE}⚙️ Checking environment configuration...${NC}"
if [ -f ".env" ]; then
    print_status "Environment file exists"
else
    if [ -f ".env.example" ]; then
        print_warning "No .env file found, but .env.example exists"
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
        print_status "Created .env file"
    else
        print_error "No environment configuration found"
        exit 1
    fi
fi

# Test build process
echo -e "${BLUE}🏗️ Testing Docker build...${NC}"
if docker build -t rag-test . &> /dev/null; then
    print_status "Docker build successful"
    docker rmi rag-test &> /dev/null || true
else
    print_error "Docker build failed"
    exit 1
fi

# Test compose file syntax
echo -e "${BLUE}📋 Validating docker-compose files...${NC}"
if docker-compose -f docker-compose.yml config &> /dev/null; then
    print_status "docker-compose.yml is valid"
else
    print_error "docker-compose.yml has syntax errors"
    exit 1
fi

if docker-compose -f docker-compose.dev.yml config &> /dev/null; then
    print_status "docker-compose.dev.yml is valid"
else
    print_error "docker-compose.dev.yml has syntax errors"
    exit 1
fi

# Test script permissions
echo -e "${BLUE}🔐 Checking script permissions...${NC}"
scripts=(
    "scripts/deploy.sh"
    "scripts/stop.sh"
    "scripts/backup.sh"
    "scripts/restore.sh"
)

for script in "${scripts[@]}"; do
    if [ -x "$script" ]; then
        print_status "Executable: $script"
    else
        print_warning "Not executable: $script (fixing...)"
        chmod +x "$script" 2>/dev/null || true
        if [ -x "$script" ]; then
            print_status "Fixed: $script"
        else
            print_warning "Could not fix permissions for: $script"
        fi
    fi
done

# Test directory structure
echo -e "${BLUE}📂 Checking directory structure...${NC}"
required_dirs=(
    "rag_system"
    "frontend"
    "tests"
    "scripts"
    "nginx"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_status "Directory exists: $dir"
    else
        print_warning "Directory missing: $dir"
    fi
done

# Create runtime directories
echo -e "${BLUE}📁 Creating runtime directories...${NC}"
runtime_dirs=(
    "data"
    "logs"
    "uploads"
    "backups"
    "vector_store"
)

for dir in "${runtime_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_status "Created: $dir"
    else
        print_status "Exists: $dir"
    fi
done

# Test network connectivity
echo -e "${BLUE}🌐 Testing network connectivity...${NC}"
if ping -c 1 google.com &> /dev/null; then
    print_status "Internet connectivity available"
else
    print_warning "No internet connectivity (may affect Docker image pulls)"
fi

# Test available resources
echo -e "${BLUE}💾 Checking system resources...${NC}"

# Check available memory
if command -v free &> /dev/null; then
    AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$AVAILABLE_MEM" -gt 2048 ]; then
        print_status "Available memory: ${AVAILABLE_MEM}MB"
    else
        print_warning "Low available memory: ${AVAILABLE_MEM}MB (recommended: >2GB)"
    fi
fi

# Check available disk space
AVAILABLE_DISK=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
if [ "$AVAILABLE_DISK" -gt 10 ]; then
    print_status "Available disk space: ${AVAILABLE_DISK}GB"
else
    print_warning "Low disk space: ${AVAILABLE_DISK}GB (recommended: >10GB)"
fi

# Summary
echo -e "${BLUE}📊 Test Summary:${NC}"
echo -e "${GREEN}✅ Deployment test completed successfully!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Review and update .env file with your configuration"
echo -e "  2. Run: ./scripts/deploy.sh development"
echo -e "  3. Access the system at: http://localhost"
echo -e "  4. Check API docs at: http://localhost:8000/docs"

echo -e "${GREEN}🎉 System is ready for deployment!${NC}"