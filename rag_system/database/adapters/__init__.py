#!/usr/bin/env python3
"""
数据库适配器模块
"""

from .sqlite_adapter import SQLiteAdapter
from .postgresql_adapter import PostgreSQLAdapter
from .mysql_adapter import MySQLAdapter

__all__ = ['SQLiteAdapter', 'PostgreSQLAdapter', 'MySQLAdapter']