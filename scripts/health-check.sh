#!/bin/bash

# RAG Knowledge QA System Health Check Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/opt/rag-system/logs/health-check.log"
ALERT_WEBHOOK="${SLACK_WEBHOOK_URL}"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to send alert
send_alert() {
    local message="$1"
    local severity="$2"
    
    log_message "ALERT [$severity]: $message"
    
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 RAG System Alert [$severity]: $message\"}" \
            "$ALERT_WEBHOOK" &>/dev/null || true
    fi
}

# Function to check service health
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local expected_status="${3:-200}"
    
    if curl -f -s -o /dev/null -w "%{http_code}" "$health_url" | grep -q "$expected_status"; then
        log_message "✓ $service_name is healthy"
        return 0
    else
        log_message "✗ $service_name is unhealthy"
        send_alert "$service_name is not responding" "CRITICAL"
        return 1
    fi
}

# Function to check container status
check_container_status() {
    local container_name="$1"
    
    if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
        log_message "✓ Container $container_name is running"
        return 0
    else
        log_message "✗ Container $container_name is not running"
        send_alert "Container $container_name is not running" "CRITICAL"
        return 1
    fi
}

# Function to check resource usage
check_resource_usage() {
    local container_name="$1"
    local memory_threshold="${2:-80}"
    local cpu_threshold="${3:-80}"
    
    # Get container stats
    stats=$(docker stats --no-stream --format "{{.MemPerc}},{{.CPUPerc}}" "$container_name" 2>/dev/null || echo "0.00%,0.00%")
    
    memory_usage=$(echo "$stats" | cut -d',' -f1 | sed 's/%//')
    cpu_usage=$(echo "$stats" | cut -d',' -f2 | sed 's/%//')
    
    # Check memory usage
    if (( $(echo "$memory_usage > $memory_threshold" | bc -l) )); then
        log_message "⚠ High memory usage in $container_name: ${memory_usage}%"
        send_alert "High memory usage in $container_name: ${memory_usage}%" "WARNING"
    fi
    
    # Check CPU usage
    if (( $(echo "$cpu_usage > $cpu_threshold" | bc -l) )); then
        log_message "⚠ High CPU usage in $container_name: ${cpu_usage}%"
        send_alert "High CPU usage in $container_name: ${cpu_usage}%" "WARNING"
    fi
    
    log_message "📊 $container_name resources: CPU ${cpu_usage}%, Memory ${memory_usage}%"
}

# Function to check disk space
check_disk_space() {
    local path="$1"
    local threshold="${2:-85}"
    
    usage=$(df "$path" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -gt "$threshold" ]; then
        log_message "⚠ High disk usage on $path: ${usage}%"
        send_alert "High disk usage on $path: ${usage}%" "WARNING"
    else
        log_message "✓ Disk usage on $path: ${usage}%"
    fi
}

# Function to check log file sizes
check_log_sizes() {
    local log_dir="/opt/rag-system/logs"
    local max_size_mb=100
    
    find "$log_dir" -name "*.log" -type f | while read -r log_file; do
        size_mb=$(du -m "$log_file" | cut -f1)
        
        if [ "$size_mb" -gt "$max_size_mb" ]; then
            log_message "⚠ Large log file: $log_file (${size_mb}MB)"
            send_alert "Large log file detected: $log_file (${size_mb}MB)" "WARNING"
        fi
    done
}

# Function to check database connectivity
check_database_connectivity() {
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U rag_user &>/dev/null; then
        log_message "✓ Database connectivity is good"
        return 0
    else
        log_message "✗ Database connectivity failed"
        send_alert "Database connectivity failed" "CRITICAL"
        return 1
    fi
}

# Function to check vector database
check_vector_database() {
    if curl -f -s "http://localhost:8001/api/v1/heartbeat" &>/dev/null; then
        log_message "✓ Vector database is responding"
        return 0
    else
        log_message "✗ Vector database is not responding"
        send_alert "Vector database is not responding" "CRITICAL"
        return 1
    fi
}

# Function to check Redis
check_redis() {
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping | grep -q "PONG"; then
        log_message "✓ Redis is responding"
        return 0
    else
        log_message "✗ Redis is not responding"
        send_alert "Redis is not responding" "CRITICAL"
        return 1
    fi
}

# Main health check function
main_health_check() {
    log_message "🏥 Starting health check..."
    
    local overall_health=0
    
    # Check container status
    containers=("rag-knowledge-qa-api-prod" "rag-postgres-prod" "rag-chroma-prod" "rag-redis-prod" "rag-nginx-prod")
    
    for container in "${containers[@]}"; do
        if ! check_container_status "$container"; then
            overall_health=1
        fi
    done
    
    # Check service health endpoints
    if ! check_service_health "API Service" "http://localhost:8000/health"; then
        overall_health=1
    fi
    
    if ! check_service_health "Nginx" "http://localhost/health"; then
        overall_health=1
    fi
    
    # Check database connectivity
    if ! check_database_connectivity; then
        overall_health=1
    fi
    
    # Check vector database
    if ! check_vector_database; then
        overall_health=1
    fi
    
    # Check Redis
    if ! check_redis; then
        overall_health=1
    fi
    
    # Check resource usage
    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
            check_resource_usage "$container"
        fi
    done
    
    # Check disk space
    check_disk_space "/" 85
    check_disk_space "/opt/rag-system" 85
    
    # Check log file sizes
    check_log_sizes
    
    # Check system load
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    cpu_count=$(nproc)
    load_threshold=$(echo "$cpu_count * 0.8" | bc)
    
    if (( $(echo "$load_avg > $load_threshold" | bc -l) )); then
        log_message "⚠ High system load: $load_avg (threshold: $load_threshold)"
        send_alert "High system load: $load_avg" "WARNING"
    else
        log_message "✓ System load: $load_avg"
    fi
    
    # Check memory usage
    memory_usage=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
    if (( $(echo "$memory_usage > 85" | bc -l) )); then
        log_message "⚠ High system memory usage: ${memory_usage}%"
        send_alert "High system memory usage: ${memory_usage}%" "WARNING"
    else
        log_message "✓ System memory usage: ${memory_usage}%"
    fi
    
    # Overall health status
    if [ $overall_health -eq 0 ]; then
        log_message "🎉 Overall system health: GOOD"
    else
        log_message "💔 Overall system health: DEGRADED"
        send_alert "System health is degraded" "WARNING"
    fi
    
    log_message "🏥 Health check completed"
    
    return $overall_health
}

# Function to generate health report
generate_health_report() {
    local report_file="/opt/rag-system/logs/health-report-$(date +%Y%m%d).json"
    
    cat > "$report_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "system": {
    "hostname": "$(hostname)",
    "uptime": "$(uptime -p)",
    "load_average": "$(uptime | awk -F'load average:' '{print $2}')",
    "memory_usage": "$(free -h | awk 'NR==2{printf "%s/%s (%.2f%%)", $3,$2,$3*100/$2}')",
    "disk_usage": "$(df -h / | awk 'NR==2{printf "%s/%s (%s)", $3,$2,$5}')"
  },
  "containers": [
EOF

    first=true
    for container in rag-knowledge-qa-api-prod rag-postgres-prod rag-chroma-prod rag-redis-prod rag-nginx-prod; do
        if [ "$first" = false ]; then
            echo "," >> "$report_file"
        fi
        first=false
        
        status="stopped"
        if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
            status="running"
        fi
        
        stats=$(docker stats --no-stream --format "{{.MemPerc}},{{.CPUPerc}}" "$container" 2>/dev/null || echo "0.00%,0.00%")
        memory_usage=$(echo "$stats" | cut -d',' -f1)
        cpu_usage=$(echo "$stats" | cut -d',' -f2)
        
        cat >> "$report_file" <<EOF
    {
      "name": "$container",
      "status": "$status",
      "cpu_usage": "$cpu_usage",
      "memory_usage": "$memory_usage"
    }
EOF
    done
    
    cat >> "$report_file" <<EOF
  ],
  "services": {
    "api": "$(curl -f -s -o /dev/null -w "%{http_code}" "http://localhost:8000/health" 2>/dev/null || echo "000")",
    "nginx": "$(curl -f -s -o /dev/null -w "%{http_code}" "http://localhost/health" 2>/dev/null || echo "000")",
    "database": "$(docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U rag_user &>/dev/null && echo "ready" || echo "not_ready")",
    "vector_db": "$(curl -f -s "http://localhost:8001/api/v1/heartbeat" &>/dev/null && echo "ready" || echo "not_ready")",
    "redis": "$(docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG" && echo "ready" || echo "not_ready")"
  }
}
EOF

    log_message "📊 Health report generated: $report_file"
}

# Script execution
case "${1:-check}" in
    "check")
        main_health_check
        ;;
    "report")
        generate_health_report
        ;;
    "alert-test")
        send_alert "Health check alert test" "INFO"
        ;;
    *)
        echo "Usage: $0 {check|report|alert-test}"
        exit 1
        ;;
esac