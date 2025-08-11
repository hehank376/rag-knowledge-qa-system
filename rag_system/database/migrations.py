"""
数据库迁移脚本
"""
import logging
from typing import List, Callable
from sqlalchemy import text
from sqlalchemy.orm import Session

from .connection import DatabaseManager
from .models import Base

logger = logging.getLogger(__name__)


class Migration:
    """迁移脚本基类"""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
    
    def up(self, session: Session) -> None:
        """执行迁移"""
        raise NotImplementedError
    
    def down(self, session: Session) -> None:
        """回滚迁移"""
        raise NotImplementedError


class InitialMigration(Migration):
    """初始迁移：创建所有表"""
    
    def __init__(self):
        super().__init__("001", "创建初始数据库表结构")
    
    def up(self, session: Session) -> None:
        """创建所有表"""
        logger.info("执行初始迁移：创建数据库表")
        # 表已经通过Base.metadata.create_all创建
        
        # 创建索引
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_documents_status 
            ON documents(status);
        """))
        
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_documents_upload_time 
            ON documents(upload_time);
        """))
        
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sessions_last_activity 
            ON sessions(last_activity);
        """))
        
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_qa_pairs_session_id 
            ON qa_pairs(session_id);
        """))
        
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_qa_pairs_timestamp 
            ON qa_pairs(timestamp);
        """))
        
        session.commit()
        logger.info("初始迁移完成")
    
    def down(self, session: Session) -> None:
        """删除所有表"""
        logger.info("回滚初始迁移：删除数据库表")
        Base.metadata.drop_all(bind=session.bind)
        logger.info("初始迁移回滚完成")


class AddUserIdMigration(Migration):
    """添加用户ID字段到会话表"""
    
    def __init__(self):
        super().__init__("002", "添加用户ID字段到会话表")
    
    def up(self, session: Session) -> None:
        """添加user_id字段"""
        logger.info("执行迁移：添加用户ID字段")
        
        # 检查字段是否已存在
        result = session.execute(text("""
            SELECT COUNT(*) as count FROM pragma_table_info('sessions') 
            WHERE name = 'user_id'
        """))
        
        if result.scalar() == 0:
            # 添加user_id字段
            session.execute(text("""
                ALTER TABLE sessions ADD COLUMN user_id VARCHAR(255)
            """))
            
            # 创建索引
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON sessions(user_id)
            """))
            
            session.commit()
            logger.info("用户ID字段添加完成")
        else:
            logger.info("用户ID字段已存在，跳过迁移")
    
    def down(self, session: Session) -> None:
        """移除user_id字段"""
        logger.info("回滚迁移：移除用户ID字段")
        # SQLite不支持DROP COLUMN，需要重建表
        # 这里简化处理，实际生产环境需要更复杂的回滚逻辑
        logger.warning("SQLite不支持删除列，回滚跳过")


class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.migrations: List[Migration] = [
            InitialMigration(),
            AddUserIdMigration()
        ]
    
    def create_migration_table(self) -> None:
        """创建迁移记录表"""
        with self.db_manager.get_session_context() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(10) PRIMARY KEY,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            session.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移版本"""
        try:
            with self.db_manager.get_session_context() as session:
                result = session.execute(text(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ))
                return [row[0] for row in result.fetchall()]
        except Exception:
            # 如果表不存在，返回空列表
            return []
    
    def mark_migration_applied(self, migration: Migration) -> None:
        """标记迁移为已应用"""
        with self.db_manager.get_session_context() as session:
            session.execute(text("""
                INSERT INTO schema_migrations (version, description) 
                VALUES (:version, :description)
            """), {
                "version": migration.version,
                "description": migration.description
            })
            session.commit()
    
    def mark_migration_reverted(self, version: str) -> None:
        """标记迁移为已回滚"""
        with self.db_manager.get_session_context() as session:
            session.execute(text(
                "DELETE FROM schema_migrations WHERE version = :version"
            ), {"version": version})
            session.commit()
    
    def run_migrations(self) -> None:
        """运行所有待执行的迁移"""
        logger.info("开始执行数据库迁移")
        
        # 创建迁移记录表
        self.create_migration_table()
        
        # 获取已应用的迁移
        applied_versions = set(self.get_applied_migrations())
        
        # 执行未应用的迁移
        for migration in self.migrations:
            if migration.version not in applied_versions:
                logger.info(f"执行迁移 {migration.version}: {migration.description}")
                
                try:
                    with self.db_manager.get_session_context() as session:
                        migration.up(session)
                        self.mark_migration_applied(migration)
                    
                    logger.info(f"迁移 {migration.version} 执行成功")
                    
                except Exception as e:
                    logger.error(f"迁移 {migration.version} 执行失败: {str(e)}")
                    raise
            else:
                logger.info(f"迁移 {migration.version} 已应用，跳过")
        
        logger.info("数据库迁移完成")
    
    def rollback_migration(self, version: str) -> None:
        """回滚指定版本的迁移"""
        logger.info(f"开始回滚迁移 {version}")
        
        # 查找迁移
        migration = None
        for m in self.migrations:
            if m.version == version:
                migration = m
                break
        
        if not migration:
            raise ValueError(f"未找到版本 {version} 的迁移")
        
        # 检查是否已应用
        applied_versions = set(self.get_applied_migrations())
        if version not in applied_versions:
            logger.warning(f"迁移 {version} 未应用，无需回滚")
            return
        
        try:
            with self.db_manager.get_session_context() as session:
                migration.down(session)
                self.mark_migration_reverted(version)
            
            logger.info(f"迁移 {version} 回滚成功")
            
        except Exception as e:
            logger.error(f"迁移 {version} 回滚失败: {str(e)}")
            raise
    
    def get_migration_status(self) -> List[dict]:
        """获取迁移状态"""
        applied_versions = set(self.get_applied_migrations())
        
        status = []
        for migration in self.migrations:
            status.append({
                "version": migration.version,
                "description": migration.description,
                "applied": migration.version in applied_versions
            })
        
        return status