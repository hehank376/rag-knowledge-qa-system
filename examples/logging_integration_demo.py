#!/usr/bin/env python3
"""
日志记录系统集成演示
演示任务9.2：日志和监控功能的日志集成
"""
import logging
import time
from datetime import datetime

from rag_system.utils.logging_config import (
    setup_logging, get_logger, log_api_access, log_error_with_context,
    DEVELOPMENT_CONFIG, PRODUCTION_CONFIG
)
from rag_system.utils.exceptions import DocumentNotFoundError, QATimeoutError
from rag_system.utils.monitoring import global_metrics_collector


def demo_logging_setup():
    """演示日志设置"""
    print("=" * 60)
    print("日志系统设置演示")
    print("=" * 60)
    
    # 1. 开发环境配置
    print("\n1. 开发环境日志配置")
    print("-" * 30)
    
    setup_logging(**DEVELOPMENT_CONFIG)
    dev_logger = get_logger("demo.development")
    
    dev_logger.debug("这是调试信息")
    dev_logger.info("这是信息日志")
    dev_logger.warning("这是警告日志")
    dev_logger.error("这是错误日志")
    
    # 2. 生产环境配置（仅演示，不实际切换）
    print("\n2. 生产环境日志配置（模拟）")
    print("-" * 30)
    print("生产环境配置:")
    print(f"  - 日志级别: {PRODUCTION_CONFIG['log_level']}")
    print(f"  - 文件日志: {PRODUCTION_CONFIG['enable_file_logging']}")
    print(f"  - 控制台日志: {PRODUCTION_CONFIG['enable_console_logging']}")


def demo_structured_logging():
    """演示结构化日志记录"""
    print("\n" + "=" * 60)
    print("结构化日志记录演示")
    print("=" * 60)
    
    # 获取不同模块的日志记录器
    api_logger = get_logger("rag_system.api")
    service_logger = get_logger("rag_system.services")
    error_logger = get_logger("rag_system.errors")
    
    # 1. API访问日志
    print("\n1. API访问日志记录")
    print("-" * 30)
    
    log_api_access(
        method="GET",
        url="/api/documents",
        status_code=200,
        response_time=0.245,
        client_ip="192.168.1.100",
        user_agent="Mozilla/5.0 (Test Browser)",
        request_id="req-12345"
    )
    
    log_api_access(
        method="POST",
        url="/api/qa",
        status_code=500,
        response_time=2.156,
        client_ip="192.168.1.101",
        user_agent="Python/requests",
        request_id="req-12346"
    )
    
    # 2. 服务日志
    print("\n2. 服务操作日志")
    print("-" * 30)
    
    service_logger.info("文档处理开始", extra={
        "document_id": "doc_123",
        "document_filename": "example.pdf",
        "file_size": 1024000,
        "operation": "text_extraction"
    })
    
    service_logger.info("向量化处理完成", extra={
        "document_id": "doc_123",
        "chunk_count": 45,
        "vector_dimension": 1536,
        "processing_time": 3.2
    })
    
    # 3. 错误日志
    print("\n3. 错误日志记录")
    print("-" * 30)
    
    # 模拟文档未找到错误
    doc_error = DocumentNotFoundError("doc_456")
    log_error_with_context(
        error_logger,
        doc_error,
        context={
            "user_id": "user_789",
            "operation": "document_retrieval",
            "request_id": "req_12347"
        }
    )
    
    # 模拟问答超时错误
    qa_error = QATimeoutError("什么是人工智能的未来发展趋势？", 30)
    log_error_with_context(
        error_logger,
        qa_error,
        context={
            "session_id": "session_abc",
            "user_id": "user_789",
            "llm_provider": "openai",
            "model": "gpt-4"
        },
        level="warning"
    )


def demo_performance_logging():
    """演示性能日志记录"""
    print("\n" + "=" * 60)
    print("性能日志记录演示")
    print("=" * 60)
    
    perf_logger = get_logger("rag_system.performance")
    
    # 1. 操作性能记录
    print("\n1. 操作性能日志")
    print("-" * 30)
    
    operations = [
        ("document_upload", 1.234),
        ("text_extraction", 2.567),
        ("text_chunking", 0.456),
        ("vector_embedding", 3.789),
        ("vector_storage", 0.234),
        ("similarity_search", 0.123),
        ("answer_generation", 4.567)
    ]
    
    for operation, duration in operations:
        perf_logger.info(f"操作完成: {operation}", extra={
            "operation": operation,
            "duration": duration,
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 记录到指标收集器
        global_metrics_collector.record_request(
            service=f"operation_{operation}",
            response_time=duration,
            success=True
        )
    
    # 2. 慢操作告警
    print("\n2. 慢操作告警")
    print("-" * 30)
    
    slow_operations = [
        ("large_document_processing", 15.234),
        ("complex_qa_generation", 12.567),
        ("batch_vector_update", 8.456)
    ]
    
    for operation, duration in slow_operations:
        if duration > 10.0:  # 超过10秒的操作
            perf_logger.warning(f"慢操作检测: {operation}", extra={
                "operation": operation,
                "duration": duration,
                "threshold": 10.0,
                "severity": "high" if duration > 15.0 else "medium"
            })


def demo_monitoring_integration():
    """演示监控与日志集成"""
    print("\n" + "=" * 60)
    print("监控与日志集成演示")
    print("=" * 60)
    
    monitor_logger = get_logger("rag_system.monitoring")
    
    # 1. 系统指标日志
    print("\n1. 系统指标日志记录")
    print("-" * 30)
    
    system_metrics = global_metrics_collector.get_system_metrics()
    
    monitor_logger.info("系统性能指标", extra={
        "cpu_usage": system_metrics.cpu_usage,
        "memory_usage": system_metrics.memory_usage,
        "disk_usage": system_metrics.disk_usage,
        "request_count": system_metrics.request_count,
        "error_count": system_metrics.error_count,
        "avg_response_time": system_metrics.avg_response_time,
        "timestamp": system_metrics.timestamp.isoformat()
    })
    
    # 2. 服务健康状态日志
    print("\n2. 服务健康状态日志")
    print("-" * 30)
    
    services_status = {
        "database": {"status": "healthy", "response_time": 0.045},
        "vector_store": {"status": "healthy", "response_time": 0.123},
        "llm_service": {"status": "degraded", "response_time": 2.345},
        "embedding_service": {"status": "unhealthy", "error": "Connection timeout"}
    }
    
    for service, status in services_status.items():
        if status["status"] == "healthy":
            monitor_logger.info(f"服务健康: {service}", extra={
                "service": service,
                "status": status["status"],
                "response_time": status.get("response_time")
            })
        elif status["status"] == "degraded":
            monitor_logger.warning(f"服务降级: {service}", extra={
                "service": service,
                "status": status["status"],
                "response_time": status.get("response_time"),
                "reason": "high_latency"
            })
        else:
            monitor_logger.error(f"服务不健康: {service}", extra={
                "service": service,
                "status": status["status"],
                "error": status.get("error")
            })
    
    # 3. 告警日志
    print("\n3. 告警日志记录")
    print("-" * 30)
    
    alerts = [
        {
            "type": "high_memory_usage",
            "message": "内存使用率过高",
            "value": 87.5,
            "threshold": 85.0,
            "severity": "warning"
        },
        {
            "type": "high_error_rate",
            "message": "错误率过高",
            "value": 0.15,
            "threshold": 0.05,
            "severity": "critical"
        },
        {
            "type": "slow_response",
            "message": "响应时间过长",
            "value": 5.2,
            "threshold": 3.0,
            "severity": "warning"
        }
    ]
    
    for alert in alerts:
        # 避免与日志记录保留字段冲突
        alert_extra = {k: v for k, v in alert.items() if k != 'message'}
        alert_extra['alert_message'] = alert['message']
        
        if alert["severity"] == "critical":
            monitor_logger.critical(f"严重告警: {alert['message']}", extra=alert_extra)
        else:
            monitor_logger.warning(f"告警: {alert['message']}", extra=alert_extra)


def demo_log_analysis():
    """演示日志分析"""
    print("\n" + "=" * 60)
    print("日志分析演示")
    print("=" * 60)
    
    analysis_logger = get_logger("rag_system.analysis")
    
    # 1. 请求统计分析
    print("\n1. 请求统计分析")
    print("-" * 30)
    
    service_metrics = global_metrics_collector.get_all_service_metrics()
    
    total_requests = sum(m.total_requests for m in service_metrics.values())
    total_errors = sum(m.failed_requests for m in service_metrics.values())
    avg_response_time = (
        sum(m.avg_response_time * m.total_requests for m in service_metrics.values()) / 
        total_requests if total_requests > 0 else 0
    )
    
    analysis_logger.info("请求统计分析", extra={
        "analysis_type": "request_statistics",
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": total_errors / total_requests if total_requests > 0 else 0,
        "avg_response_time": avg_response_time,
        "service_count": len(service_metrics),
        "analysis_timestamp": datetime.utcnow().isoformat()
    })
    
    # 2. 性能趋势分析
    print("\n2. 性能趋势分析")
    print("-" * 30)
    
    # 模拟性能趋势数据
    performance_trend = {
        "cpu_trend": "increasing",
        "memory_trend": "stable",
        "response_time_trend": "decreasing",
        "error_rate_trend": "increasing"
    }
    
    analysis_logger.info("性能趋势分析", extra={
        "analysis_type": "performance_trend",
        **performance_trend,
        "recommendation": "需要关注CPU使用率和错误率的上升趋势",
        "analysis_timestamp": datetime.utcnow().isoformat()
    })
    
    # 3. 异常模式分析
    print("\n3. 异常模式分析")
    print("-" * 30)
    
    error_patterns = {
        "most_common_error": "DocumentNotFoundError",
        "error_frequency": 15,
        "peak_error_time": "14:00-15:00",
        "affected_services": ["document_api", "qa_service"]
    }
    
    analysis_logger.warning("异常模式分析", extra={
        "analysis_type": "error_pattern",
        **error_patterns,
        "recommendation": "建议检查文档存储服务的稳定性",
        "analysis_timestamp": datetime.utcnow().isoformat()
    })


def main():
    """主演示函数"""
    print("RAG系统日志记录系统集成演示")
    print("=" * 80)
    
    try:
        # 1. 日志系统设置
        demo_logging_setup()
        
        # 2. 结构化日志记录
        demo_structured_logging()
        
        # 3. 性能日志记录
        demo_performance_logging()
        
        # 4. 监控与日志集成
        demo_monitoring_integration()
        
        # 5. 日志分析
        demo_log_analysis()
        
        print("\n" + "=" * 80)
        print("日志记录系统集成演示完成")
        print("=" * 80)
        print("\n提示：")
        print("- 日志文件保存在 logs/ 目录下")
        print("- 错误日志: logs/errors.log")
        print("- 应用日志: logs/rag_system.log")
        print("- API访问日志: logs/api_access.log")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()