"""
向量相关数据模型
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid


class Vector(BaseModel):
    """向量模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="向量唯一标识")
    document_id: str = Field(..., description="所属文档ID")
    chunk_id: str = Field(..., description="所属文本块ID")
    embedding: List[float] = Field(..., description="向量嵌入")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @field_validator('embedding')
    @classmethod
    def validate_embedding(cls, v):
        """验证向量嵌入"""
        if not v:
            raise ValueError('向量嵌入不能为空')
        if len(v) == 0:
            raise ValueError('向量维度不能为0')
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError('向量嵌入必须是数值类型')
        return v

    @field_validator('document_id', 'chunk_id')
    @classmethod
    def validate_ids(cls, v):
        """验证ID格式"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('无效的ID格式')
        return v

    model_config = ConfigDict(
        json_encoders={
            float: lambda v: round(v, 6)  # 限制浮点数精度
        }
    )


class SearchResult(BaseModel):
    """搜索结果模型"""
    chunk_id: str = Field(..., description="文本块ID")
    document_id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文本内容")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @field_validator('similarity_score')
    @classmethod
    def validate_similarity_score(cls, v):
        """验证相似度分数"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('相似度分数必须在0.0到1.0之间')
        return round(v, 4)  # 保留4位小数

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """验证内容"""
        if not v.strip():
            raise ValueError('内容不能为空')
        return v.strip()

    @field_validator('document_id', 'chunk_id')
    @classmethod
    def validate_ids(cls, v):
        """验证ID格式"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('无效的ID格式')
        return v

    model_config = ConfigDict(
        json_encoders={
            float: lambda v: round(v, 4)
        }
    )