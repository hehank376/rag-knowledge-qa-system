"""
增强的检索服务 - 集成搜索模式路由器
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.vector import SearchResult
from ..models.config import RetrievalConfig
from .retrieval_service import RetrievalService
from .search_mode_router import SearchModeRouter
from .cache_service import CacheService
from .reranking_service import RerankingService
from .model_manager import ModelManager, get_model_manager
from ..utils.exceptions import ProcessingError
from .base import BaseService

logger = logging.getLogger(__name__)


class EnhancedRetrievalService(BaseService):
    """增强的检索服务 - 集成搜索模式路由器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # 初始化基础检索服务
        self.base_retrieval_service = RetrievalService(config)
        
        # 初始化搜索模式路由器
        self.search_router = SearchModeRouter(self.base_retrieval_service)
        
        # 初始化缓存服务
        self.cache_service = CacheService(config)
        
        # 获取模型管理器（如果可用）
        self.model_manager = get_model_manager()
        
        # 初始化重排序服务（如果没有模型管理器）
        if not self.model_manager:
            # 创建专门的重排序配置
            reranking_config = self._create_reranking_config(config)
            self.reranking_service = RerankingService(reranking_config)
        else:
            self.reranking_service = None  # 将通过模型管理器获取
        
        # 默认检索配置
        self.default_config = RetrievalConfig(
            top_k=self.config.get('default_top_k', 5),
            similarity_threshold=self.config.get('similarity_threshold', 0.7),
            search_mode=self.config.get('search_mode', 'semantic'),
            enable_rerank=self.config.get('enable_rerank', False),
            enable_cache=self.config.get('enable_cache', False)
        )
        
        # 缓存统计信息
        self.cache_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_errors': 0,
            'total_search_time': 0.0,
            'cache_hit_time': 0.0,
            'cache_miss_time': 0.0
        }
        
        # 重排序统计信息
        self.rerank_stats = {
            'total_rerank_requests': 0,
            'successful_reranks': 0,
            'failed_reranks': 0,
            'total_rerank_time': 0.0,
            'avg_rerank_time': 0.0
        }
        
        logger.info("增强检索服务初始化完成")
    
    def _create_reranking_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """创建重排序配置"""
        # 从配置加载器获取重排序配置
        from ..config.loader import ConfigLoader
        
        try:
            config_loader = ConfigLoader()
            app_config = config_loader.load_config()
            
            # 使用配置文件中的重排序配置
            reranking_config = {
                'provider': app_config.reranking.provider,
                'model': app_config.reranking.model,
                'model_name': app_config.reranking.model_name,
                'api_key': app_config.reranking.api_key,
                'base_url': app_config.reranking.base_url,
                'batch_size': app_config.reranking.batch_size,
                'max_length': app_config.reranking.max_length,
                'timeout': app_config.reranking.timeout
            }
            
            logger.debug(f"创建重排序配置: provider={reranking_config['provider']}, model={reranking_config['model']}")
            return reranking_config
            
        except Exception as e:
            logger.warning(f"无法加载重排序配置，使用默认配置: {str(e)}")
            # 降级到默认配置
            return {
                'provider': 'local',
                'model': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                'batch_size': 32,
                'max_length': 512,
                'timeout': 30.0
            }
    
    def _get_reranking_service(self) -> Optional[RerankingService]:
        """获取重排序服务（优先使用模型管理器）"""
        if self.model_manager:
            return self.model_manager.get_active_reranking_service()
        return self.reranking_service
    
    async def initialize(self) -> None:
        """初始化增强检索服务"""
        try:
            logger.info("初始化增强检索服务...")
            
            # 初始化基础检索服务
            await self.base_retrieval_service.initialize()
            
            # 初始化搜索路由器
            await self.search_router.initialize()
            
            # 初始化缓存服务
            await self.cache_service.initialize()
            
            # 初始化重排序服务（如果没有模型管理器）
            if self.reranking_service:
                await self.reranking_service.initialize()
            
            logger.info("增强检索服务初始化完成")
            
        except Exception as e:
            logger.error(f"增强检索服务初始化失败: {str(e)}")
            raise ProcessingError(f"增强检索服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("清理增强检索服务资源...")
            
            # 清理缓存服务
            if self.cache_service:
                await self.cache_service.close()
            
            # 清理重排序服务（如果没有使用模型管理器）
            if self.reranking_service:
                await self.reranking_service.close()
            
            # 清理搜索路由器
            if self.search_router:
                await self.search_router.cleanup()
            
            # 清理基础检索服务
            if self.base_retrieval_service:
                await self.base_retrieval_service.cleanup()
            
            logger.info("增强检索服务资源清理完成")
            
        except Exception as e:
            logger.error(f"增强检索服务清理失败: {str(e)}")
    
    async def search_with_config(
        self, 
        query: str, 
        config: Optional[RetrievalConfig] = None,
        **kwargs
    ) -> List[SearchResult]:
        """使用配置进行检索的主要方法（集成缓存功能）
        
        Args:
            query: 查询文本
            config: 检索配置，如果为None则使用默认配置
            **kwargs: 其他搜索参数
            
        Returns:
            搜索结果列表
        """
        start_time = datetime.now()
        
        try:
            # 使用提供的配置或默认配置
            effective_config = config or self.default_config
            
            # 更新统计信息
            self.cache_stats['total_requests'] += 1
            
            logger.info(f"开始配置化检索: query='{query[:50]}...', mode={effective_config.search_mode}, cache={effective_config.enable_cache}")
            
            # 验证查询
            if not query or not query.strip():
                raise ProcessingError("查询内容不能为空")
            
            query = query.strip()
            
            # 1. 尝试从缓存获取结果
            cached_results = await self.cache_service.get_cached_results(
                query=query,
                config=effective_config,
                **kwargs
            )
            
            if cached_results is not None:
                # 缓存命中
                cache_hit_time = (datetime.now() - start_time).total_seconds()
                self.cache_stats['cache_hits'] += 1
                self.cache_stats['cache_hit_time'] += cache_hit_time
                
                logger.info(f"缓存命中: 找到 {len(cached_results)} 个结果, 耗时 {cache_hit_time:.3f}s")
                return cached_results
            
            # 2. 缓存未命中，执行实际检索
            self.cache_stats['cache_misses'] += 1
            
            # 使用搜索路由器执行检索
            results = await self.search_router.search_with_mode(
                query=query,
                config=effective_config,
                **kwargs
            )
            
            # 2.5. 应用重排序（如果启用）
            if effective_config.enable_rerank and results:
                rerank_start_time = datetime.now()
                
                try:
                    self.rerank_stats['total_rerank_requests'] += 1
                    
                    # 获取重排序服务
                    reranking_service = self._get_reranking_service()
                    if not reranking_service:
                        logger.warning("重排序服务不可用，跳过重排序")
                        return results
                    
                    # 执行重排序
                    results = await reranking_service.rerank_results(
                        query=query,
                        results=results,
                        config=effective_config
                    )
                    
                    # 更新重排序统计
                    rerank_time = (datetime.now() - rerank_start_time).total_seconds()
                    self.rerank_stats['successful_reranks'] += 1
                    self.rerank_stats['total_rerank_time'] += rerank_time
                    self.rerank_stats['avg_rerank_time'] = (
                        self.rerank_stats['total_rerank_time'] / self.rerank_stats['successful_reranks']
                    )
                    
                    logger.info(f"重排序完成: 处理{len(results)}个结果, 耗时{rerank_time:.3f}s")
                    
                except Exception as rerank_error:
                    # 重排序失败时记录错误但不影响检索结果
                    rerank_time = (datetime.now() - rerank_start_time).total_seconds()
                    self.rerank_stats['failed_reranks'] += 1
                    self.rerank_stats['total_rerank_time'] += rerank_time
                    
                    logger.warning(f"重排序失败，使用原始结果: {rerank_error}")
            
            # 3. 缓存检索结果
            try:
                await self.cache_service.cache_results(
                    query=query,
                    config=effective_config,
                    results=results,
                    **kwargs
                )
            except Exception as cache_error:
                # 缓存写入失败不应该影响检索结果
                self.cache_stats['cache_errors'] += 1
                logger.warning(f"缓存写入失败: {cache_error}")
            
            # 更新统计信息
            cache_miss_time = (datetime.now() - start_time).total_seconds()
            self.cache_stats['cache_miss_time'] += cache_miss_time
            self.cache_stats['total_search_time'] += cache_miss_time
            
            logger.info(f"配置化检索完成: 找到 {len(results)} 个结果, 耗时 {cache_miss_time:.3f}s")
            return results
            
        except Exception as e:
            # 更新错误统计
            self.cache_stats['cache_errors'] += 1
            
            logger.error(f"配置化检索失败: {str(e)}")
            raise ProcessingError(f"配置化检索失败: {str(e)}")
    
    async def search_similar_documents(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        document_ids: Optional[List[str]] = None,
        config: Optional[RetrievalConfig] = None
    ) -> List[SearchResult]:
        """搜索相似文档（兼容性方法）
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
            document_ids: 限制搜索的文档ID列表
            config: 检索配置
            
        Returns:
            搜索结果列表
        """
        try:
            # 构建有效配置
            if config is None:
                config = RetrievalConfig(
                    top_k=top_k or self.default_config.top_k,
                    similarity_threshold=similarity_threshold or self.default_config.similarity_threshold,
                    search_mode=self.default_config.search_mode,
                    enable_rerank=self.default_config.enable_rerank,
                    enable_cache=self.default_config.enable_cache
                )
            else:
                # 更新配置中的参数
                if top_k is not None:
                    config.top_k = top_k
                if similarity_threshold is not None:
                    config.similarity_threshold = similarity_threshold
            
            # 使用配置化检索
            return await self.search_with_config(
                query=query,
                config=config,
                document_ids=document_ids
            )
            
        except Exception as e:
            logger.error(f"相似文档搜索失败: {str(e)}")
            raise ProcessingError(f"相似文档搜索失败: {str(e)}")
    
    async def update_default_config(self, config: RetrievalConfig) -> None:
        """更新默认检索配置
        
        Args:
            config: 新的默认配置
        """
        try:
            logger.info(f"更新默认检索配置: {config}")
            
            # 验证配置
            errors = config.validate()
            if errors:
                raise ProcessingError(f"配置验证失败: {', '.join(errors)}")
            
            # 更新默认配置
            self.default_config = config
            
            logger.info("默认检索配置更新成功")
            
        except Exception as e:
            logger.error(f"更新默认配置失败: {str(e)}")
            raise ProcessingError(f"更新默认配置失败: {str(e)}")
    
    def get_default_config(self) -> RetrievalConfig:
        """获取当前默认配置
        
        Returns:
            当前默认配置
        """
        return self.default_config
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息（包含缓存统计）
        
        Returns:
            搜索统计信息
        """
        try:
            # 获取搜索路由器的统计信息
            router_stats = self.search_router.get_usage_statistics()
            
            # 计算缓存统计
            total_requests = self.cache_stats['total_requests']
            cache_hit_rate = 0.0
            cache_miss_rate = 0.0
            avg_cache_hit_time = 0.0
            avg_cache_miss_time = 0.0
            
            if total_requests > 0:
                cache_hit_rate = self.cache_stats['cache_hits'] / total_requests
                cache_miss_rate = self.cache_stats['cache_misses'] / total_requests
            
            if self.cache_stats['cache_hits'] > 0:
                avg_cache_hit_time = self.cache_stats['cache_hit_time'] / self.cache_stats['cache_hits']
            
            if self.cache_stats['cache_misses'] > 0:
                avg_cache_miss_time = self.cache_stats['cache_miss_time'] / self.cache_stats['cache_misses']
            
            # 获取重排序服务统计
            reranking_service = self._get_reranking_service()
            reranking_metrics = reranking_service.get_metrics() if reranking_service else {}
            
            # 计算重排序统计
            rerank_success_rate = 0.0
            rerank_failure_rate = 0.0
            
            if self.rerank_stats['total_rerank_requests'] > 0:
                rerank_success_rate = self.rerank_stats['successful_reranks'] / self.rerank_stats['total_rerank_requests']
                rerank_failure_rate = self.rerank_stats['failed_reranks'] / self.rerank_stats['total_rerank_requests']
            
            # 添加服务级别的统计信息
            service_stats = {
                'service_name': 'EnhancedRetrievalService',
                'default_config': self.default_config.to_dict(),
                'router_statistics': router_stats,
                'cache_statistics': {
                    'total_requests': total_requests,
                    'cache_hits': self.cache_stats['cache_hits'],
                    'cache_misses': self.cache_stats['cache_misses'],
                    'cache_errors': self.cache_stats['cache_errors'],
                    'cache_hit_rate': cache_hit_rate,
                    'cache_miss_rate': cache_miss_rate,
                    'avg_cache_hit_time': avg_cache_hit_time,
                    'avg_cache_miss_time': avg_cache_miss_time,
                    'total_search_time': self.cache_stats['total_search_time']
                },
                'reranking_statistics': {
                    'total_rerank_requests': self.rerank_stats['total_rerank_requests'],
                    'successful_reranks': self.rerank_stats['successful_reranks'],
                    'failed_reranks': self.rerank_stats['failed_reranks'],
                    'rerank_success_rate': rerank_success_rate,
                    'rerank_failure_rate': rerank_failure_rate,
                    'avg_rerank_time': self.rerank_stats['avg_rerank_time'],
                    'total_rerank_time': self.rerank_stats['total_rerank_time'],
                    'reranking_service_metrics': reranking_metrics
                }
            }
            
            return service_stats
            
        except Exception as e:
            logger.error(f"获取搜索统计失败: {str(e)}")
            return {'error': str(e)}
    
    def reset_statistics(self) -> None:
        """重置搜索统计信息（包含缓存统计）"""
        try:
            # 重置搜索路由器统计
            self.search_router.reset_statistics()
            
            # 重置缓存统计
            self.cache_stats = {
                'total_requests': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'cache_errors': 0,
                'total_search_time': 0.0,
                'cache_hit_time': 0.0,
                'cache_miss_time': 0.0
            }
            
            # 重置重排序统计
            self.rerank_stats = {
                'total_rerank_requests': 0,
                'successful_reranks': 0,
                'failed_reranks': 0,
                'total_rerank_time': 0.0,
                'avg_rerank_time': 0.0
            }
            
            # 重置缓存服务统计
            self.cache_service.reset_stats()
            
            # 重置重排序服务统计
            reranking_service = self._get_reranking_service()
            if reranking_service:
                reranking_service.reset_metrics()
            
            logger.info("搜索统计信息已重置")
        except Exception as e:
            logger.error(f"重置统计信息失败: {str(e)}")
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息
        
        Returns:
            缓存信息和统计
        """
        try:
            return await self.cache_service.get_cache_info()
        except Exception as e:
            logger.error(f"获取缓存信息失败: {str(e)}")
            return {'error': str(e)}
    
    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """清理缓存
        
        Args:
            pattern: 缓存键模式，如果为None则清理所有检索缓存
            
        Returns:
            清理的缓存条目数量
        """
        try:
            deleted_count = await self.cache_service.clear_cache(pattern)
            logger.info(f"缓存清理完成，删除{deleted_count}个条目")
            return deleted_count
        except Exception as e:
            logger.error(f"缓存清理失败: {str(e)}")
            return 0
    
    async def get_reranking_metrics(self) -> Dict[str, Any]:
        """获取重排序指标
        
        Returns:
            重排序指标信息
        """
        try:
            reranking_service = self._get_reranking_service()
            return reranking_service.get_metrics() if reranking_service else {'error': 'Reranking service not available'}
        except Exception as e:
            logger.error(f"获取重排序指标失败: {str(e)}")
            return {'error': str(e)}
    
    async def preload_reranking_model(self) -> bool:
        """预加载重排序模型
        
        Returns:
            是否成功预加载
        """
        try:
            reranking_service = self._get_reranking_service()
            return await reranking_service.preload_model() if reranking_service else False
        except Exception as e:
            logger.error(f"预加载重排序模型失败: {str(e)}")
            return False
    
    async def warm_up_cache(self, common_queries: List[Dict[str, Any]]) -> int:
        """缓存预热
        
        Args:
            common_queries: 常见查询列表
            
        Returns:
            预热成功的查询数量
        """
        try:
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
                    cache_key = self.cache_service._generate_cache_key(query, config)
                    
                    # 如果缓存不存在，执行检索并缓存
                    cached_results = await self.cache_service.get_cached_results(query, config)
                    if cached_results is None:
                        # 执行检索
                        results = await self.search_with_config(query, config)
                        warmed_count += 1
                        logger.info(f"预热查询成功: {query}")
                    
                except Exception as e:
                    logger.warning(f"预热查询失败: {e}")
                    continue
            
            logger.info(f"缓存预热完成，成功预热{warmed_count}个查询")
            return warmed_count
            
        except Exception as e:
            logger.error(f"缓存预热失败: {str(e)}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查（包含缓存状态）
        
        Returns:
            健康状态信息
        """
        try:
            # 检查基础检索服务
            base_service_health = True
            if not self.base_retrieval_service:
                base_service_health = False
            
            # 检查搜索路由器
            router_health = await self.search_router.health_check()
            
            # 检查缓存服务
            cache_info = await self.cache_service.get_cache_info()
            cache_health = cache_info.get('enabled', False)
            
            # 检查重排序服务
            reranking_service = self._get_reranking_service()
            reranking_health = await reranking_service.health_check() if reranking_service else {'status': 'unavailable'}
            
            # 综合健康状态
            overall_health = (
                base_service_health and 
                router_health.get('status') == 'healthy'
                # 缓存和重排序服务不是必需的，所以不影响整体健康状态
            )
            
            return {
                'status': 'healthy' if overall_health else 'unhealthy',
                'components': {
                    'base_retrieval_service': 'healthy' if base_service_health else 'unhealthy',
                    'search_router': router_health,
                    'cache_service': {
                        'status': 'healthy' if cache_health else 'disabled',
                        'enabled': cache_health,
                        'info': cache_info
                    },
                    'reranking_service': reranking_health
                },
                'default_config': self.default_config.to_dict(),
                'cache_statistics': self.cache_stats,
                'reranking_statistics': self.rerank_stats
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    # 代理方法：将其他检索方法代理到基础检索服务
    async def search_by_keywords(self, keywords: List[str], top_k: Optional[int] = None, **kwargs) -> List[SearchResult]:
        """关键词搜索（代理方法）"""
        return await self.base_retrieval_service.search_by_keywords(keywords, top_k, **kwargs)
    
    async def hybrid_search(self, query: str, top_k: Optional[int] = None, **kwargs) -> List[SearchResult]:
        """混合搜索（代理方法）"""
        return await self.base_retrieval_service.hybrid_search(query, top_k, **kwargs)
    
    async def search_by_document(self, document_id: str, top_k: Optional[int] = None, **kwargs) -> List[SearchResult]:
        """基于文档搜索（代理方法）"""
        return await self.base_retrieval_service.search_by_document(document_id, top_k, **kwargs)
    
    async def get_relevant_chunks(self, query: str, top_k: Optional[int] = None, **kwargs) -> List[SearchResult]:
        """获取相关文本块（代理方法）"""
        return await self.base_retrieval_service.get_relevant_chunks(query, top_k, **kwargs)
    
    async def get_document_statistics(self, document_id: str) -> Dict[str, Any]:
        """获取文档统计（代理方法）"""
        return await self.base_retrieval_service.get_document_statistics(document_id)
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            # 获取基础服务统计
            base_stats = await self.base_retrieval_service.get_service_stats()
            
            # 获取增强服务统计
            enhanced_stats = self.get_search_statistics()
            
            # 合并统计信息
            combined_stats = {
                'service_name': 'EnhancedRetrievalService',
                'base_service_stats': base_stats,
                'enhanced_service_stats': enhanced_stats
            }
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"获取服务统计失败: {str(e)}")
            return {'error': str(e)}
    
    async def test_search(self, test_query: str = "测试查询") -> Dict[str, Any]:
        """测试搜索功能（包含缓存和重排序测试）"""
        try:
            # 测试不同配置的搜索
            test_configs = [
                RetrievalConfig(
                    search_mode=self.default_config.search_mode,
                    enable_cache=self.default_config.enable_cache,
                    enable_rerank=False,  # 不启用重排序
                    top_k=5
                ),
                RetrievalConfig(
                    search_mode=self.default_config.search_mode,
                    enable_cache=self.default_config.enable_cache,
                    enable_rerank=True,   # 启用重排序
                    top_k=5
                )
            ]
            
            test_results = {}
            
            for i, config in enumerate(test_configs):
                config_name = f"config_{i+1}_rerank_{'on' if config.enable_rerank else 'off'}"
                
                # 第一次搜索（缓存未命中）
                start_time = datetime.now()
                results1 = await self.search_with_config(
                    query=test_query,
                    config=config
                )
                first_search_time = (datetime.now() - start_time).total_seconds()
                
                # 第二次搜索（可能缓存命中）
                start_time = datetime.now()
                results2 = await self.search_with_config(
                    query=test_query,
                    config=config
                )
                second_search_time = (datetime.now() - start_time).total_seconds()
                
                # 检查缓存效果
                cache_hit = second_search_time < first_search_time * 0.5
                
                test_results[config_name] = {
                    'result_count': len(results1),
                    'first_search_time': first_search_time,
                    'second_search_time': second_search_time,
                    'cache_hit_likely': cache_hit,
                    'rerank_enabled': config.enable_rerank,
                    'top_similarity': results1[0].similarity_score if results1 else 0.0,
                    'has_rerank_metadata': (
                        'rerank_score' in results1[0].metadata if results1 else False
                    )
                }
            
            # 获取服务统计
            service_stats = await self.get_service_stats()
            cache_info = await self.get_cache_info()
            reranking_metrics = await self.get_reranking_metrics()
            
            return {
                'success': True,
                'test_query': test_query,
                'test_results': test_results,
                'search_mode': self.default_config.search_mode,
                'cache_enabled': self.default_config.enable_cache,
                'rerank_enabled': self.default_config.enable_rerank,
                'service_stats': service_stats,
                'cache_info': cache_info,
                'reranking_metrics': reranking_metrics
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'test_query': test_query
            }