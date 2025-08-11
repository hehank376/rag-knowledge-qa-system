"""
问答服务实现
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models.qa import QAResponse, SourceInfo
from ..models.vector import SearchResult
from ..models.config import RetrievalConfig
from ..services.enhanced_retrieval_service import EnhancedRetrievalService
from ..services.embedding_service import EmbeddingService
from ..llm.factory import LLMFactory
from ..llm.base import LLMConfig, BaseLLM
from ..utils.exceptions import ProcessingError, QAError
from ..utils.model_exceptions import ModelConnectionError, ModelResponseError, UnsupportedProviderError
from .base import BaseService

logger = logging.getLogger(__name__)


class QAService(BaseService):
    """问答服务实现"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        #print(f'Qa_Service 配置 CONFIG : {config}')
        # 初始化增强检索服务
        retrieval_config = {
            'vector_store_type': self.config.get('vector_store_type', 'chroma'),
            'vector_store_path': self.config.get('vector_store_path', './chroma_db'),
            'collection_name': self.config.get('collection_name', 'documents'),
            'embedding_provider': self.config.get('embedding_provider', 'mock'),
            'embedding_model': self.config.get('embedding_model', 'text-embedding-ada-002'),
            'embedding_api_key': self.config.get('embedding_api_key'),
            'embedding_api_base': self.config.get('embedding_api_base'),
            'embedding_dimensions': self.config.get('embedding_dimensions'),
            'default_top_k': self.config.get('retrieval_top_k', 5),
            'similarity_threshold': self.config.get('similarity_threshold', 0.7),
            'search_mode': self.config.get('search_mode', 'semantic'),
            'enable_rerank': self.config.get('enable_rerank', False),
            'enable_cache': self.config.get('enable_cache', False),
            'database_url': self.config.get('database_url', 'sqlite:///./database/documents.db')
        }
        #print(f'Qa_Service 配置 retrieval_config : {retrieval_config}')
        self.retrieval_service = EnhancedRetrievalService(retrieval_config)
        
        # 创建检索配置对象
        self.retrieval_config = RetrievalConfig(
            top_k=self.config.get('retrieval_top_k', 5),
            similarity_threshold=self.config.get('similarity_threshold', 0.7),
            search_mode=self.config.get('search_mode', 'semantic'),
            enable_rerank=self.config.get('enable_rerank', False),
            enable_cache=self.config.get('enable_cache', False)
        )
        
        # 初始化LLM配置
        self.llm_config = LLMConfig(
            provider=self.config.get('llm_provider', 'mock'),
            model=self.config.get('llm_model', 'gpt-3.5-turbo'),
            api_key=self.config.get('llm_api_key'),
            api_base=self.config.get('llm_api_base'),
            base_url=self.config.get('llm_base_url'),
            temperature=self.config.get('llm_temperature', 0.7),
            max_tokens=self.config.get('llm_max_tokens', 1000),
            timeout=self.config.get('llm_timeout', 30),
            retry_attempts=self.config.get('llm_retry_attempts', 3)
        )
        #print(f'Qa_Service 配置 llm_config : {self.llm_config}')
        
        # 初始化LLM实例
        self.llm: Optional[BaseLLM] = None
        self.fallback_llm: Optional[BaseLLM] = None
        
        # 备用LLM配置（用于错误恢复）
        self.fallback_config = self._create_fallback_config()
        
        # QA配置
        self.max_context_length = self.config.get('max_context_length', 4000)
        self.include_sources = self.config.get('include_sources', True)
        self.no_answer_threshold = self.config.get('no_answer_threshold', 0.5)
        self.enable_fallback = self.config.get('enable_llm_fallback', True)
    
    def _create_fallback_config(self) -> Optional[LLMConfig]:
        """创建备用LLM配置"""
        try:
            # 如果主要配置不是mock，则使用mock作为备用
            if self.llm_config.provider != 'mock':
                return LLMConfig(
                    provider='mock',
                    model='mock-model',
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    timeout=10,
                    retry_attempts=1
                )
            return None
        except Exception as e:
            logger.warning(f"创建备用LLM配置失败: {str(e)}")
            return None
    
    async def _create_llm_instance(self, config: LLMConfig) -> Optional[BaseLLM]:
        """创建LLM实例"""
        try:
            llm = LLMFactory.create_llm(config)
            await llm.initialize()
            logger.info(f"LLM实例创建成功: {config.provider} - {config.model}")
            return llm
        except Exception as e:
            logger.error(f"LLM实例创建失败: {config.provider} - {str(e)}")
            return None
    
    async def _switch_to_fallback_llm(self) -> bool:
        """切换到备用LLM"""
        if not self.enable_fallback or not self.fallback_config:
            return False
        
        try:
            if not self.fallback_llm:
                self.fallback_llm = await self._create_llm_instance(self.fallback_config)
            
            if self.fallback_llm:
                logger.warning(f"切换到备用LLM: {self.fallback_config.provider}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"切换到备用LLM失败: {str(e)}")
            return False
    
    def _format_llm_response(self, response: Any, provider: str) -> str:
        """统一格式化LLM响应"""
        try:
            if hasattr(response, 'content'):
                # 新的LLMResponse格式
                content = response.content
            elif isinstance(response, dict):
                # 字典格式响应
                content = response.get('answer', response.get('content', str(response)))
            elif isinstance(response, str):
                # 字符串响应
                content = response
            else:
                # 其他格式
                content = str(response)
            
            # 后处理
            content = self._post_process_answer(content)
            
            # 添加提供商信息（调试模式）
            if self.config.get('debug', False):
                content += f"\n\n[Generated by: {provider}]"
            
            return content
            
        except Exception as e:
            logger.error(f"格式化LLM响应失败: {str(e)}")
            return "抱歉，响应格式化时出现错误。"
    
    async def initialize(self) -> None:
        """初始化QA服务"""
        try:
            logger.info("初始化问答服务")
            
            # 初始化检索服务
            await self.retrieval_service.initialize()
            
            # 初始化主要LLM
            self.llm = await self._create_llm_instance(self.llm_config)
            if not self.llm:
                raise ProcessingError(f"无法创建主要LLM实例: {self.llm_config.provider}")
            
            # 初始化备用LLM（如果启用）
            if self.enable_fallback and self.fallback_config:
                self.fallback_llm = await self._create_llm_instance(self.fallback_config)
                if self.fallback_llm:
                    logger.info(f"备用LLM初始化成功: {self.fallback_config.provider}")
                else:
                    logger.warning("备用LLM初始化失败，将禁用降级功能")
            
            logger.info("问答服务初始化成功")
            
        except Exception as e:
            logger.error(f"问答服务初始化失败: {str(e)}")
            raise ProcessingError(f"问答服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.llm:
                await self.llm.cleanup()
                self.llm = None
            
            if self.fallback_llm:
                await self.fallback_llm.cleanup()
                self.fallback_llm = None
            
            if self.retrieval_service:
                await self.retrieval_service.cleanup()
            
            logger.info("问答服务资源清理完成")
            
        except Exception as e:
            logger.error(f"问答服务清理失败: {str(e)}")
    
    async def answer_question(
        self, 
        question: str, 
        session_id: Optional[str] = None,
        **kwargs
    ) -> QAResponse:
        """回答问题"""
        try:
            logger.info(f"开始处理问题: {question[:100]}...")
            
            if not question or not question.strip():
                raise QAError("问题不能为空")
            
            start_time = datetime.now()
            
            print(f'问题：{question}')
            # 1. 检索相关上下文
            context_results = await self.retrieve_context(question, **kwargs)

            print(f'检索到的内容：{context_results}')
            
            # 2. 检查是否找到相关内容
            if not context_results or all(r.similarity_score < self.no_answer_threshold for r in context_results):
                return self._create_no_answer_response(question, session_id)
            
            # 3. 生成答案
            answer = await self.generate_answer(question, context_results, **kwargs)
            
            # 4. 创建源信息
            sources = self._create_source_info(context_results) if self.include_sources else []
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            response = QAResponse(
                question=question,
                answer=answer,
                sources=sources,
                processing_time=processing_time,
                confidence_score=self._calculate_confidence(context_results)
            )
            
            logger.info(f"问题处理完成，耗时: {processing_time:.2f}秒")
            return response
            
        except QAError:
            raise
        except Exception as e:
            logger.error(f"问题处理失败: {str(e)}")
            raise QAError(f"问题处理失败: {str(e)}")
    
    async def retrieve_context(
        self, 
        question: str, 
        top_k: Optional[int] = None,
        document_ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """检索相关上下文"""
        try:
            logger.debug(f"检索问题相关上下文: {question[:50]}...")
            print(f"检索问题相关上下文: {question[:50]}...")
            # 使用增强检索服务进行配置化搜索
            # 创建当前查询的检索配置
            current_config = RetrievalConfig(
                top_k=top_k or self.retrieval_config.top_k,
                similarity_threshold=self.retrieval_config.similarity_threshold,
                search_mode=self.retrieval_config.search_mode,
                enable_rerank=self.retrieval_config.enable_rerank,
                enable_cache=self.retrieval_config.enable_cache
            )
            
            # 使用配置化检索
            results = await self.retrieval_service.search_with_config(
                query=question,
                config=current_config,
                document_ids=document_ids
            )
            
            logger.debug(f"检索到 {len(results)} 个相关结果")
            return results
            
        except Exception as e:
            logger.error(f"上下文检索失败: {str(e)}")
            raise QAError(f"上下文检索失败: {str(e)}")
    
    async def generate_answer(
        self, 
        question: str, 
        context: List[SearchResult],
        **kwargs
    ) -> str:
        """生成答案"""
        try:
            logger.debug(f"基于 {len(context)} 个上下文生成答案")
            
            if not context:
                return "抱歉，我没有找到与您的问题相关的信息。"
            
            # 构建提示词
            prompt = self._build_prompt(question, context)
            
            # 尝试使用主要LLM生成答案
            answer = await self._generate_with_error_handling(
                prompt=prompt,
                question=question,
                context=context,
                **kwargs
            )
            
            logger.debug(f"答案生成完成，长度: {len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"答案生成失败: {str(e)}")
            raise QAError(f"答案生成失败: {str(e)}")
    
    async def _generate_with_error_handling(
        self,
        prompt: str,
        question: str,
        context: List[SearchResult],
        **kwargs
    ) -> str:
        """带错误处理的答案生成"""
        # 尝试主要LLM
        if self.llm:
            try:
                response = await self.llm.generate_text(
                    prompt=prompt,
                    temperature=kwargs.get('temperature'),
                    max_tokens=kwargs.get('max_tokens')
                )
                return self._format_llm_response(response, self.llm_config.provider)
                
            except (ModelConnectionError, ModelResponseError) as e:
                logger.warning(f"主要LLM调用失败: {str(e)}")
                
                # 尝试切换到备用LLM
                if await self._switch_to_fallback_llm():
                    try:
                        response = await self.fallback_llm.generate_text(
                            prompt=prompt,
                            temperature=kwargs.get('temperature', 0.7),
                            max_tokens=kwargs.get('max_tokens', 1000)
                        )
                        return self._format_llm_response(response, self.fallback_config.provider)
                    except Exception as fallback_error:
                        logger.error(f"备用LLM也失败: {str(fallback_error)}")
                
                # 如果备用LLM也失败，返回基于上下文的简单回答
                return self._generate_fallback_answer(question, context)
                
            except Exception as e:
                logger.error(f"LLM调用出现未预期错误: {str(e)}")
                
                # 尝试备用LLM
                if await self._switch_to_fallback_llm():
                    try:
                        response = await self.fallback_llm.generate_text(prompt=prompt, **kwargs)
                        return self._format_llm_response(response, self.fallback_config.provider)
                    except Exception:
                        pass
                
                # 最后的降级方案
                return self._generate_fallback_answer(question, context)
        
        # 如果没有可用的LLM
        return self._generate_fallback_answer(question, context)
    
    def _generate_fallback_answer(self, question: str, context: List[SearchResult]) -> str:
        """生成降级答案（基于上下文的简单回答）"""
        try:
            if not context:
                return "抱歉，我没有找到与您的问题相关的信息，且当前LLM服务不可用。"
            
            # 选择最相关的上下文
            best_context = max(context, key=lambda x: x.similarity_score)
            
            # 生成简单的基于上下文的回答
            answer = f"根据文档内容，我找到了以下相关信息：\n\n{best_context.content[:500]}"
            
            if len(best_context.content) > 500:
                answer += "...\n\n[注意：当前LLM服务不可用，以上为相关文档片段]"
            else:
                answer += "\n\n[注意：当前LLM服务不可用，以上为相关文档内容]"
            
            return answer
            
        except Exception as e:
            logger.error(f"生成降级答案失败: {str(e)}")
            return "抱歉，当前服务不可用，无法处理您的问题。请稍后重试。"
    
    async def switch_llm_provider(self, new_config: LLMConfig) -> bool:
        """动态切换LLM提供商"""
        try:
            logger.info(f"尝试切换LLM提供商: {self.llm_config.provider} -> {new_config.provider}")
            
            # 创建新的LLM实例
            new_llm = await self._create_llm_instance(new_config)
            if not new_llm:
                logger.error(f"无法创建新的LLM实例: {new_config.provider}")
                return False
            
            # 清理旧的LLM实例
            if self.llm:
                await self.llm.cleanup()
            
            # 更新配置和实例
            self.llm_config = new_config
            self.llm = new_llm
            
            logger.info(f"LLM提供商切换成功: {new_config.provider} - {new_config.model}")
            return True
            
        except Exception as e:
            logger.error(f"LLM提供商切换失败: {str(e)}")
            return False
    
    async def test_llm_connection(self, config: Optional[LLMConfig] = None) -> Dict[str, Any]:
        """测试LLM连接"""
        test_config = config or self.llm_config
        
        try:
            # 创建临时LLM实例进行测试
            test_llm = await self._create_llm_instance(test_config)
            if not test_llm:
                return {
                    "success": False,
                    "provider": test_config.provider,
                    "model": test_config.model,
                    "error": "无法创建LLM实例"
                }
            
            # 执行健康检查
            health_check = test_llm.health_check()
            
            # 清理测试实例
            await test_llm.cleanup()
            
            return {
                "success": health_check,
                "provider": test_config.provider,
                "model": test_config.model,
                "status": "healthy" if health_check else "unhealthy"
            }
            
        except Exception as e:
            return {
                "success": False,
                "provider": test_config.provider,
                "model": test_config.model,
                "error": str(e)
            }
    
    def _build_prompt(self, question: str, context: List[SearchResult]) -> str:
        """构建提示词"""
        # 准备上下文文本
        context_texts = []
        total_length = 0
        
        for i, result in enumerate(context):
            context_text = f"文档片段 {i+1}:\n{result.content}\n"
            
            # 检查长度限制
            if total_length + len(context_text) > self.max_context_length:
                break
            
            context_texts.append(context_text)
            total_length += len(context_text)
        
        context_str = "\n".join(context_texts)
        
        # 构建完整提示词
        prompt = f"""请基于以下文档内容回答用户的问题。如果文档中没有相关信息，请明确说明。

文档内容:
{context_str}

用户问题: {question}

请提供准确、有用的回答，并尽可能引用文档中的具体信息。如果需要，可以进行合理的推理和总结。

回答:"""
        
        return prompt
    
    def _post_process_answer(self, answer: str) -> str:
        """后处理答案"""
        # 去除多余的空白字符
        answer = answer.strip()
        
        # 移除可能的提示词残留
        if answer.startswith("回答:"):
            answer = answer[3:].strip()
        
        # 确保答案不为空
        if not answer:
            answer = "抱歉，我无法基于当前信息提供满意的答案。"
        
        return answer
    
    def _create_source_info(self, context: List[SearchResult]) -> List[SourceInfo]:
        """创建源信息"""
        sources = []
        
        for result in context:
            # 从metadata中获取文档名称和块索引
            document_name = result.metadata.get('document_name', f'Document_{result.document_id[:8]}')
            chunk_index = result.metadata.get('chunk_index', 0)
            
            source = SourceInfo(
                document_id=result.document_id,
                document_name=document_name,
                chunk_id=result.chunk_id,
                chunk_content=result.content[:200] + "..." if len(result.content) > 200 else result.content,
                chunk_index=chunk_index,
                similarity_score=result.similarity_score,
                metadata=result.metadata
            )
            sources.append(source)
        
        return sources
    
    def _calculate_confidence(self, context: List[SearchResult]) -> float:
        """计算置信度分数"""
        if not context:
            return 0.0
        
        # 基于最高相似度和结果数量计算置信度
        max_similarity = max(r.similarity_score for r in context)
        avg_similarity = sum(r.similarity_score for r in context) / len(context)
        
        # 结合最高相似度和平均相似度
        confidence = (max_similarity * 0.7 + avg_similarity * 0.3)
        
        # 根据结果数量调整
        if len(context) >= 3:
            confidence *= 1.1  # 多个相关结果增加置信度
        elif len(context) == 1:
            confidence *= 0.9  # 单个结果降低置信度
        
        return min(confidence, 1.0)
    
    def _create_no_answer_response(self, question: str, session_id: Optional[str]) -> QAResponse:
        """创建无答案响应"""
        return QAResponse(
            question=question,
            answer="抱歉，我在当前的知识库中没有找到与您的问题相关的信息。建议您：\n1. 检查问题的表述是否准确\n2. 尝试使用不同的关键词\n3. 上传更多相关的文档来丰富知识库",
            sources=[],
            processing_time=0.0,
            confidence_score=0.0
        )
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            retrieval_stats = await self.retrieval_service.get_service_stats()
            
            # 主要LLM信息
            main_llm_info = {
                "provider": self.llm_config.provider,
                "model": self.llm_config.model,
                "status": "available" if self.llm else "unavailable"
            }
            
            # 备用LLM信息
            fallback_llm_info = None
            if self.fallback_config:
                fallback_llm_info = {
                    "provider": self.fallback_config.provider,
                    "model": self.fallback_config.model,
                    "status": "available" if self.fallback_llm else "unavailable",
                    "enabled": self.enable_fallback
                }
            
            stats = {
                "service_name": "QAService",
                "main_llm": main_llm_info,
                "fallback_llm": fallback_llm_info,
                "max_context_length": self.max_context_length,
                "similarity_threshold": self.retrieval_service.similarity_threshold,
                "retrieval_top_k": self.retrieval_service.default_top_k,
                "vector_count": retrieval_stats.get("vector_count", 0),
                "document_count": retrieval_stats.get("document_count", 0),
                "available_llm_providers": LLMFactory.get_available_providers(),
                "fallback_enabled": self.enable_fallback
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取QA服务统计失败: {str(e)}")
            return {"error": str(e)}
    
    async def test_qa(self, test_question: str = "测试问题") -> Dict[str, Any]:
        """测试问答功能"""
        try:
            start_time = datetime.now()
            
            # 执行问答
            response = await self.answer_question(test_question)
            
            end_time = datetime.now()
            test_time = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "test_question": test_question,
                "answer_length": len(response.answer),
                "source_count": len(response.sources),
                "confidence_score": response.confidence_score,
                "processing_time": response.processing_time,
                "test_time": test_time,
                "service_stats": await self.get_service_stats()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_question": test_question
            }
    
    async def update_retrieval_config(self, config: RetrievalConfig) -> None:
        """更新检索配置
        
        Args:
            config: 新的检索配置
        """
        try:
            logger.info(f"更新QA服务检索配置: {config}")
            
            # 验证配置
            errors = config.validate()
            if errors:
                raise QAError(f"检索配置验证失败: {', '.join(errors)}")
            
            # 更新检索服务的默认配置
            await self.retrieval_service.update_default_config(config)
            
            # 更新本地配置
            self.retrieval_config = config
            
            logger.info("QA服务检索配置更新成功")
            
        except Exception as e:
            logger.error(f"更新检索配置失败: {str(e)}")
            raise QAError(f"更新检索配置失败: {str(e)}")
    
    def get_retrieval_config(self) -> RetrievalConfig:
        """获取当前检索配置
        
        Returns:
            当前检索配置
        """
        return self.retrieval_config
    
    async def reload_config_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """从配置字典重新加载配置
        
        Args:
            config_dict: 配置字典
        """
        try:
            logger.info("从配置字典重新加载QA服务配置")
            
            # 更新检索配置
            if 'retrieval' in config_dict:
                retrieval_config_dict = config_dict['retrieval']
                new_retrieval_config = RetrievalConfig.from_dict(retrieval_config_dict)
                await self.update_retrieval_config(new_retrieval_config)
            
            # 更新LLM配置
            if 'llm' in config_dict:
                llm_config_dict = config_dict['llm']
                new_llm_config = LLMConfig(
                    provider=llm_config_dict.get('provider', self.llm_config.provider),
                    model=llm_config_dict.get('model', self.llm_config.model),
                    api_key=llm_config_dict.get('api_key', self.llm_config.api_key),
                    base_url=llm_config_dict.get('base_url', self.llm_config.base_url),
                    temperature=llm_config_dict.get('temperature', self.llm_config.temperature),
                    max_tokens=llm_config_dict.get('max_tokens', self.llm_config.max_tokens),
                    timeout=llm_config_dict.get('timeout', self.llm_config.timeout),
                    retry_attempts=llm_config_dict.get('retry_attempts', self.llm_config.retry_attempts)
                )
                
                # 如果LLM配置有变化，切换LLM提供商
                if (new_llm_config.provider != self.llm_config.provider or 
                    new_llm_config.model != self.llm_config.model):
                    await self.switch_llm_provider(new_llm_config)
            
            # 更新其他QA配置
            if 'max_context_length' in config_dict:
                self.max_context_length = config_dict['max_context_length']
            if 'include_sources' in config_dict:
                self.include_sources = config_dict['include_sources']
            if 'no_answer_threshold' in config_dict:
                self.no_answer_threshold = config_dict['no_answer_threshold']
            if 'enable_llm_fallback' in config_dict:
                self.enable_fallback = config_dict['enable_llm_fallback']
            
            logger.info("QA服务配置重新加载成功")
            
        except Exception as e:
            logger.error(f"重新加载配置失败: {str(e)}")
            raise QAError(f"重新加载配置失败: {str(e)}")
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息
        
        Returns:
            搜索统计信息
        """
        try:
            return self.retrieval_service.get_search_statistics()
        except Exception as e:
            logger.error(f"获取搜索统计失败: {str(e)}")
            return {'error': str(e)}
    
    def reset_search_statistics(self) -> None:
        """重置搜索统计信息"""
        try:
            self.retrieval_service.reset_statistics()
            logger.info("搜索统计信息已重置")
        except Exception as e:
            logger.error(f"重置搜索统计失败: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            健康状态信息
        """
        try:
            # 检查检索服务健康状态
            retrieval_health = await self.retrieval_service.health_check()
            
            # 检查LLM健康状态
            llm_health = True
            if self.llm:
                llm_health = self.llm.health_check()
            
            # 综合健康状态
            overall_health = (
                retrieval_health.get('status') == 'healthy' and
                llm_health
            )
            
            return {
                'status': 'healthy' if overall_health else 'unhealthy',
                'components': {
                    'retrieval_service': retrieval_health,
                    'llm_service': 'healthy' if llm_health else 'unhealthy',
                    'fallback_llm': 'available' if self.fallback_llm else 'unavailable'
                },
                'config': {
                    'retrieval_config': self.retrieval_config.to_dict(),
                    'llm_config': {
                        'provider': self.llm_config.provider,
                        'model': self.llm_config.model
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }