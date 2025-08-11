"""
搜索模式路由器 - 根据配置选择搜索方法
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

from ..models.vector import SearchResult
from ..models.config import RetrievalConfig
from ..utils.exceptions import ProcessingError
from .base import BaseService

logger = logging.getLogger(__name__)


class SearchModeRouter(BaseService):
    """搜索模式路由器 - 根据配置选择搜索方法"""
    
    def __init__(self, retrieval_service):
        super().__init__()
        self.retrieval_service = retrieval_service
        
        # 搜索模式使用统计
        self.mode_usage_stats = Counter()
        self.mode_performance_stats = {}
        self.mode_error_stats = Counter()
        
        # 支持的搜索模式
        self.supported_modes = ['semantic', 'keyword', 'hybrid']
        
        logger.info("搜索模式路由器初始化完成")
    
    async def initialize(self) -> None:
        """初始化搜索模式路由器"""
        try:
            logger.info("搜索模式路由器初始化中...")
            # 这里可以添加初始化逻辑，比如预热模型等
            logger.info("搜索模式路由器初始化完成")
        except Exception as e:
            logger.error(f"搜索模式路由器初始化失败: {str(e)}")
            raise
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("搜索模式路由器清理资源...")
            # 这里可以添加清理逻辑
            logger.info("搜索模式路由器资源清理完成")
        except Exception as e:
            logger.error(f"搜索模式路由器清理失败: {str(e)}")
    
    async def search_with_mode(
        self, 
        query: str, 
        config: RetrievalConfig,
        **kwargs
    ) -> List[SearchResult]:
        """根据搜索模式执行相应的搜索方法
        
        Args:
            query: 查询文本
            config: 检索配置
            **kwargs: 其他搜索参数
            
        Returns:
            搜索结果列表
        """
        start_time = datetime.now()
        search_mode = config.search_mode
        
        try:
            logger.info(f"开始执行搜索，模式: {search_mode}, 查询: '{query[:50]}...'")
            
            # 验证搜索模式
            if search_mode not in self.supported_modes:
                logger.warning(f"不支持的搜索模式: {search_mode}，降级到语义搜索")
                search_mode = 'semantic'
                self.mode_error_stats[f"unsupported_mode:{config.search_mode}"] += 1
            
            # 记录模式使用统计
            self.mode_usage_stats[search_mode] += 1
            
            # 根据模式选择搜索方法
            if search_mode == 'semantic':
                results = await self._semantic_search(query, config, **kwargs)
            elif search_mode == 'keyword':
                results = await self._keyword_search(query, config, **kwargs)
            elif search_mode == 'hybrid':
                results = await self._hybrid_search(query, config, **kwargs)
            else:
                # 这种情况理论上不会发生，但作为最后的保险
                logger.error(f"未知搜索模式: {search_mode}，降级到语义搜索")
                results = await self._semantic_search(query, config, **kwargs)
                self.mode_error_stats[f"unknown_mode:{search_mode}"] += 1
            
            # 记录性能统计
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            self._record_performance(search_mode, processing_time, len(results))
            
            logger.info(f"搜索完成，模式: {search_mode}, 结果数: {len(results)}, 耗时: {processing_time:.3f}s")
            return results
            
        except Exception as e:
            # 记录错误统计
            self.mode_error_stats[f"error:{search_mode}"] += 1
            
            # 如果当前模式失败，尝试降级到语义搜索
            if search_mode != 'semantic':
                logger.error(f"搜索模式 {search_mode} 失败: {str(e)}，尝试降级到语义搜索")
                try:
                    results = await self._semantic_search(query, config, **kwargs)
                    
                    # 记录降级成功
                    end_time = datetime.now()
                    processing_time = (end_time - start_time).total_seconds()
                    self._record_performance('semantic_fallback', processing_time, len(results))
                    
                    logger.info(f"降级搜索成功，结果数: {len(results)}, 耗时: {processing_time:.3f}s")
                    return results
                    
                except Exception as fallback_error:
                    logger.error(f"降级搜索也失败: {str(fallback_error)}")
                    self.mode_error_stats["fallback_failed"] += 1
                    raise ProcessingError(f"搜索失败，原始错误: {str(e)}, 降级错误: {str(fallback_error)}")
            else:
                logger.error(f"语义搜索失败: {str(e)}")
                raise ProcessingError(f"搜索失败: {str(e)}")
    
    async def _semantic_search(self, query: str, config: RetrievalConfig, **kwargs) -> List[SearchResult]:
        """语义搜索实现"""
        try:
            logger.debug(f"执行语义搜索: {query[:50]}...")
            
            # 调用检索服务的语义搜索方法
            results = await self.retrieval_service.search_similar_documents(
                query=query,
                top_k=config.top_k,
                similarity_threshold=config.similarity_threshold,
                **kwargs
            )
            
            logger.debug(f"语义搜索完成，结果数: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            raise ProcessingError(f"语义搜索失败: {str(e)}")
    
    async def _keyword_search(self, query: str, config: RetrievalConfig, **kwargs) -> List[SearchResult]:
        """关键词搜索实现"""
        try:
            logger.debug(f"执行关键词搜索: {query[:50]}...")
            
            # 提取关键词
            keywords = self._extract_keywords(query)
            if not keywords:
                logger.warning("未能提取到关键词，降级到语义搜索")
                return await self._semantic_search(query, config, **kwargs)
            
            # 调用检索服务的关键词搜索方法
            results = await self.retrieval_service.search_by_keywords(
                keywords=keywords,
                top_k=config.top_k,
                **kwargs
            )
            
            # 根据相似度阈值过滤结果
            filtered_results = [
                result for result in results 
                if result.similarity_score >= config.similarity_threshold
            ]
            
            logger.debug(f"关键词搜索完成，原始结果: {len(results)}, 过滤后: {len(filtered_results)}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            raise ProcessingError(f"关键词搜索失败: {str(e)}")
    
    async def _hybrid_search(self, query: str, config: RetrievalConfig, **kwargs) -> List[SearchResult]:
        """混合搜索实现"""
        try:
            logger.debug(f"执行混合搜索: {query[:50]}...")
            
            # 调用检索服务的混合搜索方法
            results = await self.retrieval_service.hybrid_search(
                query=query,
                top_k=config.top_k,
                semantic_weight=0.7,  # 可以后续配置化
                keyword_weight=0.3,
                **kwargs
            )
            
            # 根据相似度阈值过滤结果
            filtered_results = [
                result for result in results 
                if result.similarity_score >= config.similarity_threshold
            ]
            
            logger.debug(f"混合搜索完成，原始结果: {len(results)}, 过滤后: {len(filtered_results)}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            raise ProcessingError(f"混合搜索失败: {str(e)}")
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """从文本中提取关键词
        
        Args:
            text: 输入文本
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        try:
            import re
            
            # 简单的关键词提取：按空格和标点符号分割
            # 移除标点符号，保留中英文字符和数字
            cleaned_text = re.sub(r'[^\w\s]', ' ', text)
            
            # 按空格分割
            words = cleaned_text.split()
            
            # 对于中文文本，如果没有空格分割，尝试提取有意义的词
            if len(words) == 1 and any('\u4e00' <= char <= '\u9fff' for char in text):
                # 简单的中文词提取：查找常见的词汇模式
                chinese_words = []
                # 提取2-4字的中文词组
                for i in range(len(cleaned_text)):
                    for length in [4, 3, 2]:  # 优先提取长词
                        if i + length <= len(cleaned_text):
                            word = cleaned_text[i:i+length].strip()
                            if word and all('\u4e00' <= char <= '\u9fff' for char in word):
                                chinese_words.append(word)
                
                # 去重并选择最有意义的词
                words = list(dict.fromkeys(chinese_words))
            
            # 简单的停用词列表
            stop_words = {
                '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', 
                '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', 
                '自己', '这', '那', '什么', '怎么', '为什么', '如何', '哪里', '什么时候',
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'this', 'is', 'that', 'it', 'he', 'she', 'they', 'we', 'you', 'i'
            }
            
            # 过滤停用词和短词
            keywords = []
            for word in words:
                word = word.strip().lower()
                if len(word) > 1 and word not in stop_words:
                    keywords.append(word)
            
            # 去重并限制数量
            keywords = list(dict.fromkeys(keywords))[:max_keywords]
            
            logger.debug(f"提取关键词: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            return []
    
    def _record_performance(self, mode: str, processing_time: float, result_count: int):
        """记录性能统计
        
        Args:
            mode: 搜索模式
            processing_time: 处理时间（秒）
            result_count: 结果数量
        """
        if mode not in self.mode_performance_stats:
            self.mode_performance_stats[mode] = {
                'total_requests': 0,
                'total_time': 0.0,
                'total_results': 0,
                'avg_time': 0.0,
                'avg_results': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        stats = self.mode_performance_stats[mode]
        stats['total_requests'] += 1
        stats['total_time'] += processing_time
        stats['total_results'] += result_count
        stats['avg_time'] = stats['total_time'] / stats['total_requests']
        stats['avg_results'] = stats['total_results'] / stats['total_requests']
        stats['min_time'] = min(stats['min_time'], processing_time)
        stats['max_time'] = max(stats['max_time'], processing_time)
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = sum(self.mode_usage_stats.values())
        
        return {
            'total_requests': total_requests,
            'mode_usage': dict(self.mode_usage_stats),
            'mode_usage_percentage': {
                mode: (count / total_requests * 100) if total_requests > 0 else 0
                for mode, count in self.mode_usage_stats.items()
            },
            'performance_stats': dict(self.mode_performance_stats),
            'error_stats': dict(self.mode_error_stats),
            'supported_modes': self.supported_modes
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.mode_usage_stats.clear()
        self.mode_performance_stats.clear()
        self.mode_error_stats.clear()
        logger.info("搜索模式统计信息已重置")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            健康状态信息
        """
        try:
            # 检查检索服务是否可用
            if not self.retrieval_service:
                return {
                    'status': 'unhealthy',
                    'error': '检索服务不可用'
                }
            
            # 获取统计信息
            stats = self.get_usage_statistics()
            
            return {
                'status': 'healthy',
                'supported_modes': self.supported_modes,
                'total_requests': stats['total_requests'],
                'error_rate': sum(self.mode_error_stats.values()) / max(stats['total_requests'], 1) * 100
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }