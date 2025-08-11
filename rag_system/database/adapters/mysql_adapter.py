#!/usr/bin/env python3
"""
MySQL数据库适配器
"""

from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from ..base import DatabaseAdapter
from ...utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

try:
    import aiomysql
    AIOMYSQL_AVAILABLE = True
except ImportError:
    AIOMYSQL_AVAILABLE = False
    logger.warning("aiomysql未安装，MySQL适配器不可用")

class MySQLAdapter(DatabaseAdapter):
    """MySQL数据库适配器"""
    
    def __init__(self, connection_string: str, config: Dict[str, Any] = None):
        if not AIOMYSQL_AVAILABLE:
            raise ImportError("需要安装aiomysql库才能使用MySQL适配器: pip install aiomysql")
        
        super().__init__(connection_string, config)
        self._parse_connection_string()
        self.minsize = config.get('minsize', 1) if config else 1
        self.maxsize = config.get('maxsize', 10) if config else 10
        self.charset = config.get('charset', 'utf8mb4') if config else 'utf8mb4'
    
    def _parse_connection_string(self):
        """解析MySQL连接字符串"""
        # 简单的连接字符串解析，格式: mysql://user:password@host:port/database
        if not self.connection_string.startswith('mysql://'):
            raise ValueError("MySQL连接字符串格式错误")
        
        # 移除协议前缀
        conn_str = self.connection_string[8:]  # 移除 'mysql://'
        
        # 分离用户信息和主机信息
        if '@' in conn_str:
            user_info, host_info = conn_str.split('@', 1)
            if ':' in user_info:
                self.user, self.password = user_info.split(':', 1)
            else:
                self.user = user_info
                self.password = ''
        else:
            raise ValueError("MySQL连接字符串缺少用户信息")
        
        # 分离主机和数据库
        if '/' in host_info:
            host_port, self.database = host_info.split('/', 1)
        else:
            host_port = host_info
            self.database = ''
        
        # 分离主机和端口
        if ':' in host_port:
            self.host, port_str = host_port.split(':', 1)
            self.port = int(port_str)
        else:
            self.host = host_port
            self.port = 3306
    
    async def initialize(self) -> None:
        """初始化MySQL连接池"""
        try:
            self._connection_pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                charset=self.charset,
                minsize=self.minsize,
                maxsize=self.maxsize,
                autocommit=False
            )
            logger.info("MySQL连接池初始化完成")
        except Exception as e:
            logger.error(f"MySQL连接池初始化失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭MySQL连接池"""
        if self._connection_pool:
            self._connection_pool.close()
            await self._connection_pool.wait_closed()
            logger.info("MySQL连接池已关闭")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[Any]:
        """获取MySQL连接"""
        if not self._connection_pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self._connection_pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                rows = await cursor.fetchall()
                return list(rows)
    
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                await conn.commit()
                return cursor.rowcount
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行操作"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, params_list)
                await conn.commit()
                return cursor.rowcount
    
    @asynccontextmanager
    async def begin_transaction(self) -> AsyncContextManager[Any]:
        """开始事务"""
        async with self.get_connection() as conn:
            await conn.begin()
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
    
    async def create_tables(self, schema: Dict[str, str]) -> None:
        """创建表结构"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                for table_name, create_sql in schema.items():
                    await cursor.execute(create_sql)
                await conn.commit()
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
            SELECT COUNT(*) as count FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """
        result = await self.execute_query(query, (self.database, table_name))
        return result[0]['count'] > 0 if result else False
    
    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """创建索引"""
        columns_str = ", ".join(columns)
        query = f"CREATE INDEX {index_name} ON {table_name}({columns_str})"
        try:
            await self.execute_update(query)
        except Exception as e:
            # 如果索引已存在，忽略错误
            if "Duplicate key name" not in str(e):
                raise
    
    def get_database_type(self) -> str:
        """获取数据库类型"""
        return "mysql"
    
    def format_placeholder(self, index: int) -> str:
        """格式化参数占位符"""
        return "%s"