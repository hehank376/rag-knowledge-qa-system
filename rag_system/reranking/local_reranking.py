"""
本地重排序实现

使用sentence-transformers库的CrossEncoder进行本地重排序。
支持多种预训练模型和自定义配置。
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

from .base import BaseReranking, RerankingConfig, RerankingMetrics

logger = logging.getLogger(__name__)


class LocalReranking(BaseReranking):
    """本地重排序实现"""
    
    def __init__(self, config: RerankingConfig):
        super().__init__(config)
        self.metrics = RerankingMetrics()
        self._cross_encoder = None
        self._model_load_time = 0.0
    
    async def initialize(self) -> None:
        """初始化本地重排序模型"""
        start_time = time.time()
        
        try:
            # 在线程池中加载模型以避免阻塞
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)
            
            self._model_load_time = time.time() - start_time
            self._initialized = True
            
            logger.info(f"本地重排序模型加载成功: {self.config.get_model_name()}, 耗时: {self._model_load_time:.2f}秒")
            
        except ImportError as e:
            error_msg = f"sentence-transformers库未安装: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"本地重排序模型加载失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _load_model(self) -> None:
        """加载重排序模型（在线程池中执行）"""
        try:
            from sentence_transformers import CrossEncoder
            
            model_name = self.config.get_model_name()
            
            # 配置模型参数
            model_kwargs = {
                'max_length': self.config.max_length,
                'device': self.config.device
            }
            
            # 如果指定了缓存目录
            if self.config.model_cache_dir:
                model_kwargs['cache_folder'] = self.config.model_cache_dir
            
            # 添加额外参数
            model_kwargs.update(self.config.extra_params)
            
            # 加载交叉编码器模型
            self._cross_encoder = CrossEncoder(model_name, **model_kwargs)
            
            logger.info(f"成功加载本地重排序模型: {model_name}")
            
        except Exception as e:
            logger.error(f"本地模型加载失败: {e}")
            raise
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """对文档进行重排序"""
        if not self._initialized:
            raise Exception("本地重排序模型未初始化")
        
        self._validate_inputs(query, documents)
        
        start_time = time.time()
        
        try:
            # 准备查询-文档对
            pairs = self._prepare_pairs(query, documents)
            
            # 在线程池中执行重排序计算
            loop = asyncio.get_event_loop()
            
            # 设置超时
            scores = await asyncio.wait_for(
                loop.run_in_executor(None, self._compute_scores, pairs),
                timeout=self.config.timeout
            )
            
            # 更新指标
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=True)
            
            logger.debug(f"本地重排序完成: {len(documents)}个文档，耗时: {processing_time:.3f}秒")
            return scores
            
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=False)
            error_msg = f"本地重排序计算超时（{self.config.timeout}秒）"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.update_request(processing_time, len(documents), success=False)
            await self._handle_error(e, "本地重排序")
    
    async def rerank_batch(self, queries: List[str], documents_list: List[List[str]]) -> List[List[float]]:
        """批量重排序"""
        if not self._initialized:
            raise Exception("本地重排序模型未初始化")
        
        if len(queries) != len(documents_list):
            raise ValueError("查询数量与文档列表数量不匹配")
        
        # 对于本地模型，可以优化批处理
        all_pairs = []
        pair_indices = []
        current_index = 0
        
        # 收集所有查询-文档对
        for query, documents in zip(queries, documents_list):
            pairs = self._prepare_pairs(query, documents)
            all_pairs.extend(pairs)
            pair_indices.append((current_index, current_index + len(pairs)))
            current_index += len(pairs)
        
        # 批量计算所有分数
        start_time = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            all_scores = await asyncio.wait_for(
                loop.run_in_executor(None, self._compute_scores, all_pairs),
                timeout=self.config.timeout * len(queries)
            )
            
            # 分割结果
            results = []
            for start_idx, end_idx in pair_indices:
                scores = all_scores[start_idx:end_idx]
                results.append(scores)
            
            # 更新指标
            processing_time = time.time() - start_time
            total_documents = sum(len(docs) for docs in documents_list)
            self.metrics.update_request(processing_time, total_documents, success=True)
            
            logger.debug(f"本地批量重排序完成: {len(queries)}个查询，{total_documents}个文档，耗时: {processing_time:.3f}秒")
            return results
            
        except Exception as e:
            processing_time = time.time() - start_time
            total_documents = sum(len(docs) for docs in documents_list)
            self.metrics.update_request(processing_time, total_documents, success=False)
            await self._handle_error(e, "本地批量重排序")
    
    def _compute_scores(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """
        计算重排序分数（在线程池中执行）
        
        Args:
            pairs: 查询-文档对列表
            
        Returns:
            重排序分数列表
        """
        try:
            batch_size = self.config.batch_size
            
            if len(pairs) <= batch_size:
                # 单批处理
                scores = self._cross_encoder.predict(pairs)
            else:
                # 多批处理
                scores = []
                for i in range(0, len(pairs), batch_size):
                    batch = pairs[i:i + batch_size]
                    batch_scores = self._cross_encoder.predict(batch)
                    scores.extend(batch_scores)
            
            # 确保返回Python列表
            if hasattr(scores, 'tolist'):
                return scores.tolist()
            else:
                return list(scores)
                
        except Exception as e:
            logger.error(f"本地重排序分数计算失败: {e}")
            raise
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            # 清理模型资源
            if self._cross_encoder is not None:
                # 如果模型有清理方法，调用它
                if hasattr(self._cross_encoder, 'close'):
                    self._cross_encoder.close()
                
                self._cross_encoder = None
            
            self._initialized = False
            logger.info("本地重排序模型资源清理完成")
            
        except Exception as e:
            logger.error(f"清理本地重排序模型资源失败: {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._initialized or self._cross_encoder is None:
                return False
            
            # 测试简单的重排序计算
            test_pairs = [("test query", "test document")]
            scores = self._cross_encoder.predict(test_pairs)
            
            return len(scores) == 1 and isinstance(scores[0], (int, float))
        except:
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = {
            'provider': 'local',
            'model': self.config.get_model_name(),
            'type': 'local',
            'description': '本地重排序模型，使用sentence-transformers',
            'initialized': self._initialized,
            'device': self.config.device,
            'max_length': self.config.max_length,
            'batch_size': self.config.batch_size,
            'model_load_time': self._model_load_time,
            'config': self.config.to_dict(),
            'metrics': self.metrics.to_dict(),
            'last_updated': datetime.now().isoformat()
        }
        
        # 如果模型已加载，获取更多信息
        if self._cross_encoder is not None:
            try:
                # 尝试获取模型的详细信息
                if hasattr(self._cross_encoder, 'config'):
                    base_info['model_config'] = str(self._cross_encoder.config)
                if hasattr(self._cross_encoder, 'tokenizer'):
                    base_info['tokenizer'] = str(type(self._cross_encoder.tokenizer).__name__)
            except:
                pass
        
        return base_info
    
    @classmethod
    def get_provider_info(cls) -> Dict[str, str]:
        """获取提供商信息"""
        return {
            'provider': 'local',
            'type': 'local',
            'description': '本地重排序模型，使用sentence-transformers库',
            'supports_api': False,
            'supports_local': True,
            'requires_dependencies': True,
            'dependencies': ['sentence-transformers', 'torch'],
            'supported_models': [
                'cross-encoder/ms-marco-MiniLM-L-6-v2',
                'cross-encoder/ms-marco-MiniLM-L-12-v2',
                'cross-encoder/ms-marco-TinyBERT-L-2-v2',
                'BAAI/bge-reranker-base',
                'BAAI/bge-reranker-large'
            ]
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = self.metrics.to_dict()
        metrics['model_load_time'] = self._model_load_time
        return metrics
    
    def reset_metrics(self) -> None:
        """重置性能指标"""
        self.metrics.reset()
        logger.info("本地重排序性能指标已重置")