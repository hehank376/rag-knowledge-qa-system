"""
数据库连接测试
"""
import pytest
import tempfile
import os
from sqlalchemy import text

from rag_system.models.config import DatabaseConfig
from rag_system.database.connection import DatabaseManager
from rag_system.utils.exceptions import ConfigurationError


class TestDatabaseManager:
    """数据库管理器测试"""
    
    def test_sqlite_connection(self):
        """测试SQLite连接"""
        # 使用临时文件作为数据库
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            config = DatabaseConfig(
                url=f"sqlite:///{db_path}",
                echo=False
            )
            
            db_manager = DatabaseManager(config)
            db_manager.initialize()
            
            # 测试连接
            with db_manager.get_session_context() as session:
                result = session.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
            
            # 测试表是否创建
            with db_manager.get_session_context() as session:
                result = session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
                tables = [row[0] for row in result.fetchall()]
                assert 'documents' in tables
                assert 'sessions' in tables
                assert 'qa_pairs' in tables
            
            db_manager.close()
            
        finally:
            # 清理临时文件
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_invalid_database_url(self):
        """测试无效的数据库URL"""
        config = DatabaseConfig(url="invalid://invalid")
        db_manager = DatabaseManager(config)
        
        with pytest.raises(ConfigurationError):
            db_manager.initialize()
    
    def test_session_context_manager(self):
        """测试会话上下文管理器"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            config = DatabaseConfig(url=f"sqlite:///{db_path}")
            db_manager = DatabaseManager(config)
            db_manager.initialize()
            
            # 测试正常提交
            with db_manager.get_session_context() as session:
                session.execute(text("CREATE TABLE test_table (id INTEGER)"))
            
            # 验证表已创建
            with db_manager.get_session_context() as session:
                result = session.execute(text(
                    "SELECT name FROM sqlite_master WHERE name='test_table'"
                ))
                assert result.fetchone() is not None
            
            # 测试异常回滚
            try:
                with db_manager.get_session_context() as session:
                    session.execute(text("INSERT INTO test_table VALUES (1)"))
                    raise Exception("测试异常")
            except Exception:
                pass
            
            # 验证数据未插入（已回滚）
            with db_manager.get_session_context() as session:
                result = session.execute(text("SELECT COUNT(*) FROM test_table"))
                assert result.fetchone()[0] == 0
            
            db_manager.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_engine_property(self):
        """测试引擎属性"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            config = DatabaseConfig(url=f"sqlite:///{db_path}")
            db_manager = DatabaseManager(config)
            
            # 未初始化时应该抛出异常
            with pytest.raises(ConfigurationError):
                _ = db_manager.engine
            
            db_manager.initialize()
            
            # 初始化后应该能获取引擎
            engine = db_manager.engine
            assert engine is not None
            
            db_manager.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_get_session_without_initialization(self):
        """测试未初始化时获取会话"""
        config = DatabaseConfig(url="sqlite:///test.db")
        db_manager = DatabaseManager(config)
        
        with pytest.raises(ConfigurationError):
            db_manager.get_session()


class TestGlobalDatabaseFunctions:
    """全局数据库函数测试"""
    
    def test_global_database_manager(self):
        """测试全局数据库管理器"""
        from rag_system.database.connection import (
            initialize_database, get_db_manager, get_db_session, 
            get_db_session_context, close_database
        )
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            config = DatabaseConfig(url=f"sqlite:///{db_path}")
            
            # 初始化全局数据库管理器
            initialize_database(config)
            
            # 测试获取管理器
            db_manager = get_db_manager()
            assert db_manager is not None
            
            # 测试获取会话
            session = get_db_session()
            assert session is not None
            session.close()
            
            # 测试会话上下文管理器
            with get_db_session_context() as session:
                result = session.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
            
            # 关闭数据库
            close_database()
            
            # 关闭后应该无法获取管理器
            with pytest.raises(ConfigurationError):
                get_db_manager()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)