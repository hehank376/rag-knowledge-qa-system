#!/usr/bin/env python3
"""
SQLite数据库适配器
"""

import aiosqlite
from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from ..base import DatabaseAdapter
from ...utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

class SQLiteAdapter(DatabaseAdapter):
    """SQLite数据库适配器"""
    
    def __init__(self, connection_string: str, config: Dict[str, Any] = None):
        super().__init__(connection_string, config)
        # 从连接字符串中提取数据库文件路径
        self.db_path = connection_string.replace("sqlite:///", "").replace("sqlite://", "")
        self.timeout = config.get('timeout', 30.0) if config else 30.0
    
    async def initialize(self) -> None:
        """初始化SQLite数据库"""
        try:
            # 测试连接
            async with aiosqlite.connect(self.db_path, timeout=self.timeout) as conn:
                await conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式提高并发性能
                await conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全性
                await conn.execute("PRAGMA cache_size=10000")  # 增加缓存大小
                await conn.execute("PRAGMA temp_store=memory")  # 临时表存储在内存中
                await conn.commit()
            
            logger.info(f"SQLite数据库初始化完成: {self.db_path}")
        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭SQLite连接"""
        # SQLite使用连接池，无需显式关闭
        logger.info("SQLite连接已关闭")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """获取SQLite连接"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as conn:
            # 设置行工厂，返回字典格式的结果
            conn.row_factory = aiosqlite.Row
            yield conn
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            await conn.commit()
            return cursor.rowcount
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行操作"""
        async with self.get_connection() as conn:
            cursor = await conn.executemany(query, params_list)
            await conn.commit()
            return cursor.rowcount
    
    @asynccontextmanager
    async def begin_transaction(self) -> AsyncContextManager[aiosqlite.Connection]:
        """开始事务"""
        async with self.get_connection() as conn:
            await conn.execute("BEGIN")
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
    
    async def create_tables(self, schema: Dict[str, str]) -> None:
        """创建表结构"""
        async with self.get_connection() as conn:
            for table_name, create_sql in schema.items():
                await conn.execute(create_sql)
            await conn.commit()
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = await self.execute_query(query, (table_name,))
        return len(result) > 0
    
    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """创建索引"""
        columns_str = ", ".join(columns)
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})"
        await self.execute_update(query)
    
    def get_database_type(self) -> str:
        """获取数据库类型"""
        return "sqlite"
    
    def format_placeholder(self, index: int) -> str:
        """格式化参数占位符"""
        return "?"