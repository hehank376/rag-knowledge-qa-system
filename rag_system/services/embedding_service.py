"""
嵌入向量化服务
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models.document import TextChunk
from ..models.vector import Vector
from ..embeddings import EmbeddingFactory, EmbeddingConfig, BaseEmbedding
from ..utils.exceptions import ProcessingError, ConfigurationError
from ..utils.model_exceptions import ModelConnectionError, ModelResponseError, UnsupportedProviderError
from .base import BaseService

logger = logging.getLogger(__name__)


class EmbeddingService(BaseService):
    """嵌入向量化服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._embedding_model: Optional[BaseEmbedding] = None
        self._embedding_config = self._create_embedding_config()
        self._fallback_model: Optional[BaseEmbedding] = None
        self._fallback_config = self._create_fallback_config()
        self._enable_fallback = self.config.get('enable_embedding_fallback', True)
        self._dimension_cache: Dict[str, int] = {}  # 缓存不同模型的维度
    
    def _create_embedding_config(self) -> EmbeddingConfig:
        """创建嵌入配置"""
        return EmbeddingConfig(
            provider=self.config.get('provider', 'mock'),
            model=self.config.get('model', 'text-embedding-ada-002'),
            api_key=self.config.get('api_key'),
            api_base=self.config.get('api_base'),
            base_url=self.config.get('base_url'),
            max_tokens=self.config.get('max_tokens', 8192),
            batch_size=self.config.get('batch_size', 100),
            dimensions=self.config.get('dimensions'),
            timeout=self.config.get('timeout', 30),
            retry_attempts=self.config.get('retry_attempts', 3)
        )
    
    def _create_fallback_config(self) -> Optional[EmbeddingConfig]:
        """创建备用嵌入配置"""
        try:
            # 如果主要配置不是mock，则使用mock作为备用
            if self._embedding_config.provider != 'mock':
                return EmbeddingConfig(
                    provider='mock',
                    model='mock-embedding',
                    dimensions=self._embedding_config.dimensions or 768,
                    batch_size=self._embedding_config.batch_size,
                    timeout=10,
                    retry_attempts=1
                )
            return None
        except Exception as e:
            logger.warning(f"创建备用嵌入配置失败: {str(e)}")
            return None
    
    async def _create_embedding_instance(self, config: EmbeddingConfig) -> Optional[BaseEmbedding]:
        """创建嵌入模型实例"""
        try:
            embedding = EmbeddingFactory.create_embedding(config)
            await embedding.initialize()
            logger.info(f"嵌入模型实例创建成功: {config.provider} - {config.model}")
            return embedding
        except Exception as e:
            logger.error(f"嵌入模型实例创建失败: {config.provider} - {str(e)}")
            return None
    
    async def _switch_to_fallback_embedding(self) -> bool:
        """切换到备用嵌入模型"""
        if not self._enable_fallback or not self._fallback_config:
            return False
        
        try:
            if not self._fallback_model:
                self._fallback_model = await self._create_embedding_instance(self._fallback_config)
            
            if self._fallback_model:
                logger.warning(f"切换到备用嵌入模型: {self._fallback_config.provider}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"切换到备用嵌入模型失败: {str(e)}")
            return False
    
    def _check_dimension_compatibility(self, expected_dim: int, actual_dim: int, provider: str) -> bool:
        """检查向量维度兼容性"""
        if expected_dim != actual_dim:
            logger.warning(
                f"向量维度不匹配: 期望 {expected_dim}, 实际 {actual_dim} (提供商: {provider})"
            )
            return False
        return True
    
    async def _vectorize_with_error_handling(
        self, 
        texts: List[str], 
        single: bool = False
    ) -> List[List[float]]:
        """带错误处理的向量化"""
        # 尝试主要嵌入模型
        if self._embedding_model:
            try:
                logger.debug(f"使用主要嵌入模型: {self._embedding_config.provider}")
                
                if single:
                    embedding = await self._embedding_model.embed_text(texts[0])
                    return [embedding]
                else:
                    logger.info(f"开始批量向量化: {len(texts)} 个文本")
                    embeddings = await self._embedding_model.embed_texts(texts)
                    logger.info(f"批量向量化完成: 生成 {len(embeddings)} 个向量")
                    
                    # 检查维度兼容性
                    if embeddings:
                        expected_dim = self._dimension_cache.get(self._embedding_config.provider)
                        if expected_dim and not self._check_dimension_compatibility(
                            expected_dim, len(embeddings[0]), self._embedding_config.provider
                        ):
                            logger.warning("主要模型维度不匹配，尝试使用备用模型")
                            raise ProcessingError("维度不匹配")
                    
                    return embeddings
                    
            except (ModelConnectionError, ModelResponseError) as e:
                logger.warning(f"主要嵌入模型调用失败: {str(e)}")
                
                # 尝试切换到备用模型
                if await self._switch_to_fallback_embedding():
                    try:
                        logger.info(f"使用备用嵌入模型处理 {len(texts)} 个文本")
                        
                        if single:
                            embedding = await self._fallback_model.embed_text(texts[0])
                            return [embedding]
                        else:
                            embeddings = await self._fallback_model.embed_texts(texts)
                            logger.info(f"备用模型向量化完成: 生成 {len(embeddings)} 个向量")
                            return embeddings
                            
                    except Exception as fallback_error:
                        logger.error(f"备用嵌入模型也失败: {str(fallback_error)}")
                        raise ProcessingError(f"所有嵌入模型都失败: 主要模型 - {str(e)}, 备用模型 - {str(fallback_error)}")
                
                raise ProcessingError(f"嵌入模型调用失败且无备用模型: {str(e)}")
                
            except Exception as e:
                logger.error(f"嵌入模型调用出现未预期错误: {str(e)}")
                
                # 尝试备用模型
                if await self._switch_to_fallback_embedding():
                    try:
                        if single:
                            embedding = await self._fallback_model.embed_text(texts[0])
                            return [embedding]
                        else:
                            embeddings = await self._fallback_model.embed_texts(texts)
                            return embeddings
                    except Exception:
                        pass
                
                raise ProcessingError(f"向量化失败: {str(e)}")
        
        # 如果没有可用的嵌入模型
        raise ProcessingError("没有可用的嵌入模型")
    
    async def _vectorize_query_with_error_handling(self, query: str) -> List[float]:
        """带错误处理的查询向量化"""
        # 尝试主要嵌入模型
        if self._embedding_model:
            try:
                logger.debug(f"使用主要嵌入模型向量化查询: 长度={len(query)}")
                embedding = await self._embedding_model.embed_query(query)
                logger.debug(f"查询向量化完成: 维度={len(embedding)}")
                return embedding
                
            except (ModelConnectionError, ModelResponseError) as e:
                logger.warning(f"主要嵌入模型查询失败: {str(e)}")
                
                # 尝试切换到备用模型
                if await self._switch_to_fallback_embedding():
                    try:
                        embedding = await self._fallback_model.embed_query(query)
                        logger.debug(f"备用模型查询向量化完成: 维度={len(embedding)}")
                        return embedding
                    except Exception as fallback_error:
                        logger.error(f"备用嵌入模型查询也失败: {str(fallback_error)}")
                        raise ProcessingError(f"查询向量化失败: {str(fallback_error)}")
                
                raise ProcessingError(f"查询向量化失败且无备用模型: {str(e)}")
                
            except Exception as e:
                logger.error(f"查询向量化出现未预期错误: {str(e)}")
                
                # 尝试备用模型
                if await self._switch_to_fallback_embedding():
                    try:
                        embedding = await self._fallback_model.embed_query(query)
                        return embedding
                    except Exception:
                        pass
                
                raise ProcessingError(f"查询向量化失败: {str(e)}")
        
        # 如果没有可用的嵌入模型
        raise ProcessingError("没有可用的嵌入模型")
    
    async def initialize(self) -> None:
        """初始化嵌入服务"""
        try:
            logger.info(f"初始化嵌入服务: {self._embedding_config.provider}")
            
            # 初始化主要嵌入模型
            self._embedding_model = await self._create_embedding_instance(self._embedding_config)
            if not self._embedding_model:
                raise ConfigurationError(f"无法创建主要嵌入模型实例: {self._embedding_config.provider}")
            
            # 缓存主要模型的维度
            main_dim = self._embedding_model.get_embedding_dimension()
            self._dimension_cache[self._embedding_config.provider] = main_dim
            
            # 初始化备用嵌入模型（如果启用）
            if self._enable_fallback and self._fallback_config:
                self._fallback_model = await self._create_embedding_instance(self._fallback_config)
                if self._fallback_model:
                    fallback_dim = self._fallback_model.get_embedding_dimension()
                    self._dimension_cache[self._fallback_config.provider] = fallback_dim
                    logger.info(f"备用嵌入模型初始化成功: {self._fallback_config.provider}")
                else:
                    logger.warning("备用嵌入模型初始化失败，将禁用降级功能")
            
            logger.info("嵌入服务初始化成功")
            
        except Exception as e:
            logger.error(f"嵌入服务初始化失败: {str(e)}")
            raise ConfigurationError(f"嵌入服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._embedding_model:
            await self._embedding_model.cleanup()
            self._embedding_model = None
        
        if self._fallback_model:
            await self._fallback_model.cleanup()
            self._fallback_model = None
        
        self._dimension_cache.clear()
        logger.info("嵌入服务资源清理完成")
    
    def _ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if not self._embedding_model or not self._embedding_model.is_initialized():
            raise ProcessingError("嵌入服务未初始化")
    
    async def vectorize_text(self, text: str) -> List[float]:
        """对单个文本进行向量化"""
        self._ensure_initialized()
        
        if not text or not text.strip():
            raise ProcessingError("文本内容不能为空")
        
        result = await self._vectorize_with_error_handling([text], single=True)
        return result[0]  # 返回单个向量而不是向量列表
    
    async def vectorize_texts(self, texts: List[str]) -> List[List[float]]:
        """对多个文本进行批量向量化"""
        self._ensure_initialized()
        
        if not texts:
            raise ProcessingError("文本列表不能为空")
        
        # 过滤空文本
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            raise ProcessingError("没有有效的文本内容")
        
        return await self._vectorize_with_error_handling(valid_texts, single=False)
    
    async def vectorize_query(self, query: str) -> List[float]:
        """对查询文本进行向量化"""
        self._ensure_initialized()
        
        if not query or not query.strip():
            raise ProcessingError("查询内容不能为空")
        
        # 使用查询特定的向量化方法
        return await self._vectorize_query_with_error_handling(query)
    
    async def vectorize_chunks(self, chunks: List[TextChunk], document_name: str = None) -> List[Vector]:
        """对文本块进行向量化"""
        self._ensure_initialized()
        
        if not chunks:
            raise ProcessingError("文本块列表不能为空")
        
        try:
            logger.info(f"开始向量化文本块: {len(chunks)} 个块")
            
            # 提取文本内容
            texts = [chunk.content for chunk in chunks]
            
            # 批量向量化
            embeddings = await self.vectorize_texts(texts)
            
            # 创建向量对象
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector = Vector(
                    id=str(uuid.uuid4()),
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    embedding=embedding,
                    metadata={
                        "document_name": document_name or f'Document_{chunk.document_id[:8]}',  # 添加真实文档名称
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,  # 存储实际内容
                        "content_length": len(chunk.content),
                        "embedding_model": self._embedding_config.model,
                        "embedding_provider": self._embedding_config.provider,
                        "embedding_dimensions": len(embedding),
                        "created_at": datetime.now().isoformat()
                    }
                )
                vectors.append(vector)
            
            logger.info(f"文本块向量化完成: 生成 {len(vectors)} 个向量")
            return vectors
            
        except Exception as e:
            logger.error(f"文本块向量化失败: {str(e)}")
            raise ProcessingError(f"文本块向量化失败: {str(e)}")
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量的维度"""
        self._ensure_initialized()
        return self._embedding_model.get_embedding_dimension()
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        self._ensure_initialized()
        
        base_info = await self._embedding_model.get_model_info()
        base_info.update({
            "service_type": "embedding",
            "initialized": self._embedding_model.is_initialized()
        })
        
        return base_info
    
    async def test_embedding(self, test_text: str = "这是一个测试文本") -> Dict[str, Any]:
        """测试嵌入功能"""
        self._ensure_initialized()
        
        try:
            start_time = datetime.now()
            
            # 测试单个文本向量化
            embedding = await self.vectorize_text(test_text)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "test_text": test_text,
                "embedding_dimension": len(embedding),
                "processing_time": processing_time,
                "model_info": await self.get_model_info()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_text": test_text
            }
    
    def get_supported_providers(self) -> List[str]:
        """获取支持的嵌入提供商"""
        return EmbeddingFactory.get_available_providers()
    
    async def switch_provider(self, new_config: EmbeddingConfig) -> bool:
        """动态切换嵌入提供商"""
        try:
            logger.info(f"尝试切换嵌入提供商: {self._embedding_config.provider} -> {new_config.provider}")
            
            # 创建新的嵌入模型实例
            new_embedding = await self._create_embedding_instance(new_config)
            if not new_embedding:
                logger.error(f"无法创建新的嵌入模型实例: {new_config.provider}")
                return False
            
            # 清理旧的嵌入模型实例
            if self._embedding_model:
                await self._embedding_model.cleanup()
            
            # 更新配置和实例
            self._embedding_config = new_config
            self._embedding_model = new_embedding
            
            # 更新维度缓存
            new_dim = new_embedding.get_embedding_dimension()
            self._dimension_cache[new_config.provider] = new_dim
            
            logger.info(f"嵌入提供商切换成功: {new_config.provider} - {new_config.model}")
            return True
            
        except Exception as e:
            logger.error(f"嵌入提供商切换失败: {str(e)}")
            return False
    
    async def test_embedding_connection(self, config: Optional[EmbeddingConfig] = None) -> Dict[str, Any]:
        """测试嵌入模型连接"""
        test_config = config or self._embedding_config
        
        try:
            # 创建临时嵌入模型实例进行测试
            test_embedding = await self._create_embedding_instance(test_config)
            if not test_embedding:
                return {
                    "success": False,
                    "provider": test_config.provider,
                    "model": test_config.model,
                    "error": "无法创建嵌入模型实例"
                }
            
            # 执行健康检查
            health_check = test_embedding.health_check()
            
            # 测试简单向量化
            test_text = "测试文本"
            try:
                test_embedding_result = await test_embedding.embed_text(test_text)
                dimension = len(test_embedding_result)
            except Exception as e:
                dimension = None
                health_check = False
            
            # 清理测试实例
            await test_embedding.cleanup()
            
            return {
                "success": health_check,
                "provider": test_config.provider,
                "model": test_config.model,
                "dimension": dimension,
                "status": "healthy" if health_check else "unhealthy"
            }
            
        except Exception as e:
            return {
                "success": False,
                "provider": test_config.provider,
                "model": test_config.model,
                "error": str(e)
            }
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            # 主要嵌入模型信息
            main_embedding_info = {
                "provider": self._embedding_config.provider,
                "model": self._embedding_config.model,
                "dimension": self._dimension_cache.get(self._embedding_config.provider, 0),
                "status": "available" if self._embedding_model else "unavailable"
            }
            
            # 备用嵌入模型信息
            fallback_embedding_info = None
            if self._fallback_config:
                fallback_embedding_info = {
                    "provider": self._fallback_config.provider,
                    "model": self._fallback_config.model,
                    "dimension": self._dimension_cache.get(self._fallback_config.provider, 0),
                    "status": "available" if self._fallback_model else "unavailable",
                    "enabled": self._enable_fallback
                }
            
            stats = {
                "service_name": "EmbeddingService",
                "main_embedding": main_embedding_info,
                "fallback_embedding": fallback_embedding_info,
                "batch_size": self._embedding_config.batch_size,
                "max_tokens": self._embedding_config.max_tokens,
                "available_providers": EmbeddingFactory.get_available_providers(),
                "fallback_enabled": self._enable_fallback,
                "dimension_cache": self._dimension_cache.copy()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取嵌入服务统计失败: {str(e)}")
            return {"error": str(e)}