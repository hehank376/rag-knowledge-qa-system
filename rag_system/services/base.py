"""
基础服务接口定义
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseService(ABC):
    """基础服务抽象类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass