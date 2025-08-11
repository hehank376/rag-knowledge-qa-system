# RAG Knowledge QA System - Deployment Guide

This guide provides comprehensive instructions for deploying the RAG Knowledge QA System using Docker containers.

## 📋 Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 4GB RAM available
- At least 10GB disk space

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd rag-knowledge-qa-system
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### 3. Deploy

```bash
# Production deployment
./scripts/deploy.sh production

# Development deployment
./scripts/deploy.sh development
```

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

```bash
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here

# Embedding Configuration
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Database Configuration
POSTGRES_PASSWORD=secure_password_here

# Security
SECRET_KEY=your_secret_key_here
```

### SSL/HTTPS Configuration

To enable HTTPS:

1. Place SSL certificates in `nginx/ssl/`:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key

2. Uncomment HTTPS server block in `nginx/nginx.conf`

3. Restart nginx:
   ```bash
   docker-compose restart nginx
   ```

## 🏗️ Architecture

The system consists of the following services:

- **rag-api**: Main application API
- **postgres**: PostgreSQL database
- **chroma**: Vector database
- **redis**: Cache and session storage
- **nginx**: Reverse proxy and static file server

## 📊 Service Management

### Start Services

```bash
# Production
docker-compose up -d

# Development
docker-compose -f docker-compose.dev.yml up -d
```

### Stop Services

```bash
./scripts/stop.sh [environment]
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f rag-api
```

### Service Status

```bash
docker-compose ps
```

## 🔍 Monitoring

### Health Checks

- API Health: `http://localhost:8000/health`
- Service Status: `docker-compose ps`

### Logs

Logs are stored in the `logs/` directory:
- `api.log` - Application logs
- `errors.log` - Error logs
- `access.log` - Access logs

### Metrics

Access metrics at:
- Application metrics: `http://localhost:8000/metrics`
- Container metrics: `docker stats`

## 💾 Backup and Restore

### Create Backup

```bash
./scripts/backup.sh [environment]
```

This creates a compressed backup containing:
- Database dump
- Uploaded files
- Configuration files
- Vector store data
- System logs

### Restore from Backup

```bash
./scripts/restore.sh backup_file.tar.gz [environment]
```

### Automated Backups

Set up automated backups with cron:

```bash
# Add to crontab
0 2 * * * /path/to/rag-system/scripts/backup.sh production
```

## 🔧 Troubleshooting

### Common Issues

#### Service Won't Start

1. Check logs:
   ```bash
   docker-compose logs service-name
   ```

2. Check disk space:
   ```bash
   df -h
   ```

3. Check memory usage:
   ```bash
   free -h
   ```

#### Database Connection Issues

1. Verify PostgreSQL is running:
   ```bash
   docker-compose exec postgres pg_isready -U rag_user
   ```

2. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

#### API Not Responding

1. Check API logs:
   ```bash
   docker-compose logs rag-api
   ```

2. Verify health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

#### Vector Database Issues

1. Check Chroma logs:
   ```bash
   docker-compose logs chroma
   ```

2. Verify Chroma is accessible:
   ```bash
   curl http://localhost:8001/api/v1/heartbeat
   ```

### Performance Tuning

#### Database Optimization

1. Adjust PostgreSQL settings in `docker-compose.yml`:
   ```yaml
   postgres:
     command: postgres -c shared_preload_libraries=pg_stat_statements -c max_connections=200
   ```

2. Monitor database performance:
   ```bash
   docker-compose exec postgres psql -U rag_user -d rag_db -c "SELECT * FROM pg_stat_activity;"
   ```

#### API Performance

1. Adjust worker count in `docker-compose.yml`:
   ```yaml
   rag-api:
     command: uvicorn rag_system.api.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. Monitor API performance:
   ```bash
   curl http://localhost:8000/metrics
   ```

## 🔒 Security

### Security Best Practices

1. **Change Default Passwords**: Update all default passwords in `.env`

2. **Use HTTPS**: Configure SSL certificates for production

3. **Network Security**: Use Docker networks to isolate services

4. **Regular Updates**: Keep Docker images updated

5. **Backup Encryption**: Encrypt backups for sensitive data

### Firewall Configuration

```bash
# Allow only necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 5432/tcp  # Block direct database access
ufw deny 6379/tcp  # Block direct Redis access
```

## 📈 Scaling

### Horizontal Scaling

1. **API Scaling**: Increase API replicas:
   ```yaml
   rag-api:
     deploy:
       replicas: 3
   ```

2. **Load Balancing**: Configure nginx upstream:
   ```nginx
   upstream rag_api {
       server rag-api-1:8000;
       server rag-api-2:8000;
       server rag-api-3:8000;
   }
   ```

### Vertical Scaling

1. **Resource Limits**: Set container resource limits:
   ```yaml
   rag-api:
     deploy:
       resources:
         limits:
           memory: 2G
           cpus: '1.0'
   ```

## 🚀 Production Deployment

### Pre-deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database passwords changed
- [ ] Firewall configured
- [ ] Backup strategy implemented
- [ ] Monitoring setup
- [ ] Resource limits set

### Deployment Steps

1. **Prepare Environment**:
   ```bash
   # Create production directory
   mkdir -p /opt/rag-system
   cd /opt/rag-system
   
   # Clone repository
   git clone <repository-url> .
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

3. **Deploy**:
   ```bash
   ./scripts/deploy.sh production
   ```

4. **Verify Deployment**:
   ```bash
   curl http://localhost/health
   ```

5. **Setup Monitoring**:
   ```bash
   # Setup log rotation
   logrotate -d /etc/logrotate.d/rag-system
   
   # Setup monitoring alerts
   # Configure your monitoring system
   ```

## 📞 Support

For deployment issues:

1. Check the troubleshooting section
2. Review service logs
3. Consult the API documentation at `/docs`
4. Create an issue in the repository

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Chroma Documentation](https://docs.trychroma.com/)