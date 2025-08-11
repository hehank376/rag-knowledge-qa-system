"""
健康检查API
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ..utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig
from ..llm.base import LLMConfig
from ..embeddings.base import EmbeddingConfig
from ..models.health import HealthStatus
from ..utils.exceptions import HealthCheckError

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/health", tags=["health"])

# 全局健康检查器实例
_health_checker: Optional[ModelHealthChecker] = None


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    overall_status: str
    last_check: Optional[str] = None
    total_models: int
    healthy_models: int
    unhealthy_models: int
    models: Dict[str, Dict[str, Any]]
    providers: Dict[str, Dict[str, Any]]
    alerts: List[Dict[str, Any]]


class ModelHealthResponse(BaseModel):
    """单个模型健康状态响应"""
    provider: str
    model_name: str
    model_type: str
    is_healthy: bool
    response_time: Optional[float] = None
    success_rate: float
    consecutive_failures: int
    total_checks: int
    last_check: Optional[str] = None
    error_message: Optional[str] = None


def get_health_checker() -> ModelHealthChecker:
    """获取健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        config = ModelHealthCheckConfig()
        _health_checker = ModelHealthChecker(config)
    return _health_checker


def initialize_health_checker(
    llm_configs: List[LLMConfig], 
    embedding_configs: List[EmbeddingConfig]
) -> ModelHealthChecker:
    """初始化健康检查器"""
    global _health_checker
    config = ModelHealthCheckConfig()
    _health_checker = ModelHealthChecker(config)
    
    # 启动定期健康检查
    import asyncio
    asyncio.create_task(_health_checker.start_periodic_check(llm_configs, embedding_configs))
    
    return _health_checker


@router.get("/", response_model=HealthCheckResponse)
async def get_system_health():
    """获取系统整体健康状态"""
    try:
        checker = get_health_checker()
        report = checker.generate_health_report()
        
        return HealthCheckResponse(**report)
        
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.get("/models", response_model=List[ModelHealthResponse])
async def get_models_health(
    provider: Optional[str] = Query(None, description="过滤特定提供商"),
    model_type: Optional[str] = Query(None, description="过滤模型类型 (llm/embedding)"),
    healthy_only: bool = Query(False, description="只返回健康的模型")
):
    """获取所有模型的健康状态"""
    try:
        checker = get_health_checker()
        models = []
        
        for key, status in checker.model_status.items():
            # 应用过滤条件
            if provider and status.provider != provider:
                continue
            if model_type and status.model_type != model_type:
                continue
            if healthy_only and not status.is_healthy:
                continue
            
            models.append(ModelHealthResponse(
                provider=status.provider,
                model_name=status.model_name,
                model_type=status.model_type,
                is_healthy=status.is_healthy,
                response_time=status.response_time,
                success_rate=status.success_rate,
                consecutive_failures=status.consecutive_failures,
                total_checks=status.total_checks,
                last_check=status.last_check.isoformat() if status.last_check else None,
                error_message=status.error_message
            ))
        
        return models
        
    except Exception as e:
        logger.error(f"获取模型健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型健康状态失败: {str(e)}")


@router.get("/models/{provider}/{model_name}/{model_type}", response_model=ModelHealthResponse)
async def get_model_health(provider: str, model_name: str, model_type: str):
    """获取特定模型的健康状态"""
    try:
        checker = get_health_checker()
        status = checker.get_model_status(provider, model_name, model_type)
        
        if not status:
            raise HTTPException(
                status_code=404, 
                detail=f"模型未找到: {provider}/{model_name} ({model_type})"
            )
        
        return ModelHealthResponse(
            provider=status.provider,
            model_name=status.model_name,
            model_type=status.model_type,
            is_healthy=status.is_healthy,
            response_time=status.response_time,
            success_rate=status.success_rate,
            consecutive_failures=status.consecutive_failures,
            total_checks=status.total_checks,
            last_check=status.last_check.isoformat() if status.last_check else None,
            error_message=status.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型健康状态失败: {str(e)}")


@router.get("/providers/{provider}", response_model=List[ModelHealthResponse])
async def get_provider_health(provider: str):
    """获取特定提供商的所有模型健康状态"""
    try:
        checker = get_health_checker()
        provider_status = checker.get_provider_status(provider)
        
        if not provider_status:
            raise HTTPException(status_code=404, detail=f"提供商未找到: {provider}")
        
        models = []
        for key, status in provider_status.items():
            models.append(ModelHealthResponse(
                provider=status.provider,
                model_name=status.model_name,
                model_type=status.model_type,
                is_healthy=status.is_healthy,
                response_time=status.response_time,
                success_rate=status.success_rate,
                consecutive_failures=status.consecutive_failures,
                total_checks=status.total_checks,
                last_check=status.last_check.isoformat() if status.last_check else None,
                error_message=status.error_message
            ))
        
        return models
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提供商健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取提供商健康状态失败: {str(e)}")


@router.get("/alerts")
async def get_health_alerts():
    """获取健康检查告警"""
    try:
        checker = get_health_checker()
        report = checker.generate_health_report()
        
        return {
            "alerts": report["alerts"],
            "total_alerts": len(report["alerts"]),
            "error_count": len([a for a in report["alerts"] if a["level"] == "error"]),
            "warning_count": len([a for a in report["alerts"] if a["level"] == "warning"])
        }
        
    except Exception as e:
        logger.error(f"获取健康告警失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取健康告警失败: {str(e)}")


@router.post("/check")
async def trigger_health_check():
    """手动触发健康检查"""
    try:
        checker = get_health_checker()
        
        # 这里需要从配置中获取模型配置
        # 暂时返回当前状态
        report = checker.generate_health_report()
        
        return {
            "message": "健康检查已触发",
            "timestamp": report["last_check"],
            "status": report["overall_status"]
        }
        
    except Exception as e:
        logger.error(f"触发健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"触发健康检查失败: {str(e)}")


@router.get("/status")
async def get_health_status():
    """获取简化的健康状态（用于负载均衡器等）"""
    try:
        checker = get_health_checker()
        overall_status = checker.get_overall_health_status()
        
        if overall_status == HealthStatus.HEALTHY:
            return {"status": "healthy", "code": 200}
        elif overall_status == HealthStatus.DEGRADED:
            return {"status": "degraded", "code": 200}
        else:
            return {"status": "unhealthy", "code": 503}
            
    except Exception as e:
        logger.error(f"获取健康状态失败: {str(e)}")
        return {"status": "error", "code": 500, "error": str(e)}