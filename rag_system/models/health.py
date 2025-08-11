"""
健康检查相关数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    response_time: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    last_check: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "response_time": self.response_time,
            "error": self.error,
            "details": self.details or {},
            "last_check": self.last_check.isoformat() if self.last_check else None
        }


@dataclass
class ModelHealth:
    """模型健康状态"""
    provider: str
    model: str
    is_healthy: bool
    last_check: datetime
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider": self.provider,
            "model": self.model,
            "is_healthy": self.is_healthy,
            "last_check": self.last_check.isoformat(),
            "error_message": self.error_message,
            "response_time": self.response_time,
            "metadata": self.metadata or {}
        }


@dataclass
class SystemHealth:
    """系统健康状态"""
    llm_health: Optional[ModelHealth] = None
    embedding_health: Optional[ModelHealth] = None
    overall_healthy: bool = False
    last_check: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "llm_health": self.llm_health.to_dict() if self.llm_health else None,
            "embedding_health": self.embedding_health.to_dict() if self.embedding_health else None,
            "overall_healthy": self.overall_healthy,
            "last_check": self.last_check.isoformat() if self.last_check else None
        }