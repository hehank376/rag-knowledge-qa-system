"""
文档处理服务实现
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid
from datetime import datetime

from ..models.document import TextChunk
from ..models.vector import Vector
from ..document_processing.extractors import TextExtractorFactory
from ..document_processing.splitters import RecursiveTextSplitter, SplitConfig
from ..document_processing.preprocessors import TextPreprocessor, PreprocessConfig
from .embedding_service import EmbeddingService
from ..utils.exceptions import DocumentError, ProcessingError
from .base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """文档处理结果"""
    success: bool
    chunks: List[TextChunk]
    vectors: List[Vector]
    error_message: str = ""
    processing_time: float = 0.0
    chunk_count: int = 0


class DocumentProcessor(BaseService):
    """文档处理器实现"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        #print(f'Document_Processor 配置 CONFIG : {config}')
        self.extractor_factory = TextExtractorFactory()
        
        # 初始化嵌入服务
        embedding_config = {
            'provider': self.config.get('embedding_provider', 'mock'),
            'model': self.config.get('embedding_model', 'text-embedding-ada-002'),
            'api_key': self.config.get('embedding_api_key'),
            'api_base': self.config.get('embedding_api_base'),
            'batch_size': self.config.get('embedding_batch_size', 100),
            'dimensions': self.config.get('embedding_dimensions'),
            'timeout': self.config.get('embedding_timeout', 30)
        }
        #print(f'Document_Processor 嵌入式模型配置 Config ：{embedding_config}')
        self.embedding_service = EmbeddingService(embedding_config)
        
        # 初始化分割器配置
        split_config = SplitConfig(
            chunk_size=self.config.get('chunk_size', 1000),
            chunk_overlap=self.config.get('chunk_overlap', 200),
            min_chunk_size=self.config.get('min_chunk_size', 10),  # 降低最小块大小
            max_chunk_size=self.config.get('max_chunk_size', 2000),
            preserve_structure=self.config.get('preserve_structure', True),
            generate_summary=self.config.get('generate_summary', False),
            generate_questions=self.config.get('generate_questions', False),
            semantic_split=self.config.get('semantic_split', False)
        )
        self.text_splitter = RecursiveTextSplitter(split_config)
        
        # 初始化预处理器配置
        preprocess_config = PreprocessConfig(
            remove_extra_whitespace=self.config.get('remove_extra_whitespace', True),
            remove_special_chars=self.config.get('remove_special_chars', False),
            normalize_unicode=self.config.get('normalize_unicode', True),
            remove_urls=self.config.get('remove_urls', True),
            remove_emails=self.config.get('remove_emails', True),
            remove_phone_numbers=self.config.get('remove_phone_numbers', False),
            convert_to_lowercase=self.config.get('convert_to_lowercase', False),
            remove_stopwords=self.config.get('remove_stopwords', False),
            language=self.config.get('language', 'zh'),
            custom_patterns=self.config.get('custom_patterns', None)
        )
        self.text_preprocessor = TextPreprocessor(preprocess_config)
        
        # 保持向后兼容
        self._chunk_size = split_config.chunk_size
        self._chunk_overlap = split_config.chunk_overlap
    
    async def initialize(self) -> None:
        """初始化文档处理器"""
        # 初始化嵌入服务
        await self.embedding_service.initialize()
        logger.info("文档处理器初始化完成")
    
    async def cleanup(self) -> None:
        """清理资源"""
        # 清理嵌入服务
        await self.embedding_service.cleanup()
        logger.info("文档处理器资源清理完成")
    
    def extract_text(self, file_path: str) -> str:
        """提取文本内容"""
        try:
            logger.info(f"开始提取文档文本: {file_path}")
            
            # 验证文件存在
            path = Path(file_path)
            if not path.exists():
                raise DocumentError(f"文件不存在: {file_path}")
            
            # 检查文件格式支持
            if not self.extractor_factory.is_supported(file_path):
                file_type = self.extractor_factory.detect_file_type(file_path)
                supported_formats = self.extractor_factory.get_supported_formats()
                raise DocumentError(
                    f"不支持的文件格式: {file_type}. "
                    f"支持的格式: {', '.join(supported_formats)}"
                )
            
            # 提取文本
            text_content = self.extractor_factory.extract_text(file_path)
            
            if not text_content or not text_content.strip():
                raise DocumentError("文档中没有可提取的文本内容")
            
            logger.info(f"成功提取文档文本: {file_path}, 长度: {len(text_content)}")
            return text_content.strip()
            
        except DocumentError:
            raise
        except Exception as e:
            logger.error(f"提取文档文本失败: {file_path}, 错误: {str(e)}")
            raise DocumentError(f"提取文档文本失败: {str(e)}")
    
    def split_text(self, text: str, doc_id: str) -> List[TextChunk]:
        """分割文本为块"""
        try:
            logger.info(f"开始分割文本: 文档ID={doc_id}, 文本长度={len(text)}")
            
            if not text or not text.strip():
                raise ProcessingError("文本内容为空")
            
            # 预处理文本
            preprocessed_text = self.text_preprocessor.process(text)
            logger.debug(f"文本预处理完成: 原长度={len(text)}, 处理后长度={len(preprocessed_text)}")
            
            # 使用递归分割器分割文本
            chunks = self.text_splitter.split(preprocessed_text, doc_id)
            

            
            if not chunks:
                raise ProcessingError("文本分割后没有生成任何块")
            
            logger.info(f"文本分割完成: 文档ID={doc_id}, 生成块数={len(chunks)}")
            return chunks
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.error(f"文本分割失败: 文档ID={doc_id}, 错误: {str(e)}")
            raise ProcessingError(f"文本分割失败: {str(e)}")
    
    async def vectorize_chunks(self, chunks: List[TextChunk], document_name: str = None) -> List[Vector]:
        """向量化文本块"""
        try:
            logger.info(f"开始向量化文本块: 块数={len(chunks)}")
            print(f"开始向量化文本块: 块数={len(chunks)}")
            print(f'文本块：{chunks}')
            # 使用嵌入服务进行向量化，传递文档名称
            vectors = await self.embedding_service.vectorize_chunks(chunks, document_name)
            #print(f"向量化完成: 生成向量内容={(vectors)}")
            #print(f"向量化完成: 生成向量数={len(vectors)}")
            logger.info(f"向量化完成: 生成向量数={len(vectors)}")
            return vectors
            
        except Exception as e:
            logger.error(f"向量化失败: 错误: {str(e)}")
            raise ProcessingError(f"向量化失败: {str(e)}")
    
    async def process_document(self, file_path: str, doc_id: str, document_name: str = None) -> ProcessResult:
        """处理文档的完整流程"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始处理文档: {file_path}, 文档ID: {doc_id}")
            
            # 1. 提取文本
            text_content = self.extract_text(file_path)
            print(f'提取文本：{text_content}')
            # 2. 分割文本
            chunks = self.split_text(text_content, doc_id)
            
            # 3. 向量化，传递文档名称
            vectors = await self.vectorize_chunks(chunks, document_name)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = ProcessResult(
                success=True,
                chunks=chunks,
                vectors=vectors,
                processing_time=processing_time,
                chunk_count=len(chunks)
            )
            
            logger.info(
                f"文档处理完成: {file_path}, "
                f"块数: {len(chunks)}, "
                f"向量数: {len(vectors)}, "
                f"耗时: {processing_time:.2f}秒"
            )
            
            return result
            
        except (DocumentError, ProcessingError) as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"文档处理失败: {file_path}, 错误: {str(e)}")
            
            return ProcessResult(
                success=False,
                chunks=[],
                vectors=[],
                error_message=str(e),
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"文档处理异常: {file_path}, 错误: {str(e)}")
            
            return ProcessResult(
                success=False,
                chunks=[],
                vectors=[],
                error_message=f"处理异常: {str(e)}",
                processing_time=processing_time
            )
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return self.extractor_factory.get_supported_formats()
    
    def is_supported_file(self, file_path: str) -> bool:
        """检查文件是否支持"""
        return self.extractor_factory.is_supported(file_path)
    
    def detect_file_type(self, file_path: str) -> Optional[str]:
        """检测文件类型"""
        return self.extractor_factory.detect_file_type(file_path)
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise DocumentError(f"文件不存在: {file_path}")
            
            file_type = self.detect_file_type(file_path)
            is_supported = self.is_supported_file(file_path)
            
            return {
                "file_path": str(path.absolute()),
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "file_extension": path.suffix.lower(),
                "detected_type": file_type,
                "is_supported": is_supported,
                "supported_formats": self.get_supported_formats()
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {file_path}, 错误: {str(e)}")
            raise DocumentError(f"获取文件信息失败: {str(e)}")


# 保持向后兼容的接口
class DocumentProcessorInterface:
    """文档处理器接口（已弃用，请使用DocumentProcessor）"""
    
    def __init__(self):
        import warnings
        warnings.warn(
            "DocumentProcessorInterface已弃用，请使用DocumentProcessor",
            DeprecationWarning,
            stacklevel=2
        )