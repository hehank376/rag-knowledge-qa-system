"""
文档相关数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import uuid


class DocumentStatus(str, Enum):
    """文档处理状态"""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DocumentInfo(BaseModel):
    """文档信息模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="文档唯一标识")
    filename: str = Field(..., min_length=1, max_length=255, description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., gt=0, description="文件大小(字节)")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")
    status: DocumentStatus = Field(default=DocumentStatus.PROCESSING, description="处理状态")
    chunk_count: int = Field(default=0, ge=0, description="文本块数量")
    error_message: Optional[str] = Field(default="", description="错误信息")
    file_path: Optional[str] = Field(default="", description="文件存储路径")
    processing_time: float = Field(default=0.0, ge=0, description="处理时间(秒)")

    @field_validator('file_type')
    @classmethod
    def validate_file_type(cls, v):
        """验证文件类型"""
        allowed_types = ['pdf', 'txt', 'docx', 'md']
        if v.lower() not in allowed_types:
            raise ValueError(f'不支持的文件类型: {v}. 支持的类型: {allowed_types}')
        return v.lower()

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """验证文件名"""
        if not v.strip():
            raise ValueError('文件名不能为空')
        # 检查文件名中的非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in v for char in illegal_chars):
            raise ValueError(f'文件名包含非法字符: {illegal_chars}')
        return v.strip()

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class TextChunk(BaseModel):
    """文本块模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="文本块唯一标识")
    document_id: str = Field(..., description="所属文档ID")
    content: str = Field(..., min_length=1, description="文本内容")
    chunk_index: int = Field(..., ge=0, description="文本块索引")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """验证文本内容"""
        if not v.strip():
            raise ValueError('文本内容不能为空')
        if len(v) > 10000:  # 限制单个文本块最大长度
            raise ValueError('文本块长度不能超过10000字符')
        return v.strip()

    @field_validator('document_id')
    @classmethod
    def validate_document_id(cls, v):
        """验证文档ID格式"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('无效的文档ID格式')
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )