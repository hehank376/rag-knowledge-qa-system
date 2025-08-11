#!/usr/bin/env python3
"""
数据库适配器工厂
"""

from typing import Dict, Any
from urllib.parse import urlparse
from .base import DatabaseAdapter
from .adapters import SQLiteAdapter, PostgreSQLAdapter, MySQLAdapter
from ..utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

class DatabaseFactory:
    """数据库适配器工厂"""
    
    # 注册的适配器类
    _adapters = {
        'sqlite': SQLiteAdapter,
        'postgresql': PostgreSQLAdapter,
        'postgres': PostgreSQLAdapter,  # 别名
        'mysql': MySQLAdapter,
        'mariadb': MySQLAdapter,  # MariaDB使用MySQL适配器
    }
    
    @classmethod
    def create_adapter(cls, connection_string: str, config: Dict[str, Any] = None) -> DatabaseAdapter:
        """
        根据连接字符串创建数据库适配器
        
        Args:
            connection_string: 数据库连接字符串
            config: 数据库配置参数
            
        Returns:
            DatabaseAdapter: 数据库适配器实例
            
        Raises:
            ValueError: 不支持的数据库类型
        """
        try:
            # 解析连接字符串获取数据库类型
            parsed = urlparse(connection_string)
            db_type = parsed.scheme.lower()
            
            if db_type not in cls._adapters:
                raise ValueError(f"不支持的数据库类型: {db_type}")
            
            adapter_class = cls._adapters[db_type]
            adapter = adapter_class(connection_string, config)
            
            logger.info(f"创建数据库适配器: {db_type}")
            return adapter
            
        except Exception as e:
            logger.error(f"创建数据库适配器失败: {str(e)}")
            raise
    
    @classmethod
    def register_adapter(cls, db_type: str, adapter_class: type) -> None:
        """
        注册新的数据库适配器
        
        Args:
            db_type: 数据库类型名称
            adapter_class: 适配器类
        """
        if not issubclass(adapter_class, DatabaseAdapter):
            raise ValueError("适配器类必须继承自DatabaseAdapter")
        
        cls._adapters[db_type.lower()] = adapter_class
        logger.info(f"注册数据库适配器: {db_type}")
    
    @classmethod
    def get_supported_types(cls) -> list:
        """获取支持的数据库类型列表"""
        return list(cls._adapters.keys())
    
    @classmethod
    def is_supported(cls, db_type: str) -> bool:
        """检查是否支持指定的数据库类型"""
        return db_type.lower() in cls._adapters