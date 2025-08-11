"""
问答API接口
实现任务6.3：问答结果处理和展示
"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from ..services.qa_service import QAService
from ..services.result_processor import ResultProcessor
from ..services.session_service import SessionService
from ..models.qa import QAResponse, QAStatus
from ..utils.exceptions import QAError, ProcessingError, SessionError

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/qa", tags=["qa"])


class QuestionRequest(BaseModel):
    """问题请求模型"""
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # 添加用户ID字段
    top_k: Optional[int] = None
    document_ids: Optional[List[str]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    timeout: Optional[int] = 30  # 超时时间（秒）


class StreamingQuestionRequest(BaseModel):
    """流式问题请求模型"""
    question: str
    session_id: Optional[str] = None
    top_k: Optional[int] = None
    document_ids: Optional[List[str]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = 30


class QAResponseFormatted(BaseModel):
    """格式化的问答响应模型"""
    id: str
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    has_sources: bool
    source_count: int
    confidence_score: Optional[float]
    processing_time: Optional[float]
    status: str
    timestamp: str
    metadata: Dict[str, Any]
    error_message: Optional[str] = None
    session_id: Optional[str] = None  # 添加会话ID字段


class NoAnswerResponse(BaseModel):
    """无答案响应模型"""
    answer: str
    reason: str
    suggestions: List[str]
    has_answer: bool
    confidence_score: float


class QAStatsResponse(BaseModel):
    """问答统计响应模型"""
    qa_service_stats: Dict[str, Any]
    result_processor_stats: Dict[str, Any]
    total_questions_processed: int
    average_processing_time: float
    average_confidence_score: float


# 依赖注入：获取QA服务实例
async def get_qa_service() -> QAService:
    """获取QA服务实例"""
    # 从配置文件加载实际配置
    from ..config.loader import ConfigLoader
    import os
    
    config_loader = ConfigLoader()
    app_config = config_loader.load_config()
    
    config = {
        'vector_store_type': app_config.vector_store.type,
        'vector_store_path': app_config.vector_store.persist_directory,
        'collection_name': app_config.vector_store.collection_name,
        'embedding_provider': app_config.embeddings.provider,
        'embedding_model': app_config.embeddings.model,
        'embedding_api_key': os.getenv('SILICONFLOW_API_KEY'),
        'embedding_api_base': 'https://api.siliconflow.cn/v1',
        'embedding_dimensions': 1024,
        'llm_provider': app_config.llm.provider,
        'llm_model': app_config.llm.model,
        'llm_api_key': os.getenv('SILICONFLOW_API_KEY'),
        'llm_api_base': 'https://api.siliconflow.cn/v1',
        'llm_timeout': app_config.llm.timeout,
        'llm_temperature': app_config.llm.temperature,
        'llm_max_tokens': app_config.llm.max_tokens,
        'similarity_threshold': app_config.retrieval.similarity_threshold,
        'retrieval_top_k': app_config.retrieval.top_k,
        'no_answer_threshold': 0.6,  # Reasonable threshold for cosine similarity
        'database_url': app_config.database.url
    }
    service = QAService(config)
    await service.initialize()
    return service


# 依赖注入：获取结果处理器实例
async def get_result_processor() -> ResultProcessor:
    """获取结果处理器实例"""
    config = {
        'max_answer_length': 2000,
        'max_source_content_length': 200,
        'show_confidence_score': True,
        'show_processing_time': True,
        'highlight_keywords': True,
        'max_sources_display': 5,
        'sort_sources_by_relevance': True,
        'group_sources_by_document': False
    }
    processor = ResultProcessor(config)
    await processor.initialize()
    return processor


# 依赖注入：获取会话服务实例
async def get_session_service() -> SessionService:
    """获取会话服务实例"""
    config = {
        'max_sessions_per_user': 100,
        'session_timeout_hours': 24,
        'max_qa_pairs_per_session': 1000,
        'auto_cleanup_enabled': True,
        'database_url': 'sqlite:///./database/rag_system.db'  # 使用统一的数据库
    }
    service = SessionService(config)
    await service.initialize()
    return service


@router.post("/ask", response_model=QAResponseFormatted)
async def ask_question(
    request: QuestionRequest,
    qa_service: QAService = Depends(get_qa_service),
    result_processor: ResultProcessor = Depends(get_result_processor),
    session_service: SessionService = Depends(get_session_service)
) -> QAResponseFormatted:
    """
    提问接口
    
    Args:
        request: 问题请求
        qa_service: QA服务实例
        result_processor: 结果处理器实例
        
    Returns:
        格式化的问答响应
        
    Raises:
        HTTPException: 当问答处理失败时
    """
    try:
        logger.info(f"收到问题: {request.question[:100]}...")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="问题不能为空"
            )
        
        # 执行问答
        qa_response = await qa_service.answer_question(
            question=request.question,
            top_k=request.top_k,
            document_ids=request.document_ids,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 格式化响应
        formatted_response = result_processor.format_qa_response(qa_response)
        
        # 处理会话：如果没有提供会话ID，创建新会话
        session_id = request.session_id
        if not session_id:
            try:
                user_id = getattr(request, 'user_id', None)  # 安全获取user_id
                session_id = await session_service.create_session(user_id)
                logger.info(f"自动创建新会话: {session_id} (用户: {user_id or 'anonymous'})")
            except SessionError as e:
                logger.warning(f"创建会话失败: {str(e)}")
                session_id = None
        
        # 保存问答对到会话历史
        if session_id:
            try:
                await session_service.save_qa_pair(session_id, qa_response)
                logger.info(f"问答对已保存到会话: {session_id}")
            except SessionError as e:
                logger.warning(f"保存问答对到会话失败: {str(e)}")
                # 不影响主要的问答功能，只记录警告
        
        # 将会话ID添加到格式化响应中
        formatted_response['session_id'] = session_id
        
        logger.info(f"问答完成: {qa_response.id}")
        return QAResponseFormatted(**formatted_response)
        
    except HTTPException:
        # 重新抛出HTTP异常，保持原始状态码
        raise
    except QAError as e:
        logger.error(f"问答处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答处理失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"问答接口发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="问答处理时发生内部错误"
        )


@router.post("/ask-stream")
async def ask_question_stream(
    request: StreamingQuestionRequest,
    qa_service: QAService = Depends(get_qa_service),
    result_processor: ResultProcessor = Depends(get_result_processor)
) -> StreamingResponse:
    """
    流式问答接口
    
    Args:
        request: 流式问题请求
        qa_service: QA服务实例
        result_processor: 结果处理器实例
        
    Returns:
        流式响应
        
    Raises:
        HTTPException: 当问答处理失败时
    """
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            logger.info(f"收到流式问答请求: {request.question[:100]}...")
            
            if not request.question or not request.question.strip():
                yield f"data: {json.dumps({'error': '问题不能为空'})}\n\n"
                return
            
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'message': '开始处理问题...'})}\n\n"
            
            # 设置超时
            timeout = request.timeout or 30
            
            try:
                # 使用asyncio.wait_for设置超时
                qa_response = await asyncio.wait_for(
                    qa_service.answer_question(
                        question=request.question,
                        top_k=request.top_k,
                        document_ids=request.document_ids,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens
                    ),
                    timeout=timeout
                )
                
                # 发送检索完成事件
                yield f"data: {json.dumps({'type': 'retrieval', 'message': f'找到 {len(qa_response.sources)} 个相关文档'})}\n\n"
                
                # 格式化响应
                formatted_response = result_processor.format_qa_response(qa_response)
                
                # 发送处理完成事件
                yield f"data: {json.dumps({'type': 'processing', 'message': '正在格式化答案...'})}\n\n"
                
                # 分块发送答案
                answer = formatted_response['answer']
                chunk_size = 50  # 每次发送50个字符
                
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.1)  # 模拟流式输出延迟
                
                # 发送完整响应
                yield f"data: {json.dumps({'type': 'complete', 'response': formatted_response})}\n\n"
                
                logger.info(f"流式问答完成: {qa_response.id}")
                
            except asyncio.TimeoutError:
                logger.error(f"问答请求超时: {request.question[:50]}...")
                yield f"data: {json.dumps({'type': 'error', 'error': f'请求超时（{timeout}秒）'})}\n\n"
                
        except QAError as e:
            logger.error(f"流式问答处理失败: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': f'问答处理失败: {str(e)}'})}\n\n"
        except Exception as e:
            logger.error(f"流式问答发生未知错误: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': '问答处理时发生内部错误'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.post("/ask-with-timeout", response_model=QAResponseFormatted)
async def ask_question_with_timeout(
    request: QuestionRequest,
    qa_service: QAService = Depends(get_qa_service),
    result_processor: ResultProcessor = Depends(get_result_processor)
) -> QAResponseFormatted:
    """
    带超时的问答接口
    
    Args:
        request: 问题请求
        qa_service: QA服务实例
        result_processor: 结果处理器实例
        
    Returns:
        格式化的问答响应
        
    Raises:
        HTTPException: 当问答处理失败或超时时
    """
    try:
        logger.info(f"收到带超时的问答请求: {request.question[:100]}...")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="问题不能为空"
            )
        
        # 设置超时
        timeout = request.timeout or 30
        
        try:
            # 使用asyncio.wait_for设置超时
            qa_response = await asyncio.wait_for(
                qa_service.answer_question(
                    question=request.question,
                    top_k=request.top_k,
                    document_ids=request.document_ids,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ),
                timeout=timeout
            )
            
            # 格式化响应
            formatted_response = result_processor.format_qa_response(qa_response)
            
            logger.info(f"带超时的问答完成: {qa_response.id}")
            return QAResponseFormatted(**formatted_response)
            
        except asyncio.TimeoutError:
            logger.error(f"问答请求超时: {request.question[:50]}...")
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"请求超时（{timeout}秒）"
            )
            
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except QAError as e:
        logger.error(f"带超时的问答处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答处理失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"带超时的问答发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="问答处理时发生内部错误"
        )


@router.post("/no-answer-help", response_model=NoAnswerResponse)
async def get_no_answer_help(
    question: str,
    reason: str = "no_relevant_content",
    result_processor: ResultProcessor = Depends(get_result_processor)
) -> NoAnswerResponse:
    """
    获取无答案帮助信息
    
    Args:
        question: 原始问题
        reason: 无答案的原因
        result_processor: 结果处理器实例
        
    Returns:
        无答案响应
    """
    try:
        logger.info(f"生成无答案帮助: {question[:50]}..., 原因: {reason}")
        
        no_answer_response = result_processor.create_no_answer_response(question, reason)
        return NoAnswerResponse(**no_answer_response)
        
    except Exception as e:
        logger.error(f"生成无答案帮助失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成帮助信息时发生错误"
        )


@router.get("/stats", response_model=QAStatsResponse)
async def get_qa_stats(
    qa_service: QAService = Depends(get_qa_service),
    result_processor: ResultProcessor = Depends(get_result_processor)
) -> QAStatsResponse:
    """
    获取问答系统统计信息
    
    Args:
        qa_service: QA服务实例
        result_processor: 结果处理器实例
        
    Returns:
        问答统计信息
    """
    try:
        logger.info("获取问答系统统计信息")
        
        # 获取QA服务统计
        qa_stats = await qa_service.get_service_stats()
        
        # 获取结果处理器统计
        processor_stats = result_processor.get_service_stats()
        
        # 构建响应
        response = QAStatsResponse(
            qa_service_stats=qa_stats,
            result_processor_stats=processor_stats,
            total_questions_processed=0,  # 这里可以从数据库或缓存中获取
            average_processing_time=0.0,  # 这里可以计算平均值
            average_confidence_score=0.0  # 这里可以计算平均值
        )
        
        return response
        
    except Exception as e:
        logger.error(f"获取问答统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息时发生错误"
        )


@router.post("/test", response_model=Dict[str, Any])
async def test_qa_system(
    test_question: str = "什么是人工智能？",
    qa_service: QAService = Depends(get_qa_service),
    result_processor: ResultProcessor = Depends(get_result_processor)
) -> Dict[str, Any]:
    """
    测试问答系统
    
    Args:
        test_question: 测试问题
        qa_service: QA服务实例
        result_processor: 结果处理器实例
        
    Returns:
        测试结果
    """
    try:
        logger.info(f"测试问答系统: {test_question}")
        
        # 执行QA服务测试
        qa_test_result = await qa_service.test_qa(test_question)
        
        # 如果QA测试成功，测试结果处理
        if qa_test_result.get("success"):
            # 创建一个测试响应进行格式化测试
            test_response = QAResponse(
                question=test_question,
                answer="这是一个测试答案，用于验证结果处理功能。",
                sources=[],
                confidence_score=0.8,
                processing_time=1.0,
                status=QAStatus.COMPLETED
            )
            
            formatted_test = result_processor.format_qa_response(test_response)
            
            return {
                "success": True,
                "qa_test": qa_test_result,
                "formatting_test": {
                    "success": True,
                    "formatted_response_keys": list(formatted_test.keys()),
                    "answer_length": len(formatted_test["answer"]),
                    "has_metadata": "metadata" in formatted_test
                },
                "system_status": "healthy"
            }
        else:
            return {
                "success": False,
                "qa_test": qa_test_result,
                "formatting_test": {"success": False, "error": "QA测试失败"},
                "system_status": "unhealthy"
            }
            
    except Exception as e:
        logger.error(f"测试问答系统失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "system_status": "error"
        }


@router.post("/format-response", response_model=QAResponseFormatted)
async def format_qa_response(
    qa_response: Dict[str, Any],
    result_processor: ResultProcessor = Depends(get_result_processor)
) -> QAResponseFormatted:
    """
    格式化QA响应（用于测试和调试）
    
    Args:
        qa_response: 原始QA响应数据
        result_processor: 结果处理器实例
        
    Returns:
        格式化的响应
    """
    try:
        logger.info("格式化QA响应")
        
        # 将字典转换为QAResponse对象
        response_obj = QAResponse(**qa_response)
        
        # 格式化响应
        formatted = result_processor.format_qa_response(response_obj)
        
        return QAResponseFormatted(**formatted)
        
    except Exception as e:
        logger.error(f"格式化QA响应失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"格式化响应失败: {str(e)}"
        )


@router.post("/ask-with-session", response_model=Dict[str, Any])
async def ask_question_with_session(
    request: QuestionRequest,
    user_id: Optional[str] = None,
    qa_service: QAService = Depends(get_qa_service),
    result_processor: ResultProcessor = Depends(get_result_processor),
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    带会话管理的问答接口
    
    Args:
        request: 问题请求
        user_id: 用户ID（可选）
        qa_service: QA服务实例
        result_processor: 结果处理器实例
        session_service: 会话服务实例
        
    Returns:
        包含会话信息的问答响应
    """
    try:
        logger.info(f"收到带会话的问题: {request.question[:100]}...")
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="问题不能为空"
            )
        
        # 如果没有提供会话ID，创建新会话
        session_id = request.session_id
        if not session_id:
            session_id = await session_service.create_session(user_id)
            logger.info(f"创建新会话: {session_id}")
        else:
            # 更新会话活动时间
            await session_service.update_session_activity(session_id)
        
        # 执行问答
        qa_response = await qa_service.answer_question(
            question=request.question,
            top_k=request.top_k,
            document_ids=request.document_ids,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 格式化响应
        formatted_response = result_processor.format_qa_response(qa_response)
        
        # 保存问答对到会话历史
        await session_service.save_qa_pair(session_id, qa_response)
        
        # 返回包含会话信息的响应
        result = {
            "qa_response": formatted_response,
            "session_info": {
                "session_id": session_id,
                "user_id": user_id,
                "created_new_session": request.session_id is None
            }
        }
        
        logger.info(f"带会话问答完成: {qa_response.id}, 会话: {session_id}")
        return result
        
    except HTTPException:
        raise
    except (QAError, SessionError) as e:
        logger.error(f"带会话问答处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答处理失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"带会话问答接口发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="问答处理时发生内部错误"
        )


@router.get("/session/{session_id}/history")
async def get_session_qa_history(
    session_id: str,
    limit: Optional[int] = 50,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    获取会话问答历史
    
    Args:
        session_id: 会话ID
        limit: 返回数量限制
        offset: 偏移量
        session_service: 会话服务实例
        
    Returns:
        会话历史记录
    """
    try:
        logger.info(f"获取会话历史: {session_id}")
        
        # 获取会话历史
        history = await session_service.get_session_history(session_id, limit, offset)
        
        # 获取会话统计
        session_stats = await session_service.get_session_statistics(session_id)
        
        return {
            "session_id": session_id,
            "history": [
                {
                    "id": qa.id,
                    "question": qa.question,
                    "answer": qa.answer,
                    "confidence_score": qa.confidence_score,
                    "processing_time": qa.processing_time,
                    "timestamp": qa.timestamp.isoformat(),
                    "source_count": len(qa.sources)
                }
                for qa in history
            ],
            "total_count": len(history),
            "session_stats": session_stats
        }
        
    except SessionError as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"获取会话历史失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取会话历史时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话历史时发生内部错误"
        )


@router.get("/sessions/recent")
async def get_recent_qa_pairs(
    limit: int = 20,
    user_id: Optional[str] = None,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    获取最近的问答对
    
    Args:
        limit: 返回数量限制
        user_id: 用户ID（可选）
        session_service: 会话服务实例
        
    Returns:
        最近的问答对列表
    """
    try:
        logger.info(f"获取最近问答对，用户: {user_id}, 限制: {limit}")
        
        # 获取最近的问答对
        recent_qa = await session_service.get_recent_qa_pairs(user_id, limit)
        
        return {
            "recent_qa_pairs": [
                {
                    "id": qa.id,
                    "session_id": qa.session_id,
                    "question": qa.question,
                    "answer": qa.answer[:200] + "..." if len(qa.answer) > 200 else qa.answer,
                    "confidence_score": qa.confidence_score,
                    "timestamp": qa.timestamp.isoformat(),
                    "source_count": len(qa.sources)
                }
                for qa in recent_qa
            ],
            "total_count": len(recent_qa),
            "user_id": user_id
        }
        
    except SessionError as e:
        logger.error(f"获取最近问答对失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近问答对失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取最近问答对时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取最近问答对时发生内部错误"
        )


@router.get("/search")
async def search_qa_pairs(
    query: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    搜索问答对
    
    Args:
        query: 搜索查询
        session_id: 会话ID（可选）
        user_id: 用户ID（可选）
        limit: 返回数量限制
        offset: 偏移量
        session_service: 会话服务实例
        
    Returns:
        搜索结果
    """
    try:
        logger.info(f"搜索问答对: {query[:50]}...")
        
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="搜索查询不能为空"
            )
        
        # 搜索问答对
        search_results = await session_service.search_qa_pairs(
            query=query,
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "query": query,
            "results": [
                {
                    "id": qa.id,
                    "session_id": qa.session_id,
                    "question": qa.question,
                    "answer": qa.answer[:200] + "..." if len(qa.answer) > 200 else qa.answer,
                    "confidence_score": qa.confidence_score,
                    "timestamp": qa.timestamp.isoformat(),
                    "source_count": len(qa.sources),
                    "relevance": "high"  # 可以后续添加相关性评分
                }
                for qa in search_results
            ],
            "total_count": len(search_results),
            "session_id": session_id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except SessionError as e:
        logger.error(f"搜索问答对失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索问答对失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"搜索问答对时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索问答对时发生内部错误"
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
        "service": "qa_api",
        "version": "1.0.0"
    }