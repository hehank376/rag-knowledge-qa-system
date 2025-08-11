#!/usr/bin/env python3
"""
数据库抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager

class DatabaseAdapter(ABC):
    """数据库适配器抽象基类"""
    
    def __init__(self, connection_string: str, config: Dict[str, Any] = None):
        self.connection_string = connection_string
        self.config = config or {}
        self._connection_pool = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化数据库连接"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭数据库连接"""
        pass
    
    @abstractmethod
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[Any]:
        """获取数据库连接上下文管理器"""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        pass
    
    @abstractmethod
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作并返回影响行数"""
        pass
    
    @abstractmethod
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行操作"""
        pass
    
    @abstractmethod
    async def begin_transaction(self) -> AsyncContextManager[Any]:
        """开始事务"""
        pass
    
    @abstractmethod
    async def create_tables(self, schema: Dict[str, str]) -> None:
        """创建表结构"""
        pass
    
    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        pass
    
    @abstractmethod
    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """创建索引"""
        pass
    
    @abstractmethod
    def get_database_type(self) -> str:
        """获取数据库类型"""
        pass
    
    @abstractmethod
    def format_placeholder(self, index: int) -> str:
        """格式化参数占位符（不同数据库语法不同）"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.execute_query("SELECT 1")
            return True
        except Exception:
            return False