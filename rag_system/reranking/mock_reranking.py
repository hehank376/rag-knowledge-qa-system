"""
Mock重排序实现

用于测试和开发的模拟重排序模型，提供确定性的重排序结果。
"""

import logging
import asyncio
import hashlib
from typing import List, Dict, Any
from datetime import datetime

from .base import BaseReranking, RerankingConfig, RerankingMetrics

logger = logging.getLogger(__name__)


class MockReranking(BaseReranking):
    """Mock重排序实现"""
    
    def __init__(self, config: RerankingConfig):
        super().__init__(config)
        self.metrics = RerankingMetrics()
        self._model_info = {
            'provider': 'mock',
            'model': 'mock-reranking',
            'type': 'mock',
            'description': '模拟重排序模型，用于测试和开发'
        }
    
    async def initialize(self) -> None:
        """初始化Mock重排序模型"""
        # 模拟初始化延迟
        await asyncio.sleep(0.1)
        self._initialized = True
        logger.info(f"Mock重排序模型初始化成功: {self.config.get_model_name()}")
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        对文档进行重排序
        
        使用确定性算法生成重排序分数，基于查询和文档的相似度计算。
        """
        if not self._initialized:
            raise Exception("Mock重排序模型未初始化")
        
        self._validate_inputs(query, documents)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 模拟处理延迟
            await asyncio.sleep(0.01 * len(documents))
            
            # 生成确定性的重排序分数
            scores = self._compute_mock_scores(query, documents)
            
            # 更新指标
            processing_time = asyncio.get_event_loop().time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=True)
            
            logger.debug(f"Mock重排序完成: {len(documents)}个文档，耗时: {processing_time:.3f}秒")
            return scores
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=False)
            await self._handle_error(e, "Mock重排序")
    
    async def rerank_batch(self, queries: List[str], documents_list: List[List[str]]) -> List[List[float]]:
        """批量重排序"""
        if not self._initialized:
            raise Exception("Mock重排序模型未初始化")
        
        if len(queries) != len(documents_list):
            raise ValueError("查询数量与文档列表数量不匹配")
        
        results = []
        for query, documents in zip(queries, documents_list):
            scores = await self.rerank(query, documents)
            results.append(scores)
        
        return results
    
    def _compute_mock_scores(self, query: str, documents: List[str]) -> List[float]:
        """
        计算模拟重排序分数
        
        使用简单的文本相似度算法生成确定性分数。
        """
        scores = []
        query_lower = query.lower()
        
        for doc in documents:
            doc_lower = doc.lower()
            
            # 基于文本相似度的简单算法
            # 1. 计算共同词汇数量
            query_words = set(query_lower.split())
            doc_words = set(doc_lower.split())
            common_words = len(query_words.intersection(doc_words))
            
            # 2. 计算长度相似度
            length_similarity = 1.0 - abs(len(query) - len(doc)) / max(len(query), len(doc), 1)
            
            # 3. 计算哈希相似度（确保确定性）
            combined_text = query + doc
            hash_value = int(hashlib.md5(combined_text.encode()).hexdigest()[:8], 16)
            hash_similarity = (hash_value % 1000) / 1000.0
            
            # 4. 综合分数
            score = (
                common_words * 0.4 +
                length_similarity * 0.3 +
                hash_similarity * 0.3
            )
            
            # 归一化到 [0, 1] 范围
            score = max(0.0, min(1.0, score))
            scores.append(score)
        
        return scores
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._initialized = False
        self._model = None
        logger.info("Mock重排序模型资源清理完成")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单的健康检查
            test_scores = self._compute_mock_scores("test query", ["test document"])
            return len(test_scores) == 1 and 0 <= test_scores[0] <= 1
        except:
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = self._model_info.copy()
        base_info.update({
            'initialized': self._initialized,
            'config': self.config.to_dict(),
            'metrics': self.metrics.to_dict(),
            'last_updated': datetime.now().isoformat()
        })
        return base_info
    
    @classmethod
    def get_provider_info(cls) -> Dict[str, str]:
        """获取提供商信息"""
        return {
            'provider': 'mock',
            'type': 'mock',
            'description': '模拟重排序模型，用于测试和开发',
            'supports_api': False,
            'supports_local': True,
            'requires_dependencies': False
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.to_dict()
    
    def reset_metrics(self) -> None:
        """重置性能指标"""
        self.metrics.reset()
        logger.info("Mock重排序性能指标已重置")