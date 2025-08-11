"""
向量模型单元测试
"""
import pytest
from pydantic import ValidationError
import uuid

from rag_system.models.vector import Vector, SearchResult


class TestVector:
    """Vector模型测试"""

    def test_create_vector_with_defaults(self):
        """测试使用默认值创建向量"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        vector = Vector(
            document_id=doc_id,
            chunk_id=chunk_id,
            embedding=embedding
        )
        
        assert vector.document_id == doc_id
        assert vector.chunk_id == chunk_id
        assert vector.embedding == embedding
        assert vector.metadata == {}
        # 验证ID是有效的UUID
        uuid.UUID(vector.id)

    def test_create_vector_with_all_fields(self):
        """测试创建包含所有字段的向量"""
        vector_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        embedding = [0.1, 0.2, 0.3]
        metadata = {"model": "text-embedding-ada-002", "dimension": 3}
        
        vector = Vector(
            id=vector_id,
            document_id=doc_id,
            chunk_id=chunk_id,
            embedding=embedding,
            metadata=metadata
        )
        
        assert vector.id == vector_id
        assert vector.document_id == doc_id
        assert vector.chunk_id == chunk_id
        assert vector.embedding == embedding
        assert vector.metadata == metadata

    def test_embedding_validation(self):
        """测试向量嵌入验证"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        # 测试空向量
        with pytest.raises(ValidationError) as exc_info:
            Vector(document_id=doc_id, chunk_id=chunk_id, embedding=[])
        assert "向量嵌入不能为空" in str(exc_info.value)
        
        # 测试None向量
        with pytest.raises(ValidationError) as exc_info:
            Vector(document_id=doc_id, chunk_id=chunk_id, embedding=None)
        assert "Input should be a valid list" in str(exc_info.value)
        
        # 测试包含非数值类型的向量
        with pytest.raises(ValidationError) as exc_info:
            Vector(document_id=doc_id, chunk_id=chunk_id, embedding=[0.1, "invalid", 0.3])
        assert "Input should be a valid number" in str(exc_info.value)
        
        # 测试有效向量（包含整数和浮点数）
        vector = Vector(document_id=doc_id, chunk_id=chunk_id, embedding=[1, 2.5, 3.0])
        assert vector.embedding == [1, 2.5, 3.0]

    def test_id_validation(self):
        """测试ID验证"""
        embedding = [0.1, 0.2, 0.3]
        
        # 测试无效的document_id
        with pytest.raises(ValidationError) as exc_info:
            Vector(document_id="invalid-uuid", chunk_id=str(uuid.uuid4()), embedding=embedding)
        assert "无效的ID格式" in str(exc_info.value)
        
        # 测试无效的chunk_id
        with pytest.raises(ValidationError) as exc_info:
            Vector(document_id=str(uuid.uuid4()), chunk_id="invalid-uuid", embedding=embedding)
        assert "无效的ID格式" in str(exc_info.value)
        
        # 测试有效的ID
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        vector = Vector(document_id=doc_id, chunk_id=chunk_id, embedding=embedding)
        assert vector.document_id == doc_id
        assert vector.chunk_id == chunk_id

    def test_json_serialization(self):
        """测试JSON序列化"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        embedding = [0.123456789, 0.987654321]
        metadata = {"test": "value"}
        
        vector = Vector(
            document_id=doc_id,
            chunk_id=chunk_id,
            embedding=embedding,
            metadata=metadata
        )
        
        json_data = vector.model_dump()
        assert "id" in json_data
        assert json_data["document_id"] == doc_id
        assert json_data["chunk_id"] == chunk_id
        assert json_data["metadata"] == metadata
        # 验证浮点数精度限制
        assert all(isinstance(x, float) for x in json_data["embedding"])


class TestSearchResult:
    """SearchResult模型测试"""

    def test_create_search_result(self):
        """测试创建搜索结果"""
        chunk_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        content = "This is test content"
        similarity_score = 0.85
        metadata = {"page": 1}
        
        result = SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content=content,
            similarity_score=similarity_score,
            metadata=metadata
        )
        
        assert result.chunk_id == chunk_id
        assert result.document_id == doc_id
        assert result.content == content
        assert result.similarity_score == 0.85
        assert result.metadata == metadata

    def test_similarity_score_validation(self):
        """测试相似度分数验证"""
        chunk_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        content = "test content"
        
        # 测试负数相似度分数
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                content=content,
                similarity_score=-0.1
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        # 测试大于1的相似度分数
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                content=content,
                similarity_score=1.1
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)
        
        # 测试边界值
        result1 = SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content=content,
            similarity_score=0.0
        )
        assert result1.similarity_score == 0.0
        
        result2 = SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content=content,
            similarity_score=1.0
        )
        assert result2.similarity_score == 1.0
        
        # 测试精度限制
        result3 = SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content=content,
            similarity_score=0.123456789
        )
        assert result3.similarity_score == 0.1235

    def test_content_validation(self):
        """测试内容验证"""
        chunk_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        
        # 测试空内容
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                content="",
                similarity_score=0.5
            )
        assert "内容不能为空" in str(exc_info.value)
        
        # 测试只有空格的内容
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                content="   ",
                similarity_score=0.5
            )
        assert "内容不能为空" in str(exc_info.value)
        
        # 测试内容自动去除空格
        result = SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content="  test content  ",
            similarity_score=0.5
        )
        assert result.content == "test content"

    def test_id_validation(self):
        """测试ID验证"""
        content = "test content"
        similarity_score = 0.5
        
        # 测试无效的chunk_id
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                chunk_id="invalid-uuid",
                document_id=str(uuid.uuid4()),
                content=content,
                similarity_score=similarity_score
            )
        assert "无效的ID格式" in str(exc_info.value)
        
        # 测试无效的document_id
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id="invalid-uuid",
                content=content,
                similarity_score=similarity_score
            )
        assert "无效的ID格式" in str(exc_info.value)

    def test_json_serialization(self):
        """测试JSON序列化"""
        chunk_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        content = "test content"
        similarity_score = 0.123456789
        metadata = {"test": "value"}
        
        result = SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content=content,
            similarity_score=similarity_score,
            metadata=metadata
        )
        
        json_data = result.model_dump()
        assert json_data["chunk_id"] == chunk_id
        assert json_data["document_id"] == doc_id
        assert json_data["content"] == content
        assert json_data["metadata"] == metadata
        # 验证浮点数精度限制
        assert json_data["similarity_score"] == 0.1235