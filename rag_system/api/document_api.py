"""
文档管理API接口
实现任务5.2：文档列表查询API和文档删除功能
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from pydantic import BaseModel

from ..services.document_service import DocumentService
from ..models.document import DocumentInfo, DocumentStatus
from ..utils.exceptions import DocumentError, ProcessingError

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    documents: List[DocumentInfo]
    total_count: int
    ready_count: int
    processing_count: int
    error_count: int


class DocumentDeleteResponse(BaseModel):
    """文档删除响应模型"""
    success: bool
    message: str
    document_id: str


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    success: bool
    message: str
    document_id: str
    filename: str
    file_size: int
    status: str


class DocumentStatsResponse(BaseModel):
    """文档统计响应模型"""
    total_documents: int
    ready_documents: int
    processing_documents: int
    error_documents: int
    total_chunks: int
    vector_count: int
    storage_directory: str
    supported_formats: List[str]


# 依赖注入：获取文档服务实例
async def get_document_service() -> DocumentService:
    """获取文档服务实例"""
    # 从配置文件加载实际配置
    from ..config.loader import ConfigLoader
    import os
    
    config_loader = ConfigLoader()
    app_config = config_loader.load_config()
    
    # 直接从配置文件读取document_processing配置
    import yaml
    with open(config_loader.config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)
    
    doc_processing = raw_config.get('document_processing', {})
    
    config = {
        'storage_dir': './documents',
        'vector_store_type': app_config.vector_store.type,
        'vector_store_path': app_config.vector_store.persist_directory,
        'collection_name': app_config.vector_store.collection_name,
        'embedding_provider': app_config.embeddings.provider,
        'embedding_model': app_config.embeddings.model,
        'embedding_api_key': os.getenv('SILICONFLOW_API_KEY'),
        'embedding_api_base': 'https://api.siliconflow.cn/v1',
        'embedding_dimensions': 1024,
        'chunk_size': doc_processing.get('chunk_size', app_config.embeddings.chunk_size),
        'chunk_overlap': doc_processing.get('chunk_overlap', app_config.embeddings.chunk_overlap),
        'min_chunk_size': doc_processing.get('min_chunk_size', 100),
        'max_chunk_size': doc_processing.get('max_chunk_size', 2000),
        'database_url': app_config.database.url
    }
    
    service = DocumentService(config)
    await service.initialize()
    return service


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentUploadResponse:
    """
    上传文档
    
    Args:
        file: 上传的文件
        document_service: 文档服务实例
        
    Returns:
        上传结果
        
    Raises:
        HTTPException: 当上传失败时
    """
    try:
        logger.info(f"接收文档上传请求: {file.filename}")
        
        # 验证文件类型
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 检查文件扩展名
        allowed_extensions = ['.pdf', '.txt', '.docx', '.md']
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if f'.{file_extension}' not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 检查文件大小（限制为50MB）
        max_file_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="文件大小超过限制（50MB）"
            )
        
        # 重置文件指针
        await file.seek(0)
        
        # 调用文档服务上传文档
        document_info = await document_service.upload_document(file)
        
        logger.info(f"文档上传成功: {document_info.id}")
        
        # 安全地获取状态值
        status_value = document_info.status.value if hasattr(document_info.status, 'value') else str(document_info.status)
        
        return DocumentUploadResponse(
            success=True,
            message="文档上传成功",
            document_id=document_info.id,
            filename=document_info.filename,
            file_size=document_info.file_size,
            status=status_value
        )
        
    except DocumentError as e:
        logger.error(f"文档上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文档上传失败: {str(e)}"
        )
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"文档上传发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档上传时发生内部错误"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status_filter: Optional[str] = None,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentListResponse:
    """
    获取文档列表
    
    Args:
        status_filter: 可选的状态过滤器 (ready, processing, error)
        document_service: 文档服务实例
        
    Returns:
        文档列表响应
        
    Raises:
        HTTPException: 当获取文档列表失败时
    """
    try:
        logger.info(f"获取文档列表，状态过滤器: {status_filter}")
        
        # 验证状态过滤器
        if status_filter:
            try:
                DocumentStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的状态过滤器: {status_filter}. 支持的状态: ready, processing, error"
                )
        
        # 获取所有文档
        documents = await document_service.list_documents()
        
        # 应用状态过滤器
        if status_filter:
            filter_status = DocumentStatus(status_filter.lower())
            documents = [doc for doc in documents if doc.status == filter_status]
        
        # 计算统计信息
        total_count = len(documents)
        ready_count = len([d for d in documents if d.status == DocumentStatus.READY])
        processing_count = len([d for d in documents if d.status == DocumentStatus.PROCESSING])
        error_count = len([d for d in documents if d.status == DocumentStatus.ERROR])
        
        logger.info(f"返回 {total_count} 个文档")
        
        return DocumentListResponse(
            documents=documents,
            total_count=total_count,
            ready_count=ready_count,
            processing_count=processing_count,
            error_count=error_count
        )
        
    except HTTPException:
        raise
    except DocumentError as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取文档列表时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档列表时发生内部错误"
        )


@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentInfo:
    """
    获取单个文档信息
    
    Args:
        document_id: 文档ID
        document_service: 文档服务实例
        
    Returns:
        文档信息
        
    Raises:
        HTTPException: 当文档不存在或获取失败时
    """
    try:
        logger.info(f"获取文档信息: {document_id}")
        
        document = await document_service.get_document(document_id)
        
        logger.info(f"成功获取文档信息: {document.filename}")
        return document
        
    except DocumentError as e:
        if "文档不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档不存在: {document_id}"
            )
        else:
            logger.error(f"获取文档信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取文档信息失败: {str(e)}"
            )
    except Exception as e:
        logger.error(f"获取文档信息时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档信息时发生内部错误"
        )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentDeleteResponse:
    """
    删除文档
    
    Args:
        document_id: 要删除的文档ID
        document_service: 文档服务实例
        
    Returns:
        删除操作结果
        
    Raises:
        HTTPException: 当删除失败时
    """
    try:
        logger.info(f"开始删除文档: {document_id}")
        
        # 首先检查文档是否存在
        try:
            document = await document_service.get_document(document_id)
            document_name = document.filename
        except DocumentError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档不存在: {document_id}"
            )
        
        # 执行删除操作
        success = await document_service.delete_document(document_id)
        
        if success:
            logger.info(f"文档删除成功: {document_name} ({document_id})")
            return DocumentDeleteResponse(
                success=True,
                message=f"文档 '{document_name}' 删除成功",
                document_id=document_id
            )
        else:
            logger.error(f"文档删除失败: {document_name} ({document_id})")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文档删除失败: {document_name}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档时发生未知错误: {document_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文档时发生内部错误"
        )


@router.post("/{document_id}/reprocess", response_model=Dict[str, Any])
async def reprocess_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> Dict[str, Any]:
    """
    重新处理文档
    
    Args:
        document_id: 要重新处理的文档ID
        document_service: 文档服务实例
        
    Returns:
        重新处理操作结果
        
    Raises:
        HTTPException: 当重新处理失败时
    """
    try:
        logger.info(f"开始重新处理文档: {document_id}")
        
        # 检查文档是否存在
        try:
            document = await document_service.get_document(document_id)
            document_name = document.filename
        except DocumentError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档不存在: {document_id}"
            )
        
        # 执行重新处理
        success = await document_service.reprocess_document(document_id)
        
        if success:
            logger.info(f"文档重新处理成功: {document_name} ({document_id})")
            return {
                "success": True,
                "message": f"文档 '{document_name}' 重新处理已开始",
                "document_id": document_id
            }
        else:
            logger.error(f"文档重新处理失败: {document_name} ({document_id})")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文档重新处理失败: {document_name}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新处理文档时发生未知错误: {document_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新处理文档时发生内部错误"
        )


@router.get("/supported-formats")
async def get_supported_formats() -> Dict[str, Any]:
    """
    获取支持的文件格式
    
    Returns:
        支持的文件格式列表和相关信息
    """
    return {
        "supported_formats": [".pdf", ".txt", ".docx", ".md"],
        "max_file_size_mb": 50,
        "description": {
            ".pdf": "PDF文档",
            ".txt": "纯文本文件",
            ".docx": "Microsoft Word文档",
            ".md": "Markdown文档"
        }
    }


@router.post("/batch-upload", response_model=List[DocumentUploadResponse])
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    document_service: DocumentService = Depends(get_document_service)
) -> List[DocumentUploadResponse]:
    """
    批量上传文档
    
    Args:
        files: 上传的文件列表
        document_service: 文档服务实例
        
    Returns:
        上传结果列表
    """
    results = []
    
    for file in files:
        try:
            logger.info(f"批量上传处理文件: {file.filename}")
            
            # 验证文件
            if not file.filename:
                results.append(DocumentUploadResponse(
                    success=False,
                    message="文件名不能为空",
                    document_id="",
                    filename=file.filename or "unknown",
                    file_size=0,
                    status="error"
                ))
                continue
            
            # 检查文件扩展名
            allowed_extensions = ['.pdf', '.txt', '.docx', '.md']
            file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            if f'.{file_extension}' not in allowed_extensions:
                results.append(DocumentUploadResponse(
                    success=False,
                    message=f"不支持的文件格式: {file_extension}",
                    document_id="",
                    filename=file.filename,
                    file_size=0,
                    status="error"
                ))
                continue
            
            # 上传文档
            document_info = await document_service.upload_document(file)
            
            # 安全地获取状态值
            status_value = document_info.status.value if hasattr(document_info.status, 'value') else str(document_info.status)
            
            results.append(DocumentUploadResponse(
                success=True,
                message="文档上传成功",
                document_id=document_info.id,
                filename=document_info.filename,
                file_size=document_info.file_size,
                status=status_value
            ))
            
        except Exception as e:
            logger.error(f"批量上传文件失败 {file.filename}: {str(e)}")
            results.append(DocumentUploadResponse(
                success=False,
                message=f"上传失败: {str(e)}",
                document_id="",
                filename=file.filename or "unknown",
                file_size=0,
                status="error"
            ))
    
    return results


@router.get("/stats/summary", response_model=DocumentStatsResponse)
async def get_document_stats(
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentStatsResponse:
    """
    获取文档统计信息
    
    Args:
        document_service: 文档服务实例
        
    Returns:
        文档统计信息
        
    Raises:
        HTTPException: 当获取统计信息失败时
    """
    try:
        logger.info("获取文档统计信息")
        
        stats = await document_service.get_service_stats()
        
        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取统计信息失败: {stats['error']}"
            )
        
        return DocumentStatsResponse(
            total_documents=stats.get('total_documents', 0),
            ready_documents=stats.get('ready_documents', 0),
            processing_documents=stats.get('processing_documents', 0),
            error_documents=stats.get('error_documents', 0),
            total_chunks=stats.get('total_chunks', 0),
            vector_count=stats.get('vector_count', 0),
            storage_directory=stats.get('storage_directory', ''),
            supported_formats=stats.get('supported_formats', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档统计信息时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档统计信息时发生内部错误"
        )


@router.delete("/", response_model=Dict[str, Any])
async def delete_all_documents(
    confirm: bool = False,
    document_service: DocumentService = Depends(get_document_service)
) -> Dict[str, Any]:
    """
    删除所有文档（危险操作）
    
    Args:
        confirm: 确认删除所有文档
        document_service: 文档服务实例
        
    Returns:
        批量删除操作结果
        
    Raises:
        HTTPException: 当删除失败时
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须设置 confirm=true 来确认删除所有文档"
        )
    
    try:
        logger.warning("开始删除所有文档")
        
        # 获取所有文档
        documents = await document_service.list_documents()
        
        if not documents:
            return {
                "success": True,
                "message": "没有文档需要删除",
                "deleted_count": 0,
                "failed_count": 0
            }
        
        # 批量删除
        deleted_count = 0
        failed_count = 0
        failed_documents = []
        
        for document in documents:
            try:
                success = await document_service.delete_document(document.id)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
                    failed_documents.append(document.filename)
            except Exception as e:
                failed_count += 1
                failed_documents.append(f"{document.filename} (错误: {str(e)})")
                logger.error(f"删除文档失败: {document.filename}, 错误: {str(e)}")
        
        logger.warning(f"批量删除完成: 成功 {deleted_count}, 失败 {failed_count}")
        
        result = {
            "success": failed_count == 0,
            "message": f"删除完成: 成功 {deleted_count} 个, 失败 {failed_count} 个",
            "deleted_count": deleted_count,
            "failed_count": failed_count
        }
        
        if failed_documents:
            result["failed_documents"] = failed_documents
        
        return result
        
    except Exception as e:
        logger.error(f"批量删除文档时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量删除文档时发生内部错误"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    健康检查接口
    
    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "service": "document_api",
        "version": "1.0.0"
    }