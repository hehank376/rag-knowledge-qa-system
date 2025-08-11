
"""
重排序服务模块

提供基于交叉编码器的检索结果重排序功能，支持：
- 重排序模型的加载和初始化
- 查询-文档对的重排序计算
- 重排序结果的分数更新和排序
- 错误处理和降级机制
- 性能监控和优化
- API调用支持（SiliconFlow等）
"""

import logging
import time
import asyncio
import aiohttp
import json
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..models.config import RetrievalConfig
from ..models.vector import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RerankingMetrics:
    """重排序性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    model_load_time: float = 0.0
    last_updated: datetime = None
    
    def update_request(self, processing_time: float, success: bool = True):
        """更新请求指标"""
        self.total_requests += 1
        self.total_processing_time += processing_time
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.average_processing_time = self.total_processing_time / self.total_requests
        self.last_updated = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class RerankingService:
    """重排序服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化重排序服务
        
        Args:
            config: 重排序配置字典
        """
        self.config = config or {}
        self.reranker_model = None
        self.model_loaded = False
        
        # 修复配置读取逻辑 - 支持多种配置键名
        self.model_name = (
            self.config.get('model_name') or 
            self.config.get('model') or 
            'cross-encoder/ms-marco-MiniLM-L-6-v2'
        )
        self.provider = self.config.get('provider', 'local')
        self.max_length = self.config.get('max_length', 512)
        self.batch_size = self.config.get('batch_size', 32)
        self.timeout = self.config.get('timeout', 30.0)
        
        # API相关配置
        self.api_key = self.config.get('api_key')
        self.base_url = self.config.get('base_url')
        self._session = None
        
        # 性能指标
        self.metrics = RerankingMetrics()
        
        logger.info(f"重排序服务初始化 - 提供商: {self.provider}, 模型: {self.model_name}")
    
    async def initialize(self) -> None:
        """初始化重排序模型"""
        start_time = time.time()
        
        try:
            if self.provider in ['siliconflow', 'openai'] and self.api_key and self.base_url:
                # 初始化API客户端
                await self._initialize_api_client()
            else:
                # 在线程池中加载本地模型以避免阻塞
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._load_model)
            
            load_time = time.time() - start_time
            self.metrics.model_load_time = load_time
            
            logger.info(f"重排序模型加载成功，耗时: {load_time:.2f}秒")
            
        except ImportError as e:
            logger.warning(f"sentence-transformers库未安装，重排序功能将被禁用: {e}")
            self.model_loaded = False
        except Exception as e:
            logger.error(f"重排序模型加载失败: {e}")
            self.model_loaded = False
    
    async def _initialize_api_client(self) -> None:
        """初始化API客户端"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            )
            self.model_loaded = True
            logger.info(f"API客户端初始化成功: {self.provider}")
        except Exception as e:
            logger.error(f"API客户端初始化失败: {e}")
            raise
    
    def _load_model(self) -> None:
        """加载重排序模型（在线程池中执行）"""
        try:
            from sentence_transformers import CrossEncoder
            
            # 加载交叉编码器模型
            self.reranker_model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
                device='cpu'  # 可以根据需要配置为GPU
            )
            
            self.model_loaded = True
            logger.info(f"成功加载重排序模型: {self.model_name}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    async def rerank_results(
        self, 
        query: str, 
        results: List[SearchResult], 
        config: RetrievalConfig
    ) -> List[SearchResult]:
        """
        对检索结果进行重排序
        
        Args:
            query: 查询字符串
            results: 原始检索结果
            config: 检索配置
            
        Returns:
            重排序后的检索结果列表
        """
        # 检查是否启用重排序
        if not config.enable_rerank:
            logger.debug("重排序功能未启用，返回原始结果")
            return results
        
        # 检查模型是否加载
        if not self.model_loaded:
            logger.warning("重排序模型未加载，返回原始结果")
            return results
        
        # 检查结果是否为空
        if not results:
            logger.debug("检索结果为空，无需重排序")
            return results
        
        start_time = time.time()
        
        try:
            # 执行重排序
            if self.provider in ['siliconflow', 'openai'] and self._session:
                reranked_results = await self._perform_api_reranking(query, results)
            else:
                reranked_results = await self._perform_local_reranking(query, results)
            
            # 更新性能指标
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, success=True)
            
            logger.info(f"重排序完成，处理{len(results)}个结果，耗时: {processing_time:.3f}秒")
            return reranked_results
            
        except Exception as e:
            # 更新失败指标
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, success=False)
            
            logger.error(f"重排序失败: {e}，返回原始结果")
            # 降级返回原始结果
            return results
    
    async def _perform_api_reranking(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """通过API执行重排序"""
        documents = [result.content for result in results]
        
        # 准备API请求数据
        request_data = {
            'model': self.model_name,
            'query': query,
            'documents': documents,
            'top_k': len(documents)
        }
        
        # 发送API请求
        async with self._session.post(f"{self.base_url}/rerank", json=request_data) as response:
            if response.status == 200:
                result_data = await response.json()
                scores = self._parse_api_response(result_data)
            else:
                error_text = await response.text()
                raise Exception(f"API请求失败: {response.status} - {error_text}")
        
        return self._create_reranked_results(query, results, scores)
    
    async def _perform_local_reranking(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """执行本地重排序计算"""
        # 准备查询-文档对
        pairs = []
        for result in results:
            # 截断过长的文档内容
            content = result.content[:self.max_length] if len(result.content) > self.max_length else result.content
            pairs.append((query, content))
        
        # 在线程池中执行重排序计算
        loop = asyncio.get_event_loop()
        
        # 设置超时
        try:
            scores = await asyncio.wait_for(
                loop.run_in_executor(None, self._compute_rerank_scores, pairs),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"重排序计算超时（{self.timeout}秒）")
            raise Exception("重排序计算超时")
        
        return self._create_reranked_results(query, results, scores)
    
    def _compute_rerank_scores(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """计算重排序分数（在线程池中执行）"""
        try:
            # 批处理计算分数
            if len(pairs) <= self.batch_size:
                # 单批处理
                scores = self.reranker_model.predict(pairs)
            else:
                # 多批处理
                scores = []
                for i in range(0, len(pairs), self.batch_size):
                    batch = pairs[i:i + self.batch_size]
                    batch_scores = self.reranker_model.predict(batch)
                    scores.extend(batch_scores)
            
            return scores.tolist() if hasattr(scores, 'tolist') else list(scores)
            
        except Exception as e:
            logger.error(f"重排序分数计算失败: {e}")
            raise
    
    def _parse_api_response(self, response: Dict[str, Any]) -> List[float]:
        """解析API响应"""
        try:
            if 'results' in response:
                results = response['results']
                scores = []
                # 按索引排序确保顺序正确
                sorted_results = sorted(results, key=lambda x: x.get('index', 0))
                for result in sorted_results:
                    score = result.get('relevance_score', 0.0)
                    scores.append(float(score))
                return scores
            elif 'scores' in response:
                return [float(score) for score in response['scores']]
            else:
                raise Exception(f"无法解析API响应格式: {response}")
        except Exception as e:
            logger.error(f"解析API响应失败: {str(e)}")
            raise Exception(f"解析API响应失败: {str(e)}")
    
    def _create_reranked_results(self, query: str, results: List[SearchResult], scores: List[float]) -> List[SearchResult]:
        """创建重排序后的结果"""
        # 更新结果分数
        reranked_results = []
        for i, (result, score) in enumerate(zip(results, scores)):
            # 创建新的结果对象，保留原始信息
            reranked_result = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                similarity_score=float(score),  # 使用重排序分数
                metadata={
                    **result.metadata,
                    'original_score': result.similarity_score,  # 保存原始分数
                    'rerank_score': float(score),
                    'rerank_rank': i + 1,
                    'rerank_provider': self.provider
                }
            )
            reranked_results.append(reranked_result)
        
        # 按重排序分数降序排列
        reranked_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # 更新最终排名
        for i, result in enumerate(reranked_results):
            result.metadata['final_rank'] = i + 1
        
        return reranked_results
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取重排序性能指标"""
        return {
            'model_loaded': self.model_loaded,
            'provider': self.provider,
            'model_name': self.model_name,
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'success_rate': self.metrics.success_rate,
            'failure_rate': self.metrics.failure_rate,
            'average_processing_time': self.metrics.average_processing_time,
            'model_load_time': self.metrics.model_load_time,
            'last_updated': self.metrics.last_updated.isoformat() if self.metrics.last_updated else None,
            'config': {
                'provider': self.provider,
                'model_name': self.model_name,
                'max_length': self.max_length,
                'batch_size': self.batch_size,
                'timeout': self.timeout
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = "healthy" if self.model_loaded else "unhealthy"
        
        health_info = {
            'status': status,
            'model_loaded': self.model_loaded,
            'provider': self.provider,
            'model_name': self.model_name,
            'last_check': datetime.now().isoformat(),
            'metrics': {
                'total_requests': self.metrics.total_requests,
                'success_rate': self.metrics.success_rate,
                'average_processing_time': self.metrics.average_processing_time
            }
        }
        
        return health_info
    
    async def test_reranking_connection(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """测试重排序模型连接"""
        try:
            if self.provider in ['siliconflow', 'openai'] and self._session:
                # 测试API连接
                test_data = {
                    'model': self.model_name,
                    'query': 'test query',
                    'documents': ['test document'],
                    'top_k': 1
                }
                
                async with self._session.post(f"{self.base_url}/rerank", json=test_data) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "provider": self.provider,
                            "model": self.model_name,
                            "status": "healthy"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "provider": self.provider,
                            "model": self.model_name,
                            "error": f"API测试失败: {response.status} - {error_text}"
                        }
            else:
                # 测试本地模型
                if self.reranker_model:
                    test_pairs = [("test query", "test document")]
                    scores = self.reranker_model.predict(test_pairs)
                    return {
                        "success": True,
                        "provider": self.provider,
                        "model": self.model_name,
                        "status": "healthy",
                        "test_score": float(scores[0]) if scores else None
                    }
                else:
                    return {
                        "success": False,
                        "provider": self.provider,
                        "model": self.model_name,
                        "error": "本地模型未加载"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "provider": self.provider,
                "model": self.model_name,
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            # 清理API会话
            if self._session:
                await self._session.close()
                self._session = None
            
            # 清理模型资源
            if self.reranker_model is not None:
                self.reranker_model = None
                
            self.model_loaded = False
            logger.info("重排序服务资源清理完成")
            
        except Exception as e:
            logger.error(f"清理重排序服务资源失败: {e}")
    
    async def close(self) -> None:
        """关闭重排序服务，清理资源（兼容方法）"""
        await self.cleanup()
