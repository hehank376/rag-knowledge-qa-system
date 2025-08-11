"""
问答相关数据模型
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import uuid


class QAStatus(str, Enum):
    """问答状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceInfo(BaseModel):
    """源文档信息"""
    document_id: str = Field(..., description="文档ID")
    document_name: str = Field(..., description="文档名称")
    chunk_id: str = Field(..., description="文本块ID")
    chunk_content: str = Field(..., description="文本块内容")
    chunk_index: int = Field(..., ge=0, description="文本块索引")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @field_validator('document_id', 'chunk_id')
    @classmethod
    def validate_ids(cls, v):
        """验证ID格式"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('无效的ID格式')
        return v

    @field_validator('document_name')
    @classmethod
    def validate_document_name(cls, v):
        """验证文档名称"""
        if not v.strip():
            raise ValueError('文档名称不能为空')
        return v.strip()

    @field_validator('chunk_content')
    @classmethod
    def validate_chunk_content(cls, v):
        """验证文本块内容"""
        if not v.strip():
            raise ValueError('文本块内容不能为空')
        return v.strip()

    @field_validator('similarity_score')
    @classmethod
    def validate_similarity_score(cls, v):
        """验证相似度分数"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('相似度分数必须在0.0到1.0之间')
        return round(v, 4)

    model_config = ConfigDict(
        json_encoders={
            float: lambda v: round(v, 4)
        }
    )


class QAResponse(BaseModel):
    """问答响应模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="响应唯一标识")
    question: str = Field(..., description="原始问题")
    answer: str = Field(..., description="答案")
    sources: List[SourceInfo] = Field(default_factory=list, description="源文档信息列表")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度分数")
    processing_time: float = Field(..., ge=0.0, description="处理时间(秒)")
    status: QAStatus = Field(default=QAStatus.COMPLETED, description="处理状态")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @field_validator('question', 'answer')
    @classmethod
    def validate_qa_content(cls, v):
        """验证问答内容"""
        if not v.strip():
            raise ValueError('问题和答案不能为空')
        return v.strip()

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        """验证置信度分数"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('置信度分数必须在0.0到1.0之间')
        return round(v, 4)

    @field_validator('processing_time')
    @classmethod
    def validate_processing_time(cls, v):
        """验证处理时间"""
        if v < 0:
            raise ValueError('处理时间不能为负数')
        return round(v, 3)

    model_config = ConfigDict(
        json_encoders={
            float: lambda v: round(v, 4)
        }
    )


class QAPair(BaseModel):
    """问答对模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="问答对唯一标识")
    session_id: str = Field(..., description="会话ID")
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    sources: List[SourceInfo] = Field(default_factory=list, description="源文档信息列表")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度分数")
    processing_time: float = Field(default=0.0, ge=0.0, description="处理时间(秒)")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @field_validator('question', 'answer')
    @classmethod
    def validate_qa_content(cls, v):
        """验证问答内容"""
        if not v.strip():
            raise ValueError('问题和答案不能为空')
        return v.strip()

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """验证会话ID格式"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('无效的会话ID格式')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            float: lambda v: round(v, 4)
        }
    )


class Session(BaseModel):
    """会话模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="会话唯一标识")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    qa_count: int = Field(default=0, ge=0, description="问答对数量")

    @model_validator(mode='after')
    def validate_last_activity(self):
        """验证最后活动时间"""
        if self.last_activity < self.created_at:
            raise ValueError('最后活动时间不能早于创建时间')
        return self

    @field_validator('qa_count')
    @classmethod
    def validate_qa_count(cls, v):
        """验证问答对数量"""
        if v < 0:
            raise ValueError('问答对数量不能为负数')
        return v

    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )