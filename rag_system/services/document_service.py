"""
文档管理服务实现
"""
import logging
import os
import uuid
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import UploadFile

from ..models.document import DocumentInfo, DocumentStatus
from ..models.config import VectorStoreConfig
from ..database.crud import DocumentCRUD
from ..database.connection import DatabaseManager
from ..models.config import DatabaseConfig
from .document_processor import DocumentProcessor
from .vector_service import VectorStoreService
from ..utils.exceptions import DocumentError, ProcessingError, VectorStoreError
from .base import BaseService

logger = logging.getLogger(__name__)


class DocumentService(BaseService):
    """文档管理服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        #print(f'Document_Service 配置 CONFIG : {config}')
        # 初始化文档处理
        processor_config = {
            'chunk_size': self.config.get('chunk_size', 1000),
            'chunk_overlap': self.config.get('chunk_overlap', 200),
            'min_chunk_size': self.config.get('min_chunk_size', 100),  # 添加min_chunk_size配置
            'max_chunk_size': self.config.get('max_chunk_size', 2000),  # 添加max_chunk_size配置
            'embedding_provider': self.config.get('embedding_provider', 'mock'),
            'embedding_model': self.config.get('embedding_model', 'text-embedding-ada-002'),
            'embedding_api_key': self.config.get('embedding_api_key'),
            'embedding_batch_size': self.config.get('embedding_batch_size', 10),  # 添加批量大小配置
            'embedding_dimensions': self.config.get('embedding_dimensions'),
        }
        #print(f'Document_Service 配置 processor_config : {processor_config}')

        self.document_processor = DocumentProcessor(processor_config)
        
        # 初始化向量存储服务
        vector_config = VectorStoreConfig(
            type=self.config.get('vector_store_type', 'chroma'),
            persist_directory=self.config.get('vector_store_path', './chroma_db'),
            collection_name=self.config.get('collection_name', 'documents')
        )
        #print(f'Document_Service 配置 vector_config : {vector_config}')
        self.vector_service = VectorStoreService(vector_config)
        
        # 初始化数据库管理器和CRUD
        db_config = DatabaseConfig(
            url=self.config.get('database_url', 'sqlite:///./database/documents.db'),
            echo=self.config.get('database_echo', False)
        )
        #print(f'Document_Service 配置 db_config : {db_config}')
        self.db_manager = DatabaseManager(db_config)
        self.document_crud = None  # 将在initialize中创建
        
        # 文档存储目录
        self.storage_dir = Path(self.config.get('storage_dir', './documents'))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """初始化文档服务"""
        try:
            logger.info("初始化文档管理服务")
            
            # 初始化数据库连接
            self.db_manager.initialize()
            
            # 创建CRUD实例
            session = self.db_manager.get_session()
            self.document_crud = DocumentCRUD(session)
            
            # 初始化文档处理器
            await self.document_processor.initialize()
            
            # 初始化向量存储服务
            await self.vector_service.initialize()
            
            logger.info("文档管理服务初始化成功")
            
        except Exception as e:
            logger.error(f"文档管理服务初始化失败: {str(e)}")
            raise ProcessingError(f"文档管理服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.vector_service:
                await self.vector_service.cleanup()
            
            if self.document_processor:
                await self.document_processor.cleanup()
            
            if self.db_manager:
                self.db_manager.close()
            
            logger.info("文档管理服务资源清理完成")
            
        except Exception as e:
            logger.error(f"文档管理服务清理失败: {str(e)}")
    
    async def upload_document(self, file: UploadFile) -> DocumentInfo:
        """上传文档"""
        doc_id = str(uuid.uuid4())
        
        try:
            logger.info(f"开始上传文档: {file.filename}, ID: {doc_id}")
            
            # 验证文件
            if not file.filename:
                raise DocumentError("文件名不能为空")
            
            # 检查文件格式支持
            if not self.document_processor.is_supported_file(file.filename):
                supported_formats = self.document_processor.get_supported_formats()
                raise DocumentError(
                    f"不支持的文件格式: {Path(file.filename).suffix}. "
                    f"支持的格式: {', '.join(supported_formats)}"
                )
            
            # 保存上传的文件
            file_path = await self._save_uploaded_file(file, doc_id)
            
            # 创建文档信息记录
            file_extension = Path(file.filename).suffix.lower()
            file_type = file_extension[1:] if file_extension.startswith('.') else file_extension
            
            doc_info = DocumentInfo(
                id=doc_id,
                filename=file.filename,
                file_type=file_type,
                file_size=file.size or 0,
                file_path=str(file_path),
                upload_time=datetime.now(),
                status=DocumentStatus.PROCESSING,
                chunk_count=0
            )
            
            # 保存到数据库
            self.document_crud.create_document(doc_info)
            
            # 异步处理文档（在后台进行）
            await self._process_document_async(doc_info)
            
            logger.info(f"文档上传成功: {file.filename}, ID: {doc_id}")
            return doc_info
            
        except Exception as e:
            logger.error(f"文档上传失败: {file.filename}, 错误: {str(e)}")
            
            # 清理已创建的文件
            try:
                if 'file_path' in locals():
                    os.remove(file_path)
            except:
                pass
            
            # 更新数据库状态
            try:
                doc_info.status = DocumentStatus.ERROR
                await self.document_crud.update_document(doc_info)
            except:
                pass
            
            raise DocumentError(f"文档上传失败: {str(e)}")
    
    async def _save_uploaded_file(self, file: UploadFile, doc_id: str) -> Path:
        """保存上传的文件"""
        try:
            # 生成文件路径
            file_extension = Path(file.filename).suffix
            filename = f"{doc_id}{file_extension}"
            file_path = self.storage_dir / filename
            
            # 保存文件
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.debug(f"文件保存成功: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise DocumentError(f"保存文件失败: {str(e)}")
    
    async def _process_document_async(self, doc_info: DocumentInfo) -> None:
        """异步处理文档"""
        try:
            logger.info(f"开始处理文档: {doc_info.filename}, ID: {doc_info.id}")
            
            # 处理文档，传递文档名称
            result = await self.document_processor.process_document(
                doc_info.file_path, 
                doc_info.id,
                doc_info.filename  # 传递真实的文档名称
            )
            
            if result.success:
                # 存储向量到向量数据库
                if result.vectors:
                    await self.vector_service.add_vectors(result.vectors)
                
                # 更新文档状态
                doc_info.status = DocumentStatus.READY
                doc_info.chunk_count = result.chunk_count
                doc_info.processing_time = result.processing_time
                
                logger.info(
                    f"文档处理成功: {doc_info.filename}, "
                    f"块数: {result.chunk_count}, "
                    f"向量数: {len(result.vectors)}"
                )
            else:
                # 处理失败
                doc_info.status = DocumentStatus.ERROR
                doc_info.error_message = result.error_message
                
                logger.error(f"文档处理失败: {doc_info.filename}, 错误: {result.error_message}")
            
            # 更新数据库
            from ..database.models import DocumentStatus as DBDocumentStatus
            
            if doc_info.status == DocumentStatus.READY:
                self.document_crud.update_document_status(doc_info.id, DBDocumentStatus.READY)
                self.document_crud.update_document_chunk_count(doc_info.id, doc_info.chunk_count)
            else:
                self.document_crud.update_document_status(
                    doc_info.id, 
                    DBDocumentStatus.ERROR, 
                    doc_info.error_message
                )
            
        except Exception as e:
            logger.error(f"文档处理异常: {doc_info.filename}, 错误: {str(e)}")
            
            # 更新错误状态
            try:
                from ..database.models import DocumentStatus as DBDocumentStatus
                self.document_crud.update_document_status(
                    doc_info.id, 
                    DBDocumentStatus.ERROR, 
                    str(e)
                )
            except:
                pass
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            logger.info(f"开始删除文档: {doc_id}")
            
            # 获取文档信息
            db_doc = self.document_crud.get_document(doc_id)
            if not db_doc:
                logger.warning(f"文档不存在: {doc_id}")
                return False
            
            # 删除向量数据
            try:
                await self.vector_service.delete_vectors(doc_id)
                logger.debug(f"删除文档向量成功: {doc_id}")
            except VectorStoreError as e:
                logger.warning(f"删除文档向量失败: {doc_id}, 错误: {str(e)}")
            
            # 删除文件
            try:
                # 构建文件路径（假设文件存储在storage_dir中）
                file_ext = db_doc.file_type if db_doc.file_type.startswith('.') else f".{db_doc.file_type}"
                file_path = self.storage_dir / f"{doc_id}{file_ext}"
                if file_path.exists():
                    os.remove(file_path)
                    logger.debug(f"删除文档文件成功: {file_path}")
            except Exception as e:
                logger.warning(f"删除文档文件失败: {file_path}, 错误: {str(e)}")
            
            # 删除数据库记录
            success = self.document_crud.delete_document(doc_id)
            
            if success:
                logger.info(f"文档删除成功: {doc_id}")
            else:
                logger.error(f"文档删除失败: {doc_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除文档失败: {doc_id}, 错误: {str(e)}")
            return False
    
    async def list_documents(self) -> List[DocumentInfo]:
        """获取文档列表"""
        try:
            logger.debug("获取文档列表")
            db_documents = self.document_crud.get_documents()
            
            # 转换为DocumentInfo对象
            documents = []
            for db_doc in db_documents:
                doc_info = self._convert_db_to_model(db_doc)
                documents.append(doc_info)
            
            logger.debug(f"获取到 {len(documents)} 个文档")
            return documents
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            raise DocumentError(f"获取文档列表失败: {str(e)}")
    
    async def get_document(self, doc_id: str) -> DocumentInfo:
        """获取文档信息"""
        try:
            logger.debug(f"获取文档信息: {doc_id}")
            
            db_doc = self.document_crud.get_document(doc_id)
            if not db_doc:
                raise DocumentError(f"文档不存在: {doc_id}")
            
            return self._convert_db_to_model(db_doc)
            
        except DocumentError:
            raise
        except Exception as e:
            logger.error(f"获取文档信息失败: {doc_id}, 错误: {str(e)}")
            raise DocumentError(f"获取文档信息失败: {str(e)}")
    
    async def get_document_status(self, doc_id: str) -> DocumentStatus:
        """获取文档处理状态"""
        try:
            doc_info = await self.get_document(doc_id)
            return doc_info.status
            
        except Exception as e:
            logger.error(f"获取文档状态失败: {doc_id}, 错误: {str(e)}")
            raise DocumentError(f"获取文档状态失败: {str(e)}")
    
    async def reprocess_document(self, doc_id: str) -> bool:
        """重新处理文档"""
        try:
            logger.info(f"重新处理文档: {doc_id}")
            
            # 获取文档信息
            doc_info = await self.get_document(doc_id)
            
            # 检查文件是否存在
            file_ext = doc_info.file_type if doc_info.file_type.startswith('.') else f".{doc_info.file_type}"
            file_path = self.storage_dir / f"{doc_id}{file_ext}"
            if not file_path.exists():
                raise DocumentError(f"文档文件不存在: {file_path}")
            
            # 删除旧的向量数据
            try:
                await self.vector_service.delete_vectors(doc_id)
            except:
                pass
            
            # 更新状态为处理中
            from ..database.models import DocumentStatus as DBDocumentStatus
            self.document_crud.update_document_status(doc_id, DBDocumentStatus.PROCESSING)
            
            # 重新处理文档
            doc_info.file_path = str(file_path)
            await self._process_document_async(doc_info)
            
            logger.info(f"文档重新处理完成: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"重新处理文档失败: {doc_id}, 错误: {str(e)}")
            return False
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            documents = await self.list_documents()
            
            stats = {
                "total_documents": len(documents),
                "processing_documents": len([d for d in documents if d.status == DocumentStatus.PROCESSING]),
                "ready_documents": len([d for d in documents if d.status == DocumentStatus.READY]),
                "error_documents": len([d for d in documents if d.status == DocumentStatus.ERROR]),
                "total_chunks": sum(d.chunk_count for d in documents),
                "vector_count": await self.vector_service.get_vector_count(),
                "storage_directory": str(self.storage_dir),
                "supported_formats": self.document_processor.get_supported_formats()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取服务统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    def _convert_db_to_model(self, db_doc) -> DocumentInfo:
        """将数据库模型转换为业务模型"""
        from ..database.models import DocumentStatus as DBDocumentStatus
        
        # 状态转换映射
        status_mapping = {
            DBDocumentStatus.PROCESSING: DocumentStatus.PROCESSING,
            DBDocumentStatus.READY: DocumentStatus.READY,
            DBDocumentStatus.ERROR: DocumentStatus.ERROR
        }
        
        # 确保文件类型格式正确
        file_type = db_doc.file_type
        if file_type.startswith('.'):
            file_type = file_type[1:]
        
        return DocumentInfo(
            id=db_doc.id,
            filename=db_doc.filename,
            file_type=file_type,
            file_size=db_doc.file_size,
            file_path=str(self.storage_dir / f"{db_doc.id}.{file_type}"),
            upload_time=db_doc.upload_time,
            status=status_mapping.get(db_doc.status, DocumentStatus.ERROR),
            chunk_count=db_doc.chunk_count or 0,
            error_message=db_doc.error_message or "",
            processing_time=0.0  # 这个字段在数据库模型中不存在
        )