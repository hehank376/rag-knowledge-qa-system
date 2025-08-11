#!/usr/bin/env python3
"""
数据库连接管理 - 支持多种数据库的统一接口
"""

from typing import Optional, Dict, Any, List
from .base import DatabaseAdapter
from .factory import DatabaseFactory
from ..utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """
    数据库管理器 - 使用适配器模式支持多种数据库
    
    支持的数据库类型:
    - SQLite: sqlite:///path/to/database.db
    - PostgreSQL: postgresql://user:password@host:port/database
    - MySQL: mysql://user:password@host:port/database
    """
    
    def __init__(self, database_url: str = "sqlite:///./rag_system.db", config: Dict[str, Any] = None):
        self.database_url = database_url
        self.config = config or {}
        self.adapter: Optional[DatabaseAdapter] = None
        
    async def initialize(self):
        """初始化数据库连接和表结构"""
        try:
            # 创建数据库适配器
            self.adapter = DatabaseFactory.create_adapter(self.database_url, self.config)
            
            # 初始化连接
            await self.adapter.initialize()
            
            # 创建必要的表结构
            await self._create_tables()
            
            logger.info(f"数据库管理器初始化完成: {self.adapter.get_database_type()}")
            
        except Exception as e:
            logger.error(f"数据库管理器初始化失败: {str(e)}")
            raise
    
    async def close(self):
        """关闭数据库连接"""
        if self.adapter:
            await self.adapter.close()
            logger.info("数据库连接已关闭")
    
    async def _create_tables(self):
        """创建系统所需的表结构"""
        try:
            # 定义表结构 - 使用通用SQL语法
            tables_schema = self._get_tables_schema()
            
            # 创建表
            await self.adapter.create_tables(tables_schema)
            
            # 创建索引
            await self._create_indexes()
            
            logger.info("数据库表结构创建完成")
            
        except Exception as e:
            logger.error(f"创建数据库表结构失败: {str(e)}")
            raise
    
    def _get_tables_schema(self) -> Dict[str, str]:
        """获取表结构定义"""
        db_type = self.adapter.get_database_type()
        
        if db_type == 'sqlite':
            return self._get_sqlite_schema()
        elif db_type == 'postgresql':
            return self._get_postgresql_schema()
        elif db_type == 'mysql':
            return self._get_mysql_schema()
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def _get_sqlite_schema(self) -> Dict[str, str]:
        """SQLite表结构"""
        return {
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    login_count INTEGER DEFAULT 0,
                    preferences TEXT DEFAULT '{}'
                )
            """,
            'user_sessions': """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """
        }
    
    def _get_postgresql_schema(self) -> Dict[str, str]:
        """PostgreSQL表结构"""
        return {
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100),
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    login_count INTEGER DEFAULT 0,
                    preferences JSONB DEFAULT '{}'
                )
            """,
            'user_sessions': """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address INET,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """
        }
    
    def _get_mysql_schema(self) -> Dict[str, str]:
        """MySQL表结构"""
        return {
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100),
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP NULL,
                    login_count INT DEFAULT 0,
                    preferences JSON,
                    INDEX idx_username (username),
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            'user_sessions': """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_expires_at (expires_at),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        }
    
    async def _create_indexes(self):
        """创建索引"""
        try:
            db_type = self.adapter.get_database_type()
            
            # SQLite和PostgreSQL需要单独创建索引
            if db_type in ['sqlite', 'postgresql']:
                await self.adapter.create_index('users', 'idx_users_username', ['username'])
                await self.adapter.create_index('users', 'idx_users_email', ['email'])
                await self.adapter.create_index('user_sessions', 'idx_sessions_user_id', ['user_id'])
                await self.adapter.create_index('user_sessions', 'idx_sessions_expires_at', ['expires_at'])
            
            # MySQL的索引在CREATE TABLE中定义
            
        except Exception as e:
            logger.warning(f"创建索引时出现警告: {str(e)}")
    
    # 代理方法 - 将调用转发给适配器
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询"""
        if not self.adapter:
            raise RuntimeError("数据库未初始化")
        return await self.adapter.execute_query(query, params)
    
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作"""
        if not self.adapter:
            raise RuntimeError("数据库未初始化")
        return await self.adapter.execute_update(query, params)
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行操作"""
        if not self.adapter:
            raise RuntimeError("数据库未初始化")
        return await self.adapter.execute_many(query, params_list)
    
    async def begin_transaction(self):
        """开始事务"""
        if not self.adapter:
            raise RuntimeError("数据库未初始化")
        return self.adapter.begin_transaction()
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        if not self.adapter:
            raise RuntimeError("数据库未初始化")
        return await self.adapter.table_exists(table_name)
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.adapter:
            return False
        return await self.adapter.health_check()
    
    def get_database_type(self) -> str:
        """获取数据库类型"""
        if not self.adapter:
            raise RuntimeError("数据库未初始化")
        return self.adapter.get_database_type()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'database_url': self.database_url,
            'database_type': self.get_database_type() if self.adapter else 'unknown',
            'config': self.config
        }

# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None

def get_database() -> DatabaseManager:
    """获取数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("数据库管理器未初始化，请先调用 init_database()")
    return _db_manager

async def init_database(database_url: str = None, config: Dict[str, Any] = None) -> DatabaseManager:
    """
    初始化数据库管理器
    
    Args:
        database_url: 数据库连接字符串
        config: 数据库配置参数
        
    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _db_manager
    
    if database_url is None:
        database_url = "sqlite:///./rag_system.db"
    
    _db_manager = DatabaseManager(database_url, config)
    await _db_manager.initialize()
    
    return _db_manager

async def close_database():
    """关闭数据库连接"""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None

def get_supported_databases() -> List[str]:
    """获取支持的数据库类型列表"""
    return DatabaseFactory.get_supported_types()