"""
监控和健康检查API接口
实现任务9.2：日志和监控功能
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel

from ..utils.monitoring import (
    global_metrics_collector, global_health_checker, global_performance_monitor,
    HealthStatus, PerformanceMetrics, ServiceMetrics
)
from ..utils.exceptions import RAGSystemError, ErrorCode
from ..config.loader import ConfigLoader

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: str
    services: Dict[str, Dict[str, Any]]
    overall_status: str


class MetricsResponse(BaseModel):
    """指标响应模型"""
    timestamp: str
    system_metrics: Dict[str, Any]
    service_metrics: Dict[str, Dict[str, Any]]


class AlertResponse(BaseModel):
    """告警响应模型"""
    alerts: List[Dict[str, Any]]
    total_count: int
    critical_count: int
    warning_count: int


# 健康检查函数
async def check_database_health() -> Dict[str, Any]:
    """检查数据库健康状态"""
    try:
        from ..database.connection import get_database_connection
        
        # 尝试连接数据库
        connection = get_database_connection()
        
        # 执行简单查询
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        return {
            'status': 'healthy',
            'details': {
                'connection': 'ok',
                'query_test': 'passed'
            }
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'details': {
                'error': str(e),
                'connection': 'failed'
            }
        }


async def check_vector_store_health() -> Dict[str, Any]:
    """检查向量存储健康状态"""
    try:
        from ..vector_store.chroma_store import ChromaVectorStore
        
        # 创建向量存储实例
        config = ConfigLoader().load_config()
        vector_store = ChromaVectorStore(
            persist_directory=config.vector_store.persist_directory,
            collection_name=config.vector_store.collection_name
        )
        
        # 检查集合是否存在
        collection_count = vector_store.get_collection_info().get('count', 0)
        
        return {
            'status': 'healthy',
            'details': {
                'collection_exists': True,
                'document_count': collection_count,
                'connection': 'ok'
            }
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'details': {
                'error': str(e),
                'connection': 'failed'
            }
        }


async def check_llm_health() -> Dict[str, Any]:
    """检查LLM服务健康状态"""
    try:
        from ..llm.factory import LLMFactory
        
        # 创建LLM实例
        config = ConfigLoader().load_config()
        llm = LLMFactory.create_llm(
            provider=config.llm.provider,
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )
        
        # 执行简单测试
        test_response = await llm.generate("Hello", max_tokens=10)
        
        return {
            'status': 'healthy',
            'details': {
                'provider': config.llm.provider,
                'model': config.llm.model,
                'test_response_length': len(test_response),
                'connection': 'ok'
            }
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'details': {
                'error': str(e),
                'provider': 'unknown',
                'connection': 'failed'
            }
        }


async def check_embedding_health() -> Dict[str, Any]:
    """检查嵌入服务健康状态"""
    try:
        from ..embeddings.factory import EmbeddingFactory
        
        # 创建嵌入实例
        config = ConfigLoader().load_config()
        embedding = EmbeddingFactory.create_embedding(
            provider=config.embeddings.provider,
            model=config.embeddings.model
        )
        
        # 执行简单测试
        test_vector = await embedding.embed_text("test")
        
        return {
            'status': 'healthy',
            'details': {
                'provider': config.embeddings.provider,
                'model': config.embeddings.model,
                'vector_dimension': len(test_vector),
                'connection': 'ok'
            }
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'details': {
                'error': str(e),
                'provider': 'unknown',
                'connection': 'failed'
            }
        }


# 注册健康检查
global_health_checker.register_check("database", check_database_health)
global_health_checker.register_check("vector_store", check_vector_store_health)
global_health_checker.register_check("llm", check_llm_health)
global_health_checker.register_check("embedding", check_embedding_health)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    系统健康检查
    
    Returns:
        健康检查结果
    """
    try:
        logger.info("执行系统健康检查")
        
        # 执行所有健康检查
        health_results = await global_health_checker.check_all_health()
        
        # 获取整体状态
        overall_status = global_health_checker.get_overall_status(health_results)
        
        # 转换结果格式
        services = {}
        for service, health_status in health_results.items():
            services[service] = {
                'status': health_status.status,
                'response_time': health_status.response_time,
                'error_message': health_status.error_message,
                'details': health_status.details or {}
            }
        
        logger.info(f"健康检查完成，整体状态: {overall_status}")
        
        return HealthCheckResponse(
            status="success",
            timestamp=datetime.utcnow().isoformat(),
            services=services,
            overall_status=overall_status
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/health/{service}")
async def health_check_service(service: str) -> Dict[str, Any]:
    """
    单个服务健康检查
    
    Args:
        service: 服务名称
        
    Returns:
        服务健康状态
    """
    try:
        logger.info(f"检查服务健康状态: {service}")
        
        health_status = await global_health_checker.check_health(service)
        
        return {
            'service': service,
            'status': health_status.status,
            'timestamp': health_status.timestamp.isoformat(),
            'response_time': health_status.response_time,
            'error_message': health_status.error_message,
            'details': health_status.details or {}
        }
        
    except Exception as e:
        logger.error(f"服务健康检查失败: {service}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务健康检查失败: {str(e)}"
        )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """
    获取系统性能指标
    
    Returns:
        性能指标数据
    """
    try:
        logger.info("获取系统性能指标")
        
        # 获取系统指标
        system_metrics = global_metrics_collector.get_system_metrics()
        
        # 获取服务指标
        service_metrics = global_metrics_collector.get_all_service_metrics()
        
        # 转换格式
        system_metrics_dict = {
            'cpu_usage': system_metrics.cpu_usage,
            'memory_usage': system_metrics.memory_usage,
            'disk_usage': system_metrics.disk_usage,
            'request_count': system_metrics.request_count,
            'error_count': system_metrics.error_count,
            'avg_response_time': system_metrics.avg_response_time,
            'active_connections': system_metrics.active_connections
        }
        
        service_metrics_dict = {}
        for service, metrics in service_metrics.items():
            service_metrics_dict[service] = {
                'total_requests': metrics.total_requests,
                'successful_requests': metrics.successful_requests,
                'failed_requests': metrics.failed_requests,
                'avg_response_time': metrics.avg_response_time,
                'min_response_time': metrics.min_response_time,
                'max_response_time': metrics.max_response_time,
                'last_request_time': (
                    metrics.last_request_time.isoformat()
                    if metrics.last_request_time else None
                )
            }
        
        return MetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
            system_metrics=system_metrics_dict,
            service_metrics=service_metrics_dict
        )
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能指标失败: {str(e)}"
        )


@router.get("/metrics/{service}")
async def get_service_metrics(service: str) -> Dict[str, Any]:
    """
    获取特定服务的性能指标
    
    Args:
        service: 服务名称
        
    Returns:
        服务性能指标
    """
    try:
        logger.info(f"获取服务性能指标: {service}")
        
        metrics = global_metrics_collector.get_service_metrics(service)
        
        return {
            'service': service,
            'timestamp': datetime.utcnow().isoformat(),
            'total_requests': metrics.total_requests,
            'successful_requests': metrics.successful_requests,
            'failed_requests': metrics.failed_requests,
            'success_rate': (
                metrics.successful_requests / metrics.total_requests
                if metrics.total_requests > 0 else 0.0
            ),
            'avg_response_time': metrics.avg_response_time,
            'min_response_time': metrics.min_response_time,
            'max_response_time': metrics.max_response_time,
            'last_request_time': (
                metrics.last_request_time.isoformat()
                if metrics.last_request_time else None
            )
        }
        
    except Exception as e:
        logger.error(f"获取服务指标失败: {service}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取服务指标失败: {str(e)}"
        )


@router.get("/alerts", response_model=AlertResponse)
async def get_alerts(
    minutes: int = Query(60, description="获取最近N分钟的告警", ge=1, le=1440)
) -> AlertResponse:
    """
    获取系统告警
    
    Args:
        minutes: 时间范围（分钟）
        
    Returns:
        告警信息
    """
    try:
        logger.info(f"获取最近 {minutes} 分钟的告警")
        
        # 获取当前系统指标并检查阈值
        system_metrics = global_metrics_collector.get_system_metrics()
        current_alerts = global_performance_monitor.check_thresholds(system_metrics)
        
        # 获取历史告警
        recent_alerts = global_performance_monitor.get_recent_alerts(minutes)
        
        # 合并告警
        all_alerts = recent_alerts + [
            {**alert, 'timestamp': alert['timestamp'].isoformat()}
            for alert in current_alerts
        ]
        
        # 统计告警数量
        critical_count = len([a for a in all_alerts if a.get('severity') == 'critical'])
        warning_count = len([a for a in all_alerts if a.get('severity') == 'warning'])
        
        return AlertResponse(
            alerts=all_alerts,
            total_count=len(all_alerts),
            critical_count=critical_count,
            warning_count=warning_count
        )
        
    except Exception as e:
        logger.error(f"获取告警失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取告警失败: {str(e)}"
        )


@router.post("/alerts/thresholds")
async def update_thresholds(thresholds: Dict[str, float]) -> Dict[str, Any]:
    """
    更新性能阈值
    
    Args:
        thresholds: 新的阈值设置
        
    Returns:
        更新结果
    """
    try:
        logger.info(f"更新性能阈值: {thresholds}")
        
        valid_metrics = ['cpu_usage', 'memory_usage', 'disk_usage', 'avg_response_time', 'error_rate']
        updated_thresholds = {}
        
        for metric, value in thresholds.items():
            if metric in valid_metrics:
                global_performance_monitor.set_threshold(metric, value)
                updated_thresholds[metric] = value
            else:
                logger.warning(f"忽略无效的指标: {metric}")
        
        return {
            'success': True,
            'message': f'成功更新 {len(updated_thresholds)} 个阈值',
            'updated_thresholds': updated_thresholds,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新阈值失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新阈值失败: {str(e)}"
        )


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """
    获取系统整体状态概览
    
    Returns:
        系统状态概览
    """
    try:
        logger.info("获取系统状态概览")
        
        # 健康检查
        health_results = await global_health_checker.check_all_health()
        overall_health = global_health_checker.get_overall_status(health_results)
        
        # 性能指标
        system_metrics = global_metrics_collector.get_system_metrics()
        
        # 最近告警
        recent_alerts = global_performance_monitor.get_recent_alerts(60)
        critical_alerts = [a for a in recent_alerts if a.get('severity') == 'critical']
        
        # 服务统计
        service_metrics = global_metrics_collector.get_all_service_metrics()
        total_requests = sum(m.total_requests for m in service_metrics.values())
        total_errors = sum(m.failed_requests for m in service_metrics.values())
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_health': overall_health,
            'system_performance': {
                'cpu_usage': system_metrics.cpu_usage,
                'memory_usage': system_metrics.memory_usage,
                'disk_usage': system_metrics.disk_usage,
                'avg_response_time': system_metrics.avg_response_time
            },
            'service_summary': {
                'total_services': len(service_metrics),
                'healthy_services': len([
                    h for h in health_results.values() 
                    if h.status == 'healthy'
                ]),
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': total_errors / total_requests if total_requests > 0 else 0.0
            },
            'alerts_summary': {
                'total_alerts': len(recent_alerts),
                'critical_alerts': len(critical_alerts),
                'has_critical': len(critical_alerts) > 0
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统状态失败: {str(e)}"
        )


@router.post("/metrics/reset")
async def reset_metrics() -> Dict[str, Any]:
    """
    重置性能指标
    
    Returns:
        重置结果
    """
    try:
        logger.info("重置性能指标")
        
        global_metrics_collector.reset_metrics()
        
        return {
            'success': True,
            'message': '性能指标已重置',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"重置指标失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置指标失败: {str(e)}"
        )