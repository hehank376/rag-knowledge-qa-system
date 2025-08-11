"""
检索缓存服务模块

提供基于Redis的检索结果缓存功能，支持：
- 缓存键生成（包含所有影响结果的参数）
- 检索结果的序列化和反序列化
- 缓存过期时间配置和管理
- 缓存统计信息收集
- 错误处理和降级机制
"""

import json
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import asdict

from ..models.config import RetrievalConfig
from ..models.vector import SearchResult

logger = logging.getLogger(__name__)


class CacheService:
    """检索缓存服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化缓存服务
        
        Args:
            config: 缓存配置字典，包含Redis连接信息和缓存设置
        """
        self.config = config or {}
        self.redis_client = None
        self.cache_enabled = False
        
        # 缓存配置
        self.cache_ttl = self.config.get('cache_ttl', 3600)  # 默认1小时
        self.redis_host = self.config.get('redis_host', 'localhost')
        self.redis_port = self.config.get('redis_port', 6379)
        self.redis_db = self.config.get('redis_db', 0)
        self.redis_password = self.config.get('redis_password', None)
        
        # 统计信息
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }
        
        logger.info(f"缓存服务初始化 - TTL: {self.cache_ttl}秒, Redis: {self.redis_host}:{self.redis_port}")
    
    async def initialize(self) -> None:
        """初始化缓存服务，建立Redis连接"""
        try:
            import redis.asyncio as redis
            
            # 创建Redis连接
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # 测试连接
            await self.redis_client.ping()
            self.cache_enabled = True
            
            logger.info("缓存服务初始化成功，Redis连接已建立")
            
        except ImportError:
            logger.warning("Redis库未安装，缓存功能将被禁用")
            self.cache_enabled = False
        except Exception as e:
            logger.warning(f"缓存服务初始化失败: {e}，缓存功能将被禁用")
            self.cache_enabled = False
    
    async def get_cached_results(
        self, 
        query: str,
        config: RetrievalConfig,
        **kwargs
    ) -> Optional[List[SearchResult]]:
        """
        获取缓存的检索结果
        
        Args:
            query: 查询字符串
            config: 检索配置
            **kwargs: 其他影响检索结果的参数
            
        Returns:
            缓存的检索结果列表，如果缓存未命中或禁用则返回None
        """
        if not config.enable_cache or not self.cache_enabled:
            return None
        
        self.cache_stats['total_requests'] += 1
        
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(query, config, **kwargs)
            
            # 从Redis获取缓存数据
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # 反序列化缓存数据
                results = self._deserialize_results(cached_data)
                self.cache_stats['hits'] += 1
                
                logger.info(f"缓存命中: {cache_key[:32]}... (共{len(results)}个结果)")
                return results
            else:
                self.cache_stats['misses'] += 1
                logger.debug(f"缓存未命中: {cache_key[:32]}...")
                return None
                
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"缓存读取失败: {e}")
            return None
    
    async def cache_results(
        self, 
        query: str,
        config: RetrievalConfig,
        results: List[SearchResult],
        **kwargs
    ) -> None:
        """
        缓存检索结果
        
        Args:
            query: 查询字符串
            config: 检索配置
            results: 要缓存的检索结果
            **kwargs: 其他影响检索结果的参数
        """
        if not config.enable_cache or not self.cache_enabled or not results:
            return
        
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(query, config, **kwargs)
            
            # 序列化结果数据
            serialized_data = self._serialize_results(results)
            
            # 写入Redis缓存
            await self.redis_client.setex(cache_key, self.cache_ttl, serialized_data)
            
            logger.info(f"缓存写入成功: {cache_key[:32]}... (共{len(results)}个结果)")
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"缓存写入失败: {e}")
    
    def _generate_cache_key(self, query: str, config: RetrievalConfig, **kwargs) -> str:
        """
        生成缓存键
        
        缓存键包含所有影响检索结果的参数，确保相同参数的查询能够命中缓存
        
        Args:
            query: 查询字符串
            config: 检索配置
            **kwargs: 其他参数
            
        Returns:
            生成的缓存键
        """
        # 收集影响检索结果的关键参数
        key_components = [
            f"query:{query}",
            f"search_mode:{config.search_mode}",
            f"top_k:{config.top_k}",
            f"similarity_threshold:{config.similarity_threshold}",
            f"enable_rerank:{config.enable_rerank}"
        ]
        
        # 添加其他可能影响结果的参数
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_components.append(f"{key}:{value}")
        
        # 生成MD5哈希作为缓存键
        key_string = "|".join(key_components)
        cache_key = f"retrieval:{hashlib.md5(key_string.encode('utf-8')).hexdigest()}"
        
        logger.debug(f"生成缓存键: {cache_key} <- {key_string}")
        return cache_key
    
    def _serialize_results(self, results: List[SearchResult]) -> str:
        """
        序列化检索结果
        
        Args:
            results: 检索结果列表
            
        Returns:
            序列化后的JSON字符串
        """
        try:
            # 将SearchResult对象转换为字典
            result_dicts = []
            for result in results:
                if hasattr(result, 'model_dump'):
                    # Pydantic v2
                    result_dicts.append(result.model_dump())
                elif hasattr(result, 'dict'):
                    # Pydantic v1
                    result_dicts.append(result.dict())
                elif hasattr(result, 'to_dict'):
                    result_dicts.append(result.to_dict())
                elif hasattr(result, '__dict__'):
                    # 如果没有to_dict方法，使用__dict__
                    result_dict = {
                        key: value for key, value in result.__dict__.items()
                        if not key.startswith('_')
                    }
                    result_dicts.append(result_dict)
                else:
                    # 如果是dataclass，使用asdict
                    result_dicts.append(asdict(result))
            
            # 添加缓存元数据
            cache_data = {
                'results': result_dicts,
                'cached_at': datetime.now().isoformat(),
                'count': len(results)
            }
            
            return json.dumps(cache_data, ensure_ascii=False, default=str)
            
        except Exception as e:
            logger.error(f"结果序列化失败: {e}")
            raise
    
    def _deserialize_results(self, data: str) -> List[SearchResult]:
        """
        反序列化检索结果
        
        Args:
            data: 序列化的JSON字符串
            
        Returns:
            反序列化后的检索结果列表
        """
        try:
            cache_data = json.loads(data)
            result_dicts = cache_data.get('results', [])
            
            # 将字典转换回SearchResult对象
            results = []
            for result_dict in result_dicts:
                try:
                    # 尝试使用Pydantic模型创建
                    if hasattr(SearchResult, 'model_validate'):
                        # Pydantic v2
                        result = SearchResult.model_validate(result_dict)
                    elif hasattr(SearchResult, 'parse_obj'):
                        # Pydantic v1
                        result = SearchResult.parse_obj(result_dict)
                    elif hasattr(SearchResult, 'from_dict'):
                        result = SearchResult.from_dict(result_dict)
                    else:
                        # 直接创建对象
                        result = SearchResult(**result_dict)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"反序列化单个结果失败: {e}, 跳过该结果")
                    continue
            
            logger.debug(f"反序列化成功，恢复{len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"结果反序列化失败: {e}")
            raise
    
    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        清理缓存
        
        Args:
            pattern: 缓存键模式，如果为None则清理所有检索缓存
            
        Returns:
            清理的缓存条目数量
        """
        if not self.cache_enabled:
            return 0
        
        try:
            if pattern is None:
                pattern = "retrieval:*"
            
            # 获取匹配的键
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                # 删除匹配的键
                deleted_count = await self.redis_client.delete(*keys)
                logger.info(f"清理缓存完成，删除{deleted_count}个条目")
                return deleted_count
            else:
                logger.info("没有找到匹配的缓存条目")
                return 0
                
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
            return 0
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息和统计
        
        Returns:
            缓存信息字典
        """
        info = {
            'enabled': self.cache_enabled,
            'ttl': self.cache_ttl,
            'stats': self.cache_stats.copy()
        }
        
        # 计算命中率
        total_requests = self.cache_stats['total_requests']
        if total_requests > 0:
            info['hit_rate'] = self.cache_stats['hits'] / total_requests
            info['miss_rate'] = self.cache_stats['misses'] / total_requests
            info['error_rate'] = self.cache_stats['errors'] / total_requests
        else:
            info['hit_rate'] = 0.0
            info['miss_rate'] = 0.0
            info['error_rate'] = 0.0
        
        # 如果Redis可用，获取Redis信息
        if self.cache_enabled:
            try:
                redis_info = await self.redis_client.info('memory')
                info['redis_memory'] = {
                    'used_memory': redis_info.get('used_memory', 0),
                    'used_memory_human': redis_info.get('used_memory_human', '0B'),
                    'maxmemory': redis_info.get('maxmemory', 0)
                }
                
                # 获取检索缓存的键数量
                retrieval_keys = await self.redis_client.keys("retrieval:*")
                info['cached_queries'] = len(retrieval_keys)
                
            except Exception as e:
                logger.warning(f"获取Redis信息失败: {e}")
                info['redis_error'] = str(e)
        
        return info
    
    async def warm_up_cache(self, common_queries: List[Dict[str, Any]]) -> int:
        """
        缓存预热 - 预先缓存常见查询
        
        Args:
            common_queries: 常见查询列表，每个元素包含query和config
            
        Returns:
            预热成功的查询数量
        """
        if not self.cache_enabled:
            return 0
        
        warmed_count = 0
        
        for query_info in common_queries:
            try:
                query = query_info.get('query')
                config_dict = query_info.get('config', {})
                
                if not query:
                    continue
                
                # 创建配置对象
                config = RetrievalConfig(**config_dict)
                
                # 检查是否已经缓存
                cache_key = self._generate_cache_key(query, config)
                exists = await self.redis_client.exists(cache_key)
                
                if not exists:
                    # 这里应该调用实际的检索服务来获取结果
                    # 由于这是缓存服务，我们只是标记需要预热
                    logger.info(f"标记预热查询: {query}")
                    warmed_count += 1
                
            except Exception as e:
                logger.error(f"预热查询失败: {e}")
        
        logger.info(f"缓存预热完成，标记{warmed_count}个查询需要预热")
        return warmed_count
    
    async def close(self) -> None:
        """关闭缓存服务，清理资源"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("缓存服务已关闭")
            except Exception as e:
                logger.error(f"关闭缓存服务失败: {e}")
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }
        logger.info("缓存统计信息已重置")


class CacheKeyGenerator:
    """缓存键生成器 - 提供更灵活的缓存键生成策略"""
    
    @staticmethod
    def generate_retrieval_key(query: str, config: RetrievalConfig, **kwargs) -> str:
        """生成检索缓存键"""
        return CacheService._generate_cache_key(None, query, config, **kwargs)
    
    @staticmethod
    def generate_user_key(user_id: str, query: str, config: RetrievalConfig) -> str:
        """生成用户特定的缓存键"""
        key_components = [
            f"user:{user_id}",
            f"query:{query}",
            f"search_mode:{config.search_mode}",
            f"top_k:{config.top_k}",
            f"similarity_threshold:{config.similarity_threshold}",
            f"enable_rerank:{config.enable_rerank}"
        ]
        
        key_string = "|".join(key_components)
        return f"user_retrieval:{hashlib.md5(key_string.encode('utf-8')).hexdigest()}"
    
    @staticmethod
    def generate_department_key(dept_id: str, query: str, config: RetrievalConfig) -> str:
        """生成部门特定的缓存键"""
        key_components = [
            f"dept:{dept_id}",
            f"query:{query}",
            f"search_mode:{config.search_mode}",
            f"top_k:{config.top_k}",
            f"similarity_threshold:{config.similarity_threshold}",
            f"enable_rerank:{config.enable_rerank}"
        ]
        
        key_string = "|".join(key_components)
        return f"dept_retrieval:{hashlib.md5(key_string.encode('utf-8')).hexdigest()}"


# 缓存装饰器
def cache_retrieval_results(cache_service: CacheService):
    """
    检索结果缓存装饰器
    
    Args:
        cache_service: 缓存服务实例
    """
    def decorator(func):
        async def wrapper(self, query: str, config: RetrievalConfig, **kwargs):
            # 尝试从缓存获取结果
            cached_results = await cache_service.get_cached_results(query, config, **kwargs)
            if cached_results is not None:
                return cached_results
            
            # 执行实际的检索
            results = await func(self, query, config, **kwargs)
            
            # 缓存结果
            await cache_service.cache_results(query, config, results, **kwargs)
            
            return results
        
        return wrapper
    return decorator