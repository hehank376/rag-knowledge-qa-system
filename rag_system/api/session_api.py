"""
会话管理API接口
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from datetime import datetime

from ..services.session_service import SessionService
from ..models.qa import QAResponse
from ..utils.exceptions import SessionError

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreateRequest(BaseModel):
    """会话创建请求模型"""
    title: Optional[str] = None
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    """会话响应模型"""
    session_id: str
    title: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    qa_count: int = 0


class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    sessions: List[SessionResponse]
    total_count: int


class SessionStatsResponse(BaseModel):
    """会话统计响应模型"""
    total_sessions: int
    active_sessions: int
    total_qa_pairs: int
    avg_qa_per_session: float


# 依赖注入：获取会话服务实例
async def get_session_service() -> SessionService:
    """获取会话服务实例"""
    config = {
        'max_sessions_per_user': 100,
        'session_timeout_hours': 24,
        'max_qa_pairs_per_session': 1000,
        'cleanup_interval_hours': 6,
        'auto_cleanup_enabled': True,
        'database_url': 'sqlite:///./database/rag_system.db'  # 使用统一的数据库
    }
    
    service = SessionService(config)
    await service.initialize()
    return service


@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest = SessionCreateRequest(),
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    创建新会话
    
    Args:
        request: 会话创建请求
        session_service: 会话服务实例
        
    Returns:
        创建的会话信息
        
    Raises:
        HTTPException: 当创建失败时
    """
    try:
        logger.info(f"创建新会话，用户: {request.user_id}, 标题: {request.title}")
        
        session_id = await session_service.create_session(
            user_id=request.user_id
        )
        
        # 获取会话详情
        session_info = await session_service.get_session(session_id)
        
        logger.info(f"会话创建成功: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            title=request.title,  # 使用请求中的title
            user_id=request.user_id,  # 使用请求中的user_id
            created_at=session_info.created_at,
            updated_at=session_info.last_activity,
            qa_count=session_info.qa_count
        )
        
    except SessionError as e:
        logger.error(f"创建会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"创建会话时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建会话时发生内部错误"
        )


@router.get("/recent")
async def get_recent_sessions(
    user_id: Optional[str] = None,
    limit: int = 10,
    session_service: SessionService = Depends(get_session_service)
) -> SessionListResponse:
    """
    获取最近的会话
    
    Args:
        user_id: 可选的用户ID过滤
        limit: 返回数量限制
        session_service: 会话服务实例
        
    Returns:
        最近的会话列表
        
    Raises:
        HTTPException: 当获取失败时
    """
    try:
        logger.info(f"获取最近会话，用户: {user_id}, 限制: {limit}")
        
        sessions = await session_service.list_sessions(
            user_id=user_id,
            limit=limit,
            offset=0
        )
        
        session_responses = []
        for session in sessions:
            session_responses.append(SessionResponse(
                session_id=session.id,
                title=None,  # Session model doesn't have title field
                user_id=None,  # Session model doesn't have user_id field
                created_at=session.created_at,
                updated_at=session.last_activity,
                qa_count=session.qa_count
            ))
        
        logger.info(f"返回 {len(session_responses)} 个最近会话")
        
        return SessionListResponse(
            sessions=session_responses,
            total_count=len(session_responses)
        )
        
    except SessionError as e:
        logger.error(f"获取最近会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近会话失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取最近会话时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取最近会话时发生内部错误"
        )


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service)
) -> SessionListResponse:
    """
    获取会话列表
    
    Args:
        user_id: 可选的用户ID过滤
        limit: 返回数量限制
        offset: 偏移量
        session_service: 会话服务实例
        
    Returns:
        会话列表响应
        
    Raises:
        HTTPException: 当获取失败时
    """
    try:
        logger.info(f"获取会话列表，用户: {user_id}, 限制: {limit}, 偏移: {offset}")
        
        sessions = await session_service.list_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        session_responses = []
        for session in sessions:
            session_responses.append(SessionResponse(
                session_id=session.id,
                title=None,  # Session model doesn't have title field
                user_id=None,  # Session model doesn't have user_id field
                created_at=session.created_at,
                updated_at=session.last_activity,
                qa_count=session.qa_count
            ))
        
        logger.info(f"返回 {len(session_responses)} 个会话")
        
        return SessionListResponse(
            sessions=session_responses,
            total_count=len(session_responses)
        )
        
    except SessionError as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取会话列表时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话列表时发生内部错误"
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    获取单个会话信息
    
    Args:
        session_id: 会话ID
        session_service: 会话服务实例
        
    Returns:
        会话信息
        
    Raises:
        HTTPException: 当会话不存在或获取失败时
    """
    try:
        logger.info(f"获取会话信息: {session_id}")
        
        session_info = await session_service.get_session(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在: {session_id}"
            )
        
        return SessionResponse(
            session_id=session_id,
            title=None,  # Session model doesn't have title field
            user_id=None,  # Session model doesn't have user_id field
            created_at=session_info.created_at,
            updated_at=session_info.last_activity,
            qa_count=session_info.qa_count
        )
        
    except HTTPException:
        raise
    except SessionError as e:
        logger.error(f"获取会话信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话信息失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取会话信息时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话信息时发生内部错误"
        )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    删除会话
    
    Args:
        session_id: 要删除的会话ID
        session_service: 会话服务实例
        
    Returns:
        删除操作结果
        
    Raises:
        HTTPException: 当删除失败时
    """
    try:
        logger.info(f"删除会话: {session_id}")
        
        # 检查会话是否存在
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在: {session_id}"
            )
        
        # 删除会话
        success = await session_service.delete_session(session_id)
        
        if success:
            logger.info(f"会话删除成功: {session_id}")
            return {
                "success": True,
                "message": f"会话 {session_id} 删除成功",
                "session_id": session_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"会话删除失败: {session_id}"
            )
            
    except HTTPException:
        raise
    except SessionError as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"删除会话时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除会话时发生内部错误"
        )


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    获取会话历史记录
    
    Args:
        session_id: 会话ID
        limit: 返回数量限制
        offset: 偏移量
        session_service: 会话服务实例
        
    Returns:
        会话历史记录
        
    Raises:
        HTTPException: 当获取失败时
    """
    try:
        logger.info(f"获取会话历史: {session_id}, 限制: {limit}, 偏移: {offset}")
        
        # 检查会话是否存在
        session_info = await session_service.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在: {session_id}"
            )
        
        # 获取历史记录
        history = await session_service.get_session_history(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "session_id": session_id,
            "history": history,
            "total_count": len(history),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except SessionError as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话历史失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取会话历史时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话历史时发生内部错误"
        )


@router.get("/stats/summary", response_model=SessionStatsResponse)
async def get_session_stats(
    session_service: SessionService = Depends(get_session_service)
) -> SessionStatsResponse:
    """
    获取会话统计信息
    
    Args:
        session_service: 会话服务实例
        
    Returns:
        会话统计信息
        
    Raises:
        HTTPException: 当获取失败时
    """
    try:
        logger.info("获取会话统计信息")
        
        stats = await session_service.get_session_stats()
        
        return SessionStatsResponse(
            total_sessions=stats.get('total_sessions', 0),
            active_sessions=stats.get('active_sessions', 0),
            total_qa_pairs=stats.get('total_qa_pairs', 0),
            avg_qa_per_session=stats.get('avg_qa_per_session', 0.0)
        )
        
    except SessionError as e:
        logger.error(f"获取会话统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话统计信息失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取会话统计信息时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话统计信息时发生内部错误"
        )


@router.delete("/")
async def clear_all_sessions(
    user_id: Optional[str] = None,
    confirm: bool = False,
    session_service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    清空所有会话（危险操作）
    
    Args:
        user_id: 可选的用户ID，只删除该用户的会话
        confirm: 确认删除所有会话
        session_service: 会话服务实例
        
    Returns:
        批量删除操作结果
        
    Raises:
        HTTPException: 当删除失败时
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须设置 confirm=true 来确认删除所有会话"
        )
    
    try:
        logger.warning(f"开始清空会话，用户: {user_id}")
        
        # 获取要删除的会话列表
        sessions = await session_service.list_sessions(user_id=user_id)
        
        if not sessions:
            return {
                "success": True,
                "message": "没有会话需要删除",
                "deleted_count": 0,
                "failed_count": 0
            }
        
        # 批量删除
        deleted_count = 0
        failed_count = 0
        failed_sessions = []
        
        for session in sessions:
            try:
                session_id = session.get('session_id')
                success = await session_service.delete_session(session_id)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
                    failed_sessions.append(session_id)
            except Exception as e:
                failed_count += 1
                failed_sessions.append(f"{session.get('session_id')} (错误: {str(e)})")
                logger.error(f"删除会话失败: {session.get('session_id')}, 错误: {str(e)}")
        
        logger.warning(f"批量删除完成: 成功 {deleted_count}, 失败 {failed_count}")
        
        result = {
            "success": failed_count == 0,
            "message": f"删除完成: 成功 {deleted_count} 个, 失败 {failed_count} 个",
            "deleted_count": deleted_count,
            "failed_count": failed_count
        }
        
        if failed_sessions:
            result["failed_sessions"] = failed_sessions
        
        return result
        
    except Exception as e:
        logger.error(f"批量删除会话时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量删除会话时发生内部错误"
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
        "service": "session_api",
        "version": "1.0.0"
    }