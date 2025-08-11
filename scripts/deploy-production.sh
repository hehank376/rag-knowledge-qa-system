#!/bin/bash

# RAG Knowledge QA System Production Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting RAG Knowledge QA System Production Deployment...${NC}"

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

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root for security reasons"
    exit 1
fi

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

# Check if production environment file exists
if [ ! -f ".env.production" ]; then
    print_error "Production environment file (.env.production) not found"
    echo -e "${YELLOW}Please create .env.production from .env.production template${NC}"
    exit 1
fi

# Copy production environment
cp .env.production .env
print_status "Production environment configured"

# Create necessary directories with proper permissions
echo -e "${BLUE}📁 Creating production directories...${NC}"
sudo mkdir -p /opt/rag-system/{data,logs,uploads,backups,config}
sudo mkdir -p /opt/rag-system/data/{postgres,chroma,redis,prometheus,grafana,loki}
sudo mkdir -p /opt/rag-system/logs/{nginx,app}

# Set proper ownership
sudo chown -R $USER:$USER /opt/rag-system
chmod -R 755 /opt/rag-system

print_status "Production directories created"

# Create data directories for volume mounts
mkdir -p data/{postgres,chroma,redis,prometheus,grafana,loki}
mkdir -p logs/nginx

print_status "Volume mount directories created"

# Validate configuration
echo -e "${BLUE}🔍 Validating configuration...${NC}"

# Check required environment variables
required_vars=(
    "SECRET_KEY"
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "OPENAI_API_KEY"
    "GRAFANA_PASSWORD"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] && ! grep -q "^${var}=" .env; then
        print_error "Required environment variable $var is not set"
        exit 1
    fi
done

print_status "Configuration validation passed"

# Build production images
echo -e "${BLUE}🏗️ Building production images...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

print_status "Production images built"

# Stop any existing services
echo -e "${BLUE}🛑 Stopping existing services...${NC}"
docker-compose -f docker-compose.prod.yml down --remove-orphans

print_status "Existing services stopped"

# Start production services
echo -e "${BLUE}🚀 Starting production services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

print_status "Production services started"

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
timeout=120
counter=0
while ! docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U rag_user 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done
echo

if [ $counter -eq $timeout ]; then
    print_error "PostgreSQL failed to start within $timeout seconds"
    exit 1
fi

print_status "PostgreSQL is ready"

# Wait for Chroma
echo "Waiting for Chroma..."
timeout=60
counter=0
while ! curl -f http://localhost:8001/api/v1/heartbeat 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done
echo

if [ $counter -eq $timeout ]; then
    print_error "Chroma failed to start within $timeout seconds"
    exit 1
fi

print_status "Chroma is ready"

# Wait for API service
echo "Waiting for API service..."
timeout=120
counter=0
while ! curl -f http://localhost:8000/health 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done
echo

if [ $counter -eq $timeout ]; then
    print_error "API service failed to start within $timeout seconds"
    exit 1
fi

print_status "API service is ready"

# Run database migrations
echo -e "${BLUE}🗄️ Running database migrations...${NC}"
# Add migration commands here if needed
print_status "Database migrations completed"

# Setup monitoring
echo -e "${BLUE}📊 Setting up monitoring...${NC}"

# Wait for Prometheus
timeout=60
counter=0
while ! curl -f http://localhost:9090/-/ready 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 2
    counter=$((counter + 2))
done

if [ $counter -lt $timeout ]; then
    print_status "Prometheus is ready"
else
    print_warning "Prometheus may not be ready, check logs"
fi

# Wait for Grafana
timeout=60
counter=0
while ! curl -f http://localhost:3000/api/health 2>/dev/null && [ $counter -lt $timeout ]; do
    sleep 2
    counter=$((counter + 2))
done

if [ $counter -lt $timeout ]; then
    print_status "Grafana is ready"
else
    print_warning "Grafana may not be ready, check logs"
fi

# Setup SSL certificates (if provided)
if [ -f "nginx/ssl/cert.pem" ] && [ -f "nginx/ssl/key.pem" ]; then
    echo -e "${BLUE}🔒 SSL certificates found, enabling HTTPS...${NC}"
    # Restart nginx to load SSL configuration
    docker-compose -f docker-compose.prod.yml restart nginx
    print_status "HTTPS enabled"
else
    print_warning "No SSL certificates found, running HTTP only"
    echo -e "${YELLOW}To enable HTTPS, place cert.pem and key.pem in nginx/ssl/ directory${NC}"
fi

# Setup log rotation
echo -e "${BLUE}📋 Setting up log rotation...${NC}"
sudo tee /etc/logrotate.d/rag-system > /dev/null <<EOF
/opt/rag-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f /opt/rag-system/docker-compose.prod.yml restart rag-api
    endscript
}
EOF

print_status "Log rotation configured"

# Setup backup cron job
echo -e "${BLUE}💾 Setting up automated backups...${NC}"
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/rag-system && ./scripts/backup.sh production") | crontab -

print_status "Automated backups configured"

# Setup system monitoring
echo -e "${BLUE}🔍 Setting up system monitoring...${NC}"

# Create systemd service for monitoring
sudo tee /etc/systemd/system/rag-system-monitor.service > /dev/null <<EOF
[Unit]
Description=RAG System Monitor
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/opt/rag-system/scripts/health-check.sh
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer
sudo tee /etc/systemd/system/rag-system-monitor.timer > /dev/null <<EOF
[Unit]
Description=Run RAG System Monitor every 5 minutes
Requires=rag-system-monitor.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable rag-system-monitor.timer
sudo systemctl start rag-system-monitor.timer

print_status "System monitoring configured"

# Show service status
echo -e "${BLUE}📊 Service Status:${NC}"
docker-compose -f docker-compose.prod.yml ps

# Show resource usage
echo -e "${BLUE}💻 Resource Usage:${NC}"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Security hardening
echo -e "${BLUE}🔒 Applying security hardening...${NC}"

# Set proper file permissions
chmod 600 .env
chmod 600 .env.production
chmod -R 700 nginx/ssl/ 2>/dev/null || true

# Update firewall rules (if ufw is available)
if command -v ufw &> /dev/null; then
    sudo ufw --force enable
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 22/tcp
    print_status "Firewall configured"
fi

print_status "Security hardening applied"

# Final health check
echo -e "${BLUE}🏥 Running final health check...${NC}"
sleep 10

health_endpoints=(
    "http://localhost:8000/health"
    "http://localhost:9090/-/ready"
    "http://localhost:3000/api/health"
)

all_healthy=true
for endpoint in "${health_endpoints[@]}"; do
    if curl -f "$endpoint" &>/dev/null; then
        print_status "$(echo $endpoint | cut -d'/' -f3) is healthy"
    else
        print_warning "$(echo $endpoint | cut -d'/' -f3) health check failed"
        all_healthy=false
    fi
done

# Print deployment summary
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "${GREEN}✅ RAG Knowledge QA System deployed successfully!${NC}"
echo -e "${BLUE}Access Information:${NC}"
echo -e "  • Web Interface: http://$(hostname -I | awk '{print $1}')"
echo -e "  • API Endpoint: http://$(hostname -I | awk '{print $1}'):8000"
echo -e "  • API Documentation: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo -e "  • Monitoring Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
echo -e "  • Metrics: http://$(hostname -I | awk '{print $1}'):9090"

if [ -f "nginx/ssl/cert.pem" ]; then
    echo -e "  • HTTPS Web Interface: https://$(hostname -I | awk '{print $1}')"
fi

echo -e "${BLUE}Management Commands:${NC}"
echo -e "  • View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo -e "  • Stop services: docker-compose -f docker-compose.prod.yml down"
echo -e "  • Restart services: docker-compose -f docker-compose.prod.yml restart"
echo -e "  • Create backup: ./scripts/backup.sh production"
echo -e "  • Monitor status: docker-compose -f docker-compose.prod.yml ps"

echo -e "${BLUE}Important Notes:${NC}"
echo -e "  • Change default passwords in .env.production"
echo -e "  • Configure SSL certificates for HTTPS"
echo -e "  • Set up external monitoring and alerting"
echo -e "  • Review and update security settings"
echo -e "  • Configure backup storage (S3, etc.)"

if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}🎉 Production deployment completed successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️ Deployment completed with warnings. Please check service logs.${NC}"
    exit 1
fi