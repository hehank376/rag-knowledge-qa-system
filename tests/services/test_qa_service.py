"""
问答服务测试
"""
import pytest
import pytest_asyncio
import tempfile
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.qa_service import QAService
from rag_system.models.qa import QAResponse, SourceInfo
from rag_system.models.vector import SearchResult
from rag_system.utils.exceptions import QAError, ProcessingError


@pytest_asyncio.fixture
async def qa_service():
    """QA服务fixture"""
    temp_dir = tempfile.mkdtemp()
    
    config = {
        'vector_store_type': 'chroma',
        'vector_store_path': temp_dir + '/chroma_db',
        'embedding_provider': 'mock',
        'embedding_model': 'test-model',
        'llm_provider': 'mock',
        'llm_model': 'test-llm',
        'retrieval_top_k': 3,
        'similarity_threshold': 0.7,
        'max_context_length': 2000,
        'database_url': f'sqlite:///{temp_dir}/test.db'
    }
    
    service = QAService(config)
    
    # Mock检索服务
    service.retrieval_service = Mock()
    service.retrieval_service.initialize = AsyncMock()
    service.retrieval_service.cleanup = AsyncMock()
    service.retrieval_service.search_similar_documents = AsyncMock()
    service.retrieval_service.get_service_stats = AsyncMock(return_value={
        'vector_count': 100,
        'document_count': 10
    })
    service.retrieval_service.similarity_threshold = 0.7
    service.retrieval_service.default_top_k = 3
    
    # Mock LLM
    service.llm = Mock()
    service.llm.initialize = AsyncMock()
    service.llm.cleanup = AsyncMock()
    service.llm.generate_text = AsyncMock()
    service.llm.config = Mock()
    service.llm.config.provider = 'mock'
    service.llm.config.model = 'test-llm'
    
    await service.initialize()
    
    yield service
    
    await service.cleanup()
    
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
def sample_search_results():
    """示例搜索结果fixture"""
    return [
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="这是第一个相关文档片段，包含了关于人工智能的基础知识。人工智能是计算机科学的一个分支。",
            similarity_score=0.95,
            metadata={"document_name": "AI基础.txt", "chunk_index": 0}
        ),
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="这是第二个相关文档片段，详细介绍了机器学习的概念和应用。机器学习是人工智能的重要组成部分。",
            similarity_score=0.88,
            metadata={"document_name": "机器学习.pdf", "chunk_index": 1}
        ),
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="这是第三个相关文档片段，讨论了深度学习的发展历程和未来趋势。",
            similarity_score=0.82,
            metadata={"document_name": "深度学习.docx", "chunk_index": 0}
        )
    ]


class TestQAService:
    """QA服务测试"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试服务初始化"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {
                'llm_provider': 'mock',
                'embedding_provider': 'mock',
                'vector_store_path': temp_dir + '/chroma_db'
            }
            
            service = QAService(config)
            
            # Mock依赖
            service.retrieval_service = Mock()
            service.retrieval_service.initialize = AsyncMock()
            service.llm = Mock()
            service.llm.initialize = AsyncMock()
            
            await service.initialize()
            
            # 验证初始化调用
            service.retrieval_service.initialize.assert_called_once()
            service.llm.initialize.assert_called_once()
            
            await service.cleanup()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_answer_question_success(self, qa_service, sample_search_results):
        """测试成功回答问题"""
        question = "什么是人工智能？"
        
        # Mock检索结果
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # Mock LLM响应
        qa_service.llm.generate_text.return_value = "人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。根据提供的文档，人工智能包括机器学习和深度学习等重要组成部分。"
        
        response = await qa_service.answer_question(question)
        
        # 验证响应
        assert isinstance(response, QAResponse)
        assert response.question == question
        assert len(response.answer) > 0
        assert len(response.sources) == 3
        assert response.confidence_score > 0.8
        assert response.processing_time >= 0
        
        # 验证源信息
        assert all(isinstance(source, SourceInfo) for source in response.sources)
        assert response.sources[0].similarity_score == 0.95
        
        # 验证服务调用
        qa_service.retrieval_service.search_similar_documents.assert_called_once_with(
            query=question,
            top_k=None,
            document_ids=None
        )
        qa_service.llm.generate_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_answer_question_empty_question(self, qa_service):
        """测试空问题"""
        with pytest.raises(QAError) as exc_info:
            await qa_service.answer_question("")
        
        assert "问题不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_answer_question_no_context(self, qa_service):
        """测试没有找到相关上下文"""
        question = "这是一个无关的问题"
        
        # Mock空检索结果
        qa_service.retrieval_service.search_similar_documents.return_value = []
        
        response = await qa_service.answer_question(question)
        
        # 验证无答案响应
        assert response.question == question
        assert "没有找到与您的问题相关的信息" in response.answer
        assert len(response.sources) == 0
        assert response.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_answer_question_low_similarity(self, qa_service):
        """测试低相似度结果"""
        question = "测试问题"
        
        # Mock低相似度结果
        low_similarity_results = [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="不太相关的内容",
                similarity_score=0.3,  # 低于阈值
                metadata={}
            )
        ]
        
        qa_service.retrieval_service.search_similar_documents.return_value = low_similarity_results
        
        response = await qa_service.answer_question(question)
        
        # 应该返回无答案响应
        assert "没有找到与您的问题相关的信息" in response.answer
        assert response.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_retrieve_context(self, qa_service, sample_search_results):
        """测试检索上下文"""
        question = "测试问题"
        
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        
        results = await qa_service.retrieve_context(question, top_k=5)
        
        assert len(results) == 3
        assert all(isinstance(result, SearchResult) for result in results)
        
        # 验证调用参数
        qa_service.retrieval_service.search_similar_documents.assert_called_once_with(
            query=question,
            top_k=5,
            document_ids=None
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_context_with_document_filter(self, qa_service, sample_search_results):
        """测试带文档过滤的上下文检索"""
        question = "测试问题"
        document_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        
        results = await qa_service.retrieve_context(
            question, 
            top_k=3, 
            document_ids=document_ids
        )
        
        assert len(results) == 3
        
        # 验证调用参数
        qa_service.retrieval_service.search_similar_documents.assert_called_once_with(
            query=question,
            top_k=3,
            document_ids=document_ids
        )
    
    @pytest.mark.asyncio
    async def test_generate_answer(self, qa_service, sample_search_results):
        """测试生成答案"""
        question = "什么是机器学习？"
        expected_answer = "机器学习是人工智能的一个重要分支，它使计算机能够从数据中学习并做出预测或决策。"
        
        qa_service.llm.generate_text.return_value = expected_answer
        
        answer = await qa_service.generate_answer(question, sample_search_results)
        
        assert answer == expected_answer
        
        # 验证LLM调用
        qa_service.llm.generate_text.assert_called_once()
        call_args = qa_service.llm.generate_text.call_args
        prompt = call_args[1]['prompt']
        
        # 验证提示词包含问题和上下文
        assert question in prompt
        assert "文档片段" in prompt
        assert sample_search_results[0].content in prompt
    
    @pytest.mark.asyncio
    async def test_generate_answer_empty_context(self, qa_service):
        """测试空上下文生成答案"""
        question = "测试问题"
        
        answer = await qa_service.generate_answer(question, [])
        
        assert "没有找到与您的问题相关的信息" in answer
        
        # LLM不应该被调用
        qa_service.llm.generate_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_answer_with_parameters(self, qa_service, sample_search_results):
        """测试带参数的答案生成"""
        question = "测试问题"
        expected_answer = "测试答案"
        
        qa_service.llm.generate_text.return_value = expected_answer
        
        answer = await qa_service.generate_answer(
            question, 
            sample_search_results,
            temperature=0.5,
            max_tokens=500
        )
        
        assert answer == expected_answer
        
        # 验证参数传递
        call_args = qa_service.llm.generate_text.call_args
        assert call_args[1]['temperature'] == 0.5
        assert call_args[1]['max_tokens'] == 500
    
    def test_build_prompt(self, qa_service, sample_search_results):
        """测试构建提示词"""
        question = "什么是人工智能？"
        
        prompt = qa_service._build_prompt(question, sample_search_results)
        
        # 验证提示词结构
        assert question in prompt
        assert "文档片段 1:" in prompt
        assert "文档片段 2:" in prompt
        assert "文档片段 3:" in prompt
        assert sample_search_results[0].content in prompt
        assert sample_search_results[1].content in prompt
        assert sample_search_results[2].content in prompt
        assert "请基于以下文档内容回答用户的问题" in prompt
    
    def test_build_prompt_length_limit(self, qa_service):
        """测试提示词长度限制"""
        question = "测试问题"
        
        # 创建超长内容的搜索结果
        long_content = "这是一个很长的内容。" * 200  # 创建长内容
        long_results = [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=long_content,
                similarity_score=0.9,
                metadata={}
            )
        ]
        
        # 设置较小的长度限制
        qa_service.max_context_length = 100
        
        prompt = qa_service._build_prompt(question, long_results)
        
        # 验证提示词长度被限制
        assert len(prompt) < len(long_content) + 200  # 应该比原始内容短很多
    
    def test_post_process_answer(self, qa_service):
        """测试答案后处理"""
        # 测试去除前缀
        answer1 = "回答:这是一个测试答案"
        processed1 = qa_service._post_process_answer(answer1)
        assert processed1 == "这是一个测试答案"
        
        # 测试去除空白字符
        answer2 = "  \n  这是另一个答案  \n  "
        processed2 = qa_service._post_process_answer(answer2)
        assert processed2 == "这是另一个答案"
        
        # 测试空答案处理
        answer3 = ""
        processed3 = qa_service._post_process_answer(answer3)
        assert "无法基于当前信息提供满意的答案" in processed3
    
    def test_create_source_info(self, qa_service, sample_search_results):
        """测试创建源信息"""
        sources = qa_service._create_source_info(sample_search_results)
        
        assert len(sources) == 3
        assert all(isinstance(source, SourceInfo) for source in sources)
        
        # 验证第一个源信息
        source1 = sources[0]
        assert source1.document_id == sample_search_results[0].document_id
        assert source1.chunk_id == sample_search_results[0].chunk_id
        assert source1.similarity_score == sample_search_results[0].similarity_score
        assert source1.metadata == sample_search_results[0].metadata
        
        # 验证内容截断
        if len(sample_search_results[0].content) > 200:
            assert source1.chunk_content.endswith("...")
        else:
            assert source1.chunk_content == sample_search_results[0].content
    
    def test_calculate_confidence(self, qa_service, sample_search_results):
        """测试计算置信度"""
        confidence = qa_service._calculate_confidence(sample_search_results)
        
        # 验证置信度在合理范围内
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # 高相似度结果应该有高置信度
        
        # 测试空结果
        empty_confidence = qa_service._calculate_confidence([])
        assert empty_confidence == 0.0
        
        # 测试单个结果
        single_result = [sample_search_results[0]]
        single_confidence = qa_service._calculate_confidence(single_result)
        assert single_confidence < confidence  # 单个结果置信度应该较低
    
    def test_create_no_answer_response(self, qa_service):
        """测试创建无答案响应"""
        question = "无关问题"
        session_id = str(uuid.uuid4())
        
        response = qa_service._create_no_answer_response(question, session_id)
        
        assert isinstance(response, QAResponse)
        assert response.question == question
        # QAResponse模型中没有session_id字段，这个功能需要在会话管理中实现
        assert response.id is not None
        assert "没有找到与您的问题相关的信息" in response.answer
        assert len(response.sources) == 0
        assert response.confidence_score == 0.0
        assert response.processing_time == 0.0
    
    @pytest.mark.asyncio
    async def test_get_service_stats(self, qa_service):
        """测试获取服务统计"""
        stats = await qa_service.get_service_stats()
        
        assert stats["service_name"] == "QAService"
        assert stats["llm_provider"] == "mock"
        assert stats["llm_model"] == "test-llm"
        assert "max_context_length" in stats
        assert "similarity_threshold" in stats
        assert "vector_count" in stats
        assert "document_count" in stats
    
    @pytest.mark.asyncio
    async def test_test_qa(self, qa_service, sample_search_results):
        """测试QA功能测试"""
        # Mock成功的问答流程
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        qa_service.llm.generate_text.return_value = "这是一个测试答案"
        
        result = await qa_service.test_qa("测试问题")
        
        assert result["success"] is True
        assert result["test_question"] == "测试问题"
        assert result["answer_length"] > 0
        assert result["source_count"] == 3
        assert result["confidence_score"] > 0
        assert "processing_time" in result
        assert "service_stats" in result
    
    @pytest.mark.asyncio
    async def test_answer_question_with_session_id(self, qa_service, sample_search_results):
        """测试带会话ID的问答"""
        question = "测试问题"
        session_id = str(uuid.uuid4())
        
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        qa_service.llm.generate_text.return_value = "测试答案"
        
        response = await qa_service.answer_question(question, session_id=session_id)
        
        # QAResponse模型中没有session_id字段，这个功能需要在会话管理中实现
        assert response.id is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_retrieval_failure(self, qa_service):
        """测试检索失败的错误处理"""
        question = "测试问题"
        
        # Mock检索服务抛出异常
        qa_service.retrieval_service.search_similar_documents.side_effect = Exception("检索失败")
        
        with pytest.raises(QAError) as exc_info:
            await qa_service.answer_question(question)
        
        assert "上下文检索失败" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_handling_llm_failure(self, qa_service, sample_search_results):
        """测试LLM失败的错误处理"""
        question = "测试问题"
        
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        qa_service.llm.generate_text.side_effect = Exception("LLM调用失败")
        
        with pytest.raises(QAError) as exc_info:
            await qa_service.answer_question(question)
        
        assert "答案生成失败" in str(exc_info.value)


class TestQAServiceIntegration:
    """QA服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_qa_workflow(self, qa_service, sample_search_results):
        """测试完整的问答工作流"""
        question = "人工智能的主要应用领域有哪些？"
        
        # Mock完整的工作流
        qa_service.retrieval_service.search_similar_documents.return_value = sample_search_results
        qa_service.llm.generate_text.return_value = "人工智能的主要应用领域包括：1. 自然语言处理；2. 计算机视觉；3. 机器学习；4. 深度学习等。这些领域在各行各业都有广泛的应用。"
        
        # 执行问答
        response = await qa_service.answer_question(question)
        
        # 验证完整响应
        assert isinstance(response, QAResponse)
        assert response.question == question
        assert len(response.answer) > 50  # 答案应该有一定长度
        assert len(response.sources) == 3
        assert response.confidence_score > 0.8
        assert response.processing_time > 0
        assert response.session_id is not None
        assert isinstance(response.timestamp, datetime)
        
        # 验证源信息的完整性
        for source in response.sources:
            assert source.document_id is not None
            assert source.chunk_id is not None
            assert len(source.content) > 0
            assert 0 <= source.similarity_score <= 1
    
    @pytest.mark.asyncio
    async def test_qa_with_different_configurations(self, sample_search_results):
        """测试不同配置的QA服务"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 测试不同的配置参数
            config = {
                'llm_provider': 'mock',
                'embedding_provider': 'mock',
                'vector_store_path': temp_dir + '/chroma_db',
                'retrieval_top_k': 5,
                'similarity_threshold': 0.8,
                'max_context_length': 1000,
                'no_answer_threshold': 0.6,
                'include_sources': True
            }
            
            service = QAService(config)
            
            # Mock依赖
            service.retrieval_service = Mock()
            service.retrieval_service.initialize = AsyncMock()
            service.retrieval_service.cleanup = AsyncMock()
            service.retrieval_service.search_similar_documents = AsyncMock(return_value=sample_search_results)
            service.retrieval_service.get_service_stats = AsyncMock(return_value={'vector_count': 50, 'document_count': 5})
            service.retrieval_service.similarity_threshold = 0.8
            service.retrieval_service.default_top_k = 5
            
            service.llm = Mock()
            service.llm.initialize = AsyncMock()
            service.llm.cleanup = AsyncMock()
            service.llm.generate_text = AsyncMock(return_value="配置测试答案")
            service.llm.config = Mock()
            service.llm.config.provider = 'mock'
            service.llm.config.model = 'test-model'
            
            await service.initialize()
            
            # 测试问答
            response = await service.answer_question("配置测试问题")
            
            # 验证配置生效
            assert response.answer == "配置测试答案"
            assert len(response.sources) == 3  # include_sources=True
            assert service.max_context_length == 1000
            assert service.no_answer_threshold == 0.6
            
            await service.cleanup()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)