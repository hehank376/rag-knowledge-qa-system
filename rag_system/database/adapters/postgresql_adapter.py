#!/usr/bin/env python3
"""
PostgreSQL数据库适配器
"""

from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from ..base import DatabaseAdapter
from ...utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg未安装，PostgreSQL适配器不可用")

class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL数据库适配器"""
    
    def __init__(self, connection_string: str, config: Dict[str, Any] = None):
        if not ASYNCPG_AVAILABLE:
            raise ImportError("需要安装asyncpg库才能使用PostgreSQL适配器: pip install asyncpg")
        
        super().__init__(connection_string, config)
        self.min_size = config.get('min_size', 1) if config else 1
        self.max_size = config.get('max_size', 10) if config else 10
        self.command_timeout = config.get('command_timeout', 60) if config else 60
    
    async def initialize(self) -> None:
        """初始化PostgreSQL连接池"""
        try:
            self._connection_pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.command_timeout
            )
            logger.info("PostgreSQL连接池初始化完成")
        except Exception as e:
            logger.error(f"PostgreSQL连接池初始化失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭PostgreSQL连接池"""
        if self._connection_pool:
            await self._connection_pool.close()
            logger.info("PostgreSQL连接池已关闭")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[Any]:
        """获取PostgreSQL连接"""
        if not self._connection_pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self._connection_pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询"""
        async with self.get_connection() as conn:
            # 将占位符从?转换为$1, $2, ...
            pg_query = self._convert_placeholders(query)
            rows = await conn.fetch(pg_query, *(params or ()))
            return [dict(row) for row in rows]
    
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作"""
        async with self.get_connection() as conn:
            pg_query = self._convert_placeholders(query)
            result = await conn.execute(pg_query, *(params or ()))
            # PostgreSQL返回格式如 "UPDATE 3"，提取数字
            return int(result.split()[-1]) if result.split()[-1].isdigit() else 0
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行操作"""
        async with self.get_connection() as conn:
            pg_query = self._convert_placeholders(query)
            await conn.executemany(pg_query, params_list)
            return len(params_list)  # PostgreSQL executemany不返回影响行数
    
    @asynccontextmanager
    async def begin_transaction(self) -> AsyncContextManager[Any]:
        """开始事务"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def create_tables(self, schema: Dict[str, str]) -> None:
        """创建表结构"""
        async with self.get_connection() as conn:
            for table_name, create_sql in schema.items():
                await conn.execute(create_sql)
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
        """
        async with self.get_connection() as conn:
            return await conn.fetchval(query, table_name)
    
    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """创建索引"""
        columns_str = ", ".join(columns)
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})"
        await self.execute_update(query)
    
    def get_database_type(self) -> str:
        """获取数据库类型"""
        return "postgresql"
    
    def format_placeholder(self, index: int) -> str:
        """格式化参数占位符"""
        return f"${index}"
    
    def _convert_placeholders(self, query: str) -> str:
        """将?占位符转换为PostgreSQL的$1, $2, ...格式"""
        parts = query.split('?')
        if len(parts) == 1:
            return query
        
        result = parts[0]
        for i, part in enumerate(parts[1:], 1):
            result += f"${i}" + part
        
        return result