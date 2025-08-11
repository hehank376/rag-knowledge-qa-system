# 多平台模型运维指南

本指南详细介绍 RAG 系统多平台模型支持的日常运维、监控、故障处理和性能优化。

## 日常运维任务

### 1. 系统健康检查

#### 自动化健康检查

```python
#!/usr/bin/env python3
# daily_health_check.py

import asyncio
import json
import logging
from datetime import datetime
from rag_system.utils.health_checker import ModelHealthChecker

async def daily_health_check():
    """每日健康检查任务"""
    checker = ModelHealthChecker()
    
    print(f"开始健康检查 - {datetime.now()}")
    
    # 检查整体系统健康
    health_status = await checker.check_system_health()
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": health_status["overall_status"],
        "components": {}
    }
    
    for component, status in health_status["components"].items():
        report["components"][component] = {
            "status": status["status"],
            "response_time": status.get("response_time", 0),
            "last_check": status.get("last_check", ""),
            "error": status.get("error", None)
        }
        
        # 打印组件状态
        print(f"{component}: {status['status']}")
        if status["status"] != "healthy":
            print(f"  ⚠️  问题: {status.get('error', '未知错误')}")
    
    # 保存报告
    with open(f"health_reports/health_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 发送告警（如果有问题）
    if health_status["overall_status"] != "healthy":
        await send_alert(report)
    
    return report

async def send_alert(report):
    """发送告警通知"""
    # 这里可以集成邮件、Slack、钉钉等通知方式
    print("🚨 系统健康检查发现问题，需要关注！")
    
if __name__ == "__main__":
    asyncio.run(daily_health_check())
```

#### 手动健康检查命令

```bash
# 快速健康检查
curl -s http://localhost:8000/api/health | jq '.'

# 详细健康检查
curl -s http://localhost:8000/api/health/detailed | jq '.'

# 检查特定组件
curl -s http://localhost:8000/api/health/llm | jq '.'
curl -s http://localhost:8000/api/health/embeddings | jq '.'
```

### 2. 日志管理

#### 日志轮转配置

```bash
# /etc/logrotate.d/rag-system
/app/logs/rag-system.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 raguser raguser
    postrotate
        systemctl reload rag-system
    endscript
}
```

#### 日志分析脚本

```python
#!/usr/bin/env python3
# log_analyzer.py

import re
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta

def analyze_logs(log_file, hours=24):
    """分析最近N小时的日志"""
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    stats = {
        "total_requests": 0,
        "error_count": 0,
        "response_times": [],
        "providers": Counter(),
        "models": Counter(),
        "error_types": Counter(),
        "slow_requests": []
    }
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                log_time = datetime.fromisoformat(log_entry["timestamp"])
                
                if log_time < cutoff_time:
                    continue
                
                # 统计请求
                if "request" in log_entry.get("message", "").lower():
                    stats["total_requests"] += 1
                
                # 统计错误
                if log_entry["level"] == "ERROR":
                    stats["error_count"] += 1
                    stats["error_types"][log_entry.get("error_type", "unknown")] += 1
                
                # 统计响应时间
                if "response_time" in log_entry:
                    response_time = log_entry["response_time"]
                    stats["response_times"].append(response_time)
                    
                    # 记录慢请求
                    if response_time > 5.0:
                        stats["slow_requests"].append({
                            "timestamp": log_entry["timestamp"],
                            "response_time": response_time,
                            "endpoint": log_entry.get("endpoint", "unknown")
                        })
                
                # 统计提供商和模型使用
                if "provider" in log_entry:
                    stats["providers"][log_entry["provider"]] += 1
                if "model" in log_entry:
                    stats["models"][log_entry["model"]] += 1
                    
            except (json.JSONDecodeError, KeyError):
                continue
    
    # 计算统计信息
    if stats["response_times"]:
        stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
        stats["max_response_time"] = max(stats["response_times"])
        stats["min_response_time"] = min(stats["response_times"])
    
    stats["error_rate"] = stats["error_count"] / max(stats["total_requests"], 1)
    
    return stats

def print_log_summary(stats):
    """打印日志摘要"""
    print("📊 日志分析摘要")
    print("=" * 50)
    print(f"总请求数: {stats['total_requests']}")
    print(f"错误数量: {stats['error_count']}")
    print(f"错误率: {stats['error_rate']:.2%}")
    
    if stats["response_times"]:
        print(f"平均响应时间: {stats['avg_response_time']:.2f}s")
        print(f"最大响应时间: {stats['max_response_time']:.2f}s")
        print(f"最小响应时间: {stats['min_response_time']:.2f}s")
    
    print("\n🔧 提供商使用统计:")
    for provider, count in stats["providers"].most_common():
        print(f"  {provider}: {count}")
    
    print("\n🤖 模型使用统计:")
    for model, count in stats["models"].most_common():
        print(f"  {model}: {count}")
    
    if stats["error_types"]:
        print("\n❌ 错误类型统计:")
        for error_type, count in stats["error_types"].most_common():
            print(f"  {error_type}: {count}")
    
    if stats["slow_requests"]:
        print(f"\n🐌 慢请求 (>{5.0}s): {len(stats['slow_requests'])} 个")
        for req in stats["slow_requests"][:5]:  # 显示前5个
            print(f"  {req['timestamp']}: {req['response_time']:.2f}s - {req['endpoint']}")

if __name__ == "__main__":
    import sys
    log_file = sys.argv[1] if len(sys.argv) > 1 else "/app/logs/rag-system.log"
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    
    stats = analyze_logs(log_file, hours)
    print_log_summary(stats)
```

### 3. 配置管理

#### 配置备份脚本

```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/app/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份配置文件
cp config/production.yaml $BACKUP_DIR/production_$DATE.yaml
cp .env $BACKUP_DIR/env_$DATE.backup

# 备份数据库配置
sqlite3 rag_system.db ".backup $BACKUP_DIR/database_$DATE.db"

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.yaml" -mtime +30 -delete
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "配置备份完成: $DATE"
```

#### 配置验证脚本

```python
#!/usr/bin/env python3
# validate_config.py

from rag_system.config.loader import ConfigLoader
from rag_system.utils.compatibility import check_config_compatibility
import sys

def validate_config_file(config_path):
    """验证配置文件"""
    try:
        loader = ConfigLoader()
        config = loader.load_config(config_path)
        
        print(f"✅ 配置文件格式正确: {config_path}")
        
        # 检查兼容性
        issues = check_config_compatibility(config)
        if issues:
            print("⚠️  发现配置问题:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("✅ 配置兼容性检查通过")
            return True
            
    except Exception as e:
        print(f"❌ 配置文件验证失败: {e}")
        return False

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/production.yaml"
    
    if validate_config_file(config_path):
        print("🎉 配置验证通过，可以安全部署")
        sys.exit(0)
    else:
        print("💥 配置验证失败，请修复后再部署")
        sys.exit(1)
```

## 监控和告警

### 1. Prometheus 指标

#### 自定义指标收集

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# 定义指标
REQUEST_COUNT = Counter('rag_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('rag_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('rag_active_connections', 'Active connections')
MODEL_RESPONSE_TIME = Histogram('rag_model_response_seconds', 'Model response time', ['provider', 'model'])
ERROR_COUNT = Counter('rag_errors_total', 'Total errors', ['error_type', 'provider'])

class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()
    
    def record_request(self, method, endpoint, status, duration):
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_DURATION.observe(duration)
    
    def record_model_call(self, provider, model, duration):
        MODEL_RESPONSE_TIME.labels(provider=provider, model=model).observe(duration)
    
    def record_error(self, error_type, provider):
        ERROR_COUNT.labels(error_type=error_type, provider=provider).inc()
    
    def update_active_connections(self, count):
        ACTIVE_CONNECTIONS.set(count)

# 启动指标服务器
def start_metrics_server(port=9090):
    start_http_server(port)
    print(f"Metrics server started on port {port}")
```

### 2. 告警规则

#### Prometheus 告警规则

```yaml
# alerts.yml
groups:
  - name: rag-system
    rules:
      - alert: HighErrorRate
        expr: rate(rag_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "RAG系统错误率过高"
          description: "错误率超过10%，当前值: {{ $value }}"
      
      - alert: SlowResponse
        expr: histogram_quantile(0.95, rate(rag_request_duration_seconds_bucket[5m])) > 5
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "RAG系统响应缓慢"
          description: "95%分位响应时间超过5秒"
      
      - alert: ModelUnavailable
        expr: up{job="rag-system"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "RAG系统不可用"
          description: "系统已下线超过1分钟"
      
      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用过高"
          description: "内存使用超过1GB"
```

### 3. 监控仪表板

#### Grafana 仪表板配置

```json
{
  "dashboard": {
    "title": "RAG System Operations Dashboard",
    "tags": ["rag", "operations"],
    "panels": [
      {
        "title": "系统概览",
        "type": "stat",
        "targets": [
          {"expr": "up{job=\"rag-system\"}", "legendFormat": "系统状态"},
          {"expr": "rate(rag_requests_total[5m])", "legendFormat": "请求速率"},
          {"expr": "rate(rag_errors_total[5m])", "legendFormat": "错误速率"}
        ]
      },
      {
        "title": "响应时间分布",
        "type": "heatmap",
        "targets": [
          {"expr": "rate(rag_request_duration_seconds_bucket[5m])"}
        ]
      },
      {
        "title": "模型性能对比",
        "type": "graph",
        "targets": [
          {"expr": "histogram_quantile(0.95, rate(rag_model_response_seconds_bucket[5m]))", "legendFormat": "{{provider}}-{{model}}"}
        ]
      },
      {
        "title": "错误类型分布",
        "type": "piechart",
        "targets": [
          {"expr": "sum by (error_type) (rate(rag_errors_total[5m]))"}
        ]
      }
    ]
  }
}
```

## 性能调优

### 1. 系统性能监控

```python
#!/usr/bin/env python3
# performance_monitor.py

import psutil
import time
import json
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
    
    def collect_metrics(self):
        """收集系统性能指标"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        }
        
        return metrics
    
    def monitor_continuous(self, duration_minutes=60, interval_seconds=30):
        """持续监控系统性能"""
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            metrics = self.collect_metrics()
            self.metrics.append(metrics)
            
            # 实时显示关键指标
            print(f"CPU: {metrics['cpu']['percent']:.1f}% | "
                  f"内存: {metrics['memory']['percent']:.1f}% | "
                  f"磁盘: {metrics['disk']['percent']:.1f}%")
            
            # 检查是否需要告警
            if metrics['cpu']['percent'] > 80:
                print("⚠️  CPU使用率过高!")
            if metrics['memory']['percent'] > 85:
                print("⚠️  内存使用率过高!")
            if metrics['disk']['percent'] > 90:
                print("⚠️  磁盘空间不足!")
            
            time.sleep(interval_seconds)
        
        return self.metrics
    
    def generate_report(self):
        """生成性能报告"""
        if not self.metrics:
            return None
        
        cpu_values = [m['cpu']['percent'] for m in self.metrics]
        memory_values = [m['memory']['percent'] for m in self.metrics]
        
        report = {
            "monitoring_period": {
                "start": self.metrics[0]['timestamp'],
                "end": self.metrics[-1]['timestamp'],
                "duration_minutes": len(self.metrics) * 0.5  # 假设30秒间隔
            },
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "recommendations": []
        }
        
        # 生成优化建议
        if report['cpu']['avg'] > 70:
            report['recommendations'].append("考虑增加CPU资源或优化计算密集型操作")
        if report['memory']['avg'] > 80:
            report['recommendations'].append("考虑增加内存或优化内存使用")
        
        return report

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    print("开始性能监控...")
    
    try:
        monitor.monitor_continuous(duration_minutes=10, interval_seconds=30)
        report = monitor.generate_report()
        
        print("\n📊 性能监控报告")
        print("=" * 50)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
    except KeyboardInterrupt:
        print("\n监控已停止")
```

### 2. 模型性能优化

```python
# model_optimizer.py

class ModelOptimizer:
    def __init__(self):
        self.optimization_strategies = {
            'batch_size': self.optimize_batch_size,
            'concurrent_requests': self.optimize_concurrency,
            'timeout_settings': self.optimize_timeouts,
            'caching': self.optimize_caching
        }
    
    def optimize_batch_size(self, current_config):
        """优化批处理大小"""
        current_batch_size = current_config.get('batch_size', 100)
        
        # 基于内存和性能测试结果调整
        if current_config.get('memory_usage_percent', 0) > 80:
            recommended_batch_size = max(50, current_batch_size // 2)
            return {
                'batch_size': recommended_batch_size,
                'reason': '内存使用率过高，减少批处理大小'
            }
        elif current_config.get('avg_response_time', 0) > 3.0:
            recommended_batch_size = max(50, current_batch_size // 2)
            return {
                'batch_size': recommended_batch_size,
                'reason': '响应时间过长，减少批处理大小'
            }
        elif current_config.get('cpu_usage_percent', 0) < 50:
            recommended_batch_size = min(200, current_batch_size * 1.5)
            return {
                'batch_size': int(recommended_batch_size),
                'reason': 'CPU使用率较低，可以增加批处理大小'
            }
        
        return {'batch_size': current_batch_size, 'reason': '当前配置已优化'}
    
    def optimize_concurrency(self, current_config):
        """优化并发请求数"""
        current_concurrency = current_config.get('max_concurrent_requests', 5)
        cpu_count = psutil.cpu_count()
        
        if current_config.get('error_rate', 0) > 0.05:
            recommended_concurrency = max(2, current_concurrency - 1)
            return {
                'max_concurrent_requests': recommended_concurrency,
                'reason': '错误率过高，减少并发数'
            }
        elif current_config.get('cpu_usage_percent', 0) < 60:
            recommended_concurrency = min(cpu_count * 2, current_concurrency + 1)
            return {
                'max_concurrent_requests': recommended_concurrency,
                'reason': 'CPU资源充足，可以增加并发数'
            }
        
        return {'max_concurrent_requests': current_concurrency, 'reason': '当前并发配置已优化'}
    
    def generate_optimization_report(self, current_config, performance_metrics):
        """生成优化报告"""
        config_with_metrics = {**current_config, **performance_metrics}
        
        recommendations = {}
        for strategy_name, strategy_func in self.optimization_strategies.items():
            recommendations[strategy_name] = strategy_func(config_with_metrics)
        
        return {
            'current_config': current_config,
            'performance_metrics': performance_metrics,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
```

这个运维指南提供了完整的日常运维流程、监控告警机制和性能优化策略，帮助运维团队有效管理多平台模型系统。