#!/usr/bin/env python3
"""
数据库服务 - 与现有配置系统集成的数据库管理服务
"""

from typing import Dict, Any, Optional
from ..database.connection import init_database, get_database, close_database
from .config_service import ConfigService
from ..utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

class DatabaseService:
    """
    数据库服务 - 集成现有配置系统的数据库管理
    
    特点：
    1. 完全兼容现有配置文件格式
    2. 支持多种数据库类型
    3. 提供连接测试和健康检查
    4. 集成现有的配置管理流程
    """
    
    def __init__(self):
        self.config_service = ConfigService()
        self.db_manager = None
        self._initialized = False
    
    async def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return self.db_manager
        
        try:
            db_config = self.get_database_config()
            
            # 使用我们的多数据库架构初始化
            self.db_manager = await init_database(
                database_url=db_config['url'],
                config=db_config.get('config', {})
            )
            
            self._initialized = True
            logger.info(f"数据库服务初始化完成: {self.db_manager.get_database_type()}")
            
            return self.db_manager
            
        except Exception as e:
            logger.error(f"数据库服务初始化失败: {str(e)}")
            raise
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        获取数据库配置，兼容现有配置文件格式
        
        从 config/development.yaml 中的 database 部分读取配置
        """
        try:
            # 获取完整配置
            full_config = self.config_service.get_config()
            db_section = full_config.get('database', {})
            
            # 解析数据库URL和类型
            db_url = db_section.get('url', 'sqlite:///./database/rag_system.db')
            db_type = self._parse_database_type(db_url)
            
            # 构建配置对象
            config = {
                'url': db_url,
                'type': db_type,
                'config': self._build_adapter_config(db_type, db_section)
            }
            
            logger.debug(f"数据库配置加载完成: {db_type}")
            return config
            
        except Exception as e:
            logger.error(f"获取数据库配置失败: {str(e)}")
            # 返回默认配置
            return {
                'url': 'sqlite:///./database/rag_system.db',
                'type': 'sqlite',
                'config': {'timeout': 30.0}
            }
    
    def _parse_database_type(self, url: str) -> str:
        """从URL解析数据库类型"""
        if url.startswith('sqlite'):
            return 'sqlite'
        elif url.startswith('postgresql') or url.startswith('postgres'):
            return 'postgresql'
        elif url.startswith('mysql'):
            return 'mysql'
        else:
            logger.warning(f"未知的数据库类型: {url}")
            return 'unknown'
    
    def _build_adapter_config(self, db_type: str, db_section: Dict[str, Any]) -> Dict[str, Any]:
        """根据数据库类型构建适配器配置"""
        base_config = {
            'echo': db_section.get('echo', False)
        }
        
        if db_type == 'sqlite':
            base_config.update({
                'timeout': db_section.get('timeout', 30.0)
            })
        elif db_type in ['postgresql', 'mysql']:
            base_config.update({
                'min_size': db_section.get('pool_size', 5),
                'max_size': db_section.get('max_overflow', 10) + db_section.get('pool_size', 5),
                'command_timeout': db_section.get('pool_timeout', 30),
                'pool_recycle': db_section.get('pool_recycle', 3600)
            })
            
            if db_type == 'mysql':
                base_config.update({
                    'charset': db_section.get('charset', 'utf8mb4')
                })
        
        return base_config
    
    async def test_connection(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        测试数据库连接
        
        Args:
            config: 可选的测试配置，如果不提供则使用当前配置
            
        Returns:
            Dict: 测试结果
        """
        try:
            if config:
                # 使用提供的配置进行测试
                test_config = config
            else:
                # 使用当前配置进行测试
                test_config = self.get_database_config()
            
            # 创建临时数据库管理器进行测试
            from ..database.connection import DatabaseManager
            
            test_manager = DatabaseManager(
                database_url=test_config['url'],
                config=test_config.get('config', {})
            )
            
            # 初始化并测试连接
            await test_manager.initialize()
            is_healthy = await test_manager.health_check()
            
            # 获取连接信息
            connection_info = test_manager.get_connection_info()
            
            # 清理测试连接
            await test_manager.close()
            
            return {
                'success': is_healthy,
                'database_type': test_manager.get_database_type(),
                'connection_info': connection_info,
                'message': '数据库连接测试成功' if is_healthy else '数据库连接测试失败'
            }
            
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'数据库连接测试失败: {str(e)}'
            }
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.db_manager:
                await self.initialize()
            
            return await self.db_manager.health_check()
            
        except Exception as e:
            logger.error(f"数据库健康检查失败: {str(e)}")
            return False
    
    def get_connection_info(self) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        if not self.db_manager:
            return None
        
        info = self.db_manager.get_connection_info()
        
        # 添加服务级别的信息
        info.update({
            'service_initialized': self._initialized,
            'supported_types': ['sqlite', 'postgresql', 'mysql'],
            'current_config': self.get_database_config()
        })
        
        return info
    
    def get_database_manager(self):
        """获取数据库管理器实例"""
        return self.db_manager
    
    async def reload_config(self):
        """重新加载配置"""
        try:
            # 关闭现有连接
            if self.db_manager:
                await self.db_manager.close()
            
            # 重置状态
            self._initialized = False
            self.db_manager = None
            
            # 重新初始化
            await self.initialize()
            
            logger.info("数据库配置重新加载完成")
            return True
            
        except Exception as e:
            logger.error(f"重新加载数据库配置失败: {str(e)}")
            return False
    
    async def close(self):
        """关闭数据库服务"""
        try:
            if self.db_manager:
                await self.db_manager.close()
            
            await close_database()
            
            self._initialized = False
            self.db_manager = None
            
            logger.info("数据库服务已关闭")
            
        except Exception as e:
            logger.error(f"关闭数据库服务失败: {str(e)}")
    
    def get_supported_databases(self) -> Dict[str, Dict[str, Any]]:
        """获取支持的数据库类型信息"""
        return {
            'sqlite': {
                'name': 'SQLite',
                'description': '轻量级文件数据库，适合开发和小型应用',
                'url_template': 'sqlite:///./database/{dbname}.db',
                'config_fields': ['timeout', 'echo'],
                'features': ['file_based', 'serverless', 'zero_config']
            },
            'postgresql': {
                'name': 'PostgreSQL',
                'description': '企业级关系数据库，适合生产环境',
                'url_template': 'postgresql://{user}:{password}@{host}:{port}/{database}',
                'config_fields': ['pool_size', 'max_overflow', 'pool_timeout', 'echo'],
                'features': ['connection_pooling', 'transactions', 'json_support']
            },
            'mysql': {
                'name': 'MySQL',
                'description': '流行的关系数据库，适合Web应用',
                'url_template': 'mysql://{user}:{password}@{host}:{port}/{database}',
                'config_fields': ['pool_size', 'max_overflow', 'pool_timeout', 'charset', 'echo'],
                'features': ['connection_pooling', 'transactions', 'high_performance']
            }
        }

# 全局数据库服务实例
_database_service: Optional[DatabaseService] = None

def get_database_service() -> DatabaseService:
    """获取数据库服务实例"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service

async def init_database_service() -> DatabaseService:
    """初始化数据库服务"""
    service = get_database_service()
    await service.initialize()
    return service