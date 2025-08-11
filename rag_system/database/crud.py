"""
数据库CRUD操作
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from ..models.document import DocumentInfo, DocumentStatus as ModelDocumentStatus
from ..models.qa import QAPair, Session as ModelSession
from ..utils.exceptions import DocumentError, SessionError
from .models import DocumentModel, QAPairModel, SessionModel, DocumentStatus


class BaseCRUD:
    """基础CRUD操作类"""
    
    def __init__(self, session: Session):
        self.session = session


class DocumentCRUD(BaseCRUD):
    """文档CRUD操作"""
    
    def create_document(self, document_info: DocumentInfo) -> DocumentModel:
        """创建文档记录"""
        try:
            # 转换状态枚举
            status_mapping = {
                ModelDocumentStatus.PROCESSING: DocumentStatus.PROCESSING,
                ModelDocumentStatus.READY: DocumentStatus.READY,
                ModelDocumentStatus.ERROR: DocumentStatus.ERROR
            }
            
            db_document = DocumentModel(
                id=document_info.id,
                filename=document_info.filename,
                file_type=document_info.file_type,
                file_size=document_info.file_size,
                upload_time=document_info.upload_time,
                status=status_mapping[document_info.status],
                chunk_count=document_info.chunk_count,
                error_message=document_info.error_message
            )
            
            self.session.add(db_document)
            self.session.commit()
            self.session.refresh(db_document)
            
            return db_document
            
        except Exception as e:
            self.session.rollback()
            raise DocumentError(f"创建文档记录失败: {str(e)}")
    
    def get_document(self, doc_id: str) -> Optional[DocumentModel]:
        """获取文档记录"""
        try:
            return self.session.query(DocumentModel).filter(
                DocumentModel.id == doc_id
            ).first()
        except Exception as e:
            raise DocumentError(f"获取文档记录失败: {str(e)}")
    
    def get_documents(self, limit: int = 100, offset: int = 0) -> List[DocumentModel]:
        """获取文档列表"""
        try:
            return self.session.query(DocumentModel).order_by(
                desc(DocumentModel.upload_time)
            ).limit(limit).offset(offset).all()
        except Exception as e:
            raise DocumentError(f"获取文档列表失败: {str(e)}")
    
    def update_document_status(self, doc_id: str, status: DocumentStatus, 
                             error_message: Optional[str] = None) -> bool:
        """更新文档状态"""
        try:
            document = self.get_document(doc_id)
            if not document:
                return False
            
            document.status = status
            if error_message:
                document.error_message = error_message
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise DocumentError(f"更新文档状态失败: {str(e)}")
    
    def update_document_chunk_count(self, doc_id: str, chunk_count: int) -> bool:
        """更新文档块数量"""
        try:
            document = self.get_document(doc_id)
            if not document:
                return False
            
            document.chunk_count = chunk_count
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise DocumentError(f"更新文档块数量失败: {str(e)}")
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档记录"""
        try:
            document = self.get_document(doc_id)
            if not document:
                return False
            
            self.session.delete(document)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise DocumentError(f"删除文档记录失败: {str(e)}")
    
    def count_documents(self) -> int:
        """统计文档数量"""
        try:
            return self.session.query(DocumentModel).count()
        except Exception as e:
            raise DocumentError(f"统计文档数量失败: {str(e)}")


class SessionCRUD(BaseCRUD):
    """会话CRUD操作"""
    
    def create_session(self, session_id: Optional[str] = None) -> SessionModel:
        """创建会话记录"""
        try:
            db_session = SessionModel()
            if session_id:
                db_session.id = session_id
            
            self.session.add(db_session)
            self.session.commit()
            self.session.refresh(db_session)
            
            return db_session
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"创建会话记录失败: {str(e)}")
    
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """获取会话记录"""
        try:
            return self.session.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()
        except Exception as e:
            raise SessionError(f"获取会话记录失败: {str(e)}")
    
    def get_sessions(self, limit: int = 100, offset: int = 0) -> List[SessionModel]:
        """获取会话列表"""
        try:
            return self.session.query(SessionModel).order_by(
                desc(SessionModel.last_activity)
            ).limit(limit).offset(offset).all()
        except Exception as e:
            raise SessionError(f"获取会话列表失败: {str(e)}")
    
    def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.update_activity()
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"更新会话活动时间失败: {str(e)}")
    
    def increment_qa_count(self, session_id: str) -> bool:
        """增加会话问答数量"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.qa_count += 1
            session.update_activity()
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"增加会话问答数量失败: {str(e)}")
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话记录"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            self.session.delete(session)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"删除会话记录失败: {str(e)}")
    
    def create_session(self, session: 'ModelSession', user_id: Optional[str] = None) -> bool:
        """创建会话记录（使用Session模型）"""
        try:
            db_session = SessionModel(
                id=session.id,
                created_at=session.created_at,
                last_activity=session.last_activity,
                qa_count=session.qa_count,
                user_id=user_id
            )
            
            self.session.add(db_session)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"创建会话记录失败: {str(e)}")
    
    def update_session(self, session: 'ModelSession') -> bool:
        """更新会话记录"""
        try:
            db_session = self.get_session(session.id)
            if not db_session:
                return False
            
            db_session.last_activity = session.last_activity
            db_session.qa_count = session.qa_count
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"更新会话记录失败: {str(e)}")
    
    def list_sessions(self, user_id: Optional[str] = None, limit: Optional[int] = None, 
                     offset: int = 0) -> List[SessionModel]:
        """列出会话"""
        try:
            query = self.session.query(SessionModel)
            
            if user_id:
                query = query.filter(SessionModel.user_id == user_id)
            
            query = query.order_by(desc(SessionModel.last_activity))
            
            if limit:
                query = query.limit(limit)
            
            if offset > 0:
                query = query.offset(offset)
            
            return query.all()
            
        except Exception as e:
            raise SessionError(f"列出会话失败: {str(e)}")
    
    def count_user_sessions(self, user_id: str) -> int:
        """统计用户会话数量"""
        try:
            return self.session.query(SessionModel).filter(
                SessionModel.user_id == user_id
            ).count()
        except Exception as e:
            raise SessionError(f"统计用户会话数量失败: {str(e)}")
    
    def get_oldest_user_sessions(self, user_id: str, count: int) -> List[SessionModel]:
        """获取用户最旧的会话"""
        try:
            return self.session.query(SessionModel).filter(
                SessionModel.user_id == user_id
            ).order_by(SessionModel.created_at).limit(count).all()
        except Exception as e:
            raise SessionError(f"获取最旧用户会话失败: {str(e)}")
    
    def get_expired_sessions(self, cutoff_time: datetime) -> List[SessionModel]:
        """获取过期会话"""
        try:
            return self.session.query(SessionModel).filter(
                SessionModel.last_activity < cutoff_time
            ).all()
        except Exception as e:
            raise SessionError(f"获取过期会话失败: {str(e)}")
    
    def count_total_sessions(self) -> int:
        """统计总会话数量"""
        try:
            return self.session.query(SessionModel).count()
        except Exception as e:
            raise SessionError(f"统计总会话数量失败: {str(e)}")
    
    def count_active_sessions(self, cutoff_time: datetime) -> int:
        """统计活跃会话数量（在指定时间之后有活动的会话）"""
        try:
            return self.session.query(SessionModel).filter(
                SessionModel.last_activity >= cutoff_time
            ).count()
        except Exception as e:
            raise SessionError(f"统计活跃会话数量失败: {str(e)}")


class QAPairCRUD(BaseCRUD):
    """问答对CRUD操作"""
    
    def create_qa_pair(self, qa_pair: QAPair) -> QAPairModel:
        """创建问答对记录"""
        try:
            # 转换源文档信息为JSON格式
            sources_json = []
            for source in qa_pair.sources:
                sources_json.append({
                    "document_id": source.document_id,
                    "document_name": source.document_name,
                    "chunk_id": source.chunk_id,
                    "chunk_content": source.chunk_content,
                    "chunk_index": source.chunk_index,
                    "similarity_score": source.similarity_score,
                    "metadata": source.metadata
                })
            
            db_qa_pair = QAPairModel(
                id=qa_pair.id,
                session_id=qa_pair.session_id,
                question=qa_pair.question,
                answer=qa_pair.answer,
                sources=sources_json,
                confidence_score=qa_pair.confidence_score,
                processing_time=qa_pair.processing_time,
                timestamp=qa_pair.timestamp,
                extra_metadata=qa_pair.metadata
            )
            
            self.session.add(db_qa_pair)
            self.session.commit()
            self.session.refresh(db_qa_pair)
            
            return db_qa_pair
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"创建问答对记录失败: {str(e)}")
    
    def get_qa_pair(self, qa_id: str) -> Optional[QAPairModel]:
        """获取问答对记录"""
        try:
            return self.session.query(QAPairModel).filter(
                QAPairModel.id == qa_id
            ).first()
        except Exception as e:
            raise SessionError(f"获取问答对记录失败: {str(e)}")
    
    def get_session_qa_pairs(self, session_id: str, limit: int = 100, 
                           offset: int = 0) -> List[QAPairModel]:
        """获取会话的问答对列表"""
        try:
            return self.session.query(QAPairModel).filter(
                QAPairModel.session_id == session_id
            ).order_by(desc(QAPairModel.timestamp)).limit(limit).offset(offset).all()
        except Exception as e:
            raise SessionError(f"获取会话问答对列表失败: {str(e)}")
    
    def get_recent_qa_pairs(self, limit: int = 50) -> List[QAPairModel]:
        """获取最近的问答对"""
        try:
            return self.session.query(QAPairModel).order_by(
                desc(QAPairModel.timestamp)
            ).limit(limit).all()
        except Exception as e:
            raise SessionError(f"获取最近问答对失败: {str(e)}")
    
    def search_qa_pairs(self, query: str, limit: int = 20) -> List[QAPairModel]:
        """搜索问答对"""
        try:
            return self.session.query(QAPairModel).filter(
                or_(
                    QAPairModel.question.contains(query),
                    QAPairModel.answer.contains(query)
                )
            ).order_by(desc(QAPairModel.timestamp)).limit(limit).all()
        except Exception as e:
            raise SessionError(f"搜索问答对失败: {str(e)}")
    
    def delete_qa_pair(self, qa_id: str) -> bool:
        """删除问答对记录"""
        try:
            qa_pair = self.get_qa_pair(qa_id)
            if not qa_pair:
                return False
            
            self.session.delete(qa_pair)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"删除问答对记录失败: {str(e)}")
    
    def delete_session_qa_pairs(self, session_id: str) -> int:
        """删除会话的所有问答对"""
        try:
            count = self.session.query(QAPairModel).filter(
                QAPairModel.session_id == session_id
            ).count()
            
            self.session.query(QAPairModel).filter(
                QAPairModel.session_id == session_id
            ).delete()
            
            self.session.commit()
            return count
            
        except Exception as e:
            self.session.rollback()
            raise SessionError(f"删除会话问答对失败: {str(e)}")
    
    def count_session_qa_pairs(self, session_id: str) -> int:
        """统计会话问答对数量"""
        try:
            return self.session.query(QAPairModel).filter(
                QAPairModel.session_id == session_id
            ).count()
        except Exception as e:
            raise SessionError(f"统计会话问答对数量失败: {str(e)}")
    
    def get_oldest_session_qa_pairs(self, session_id: str, count: int) -> List[QAPairModel]:
        """获取会话中最旧的问答对"""
        try:
            return self.session.query(QAPairModel).filter(
                QAPairModel.session_id == session_id
            ).order_by(QAPairModel.timestamp).limit(count).all()
        except Exception as e:
            raise SessionError(f"获取最旧问答对失败: {str(e)}")
    
    def search_qa_pairs(self, query: str, session_id: Optional[str] = None, 
                       user_id: Optional[str] = None, limit: Optional[int] = None,
                       offset: int = 0) -> List[QAPairModel]:
        """搜索问答对（扩展版本）"""
        try:
            db_query = self.session.query(QAPairModel)
            
            # 添加文本搜索条件
            db_query = db_query.filter(
                or_(
                    QAPairModel.question.contains(query),
                    QAPairModel.answer.contains(query)
                )
            )
            
            # 添加会话过滤
            if session_id:
                db_query = db_query.filter(QAPairModel.session_id == session_id)
            
            # 添加用户过滤（需要join会话表）
            if user_id:
                from .models import SessionModel
                db_query = db_query.join(SessionModel).filter(
                    SessionModel.user_id == user_id
                )
            
            # 排序和分页
            db_query = db_query.order_by(desc(QAPairModel.timestamp))
            
            if limit:
                db_query = db_query.limit(limit)
            
            if offset > 0:
                db_query = db_query.offset(offset)
            
            return db_query.all()
            
        except Exception as e:
            raise SessionError(f"搜索问答对失败: {str(e)}")
    
    def count_total_qa_pairs(self) -> int:
        """统计总问答对数量"""
        try:
            return self.session.query(QAPairModel).count()
        except Exception as e:
            raise SessionError(f"统计总问答对数量失败: {str(e)}")
    
    def count_session_qa_pairs(self, session_id: str) -> int:
        """统计会话问答对数量"""
        try:
            return self.session.query(QAPairModel).filter(
                QAPairModel.session_id == session_id
            ).count()
        except Exception as e:
            raise SessionError(f"统计会话问答对数量失败: {str(e)}")