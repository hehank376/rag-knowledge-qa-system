"""
会话管理服务
负责管理用户会话和历史记录
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from ..models.qa import Session, QAPair, QAResponse
from ..database.crud import SessionCRUD, QAPairCRUD
from ..database.connection import DatabaseManager
from ..utils.exceptions import SessionError
from .base import BaseService

logger = logging.getLogger(__name__)


class SessionService(BaseService):
    """会话管理服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # 会话配置
        self.max_sessions_per_user = self.config.get('max_sessions_per_user', 100)
        self.session_timeout_hours = self.config.get('session_timeout_hours', 24)
        self.max_qa_pairs_per_session = self.config.get('max_qa_pairs_per_session', 1000)
        self.auto_cleanup_enabled = self.config.get('auto_cleanup_enabled', True)
        self.cleanup_interval_hours = self.config.get('cleanup_interval_hours', 6)
        
        # 数据库管理器
        self.db_manager = None
        
        # 统计信息
        self.stats = {
            'sessions_created': 0,
            'sessions_deleted': 0,
            'qa_pairs_saved': 0,
            'cleanup_runs': 0,
            'last_cleanup': None
        }
    
    async def initialize(self) -> None:
        """初始化会话管理服务"""
        logger.info("初始化会话管理服务")
        
        try:
            # 获取数据库管理器
            from ..models.config import DatabaseConfig
            db_config = DatabaseConfig(
                url=self.config.get('database_url', 'sqlite:///./sessions.db'),
                echo=self.config.get('database_echo', False)
            )
            self.db_manager = DatabaseManager(db_config)
            self.db_manager.initialize()
            
            # 执行初始清理（如果启用）
            if self.auto_cleanup_enabled:
                await self._cleanup_expired_sessions()
            
            logger.info("会话管理服务初始化成功")
            
        except Exception as e:
            logger.error(f"会话管理服务初始化失败: {str(e)}")
            raise SessionError(f"服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("会话管理服务资源清理完成")
    
    async def create_session(self, user_id: Optional[str] = None) -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户ID（可选）
            
        Returns:
            会话ID
            
        Raises:
            SessionError: 当会话创建失败时
        """
        try:
            logger.info(f"创建新会话，用户ID: {user_id or 'anonymous'}")
            
            # 创建新会话
            session = Session()
            
            # 使用数据库会话上下文
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                
                # 检查用户会话数量限制
                if user_id and self.max_sessions_per_user > 0:
                    user_session_count = session_crud.count_user_sessions(user_id)
                    if user_session_count >= self.max_sessions_per_user:
                        # 清理最旧的会话
                        oldest_sessions = session_crud.get_oldest_user_sessions(user_id, 1)
                        for old_session in oldest_sessions:
                            await self._delete_session_with_crud(old_session.id, session_crud, db_session)
                
                # 保存到数据库
                session_crud.create_session(session, user_id)
            
            # 更新统计
            self.stats['sessions_created'] += 1
            
            logger.info(f"会话创建成功: {session.id}")
            return session.id
            
        except Exception as e:
            logger.error(f"会话创建失败: {str(e)}")
            raise SessionError(f"会话创建失败: {str(e)}")
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话对象，如果不存在则返回None
        """
        try:
            logger.debug(f"获取会话信息: {session_id}")
            
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                db_session_obj = session_crud.get_session(session_id)
                
                if not db_session_obj:
                    return None
                
                # 转换为模型对象
                session = Session(
                    id=db_session_obj.id,
                    created_at=db_session_obj.created_at,
                    last_activity=db_session_obj.last_activity,
                    qa_count=db_session_obj.qa_count
                )
                
                # 检查会话是否过期
                if self._is_session_expired(session):
                    logger.info(f"会话已过期，自动删除: {session_id}")
                    await self.delete_session(session_id)
                    return None
                
                return session
            
        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}")
            raise SessionError(f"获取会话失败: {str(e)}")
    
    async def update_session_activity(self, session_id: str) -> bool:
        """
        更新会话活动时间
        
        Args:
            session_id: 会话ID
            
        Returns:
            更新是否成功
        """
        try:
            logger.debug(f"更新会话活动时间: {session_id}")
            
            session = await self.get_session(session_id)
            if not session:
                return False
            
            session.update_activity()
            
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                session_crud.update_session(session)
            
            return True
            
        except Exception as e:
            logger.error(f"更新会话活动时间失败: {str(e)}")
            return False
    
    async def save_qa_pair(
        self, 
        session_id: str, 
        qa_response: QAResponse
    ) -> bool:
        """
        保存问答对到会话历史
        
        Args:
            session_id: 会话ID
            qa_response: 问答响应对象
            
        Returns:
            保存是否成功
            
        Raises:
            SessionError: 当保存失败时
        """
        try:
            logger.debug(f"保存问答对到会话: {session_id}")
            
            # 检查会话是否存在
            session = await self.get_session(session_id)
            if not session:
                raise SessionError(f"会话不存在: {session_id}")
            
            with self.db_manager.get_session_context() as db_session:
                qa_pair_crud = QAPairCRUD(db_session)
                session_crud = SessionCRUD(db_session)
                
                # 检查会话问答对数量限制
                if self.max_qa_pairs_per_session > 0:
                    qa_count = qa_pair_crud.count_session_qa_pairs(session_id)
                    if qa_count >= self.max_qa_pairs_per_session:
                        # 删除最旧的问答对
                        oldest_qa_pairs = qa_pair_crud.get_oldest_session_qa_pairs(session_id, 1)
                        for qa_pair in oldest_qa_pairs:
                            qa_pair_crud.delete_qa_pair(qa_pair.id)
                
                # 创建问答对
                qa_pair = QAPair(
                    session_id=session_id,
                    question=qa_response.question,
                    answer=qa_response.answer,
                    sources=qa_response.sources,
                    confidence_score=qa_response.confidence_score,
                    processing_time=qa_response.processing_time,
                    metadata=qa_response.metadata
                )
                
                # 保存问答对
                qa_pair_crud.create_qa_pair(qa_pair)
                
                # 更新会话信息
                session.qa_count += 1
                session.update_activity()
                session_crud.update_session(session)
            
            # 更新统计
            self.stats['qa_pairs_saved'] += 1
            
            logger.info(f"问答对保存成功: {qa_pair.id}")
            return True
            
        except Exception as e:
            logger.error(f"保存问答对失败: {str(e)}")
            raise SessionError(f"保存问答对失败: {str(e)}")
    
    async def get_session_history(
        self, 
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[QAPair]:
        """
        获取会话历史记录
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            问答对列表
            
        Raises:
            SessionError: 当获取失败时
        """
        try:
            logger.debug(f"获取会话历史: {session_id}, limit={limit}, offset={offset}")
            
            # 检查会话是否存在
            session = await self.get_session(session_id)
            if not session:
                raise SessionError(f"会话不存在: {session_id}")
            
            with self.db_manager.get_session_context() as db_session:
                qa_pair_crud = QAPairCRUD(db_session)
                db_qa_pairs = qa_pair_crud.get_session_qa_pairs(session_id, limit, offset)
                
                # 转换为模型对象
                qa_pairs = []
                for db_qa_pair in db_qa_pairs:
                    # 重建源信息列表
                    sources = []
                    if db_qa_pair.sources:
                        from ..models.qa import SourceInfo
                        for source_data in db_qa_pair.sources:
                            sources.append(SourceInfo(**source_data))
                    
                    qa_pair = QAPair(
                        id=db_qa_pair.id,
                        session_id=db_qa_pair.session_id,
                        question=db_qa_pair.question,
                        answer=db_qa_pair.answer,
                        sources=sources,
                        confidence_score=db_qa_pair.confidence_score,
                        processing_time=db_qa_pair.processing_time,
                        timestamp=db_qa_pair.timestamp,
                        metadata=db_qa_pair.extra_metadata or {}
                    )
                    qa_pairs.append(qa_pair)
            
            logger.debug(f"获取到 {len(qa_pairs)} 个问答对")
            return qa_pairs
            
        except Exception as e:
            logger.error(f"获取会话历史失败: {str(e)}")
            raise SessionError(f"获取会话历史失败: {str(e)}")
    
    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话及其所有历史记录
        
        Args:
            session_id: 会话ID
            
        Returns:
            删除是否成功
            
        Raises:
            SessionError: 当删除失败时
        """
        try:
            logger.info(f"删除会话: {session_id}")
            
            with self.db_manager.get_session_context() as db_session:
                success = await self._delete_session_with_crud(session_id, None, db_session)
            
            if success:
                # 更新统计
                self.stats['sessions_deleted'] += 1
                logger.info(f"会话删除成功: {session_id}")
            else:
                logger.warning(f"会话删除失败，可能不存在: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除会话失败: {str(e)}")
            raise SessionError(f"删除会话失败: {str(e)}")
    
    async def _delete_session_with_crud(
        self, 
        session_id: str, 
        session_crud: Optional[SessionCRUD] = None,
        db_session = None
    ) -> bool:
        """使用CRUD删除会话的内部方法"""
        if not session_crud:
            session_crud = SessionCRUD(db_session)
        
        qa_pair_crud = QAPairCRUD(db_session)
        
        # 删除会话的所有问答对
        qa_pair_crud.delete_session_qa_pairs(session_id)
        
        # 删除会话
        return session_crud.delete_session(session_id)
    
    async def search_qa_pairs(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[QAPair]:
        """
        搜索问答对
        
        Args:
            query: 搜索查询
            session_id: 会话ID（可选）
            user_id: 用户ID（可选）
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            匹配的问答对列表
        """
        try:
            logger.debug(f"搜索问答对: {query[:50]}...")
            
            with self.db_manager.get_session_context() as db_session:
                qa_pair_crud = QAPairCRUD(db_session)
                db_qa_pairs = qa_pair_crud.search_qa_pairs(
                    query=query,
                    session_id=session_id,
                    user_id=user_id,
                    limit=limit,
                    offset=offset
                )
                
                # 转换为模型对象
                qa_pairs = []
                for db_qa_pair in db_qa_pairs:
                    # 重建源信息列表
                    sources = []
                    if db_qa_pair.sources:
                        from ..models.qa import SourceInfo
                        for source_data in db_qa_pair.sources:
                            sources.append(SourceInfo(**source_data))
                    
                    qa_pair = QAPair(
                        id=db_qa_pair.id,
                        session_id=db_qa_pair.session_id,
                        question=db_qa_pair.question,
                        answer=db_qa_pair.answer,
                        sources=sources,
                        confidence_score=db_qa_pair.confidence_score,
                        processing_time=db_qa_pair.processing_time,
                        timestamp=db_qa_pair.timestamp,
                        metadata=db_qa_pair.extra_metadata or {}
                    )
                    qa_pairs.append(qa_pair)
            
            logger.debug(f"搜索到 {len(qa_pairs)} 个问答对")
            return qa_pairs
            
        except Exception as e:
            logger.error(f"搜索问答对失败: {str(e)}")
            raise SessionError(f"搜索问答对失败: {str(e)}")
    
    async def get_recent_qa_pairs(
        self,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[QAPair]:
        """
        获取最近的问答对
        
        Args:
            user_id: 用户ID（可选）
            limit: 返回数量限制
            
        Returns:
            最近的问答对列表
        """
        try:
            logger.debug(f"获取最近问答对，用户ID: {user_id}, limit={limit}")
            
            with self.db_manager.get_session_context() as db_session:
                qa_pair_crud = QAPairCRUD(db_session)
                
                if user_id:
                    # 如果指定用户ID，需要通过会话过滤
                    db_qa_pairs = qa_pair_crud.search_qa_pairs(
                        query="",  # 空查询返回所有
                        user_id=user_id,
                        limit=limit,
                        offset=0
                    )
                else:
                    # 获取所有用户的最近问答对
                    db_qa_pairs = qa_pair_crud.get_recent_qa_pairs(limit)
                
                # 转换为模型对象
                qa_pairs = []
                for db_qa_pair in db_qa_pairs:
                    # 重建源信息列表
                    sources = []
                    if db_qa_pair.sources:
                        from ..models.qa import SourceInfo
                        for source_data in db_qa_pair.sources:
                            sources.append(SourceInfo(**source_data))
                    
                    qa_pair = QAPair(
                        id=db_qa_pair.id,
                        session_id=db_qa_pair.session_id,
                        question=db_qa_pair.question,
                        answer=db_qa_pair.answer,
                        sources=sources,
                        confidence_score=db_qa_pair.confidence_score,
                        processing_time=db_qa_pair.processing_time,
                        timestamp=db_qa_pair.timestamp,
                        metadata=db_qa_pair.extra_metadata or {}
                    )
                    qa_pairs.append(qa_pair)
            
            logger.debug(f"获取到 {len(qa_pairs)} 个最近问答对")
            return qa_pairs
            
        except Exception as e:
            logger.error(f"获取最近问答对失败: {str(e)}")
            raise SessionError(f"获取最近问答对失败: {str(e)}")
    
    async def delete_qa_pair(self, qa_pair_id: str) -> bool:
        """
        删除单个问答对
        
        Args:
            qa_pair_id: 问答对ID
            
        Returns:
            删除是否成功
        """
        try:
            logger.info(f"删除问答对: {qa_pair_id}")
            
            with self.db_manager.get_session_context() as db_session:
                qa_pair_crud = QAPairCRUD(db_session)
                session_crud = SessionCRUD(db_session)
                
                # 获取问答对信息
                db_qa_pair = qa_pair_crud.get_qa_pair(qa_pair_id)
                if not db_qa_pair:
                    logger.warning(f"问答对不存在: {qa_pair_id}")
                    return False
                
                session_id = db_qa_pair.session_id
                
                # 删除问答对
                success = qa_pair_crud.delete_qa_pair(qa_pair_id)
                
                if success:
                    # 更新会话的问答对数量
                    session = await self.get_session(session_id)
                    if session and session.qa_count > 0:
                        session.qa_count -= 1
                        session_crud.update_session(session)
                    
                    logger.info(f"问答对删除成功: {qa_pair_id}")
                else:
                    logger.warning(f"问答对删除失败: {qa_pair_id}")
                
                return success
            
        except Exception as e:
            logger.error(f"删除问答对失败: {str(e)}")
            raise SessionError(f"删除问答对失败: {str(e)}")
    
    async def get_session_statistics(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话统计信息
        """
        try:
            logger.debug(f"获取会话统计: {session_id}")
            
            session = await self.get_session(session_id)
            if not session:
                raise SessionError(f"会话不存在: {session_id}")
            
            with self.db_manager.get_session_context() as db_session:
                qa_pair_crud = QAPairCRUD(db_session)
                
                # 获取问答对统计
                qa_pairs = qa_pair_crud.get_session_qa_pairs(session_id, limit=None)
                
                # 计算统计信息
                total_qa_pairs = len(qa_pairs)
                avg_confidence = 0.0
                avg_processing_time = 0.0
                
                if qa_pairs:
                    total_confidence = sum(qa.confidence_score for qa in qa_pairs)
                    total_processing_time = sum(qa.processing_time for qa in qa_pairs)
                    avg_confidence = total_confidence / total_qa_pairs
                    avg_processing_time = total_processing_time / total_qa_pairs
                
                # 获取最新和最旧的问答对时间
                latest_timestamp = None
                oldest_timestamp = None
                if qa_pairs:
                    timestamps = [qa.timestamp for qa in qa_pairs]
                    latest_timestamp = max(timestamps)
                    oldest_timestamp = min(timestamps)
            
            return {
                "session_id": session_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "total_qa_pairs": total_qa_pairs,
                "average_confidence_score": round(avg_confidence, 4),
                "average_processing_time": round(avg_processing_time, 3),
                "latest_qa_timestamp": latest_timestamp,
                "oldest_qa_timestamp": oldest_timestamp,
                "session_duration_hours": (session.last_activity - session.created_at).total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"获取会话统计失败: {str(e)}")
            raise SessionError(f"获取会话统计失败: {str(e)}")
    
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Session]:
        """
        列出会话
        
        Args:
            user_id: 用户ID（可选）
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            会话列表
        """
        try:
            logger.debug(f"列出会话，用户ID: {user_id}, limit={limit}, offset={offset}")
            
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                db_sessions = session_crud.list_sessions(user_id, limit, offset)
                
                # 转换为模型对象并过滤过期会话
                active_sessions = []
                for db_session_obj in db_sessions:
                    session = Session(
                        id=db_session_obj.id,
                        created_at=db_session_obj.created_at,
                        last_activity=db_session_obj.last_activity,
                        qa_count=db_session_obj.qa_count
                    )
                    
                    if not self._is_session_expired(session):
                        active_sessions.append(session)
                    else:
                        # 异步删除过期会话
                        await self.delete_session(session.id)
            
            logger.debug(f"返回 {len(active_sessions)} 个活跃会话")
            return active_sessions
            
        except Exception as e:
            logger.error(f"列出会话失败: {str(e)}")
            raise SessionError(f"列出会话失败: {str(e)}")
    
    def _is_session_expired(self, session: Session) -> bool:
        """检查会话是否过期"""
        if self.session_timeout_hours <= 0:
            return False
        
        timeout_delta = timedelta(hours=self.session_timeout_hours)
        return datetime.now() - session.last_activity > timeout_delta
    
    async def _cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        try:
            logger.info("开始清理过期会话")
            
            if self.session_timeout_hours <= 0:
                logger.debug("会话超时未启用，跳过清理")
                return
            
            cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
            
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                expired_sessions = session_crud.get_expired_sessions(cutoff_time)
                
                cleaned_count = 0
                for session in expired_sessions:
                    await self._delete_session_with_crud(session.id, session_crud, db_session)
                    cleaned_count += 1
            
            # 更新统计
            self.stats['cleanup_runs'] += 1
            self.stats['last_cleanup'] = datetime.now()
            
            logger.info(f"清理完成，删除了 {cleaned_count} 个过期会话")
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {str(e)}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                qa_pair_crud = QAPairCRUD(db_session)
                
                # 获取数据库统计
                total_sessions = session_crud.count_total_sessions()
                total_qa_pairs = qa_pair_crud.count_total_qa_pairs()
            
            return {
                "service_name": "SessionService",
                "total_sessions": total_sessions,
                "total_qa_pairs": total_qa_pairs,
                "sessions_created": self.stats['sessions_created'],
                "sessions_deleted": self.stats['sessions_deleted'],
                "qa_pairs_saved": self.stats['qa_pairs_saved'],
                "cleanup_runs": self.stats['cleanup_runs'],
                "last_cleanup": self.stats['last_cleanup'].isoformat() if self.stats['last_cleanup'] else None,
                "config": {
                    "max_sessions_per_user": self.max_sessions_per_user,
                    "session_timeout_hours": self.session_timeout_hours,
                    "max_qa_pairs_per_session": self.max_qa_pairs_per_session,
                    "auto_cleanup_enabled": self.auto_cleanup_enabled,
                    "cleanup_interval_hours": self.cleanup_interval_hours
                }
            }
        except Exception as e:
            logger.error(f"获取服务统计失败: {str(e)}")
            return {
                "service_name": "SessionService",
                "error": str(e)
            }
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            会话统计信息字典
        """
        try:
            logger.debug("获取会话统计信息")
            
            with self.db_manager.get_session_context() as db_session:
                session_crud = SessionCRUD(db_session)
                qa_pair_crud = QAPairCRUD(db_session)
                
                # 获取基本统计
                total_sessions = session_crud.count_total_sessions()
                total_qa_pairs = qa_pair_crud.count_total_qa_pairs()
                
                # 获取活跃会话数（未过期的会话）
                active_sessions = 0
                if self.session_timeout_hours > 0:
                    cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
                    active_sessions = session_crud.count_active_sessions(cutoff_time)
                else:
                    active_sessions = total_sessions
                
                # 计算平均问答对数
                avg_qa_per_session = 0.0
                if total_sessions > 0:
                    avg_qa_per_session = total_qa_pairs / total_sessions
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_qa_pairs": total_qa_pairs,
                "avg_qa_per_session": round(avg_qa_per_session, 2)
            }
            
        except Exception as e:
            logger.error(f"获取会话统计失败: {str(e)}")
            raise SessionError(f"获取会话统计失败: {str(e)}")
    
    async def test_session_management(self, test_question: str = "测试问题") -> Dict[str, Any]:
        """
        测试会话管理功能
        
        Args:
            test_question: 测试问题
            
        Returns:
            测试结果
        """
        try:
            logger.info("开始测试会话管理功能")
            
            # 创建测试会话
            session_id = await self.create_session("test_user")
            
            # 获取会话信息
            session = await self.get_session(session_id)
            
            # 创建测试QA响应
            from ..models.qa import QAResponse, QAStatus
            test_qa_response = QAResponse(
                question=test_question,
                answer="这是一个测试答案",
                sources=[],
                confidence_score=0.8,
                processing_time=1.0,
                status=QAStatus.COMPLETED
            )
            
            # 保存问答对
            save_success = await self.save_qa_pair(session_id, test_qa_response)
            
            # 获取会话历史
            history = await self.get_session_history(session_id)
            
            # 清理测试数据
            delete_success = await self.delete_session(session_id)
            
            return {
                "success": True,
                "session_created": session_id,
                "session_retrieved": session is not None,
                "qa_pair_saved": save_success,
                "history_count": len(history),
                "session_deleted": delete_success,
                "test_completed": True
            }
            
        except Exception as e:
            logger.error(f"会话管理测试失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "test_completed": False
            }