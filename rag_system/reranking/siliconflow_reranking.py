"""
SiliconFlow API重排序实现

通过SiliconFlow API进行重排序，支持多种重排序模型。
"""

import logging
import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp

from .base import BaseReranking, RerankingConfig, RerankingMetrics

logger = logging.getLogger(__name__)


class SiliconFlowReranking(BaseReranking):
    """SiliconFlow API重排序实现"""
    
    def __init__(self, config: RerankingConfig):
        super().__init__(config)
        self.metrics = RerankingMetrics()
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_endpoint = f"{config.base_url.rstrip('/')}/rerank"
        
        # 验证必要的配置
        if not config.api_key:
            raise ValueError("SiliconFlow重排序需要API密钥")
        if not config.base_url:
            raise ValueError("SiliconFlow重排序需要基础URL")
    
    async def initialize(self) -> None:
        """初始化SiliconFlow重排序客户端"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            connector = aiohttp.TCPConnector(
                limit=self.config.max_concurrent_requests,
                limit_per_host=self.config.max_concurrent_requests
            )
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'Authorization': f'Bearer {self.config.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'RAG-System/1.0'
                }
            )
            
            # 测试API连接
            await self._test_connection()
            
            self._initialized = True
            logger.info(f"SiliconFlow重排序客户端初始化成功: {self.config.get_model_name()}")
            
        except Exception as e:
            error_msg = f"SiliconFlow重排序客户端初始化失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def _test_connection(self) -> None:
        """测试API连接"""
        try:
            # 发送简单的测试请求
            test_data = {
                'model': self.config.get_model_name(),
                'query': 'test',
                'documents': ['test document'],
                'top_k': 1
            }
            
            async with self._session.post(self._api_endpoint, json=test_data) as response:
                if response.status == 200:
                    logger.debug("SiliconFlow API连接测试成功")
                else:
                    error_text = await response.text()
                    raise Exception(f"API连接测试失败: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"SiliconFlow API连接测试失败: {str(e)}")
            raise
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """对文档进行重排序"""
        if not self._initialized:
            raise Exception("SiliconFlow重排序客户端未初始化")
        
        self._validate_inputs(query, documents)
        
        start_time = time.time()
        
        try:
            # 准备API请求数据
            request_data = {
                'model': self.config.get_model_name(),
                'query': self._truncate_text(query),
                'documents': [self._truncate_text(doc) for doc in documents],
                'top_k': len(documents),  # 返回所有文档的分数
                'return_documents': False  # 只返回分数
            }
            
            # 添加额外参数
            if self.config.extra_params:
                request_data.update(self.config.extra_params)
            
            # 发送API请求
            scores = await self._make_api_request(request_data)
            
            # 更新指标
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=True)
            
            logger.debug(f"SiliconFlow重排序完成: {len(documents)}个文档，耗时: {processing_time:.3f}秒")
            return scores
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=False)
            await self._handle_error(e, "SiliconFlow重排序")
    
    async def rerank_batch(self, queries: List[str], documents_list: List[List[str]]) -> List[List[float]]:
        """批量重排序"""
        if not self._initialized:
            raise Exception("SiliconFlow重排序客户端未初始化")
        
        if len(queries) != len(documents_list):
            raise ValueError("查询数量与文档列表数量不匹配")
        
        # 并发处理多个查询
        tasks = []
        for query, documents in zip(queries, documents_list):
            task = self.rerank(query, documents)
            tasks.append(task)
        
        # 控制并发数量
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        async def limited_rerank(task):
            async with semaphore:
                # 添加请求间隔
                if self.config.request_interval > 0:
                    await asyncio.sleep(self.config.request_interval)
                return await task
        
        # 执行所有任务
        results = await asyncio.gather(*[limited_rerank(task) for task in tasks])
        
        return results
    
    async def _make_api_request(self, request_data: Dict[str, Any]) -> List[float]:
        """发送API请求"""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.retry_attempts:
            try:
                async with self._session.post(self._api_endpoint, json=request_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_api_response(result)
                    elif response.status == 429:  # 速率限制
                        retry_after = int(response.headers.get('Retry-After', 1))
                        logger.warning(f"API速率限制，等待{retry_after}秒后重试")
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"API请求失败: {response.status} - {error_text}")
                        
            except asyncio.TimeoutError:
                last_error = Exception("API请求超时")
                logger.warning(f"API请求超时，重试 {retry_count + 1}/{self.config.retry_attempts + 1}")
            except Exception as e:
                last_error = e
                logger.warning(f"API请求失败，重试 {retry_count + 1}/{self.config.retry_attempts + 1}: {str(e)}")
            
            retry_count += 1
            if retry_count <= self.config.retry_attempts:
                # 指数退避
                wait_time = min(2 ** retry_count, 10)
                await asyncio.sleep(wait_time)
        
        # 所有重试都失败了
        raise last_error or Exception("API请求失败")
    
    def _parse_api_response(self, response: Dict[str, Any]) -> List[float]:
        """解析API响应"""
        try:
            # SiliconFlow API响应格式
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
                # 直接返回分数列表
                return [float(score) for score in response['scores']]
            else:
                raise Exception(f"无法解析API响应格式: {response}")
                
        except Exception as e:
            logger.error(f"解析API响应失败: {str(e)}")
            raise Exception(f"解析API响应失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self._initialized = False
            logger.info("SiliconFlow重排序客户端资源清理完成")
            
        except Exception as e:
            logger.error(f"清理SiliconFlow重排序客户端资源失败: {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            return (
                self._initialized and 
                self._session is not None and 
                not self._session.closed
            )
        except:
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = {
            'provider': 'siliconflow',
            'model': self.config.get_model_name(),
            'type': 'api',
            'description': 'SiliconFlow API重排序模型',
            'initialized': self._initialized,
            'api_endpoint': self._api_endpoint,
            'max_length': self.config.max_length,
            'batch_size': self.config.batch_size,
            'timeout': self.config.timeout,
            'max_concurrent_requests': self.config.max_concurrent_requests,
            'config': self.config.to_dict(),
            'metrics': self.metrics.to_dict(),
            'last_updated': datetime.now().isoformat()
        }
        
        # 如果会话存在，添加连接信息
        if self._session:
            base_info['session_closed'] = self._session.closed
            base_info['connector_limit'] = self._session.connector.limit
        
        return base_info
    
    @classmethod
    def get_provider_info(cls) -> Dict[str, str]:
        """获取提供商信息"""
        return {
            'provider': 'siliconflow',
            'type': 'api',
            'description': 'SiliconFlow API重排序服务',
            'supports_api': True,
            'supports_local': False,
            'requires_dependencies': True,
            'dependencies': ['aiohttp'],
            'supported_models': [
                'BAAI/bge-reranker-v2-m3',
                'BAAI/bge-reranker-base',
                'BAAI/bge-reranker-large'
            ],
            'api_docs': 'https://docs.siliconflow.cn/api-reference/rerank'
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.to_dict()
    
    def reset_metrics(self) -> None:
        """重置性能指标"""
        self.metrics.reset()
        logger.info("SiliconFlow重排序性能指标已重置")