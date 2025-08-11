"""
数据库模型定义
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid

Base = declarative_base()


class DocumentStatus(enum.Enum):
    """文档处理状态"""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DocumentModel(Base):
    """文档数据库模型"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_time = Column(DateTime, default=datetime.now, nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PROCESSING, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # 关联的问答对
    qa_pairs = relationship("QAPairModel", back_populates="document", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
            "status": self.status.value if self.status else None,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message
        }


class SessionModel(Base):
    """会话数据库模型"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_activity = Column(DateTime, default=datetime.now, nullable=False)
    qa_count = Column(Integer, default=0, nullable=False)
    user_id = Column(String(255), nullable=True)  # 用户ID，可选
    
    # 关联的问答对
    qa_pairs = relationship("QAPairModel", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "qa_count": self.qa_count,
            "user_id": self.user_id
        }
    
    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity = datetime.now()


class QAPairModel(Base):
    """问答对数据库模型"""
    __tablename__ = "qa_pairs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # 存储源文档信息的JSON
    confidence_score = Column(Float, default=0.0, nullable=False)
    processing_time = Column(Float, default=0.0, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    extra_metadata = Column(JSON, nullable=True)  # 额外元数据
    
    # 外键关系
    session = relationship("SessionModel", back_populates="qa_pairs")
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    document = relationship("DocumentModel", back_populates="qa_pairs")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question": self.question,
            "answer": self.answer,
            "sources": self.sources or [],
            "confidence_score": self.confidence_score,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.extra_metadata or {}
        }