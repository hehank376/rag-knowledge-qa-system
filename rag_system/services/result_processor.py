"""
问答结果处理服务
负责答案格式化、源文档信息整理和结果展示
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from ..models.qa import QAResponse, SourceInfo, QAStatus
from ..models.vector import SearchResult
from ..utils.exceptions import ProcessingError
from .base import BaseService

logger = logging.getLogger(__name__)


class ResultProcessor(BaseService):
    """问答结果处理服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # 格式化配置
        self.max_answer_length = self.config.get('max_answer_length', 2000)
        self.max_source_content_length = self.config.get('max_source_content_length', 200)
        self.show_confidence_score = self.config.get('show_confidence_score', True)
        self.show_processing_time = self.config.get('show_processing_time', True)
        self.highlight_keywords = self.config.get('highlight_keywords', True)
        
        # 源文档配置
        self.max_sources_display = self.config.get('max_sources_display', 5)
        self.sort_sources_by_relevance = self.config.get('sort_sources_by_relevance', True)
        self.group_sources_by_document = self.config.get('group_sources_by_document', False)
        
        # 无答案处理配置
        self.no_answer_suggestions = self.config.get('no_answer_suggestions', [
            "检查问题的表述是否准确",
            "尝试使用不同的关键词",
            "上传更多相关的文档来丰富知识库",
            "确认问题是否在知识库的覆盖范围内"
        ])
    
    async def initialize(self) -> None:
        """初始化结果处理服务"""
        logger.info("初始化问答结果处理服务")
        # 结果处理服务通常不需要特殊的初始化
        logger.info("问答结果处理服务初始化成功")
    
    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("问答结果处理服务资源清理完成")
    
    def format_answer(self, answer: str, question: str = "") -> str:
        """格式化答案文本
        
        Args:
            answer: 原始答案
            question: 原始问题（用于关键词高亮）
            
        Returns:
            格式化后的答案
        """
        try:
            logger.debug(f"格式化答案，长度: {len(answer)}")
            
            if not answer or not answer.strip():
                return "抱歉，我无法为您的问题提供答案。"
            
            # 清理答案文本
            formatted_answer = self._clean_answer_text(answer)
            
            # 截断过长的答案
            if len(formatted_answer) > self.max_answer_length:
                # 在单词边界截断，避免截断中文字符
                truncated = formatted_answer[:self.max_answer_length-3]
                if ' ' in truncated:
                    truncated = truncated.rsplit(' ', 1)[0]
                formatted_answer = truncated + "..."
                logger.debug(f"答案被截断到 {len(formatted_answer)} 字符")
            
            # 关键词高亮（如果启用）
            if self.highlight_keywords and question:
                formatted_answer = self._highlight_keywords(formatted_answer, question)
            
            # 格式化段落
            formatted_answer = self._format_paragraphs(formatted_answer)
            
            logger.debug("答案格式化完成")
            return formatted_answer
            
        except Exception as e:
            logger.error(f"答案格式化失败: {str(e)}")
            return answer  # 返回原始答案作为降级处理
    
    def process_sources(self, sources: List[SourceInfo]) -> List[SourceInfo]:
        """处理和整理源文档信息
        
        Args:
            sources: 原始源信息列表
            
        Returns:
            处理后的源信息列表
        """
        try:
            logger.debug(f"处理 {len(sources)} 个源文档")
            
            if not sources:
                return []
            
            # 复制源列表以避免修改原始数据
            processed_sources = []
            
            for source in sources:
                processed_source = self._process_single_source(source)
                if processed_source:
                    processed_sources.append(processed_source)
            
            # 按相关性排序
            if self.sort_sources_by_relevance:
                processed_sources.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # 限制显示数量
            if len(processed_sources) > self.max_sources_display:
                processed_sources = processed_sources[:self.max_sources_display]
                logger.debug(f"源文档数量限制为 {self.max_sources_display} 个")
            
            # 按文档分组（如果启用）
            if self.group_sources_by_document:
                processed_sources = self._group_sources_by_document(processed_sources)
            
            logger.debug(f"源文档处理完成，最终数量: {len(processed_sources)}")
            return processed_sources
            
        except Exception as e:
            logger.error(f"源文档处理失败: {str(e)}")
            return sources  # 返回原始源列表作为降级处理
    
    def create_no_answer_response(
        self, 
        question: str, 
        reason: str = "no_relevant_content"
    ) -> Dict[str, Any]:
        """创建无答案响应
        
        Args:
            question: 原始问题
            reason: 无答案的原因
            
        Returns:
            格式化的无答案响应
        """
        try:
            logger.debug(f"创建无答案响应，原因: {reason}")
            
            # 根据不同原因生成不同的回复
            if reason == "no_relevant_content":
                answer = "抱歉，我在当前的知识库中没有找到与您的问题相关的信息。"
            elif reason == "low_confidence":
                answer = "抱歉，我对这个问题的答案不够确信，无法为您提供可靠的回答。"
            elif reason == "processing_error":
                answer = "抱歉，在处理您的问题时遇到了技术问题，请稍后重试。"
            else:
                answer = "抱歉，我无法回答您的问题。"
            
            # 添加建议
            suggestions = self._generate_suggestions(question, reason)
            if suggestions:
                answer += "\n\n建议您：\n" + "\n".join(f"{i+1}. {suggestion}" for i, suggestion in enumerate(suggestions))
            
            response = {
                "answer": answer,
                "reason": reason,
                "suggestions": suggestions,
                "has_answer": False,
                "confidence_score": 0.0
            }
            
            logger.debug("无答案响应创建完成")
            return response
            
        except Exception as e:
            logger.error(f"创建无答案响应失败: {str(e)}")
            return {
                "answer": "抱歉，系统遇到了问题，无法处理您的请求。",
                "reason": "system_error",
                "suggestions": [],
                "has_answer": False,
                "confidence_score": 0.0
            }
    
    def format_qa_response(self, response: QAResponse) -> Dict[str, Any]:
        """格式化完整的问答响应
        
        Args:
            response: QA响应对象
            
        Returns:
            格式化的响应字典
        """
        try:
            logger.debug(f"格式化问答响应: {response.id}")
            
            # 格式化答案
            formatted_answer = self.format_answer(response.answer, response.question)
            
            # 处理源文档
            processed_sources = self.process_sources(response.sources)
            
            # 构建格式化响应
            formatted_response = {
                "id": response.id,
                "question": response.question,
                "answer": formatted_answer,
                "sources": [self._source_to_dict(source) for source in processed_sources],
                "has_sources": len(processed_sources) > 0,
                "source_count": len(processed_sources),
                "confidence_score": response.confidence_score if self.show_confidence_score else None,
                "processing_time": response.processing_time if self.show_processing_time else None,
                "status": response.status.value,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "original_source_count": len(response.sources),
                    "answer_length": len(formatted_answer),
                    "has_answer": bool(formatted_answer and formatted_answer.strip())
                }
            }
            
            # 添加错误信息（如果有）
            if response.error_message:
                formatted_response["error_message"] = response.error_message
            
            logger.debug("问答响应格式化完成")
            return formatted_response
            
        except Exception as e:
            logger.error(f"问答响应格式化失败: {str(e)}")
            # 返回基本的降级响应
            return {
                "id": response.id,
                "question": response.question,
                "answer": response.answer,
                "sources": [],
                "has_sources": False,
                "source_count": 0,
                "confidence_score": response.confidence_score,
                "processing_time": response.processing_time,
                "status": response.status.value,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _clean_answer_text(self, answer: str) -> str:
        """清理答案文本"""
        # 移除多余的空白字符
        answer = re.sub(r'\s+', ' ', answer.strip())
        
        # 移除可能的提示词残留
        prefixes_to_remove = [
            "回答:", "答案:", "Answer:", "根据文档内容,", "基于提供的信息,"
        ]
        
        for prefix in prefixes_to_remove:
            if answer.startswith(prefix):
                answer = answer[len(prefix):].strip()
        
        return answer
    
    def _highlight_keywords(self, answer: str, question: str) -> str:
        """在答案中高亮关键词"""
        try:
            # 提取问题中的关键词
            keywords = self._extract_keywords_from_question(question)
            
            # 在答案中高亮这些关键词
            for keyword in keywords:
                if len(keyword) > 2:  # 只高亮长度大于2的关键词
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    answer = pattern.sub(f"**{keyword}**", answer)
            
            return answer
            
        except Exception as e:
            logger.debug(f"关键词高亮失败: {str(e)}")
            return answer
    
    def _extract_keywords_from_question(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        # 对中文和英文分别处理
        # 中文词汇提取
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', question)
        # 英文词汇提取
        english_words = re.findall(r'\b[a-zA-Z]+\b', question.lower())
        
        # 合并所有词汇
        all_words = chinese_words + english_words
        
        # 过滤停用词
        stop_words = {
            '什么', '如何', '为什么', '怎么', '哪里', '什么时候', '谁', '哪个',
            '是', '的', '了', '在', '有', '和', '就', '不', '人', '都', '一',
            'what', 'how', 'why', 'where', 'when', 'who', 'which', 'is', 'are',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'
        }
        
        keywords = [word for word in all_words if word not in stop_words and len(word) > 1]
        return keywords[:5]  # 限制关键词数量
    
    def _format_paragraphs(self, answer: str) -> str:
        """格式化段落"""
        # 确保句子之间有适当的间距
        answer = re.sub(r'([.!?])([A-Z\u4e00-\u9fff])', r'\1 \2', answer)
        
        # 处理列表格式
        answer = re.sub(r'(\d+\.)([^\s])', r'\n\1 \2', answer)
        
        return answer.strip()
    
    def _process_single_source(self, source: SourceInfo) -> Optional[SourceInfo]:
        """处理单个源文档"""
        try:
            # 截断内容长度
            content = source.chunk_content
            if len(content) > self.max_source_content_length:
                # 在单词边界截断，避免截断中文字符
                truncated = content[:self.max_source_content_length-3]
                if ' ' in truncated:
                    truncated = truncated.rsplit(' ', 1)[0]
                content = truncated + "..."
            
            # 创建处理后的源信息
            processed_source = SourceInfo(
                document_id=source.document_id,
                document_name=source.document_name,
                chunk_id=source.chunk_id,
                chunk_content=content,
                chunk_index=source.chunk_index,
                similarity_score=round(source.similarity_score, 3),
                metadata=source.metadata
            )
            
            return processed_source
            
        except Exception as e:
            logger.debug(f"处理单个源文档失败: {str(e)}")
            return source
    
    def _group_sources_by_document(self, sources: List[SourceInfo]) -> List[SourceInfo]:
        """按文档分组源信息"""
        # 按文档ID分组
        document_groups = {}
        for source in sources:
            doc_id = source.document_id
            if doc_id not in document_groups:
                document_groups[doc_id] = []
            document_groups[doc_id].append(source)
        
        # 每个文档只保留最相关的源
        grouped_sources = []
        for doc_id, doc_sources in document_groups.items():
            # 按相似度排序，取最高的
            doc_sources.sort(key=lambda x: x.similarity_score, reverse=True)
            grouped_sources.append(doc_sources[0])
        
        # 按相似度重新排序
        grouped_sources.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return grouped_sources
    
    def _generate_suggestions(self, question: str, reason: str) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if reason == "no_relevant_content":
            suggestions.extend(self.no_answer_suggestions)
        elif reason == "low_confidence":
            suggestions.extend([
                "尝试提供更具体的问题描述",
                "检查问题中的关键词是否准确",
                "考虑从不同角度重新表述问题"
            ])
        elif reason == "processing_error":
            suggestions.extend([
                "稍后重试您的问题",
                "检查网络连接是否正常",
                "联系系统管理员获取帮助"
            ])
        
        return suggestions[:4]  # 限制建议数量
    
    def _source_to_dict(self, source: SourceInfo) -> Dict[str, Any]:
        """将源信息转换为字典"""
        return {
            "document_id": source.document_id,
            "document_name": source.document_name,
            "chunk_id": source.chunk_id,
            "content": source.chunk_content,
            "chunk_index": source.chunk_index,
            "similarity_score": source.similarity_score,
            "metadata": source.metadata
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "service_name": "ResultProcessor",
            "max_answer_length": self.max_answer_length,
            "max_source_content_length": self.max_source_content_length,
            "max_sources_display": self.max_sources_display,
            "show_confidence_score": self.show_confidence_score,
            "show_processing_time": self.show_processing_time,
            "highlight_keywords": self.highlight_keywords,
            "sort_sources_by_relevance": self.sort_sources_by_relevance,
            "group_sources_by_document": self.group_sources_by_document
        }