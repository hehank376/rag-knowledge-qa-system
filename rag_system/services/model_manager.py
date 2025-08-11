"""
统一模型管理服务

统一管理embedding模型和重排序模型：
- 模型配置管理
- 模型生命周期管理
- 模型切换和热更新
- 模型性能监控
- 模型资源优化
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .embedding_service import EmbeddingService
from .reranking_service import RerankingService
from ..embeddings import EmbeddingConfig
from ..utils.exceptions import ConfigurationError, ProcessingError

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型枚举"""
    EMBEDDING = "embedding"
    RERANKING = "reranking"


@dataclass
class ModelConfig:
    """统一模型配置"""
    model_type: ModelType
    name: str
    provider: str
    model_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0  # 优先级，数字越大优先级越高
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_type': self.model_type.value,
            'name': self.name,
            'provider': self.provider,
            'model_name': self.model_name,
            'config': self.config,
            'enabled': self.enabled,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        """从字典创建"""
        return cls(
            model_type=ModelType(data['model_type']),
            name=data['name'],
            provider=data['provider'],
            model_name=data['model_name'],
            config=data.get('config', {}),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )


@dataclass
class ModelStatus:
    """模型状态"""
    name: str
    model_type: ModelType
    status: str  # 'loading', 'ready', 'error', 'disabled'
    health: str  # 'healthy', 'unhealthy', 'unknown'
    load_time: Optional[float] = None
    last_used: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'model_type': self.model_type.value,
            'status': self.status,
            'health': self.health,
            'load_time': self.load_time,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'error_message': self.error_message,
            'metrics': self.metrics
        }


class ModelManager:
    """统一模型管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化模型管理器
        
        Args:
            config: 管理器配置
        """
        self.config = config or {}
        
        # 模型配置存储
        self.model_configs: Dict[str, ModelConfig] = {}
        
        # 模型实例存储
        self.embedding_services: Dict[str, EmbeddingService] = {}
        self.reranking_services: Dict[str, RerankingService] = {}
        
        # 模型状态
        self.model_statuses: Dict[str, ModelStatus] = {}
        
        # 当前活跃模型
        self.active_embedding_model: Optional[str] = None
        self.active_reranking_model: Optional[str] = None
        
        # 管理器设置
        self.auto_load_models = self.config.get('auto_load_models', True)
        self.enable_model_switching = self.config.get('enable_model_switching', True)
        self.model_cache_size = self.config.get('model_cache_size', 3)
        self.health_check_interval = self.config.get('health_check_interval', 300)  # 5分钟
        
        # 统计信息
        self.stats = {
            'total_models': 0,
            'loaded_models': 0,
            'failed_models': 0,
            'model_switches': 0,
            'total_requests': 0,
            'embedding_requests': 0,
            'reranking_requests': 0
        }
        
        logger.info("模型管理器初始化完成")
    
    async def initialize(self) -> None:
        """初始化模型管理器"""
        try:
            logger.info("初始化模型管理器...")
            
            # 加载默认模型配置
            await self._load_default_configs()
            
            # 自动加载模型（如果启用）
            if self.auto_load_models:
                await self._auto_load_models()
            
            # 启动健康检查任务
            asyncio.create_task(self._health_check_loop())
            
            logger.info("模型管理器初始化完成")
            
        except Exception as e:
            logger.error(f"模型管理器初始化失败: {e}")
            raise ConfigurationError(f"模型管理器初始化失败: {e}")
    
    async def _load_default_configs(self) -> None:
        """加载默认模型配置"""
        try:
            # 默认embedding模型配置
            default_embedding_configs = self.config.get('default_embedding_models', [
                {
                    'name': 'default_embedding',
                    'provider': 'openai',
                    'model_name': 'text-embedding-ada-002',
                    'config': {
                        'api_key': self.config.get('openai_api_key'),
                        'batch_size': 100,
                        'max_tokens': 8192,
                        'timeout': 30
                    },
                    'enabled': True,
                    'priority': 10
                },
                {
                    'name': 'fallback_embedding',
                    'provider': 'mock',
                    'model_name': 'mock-embedding',
                    'config': {
                        'dimensions': 768,
                        'batch_size': 100
                    },
                    'enabled': True,
                    'priority': 1
                }
            ])
            
            # 默认重排序模型配置
            default_reranking_configs = self.config.get('default_reranking_models', [
                {
                    'name': 'default_reranking',
                    'provider': 'sentence_transformers',
                    'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                    'config': {
                        'max_length': 512,
                        'batch_size': 32,
                        'timeout': 30.0,
                        'device': 'cpu'
                    },
                    'enabled': True,
                    'priority': 10
                },
                {
                    'name': 'fast_reranking',
                    'provider': 'sentence_transformers',
                    'model_name': 'cross-encoder/ms-marco-TinyBERT-L-2-v2',
                    'config': {
                        'max_length': 256,
                        'batch_size': 64,
                        'timeout': 15.0,
                        'device': 'cpu'
                    },
                    'enabled': False,
                    'priority': 5
                }
            ])
            
            # 注册embedding模型配置
            for config_data in default_embedding_configs:
                model_config = ModelConfig(
                    model_type=ModelType.EMBEDDING,
                    name=config_data['name'],
                    provider=config_data['provider'],
                    model_name=config_data['model_name'],
                    config=config_data['config'],
                    enabled=config_data.get('enabled', True),
                    priority=config_data.get('priority', 0)
                )
                self.model_configs[model_config.name] = model_config
            
            # 注册重排序模型配置
            for config_data in default_reranking_configs:
                model_config = ModelConfig(
                    model_type=ModelType.RERANKING,
                    name=config_data['name'],
                    provider=config_data['provider'],
                    model_name=config_data['model_name'],
                    config=config_data['config'],
                    enabled=config_data.get('enabled', True),
                    priority=config_data.get('priority', 0)
                )
                self.model_configs[model_config.name] = model_config
            
            self.stats['total_models'] = len(self.model_configs)
            logger.info(f"加载默认模型配置完成: {len(self.model_configs)} 个模型")
            
        except Exception as e:
            logger.error(f"加载默认模型配置失败: {e}")
            raise
    
    async def _auto_load_models(self) -> None:
        """自动加载启用的模型"""
        try:
            # 按优先级排序
            sorted_configs = sorted(
                [config for config in self.model_configs.values() if config.enabled],
                key=lambda x: x.priority,
                reverse=True
            )
            
            # 加载embedding模型
            embedding_configs = [c for c in sorted_configs if c.model_type == ModelType.EMBEDDING]
            if embedding_configs and not self.active_embedding_model:
                for config in embedding_configs:
                    if await self.load_model(config.name):
                        self.active_embedding_model = config.name
                        break
            
            # 加载重排序模型
            reranking_configs = [c for c in sorted_configs if c.model_type == ModelType.RERANKING]
            if reranking_configs and not self.active_reranking_model:
                for config in reranking_configs:
                    if await self.load_model(config.name):
                        self.active_reranking_model = config.name
                        break
            
            logger.info(f"自动加载模型完成 - Embedding: {self.active_embedding_model}, Reranking: {self.active_reranking_model}")
            
        except Exception as e:
            logger.error(f"自动加载模型失败: {e}")
    
    async def register_model(self, model_config: ModelConfig) -> bool:
        """
        注册新模型配置
        
        Args:
            model_config: 模型配置
            
        Returns:
            是否注册成功
        """
        try:
            if model_config.name in self.model_configs:
                logger.warning(f"模型配置已存在，将更新: {model_config.name}")
            
            model_config.updated_at = datetime.now()
            self.model_configs[model_config.name] = model_config
            
            # 初始化模型状态
            self.model_statuses[model_config.name] = ModelStatus(
                name=model_config.name,
                model_type=model_config.model_type,
                status='registered',
                health='unknown'
            )
            
            self.stats['total_models'] = len(self.model_configs)
            logger.info(f"模型配置注册成功: {model_config.name}")
            return True
            
        except Exception as e:
            logger.error(f"模型配置注册失败: {e}")
            return False
    
    async def load_model(self, model_name: str) -> bool:
        """
        加载指定模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否加载成功
        """
        if model_name not in self.model_configs:
            logger.error(f"模型配置不存在: {model_name}")
            return False
        
        config = self.model_configs[model_name]
        
        try:
            logger.info(f"开始加载模型: {model_name} ({config.model_type.value})")
            start_time = datetime.now()
            
            # 更新状态
            self.model_statuses[model_name] = ModelStatus(
                name=model_name,
                model_type=config.model_type,
                status='loading',
                health='unknown'
            )
            
            if config.model_type == ModelType.EMBEDDING:
                success = await self._load_embedding_model(model_name, config)
            elif config.model_type == ModelType.RERANKING:
                success = await self._load_reranking_model(model_name, config)
            else:
                logger.error(f"不支持的模型类型: {config.model_type}")
                success = False
            
            load_time = (datetime.now() - start_time).total_seconds()
            
            if success:
                self.model_statuses[model_name].status = 'ready'
                self.model_statuses[model_name].health = 'healthy'
                self.model_statuses[model_name].load_time = load_time
                self.stats['loaded_models'] += 1
                logger.info(f"模型加载成功: {model_name}, 耗时: {load_time:.2f}秒")
            else:
                self.model_statuses[model_name].status = 'error'
                self.model_statuses[model_name].health = 'unhealthy'
                self.model_statuses[model_name].error_message = "模型加载失败"
                self.stats['failed_models'] += 1
                logger.error(f"模型加载失败: {model_name}")
            
            return success
            
        except Exception as e:
            self.model_statuses[model_name].status = 'error'
            self.model_statuses[model_name].health = 'unhealthy'
            self.model_statuses[model_name].error_message = str(e)
            self.stats['failed_models'] += 1
            logger.error(f"模型加载异常: {model_name}, 错误: {e}")
            return False
    
    async def _load_embedding_model(self, model_name: str, config: ModelConfig) -> bool:
        """加载embedding模型"""
        try:
            # 创建embedding配置
            embedding_config = EmbeddingConfig(
                provider=config.provider,
                model=config.model_name,
                **config.config
            )
            
            # 创建embedding服务
            service = EmbeddingService({'provider': config.provider, **config.config})
            service._embedding_config = embedding_config
            
            # 初始化服务
            await service.initialize()
            
            # 存储服务实例
            self.embedding_services[model_name] = service
            
            return True
            
        except Exception as e:
            logger.error(f"加载embedding模型失败: {model_name}, 错误: {e}")
            return False
    
    async def _load_reranking_model(self, model_name: str, config: ModelConfig) -> bool:
        """加载重排序模型"""
        try:
            # 使用新的重排序架构
            from ..reranking.factory import RerankingFactory
            from ..reranking.base import RerankingConfig
            
            # 创建重排序配置
            reranking_config = RerankingConfig(
                provider=config.provider,
                model=config.model_name,
                **config.config
            )
            
            # 使用工厂创建重排序实例
            reranking_instance = RerankingFactory.create_reranking(reranking_config)
            
            # 初始化重排序实例
            await reranking_instance.initialize()
            
            # 创建一个包装服务来兼容现有接口
            class RerankingServiceWrapper:
                def __init__(self, reranking_instance):
                    self.reranking_instance = reranking_instance
                    self.provider = reranking_instance.config.provider
                    self.model_name = reranking_instance.config.model
                
                async def test_reranking_connection(self) -> Dict[str, Any]:
                    """测试重排序连接"""
                    try:
                        # 使用重排序实例进行测试
                        test_query = "test query"
                        test_documents = ["test document"]
                        scores = await self.reranking_instance.rerank(test_query, test_documents)
                        
                        return {
                            "success": True,
                            "provider": self.provider,
                            "model": self.model_name,
                            "status": "healthy",
                            "test_score": scores[0] if scores else None
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "provider": self.provider,
                            "model": self.model_name,
                            "error": str(e)
                        }
                
                async def cleanup(self):
                    """清理资源"""
                    if hasattr(self.reranking_instance, 'cleanup'):
                        await self.reranking_instance.cleanup()
            
            # 创建包装服务
            service = RerankingServiceWrapper(reranking_instance)
            
            # 存储服务实例
            self.reranking_services[model_name] = service
            
            return True
            
        except Exception as e:
            logger.error(f"加载重排序模型失败: {model_name}, 错误: {e}")
            return False
    
    async def unload_model(self, model_name: str) -> bool:
        """
        卸载指定模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否卸载成功
        """
        try:
            if model_name not in self.model_configs:
                logger.warning(f"模型配置不存在: {model_name}")
                return False
            
            config = self.model_configs[model_name]
            
            if config.model_type == ModelType.EMBEDDING:
                if model_name in self.embedding_services:
                    await self.embedding_services[model_name].cleanup()
                    del self.embedding_services[model_name]
                    
                    # 如果是当前活跃模型，清除引用
                    if self.active_embedding_model == model_name:
                        self.active_embedding_model = None
            
            elif config.model_type == ModelType.RERANKING:
                if model_name in self.reranking_services:
                    await self.reranking_services[model_name].cleanup()  # 使用新的cleanup方法
                    del self.reranking_services[model_name]
                    
                    # 如果是当前活跃模型，清除引用
                    if self.active_reranking_model == model_name:
                        self.active_reranking_model = None
            
            # 更新状态
            if model_name in self.model_statuses:
                self.model_statuses[model_name].status = 'unloaded'
                self.model_statuses[model_name].health = 'unknown'
            
            self.stats['loaded_models'] = max(0, self.stats['loaded_models'] - 1)
            logger.info(f"模型卸载成功: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"模型卸载失败: {model_name}, 错误: {e}")
            return False
    
    async def switch_active_model(self, model_type: ModelType, model_name: str) -> bool:
        """
        切换活跃模型
        
        Args:
            model_type: 模型类型
            model_name: 模型名称
            
        Returns:
            是否切换成功
        """
        if not self.enable_model_switching:
            logger.warning("模型切换功能已禁用")
            return False
        
        try:
            if model_name not in self.model_configs:
                logger.error(f"模型配置不存在: {model_name}")
                return False
            
            config = self.model_configs[model_name]
            if config.model_type != model_type:
                logger.error(f"模型类型不匹配: 期望 {model_type.value}, 实际 {config.model_type.value}")
                return False
            
            # 确保模型已加载
            if model_name not in self.model_statuses or self.model_statuses[model_name].status != 'ready':
                logger.info(f"模型未加载，尝试加载: {model_name}")
                if not await self.load_model(model_name):
                    return False
            
            # 切换活跃模型
            if model_type == ModelType.EMBEDDING:
                old_model = self.active_embedding_model
                self.active_embedding_model = model_name
                logger.info(f"切换活跃embedding模型: {old_model} -> {model_name}")
            elif model_type == ModelType.RERANKING:
                old_model = self.active_reranking_model
                self.active_reranking_model = model_name
                logger.info(f"切换活跃重排序模型: {old_model} -> {model_name}")
            
            self.stats['model_switches'] += 1
            return True
            
        except Exception as e:
            logger.error(f"切换活跃模型失败: {e}")
            return False
    
    def get_active_embedding_service(self) -> Optional[EmbeddingService]:
        """获取当前活跃的embedding服务"""
        if self.active_embedding_model and self.active_embedding_model in self.embedding_services:
            self.stats['embedding_requests'] += 1
            self.stats['total_requests'] += 1
            
            # 更新最后使用时间
            if self.active_embedding_model in self.model_statuses:
                self.model_statuses[self.active_embedding_model].last_used = datetime.now()
            
            return self.embedding_services[self.active_embedding_model]
        return None
    
    def get_active_reranking_service(self) -> Optional[RerankingService]:
        """获取当前活跃的重排序服务"""
        if self.active_reranking_model and self.active_reranking_model in self.reranking_services:
            self.stats['reranking_requests'] += 1
            self.stats['total_requests'] += 1
            
            # 更新最后使用时间
            if self.active_reranking_model in self.model_statuses:
                self.model_statuses[self.active_reranking_model].last_used = datetime.now()
            
            return self.reranking_services[self.active_reranking_model]
        return None
    
    def get_embedding_service(self, model_name: str) -> Optional[EmbeddingService]:
        """获取指定的embedding服务"""
        # 首先尝试直接查找（使用注册名称）
        service = self.embedding_services.get(model_name)
        if service:
            return service
        
        # 如果没找到，尝试通过实际模型名称查找
        for name, config in self.model_configs.items():
            if (config.model_type == ModelType.EMBEDDING and 
                config.model_name == model_name and 
                name in self.embedding_services):
                return self.embedding_services[name]
        
        return None
    
    def get_reranking_service(self, model_name: str) -> Optional[RerankingService]:
        """获取指定的重排序服务"""
        # 首先尝试直接查找（使用注册名称）
        service = self.reranking_services.get(model_name)
        if service:
            return service
        
        # 如果没找到，尝试通过实际模型名称查找
        for name, config in self.model_configs.items():
            if (config.model_type == ModelType.RERANKING and 
                config.model_name == model_name and 
                name in self.reranking_services):
                return self.reranking_services[name]
        
        return None
    
    async def test_model(self, model_type: Union[str, ModelType], model_name: str) -> Dict[str, Any]:
        """测试指定模型"""
        try:
            if isinstance(model_type, str):
                model_type = ModelType(model_type)
            
            if model_type == ModelType.EMBEDDING:
                service = self.get_embedding_service(model_name)
                if service:
                    return await service.test_embedding()
                else:
                    return {
                        "success": False,
                        "error": f"嵌入模型 '{model_name}' 未找到"
                    }
            
            elif model_type == ModelType.RERANKING:
                service = self.get_reranking_service(model_name)
                if service:
                    # 使用新的重排序服务测试方法
                    return await service.test_reranking_connection()
                else:
                    return {
                        "success": False,
                        "error": f"重排序模型 '{model_name}' 未找到"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"不支持的模型类型: {model_type}"
                }
                
        except Exception as e:
            logger.error(f"测试模型失败 {model_type}/{model_name}: {str(e)}")
            return {
                "success": False,
                "error": f"测试失败: {str(e)}"
            }
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
    
    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        try:
            logger.debug("开始执行模型健康检查")
            
            # 检查embedding服务
            for model_name, service in self.embedding_services.items():
                try:
                    # 简单的健康检查
                    test_result = await service.test_embedding("健康检查测试")
                    
                    if model_name in self.model_statuses:
                        if test_result.get('success', False):
                            self.model_statuses[model_name].health = 'healthy'
                            self.model_statuses[model_name].error_message = None
                        else:
                            self.model_statuses[model_name].health = 'unhealthy'
                            self.model_statuses[model_name].error_message = test_result.get('error', 'Unknown error')
                
                except Exception as e:
                    if model_name in self.model_statuses:
                        self.model_statuses[model_name].health = 'unhealthy'
                        self.model_statuses[model_name].error_message = str(e)
            
            # 检查重排序服务
            for model_name, service in self.reranking_services.items():
                try:
                    health_check = await service.health_check()
                    
                    if model_name in self.model_statuses:
                        if health_check.get('status') == 'healthy':
                            self.model_statuses[model_name].health = 'healthy'
                            self.model_statuses[model_name].error_message = None
                        else:
                            self.model_statuses[model_name].health = 'unhealthy'
                            self.model_statuses[model_name].error_message = health_check.get('recovery_error', 'Health check failed')
                
                except Exception as e:
                    if model_name in self.model_statuses:
                        self.model_statuses[model_name].health = 'unhealthy'
                        self.model_statuses[model_name].error_message = str(e)
            
            logger.debug("模型健康检查完成")
            
        except Exception as e:
            logger.error(f"执行健康检查失败: {e}")
    
    def get_model_status(self, model_name: str) -> Optional[ModelStatus]:
        """获取模型状态"""
        return self.model_statuses.get(model_name)
    
    def get_all_model_statuses(self) -> Dict[str, ModelStatus]:
        """获取所有模型状态"""
        return self.model_statuses.copy()
    
    def get_model_configs(self) -> Dict[str, ModelConfig]:
        """获取所有模型配置"""
        return self.model_configs.copy()
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            **self.stats,
            'active_embedding_model': self.active_embedding_model,
            'active_reranking_model': self.active_reranking_model,
            'total_embedding_services': len(self.embedding_services),
            'total_reranking_services': len(self.reranking_services),
            'health_check_interval': self.health_check_interval,
            'auto_load_models': self.auto_load_models,
            'enable_model_switching': self.enable_model_switching
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """获取所有模型的性能指标"""
        metrics = {
            'manager_stats': self.get_manager_stats(),
            'embedding_metrics': {},
            'reranking_metrics': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # 获取嵌入模型指标
        for name, service in self.embedding_services.items():
            try:
                model_info = await service.get_model_info()
                metrics['embedding_metrics'][name] = model_info
            except Exception as e:
                logger.error(f"获取嵌入模型指标失败 {name}: {str(e)}")
                metrics['embedding_metrics'][name] = {'error': str(e)}
        
        # 获取重排序模型指标
        for name, service in self.reranking_services.items():
            try:
                model_info = await service.get_model_info()
                metrics['reranking_metrics'][name] = model_info
            except Exception as e:
                logger.error(f"获取重排序模型指标失败 {name}: {str(e)}")
                metrics['reranking_metrics'][name] = {'error': str(e)}
        
        return metrics

    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态信息"""
        try:
            # 基本信息
            status = {
                'manager_stats': self.get_manager_stats(),
                'model_configs': {name: config.to_dict() for name, config in self.model_configs.items()},
                'model_statuses': {name: status.to_dict() for name, status in self.model_statuses.items()},
                'active_models': {
                    'embedding': self.active_embedding_model,
                    'reranking': self.active_reranking_model
                }
            }
            
            # 添加服务详细信息
            embedding_details = {}
            for name, service in self.embedding_services.items():
                try:
                    embedding_details[name] = await service.get_service_stats()
                except Exception as e:
                    embedding_details[name] = {'error': str(e)}
            
            reranking_details = {}
            for name, service in self.reranking_services.items():
                try:
                    reranking_details[name] = service.get_metrics()
                except Exception as e:
                    reranking_details[name] = {'error': str(e)}
            
            status['service_details'] = {
                'embedding_services': embedding_details,
                'reranking_services': reranking_details
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取综合状态失败: {e}")
            return {'error': str(e)}
    
    async def cleanup(self) -> None:
        """清理所有资源"""
        try:
            logger.info("开始清理模型管理器资源...")
            
            # 清理embedding服务
            for name, service in self.embedding_services.items():
                try:
                    await service.cleanup()
                    logger.info(f"Embedding服务清理完成: {name}")
                except Exception as e:
                    logger.error(f"Embedding服务清理失败: {name}, 错误: {e}")
            
            # 清理重排序服务
            for name, service in self.reranking_services.items():
                try:
                    await service.close()
                    logger.info(f"重排序服务清理完成: {name}")
                except Exception as e:
                    logger.error(f"重排序服务清理失败: {name}, 错误: {e}")
            
            # 清理数据
            self.embedding_services.clear()
            self.reranking_services.clear()
            self.model_statuses.clear()
            self.active_embedding_model = None
            self.active_reranking_model = None
            
            logger.info("模型管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"模型管理器清理失败: {e}")


# 全局模型管理器实例
_global_model_manager: Optional[ModelManager] = None


def get_model_manager() -> Optional[ModelManager]:
    """获取全局模型管理器实例"""
    return _global_model_manager


async def initialize_global_model_manager(config: Optional[Dict[str, Any]] = None) -> ModelManager:
    """初始化全局模型管理器"""
    global _global_model_manager
    
    if _global_model_manager is None:
        _global_model_manager = ModelManager(config)
        await _global_model_manager.initialize()
    
    return _global_model_manager


async def cleanup_global_model_manager() -> None:
    """清理全局模型管理器"""
    global _global_model_manager
    
    if _global_model_manager is not None:
        await _global_model_manager.cleanup()
        _global_model_manager = None