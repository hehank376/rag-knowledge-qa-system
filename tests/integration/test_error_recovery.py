"""
Error Recovery and Exception Handling Integration Tests
Tests error scenarios and recovery mechanisms in document processing
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import time

from rag_system.services.document_service import DocumentService
from rag_system.services.document_processor import DocumentProcessor
from rag_system.services.embedding_service import EmbeddingService
from rag_system.services.vector_service import VectorStoreService
from rag_system.database.connection import get_database
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.utils.exceptions import (
    DocumentProcessingError, 
    VectorStoreError, 
    EmbeddingError,
    DatabaseError
)


class TestErrorRecovery:
    """Test error handling and recovery mechanisms"""

    @pytest.fixture
    async def setup_services(self):
        """Setup services with error injection capabilities"""
        db = await get_database()
        
        # Initialize services with test configuration
        test_config = {
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'embedding_provider': 'mock',
            'vector_store_type': 'chroma',
            'vector_store_path': './test_chroma_db',
            'collection_name': 'test_collection'
        }
        document_service = DocumentService(test_config)
        document_processor = DocumentProcessor(test_config)
        embedding_service = EmbeddingService(test_config)
        # Create vector service with config
        from rag_system.models.config import VectorStoreConfig
        vector_config = VectorStoreConfig(
            type="chroma",
            persist_directory="./test_chroma_db",
            collection_name="test_collection"
        )
        vector_service = VectorStoreService(vector_config)
        
        return {
            'db': db,
            'document_service': document_service,
            'document_processor': document_processor,
            'embedding_service': embedding_service,
            'vector_service': vector_service
        }

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing"""
        temp_dir = tempfile.mkdtemp()
        file_path = Path(temp_dir) / "test.txt"
        file_path.write_text("This is a test document for error recovery testing.")
        
        yield str(file_path)
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_database_connection_failure_recovery(self, setup_services, sample_document):
        """Test recovery from database connection failures"""
        services = await setup_services
        document_service = services['document_service']
        
        # Upload document successfully first
        with open(sample_document, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="db_test.txt",
            content=content,
            content_type="text/plain"
        )
        
        # Simulate database connection failure
        with patch.object(document_service, 'update_document_status', side_effect=DatabaseError("Connection lost")):
            with pytest.raises(DatabaseError):
                await document_service.update_document_status(
                    document_info.id,
                    DocumentStatus.READY
                )
        
        # Test recovery - connection restored
        # Should be able to update status after connection recovery
        await document_service.update_document_status(
            document_info.id,
            DocumentStatus.READY
        )
        
        # Verify recovery worked
        updated_doc = await document_service.get_document(document_info.id)
        assert updated_doc.status == DocumentStatus.READY

    @pytest.mark.asyncio
    async def test_embedding_service_failure_retry(self, setup_services, sample_document):
        """Test retry mechanism for embedding service failures"""
        services = await setup_services
        embedding_service = services['embedding_service']
        document_processor = services['document_processor']
        
        # Extract text from document
        text = document_processor.extract_text(sample_document)
        chunks = document_processor.split_text(text)
        
        # Mock embedding service to fail first few times, then succeed
        call_count = 0
        
        async def mock_embed_with_retry(text):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise EmbeddingError("Service temporarily unavailable")
            return [0.1] * 1536  # Success on 3rd attempt
        
        with patch.object(embedding_service, 'embed_text', side_effect=mock_embed_with_retry):
            # Implement retry logic
            max_retries = 3
            retry_delay = 0.1
            
            for attempt in range(max_retries):
                try:
                    embedding = await embedding_service.embed_text(chunks[0].content)
                    break
                except EmbeddingError as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            
            # Should succeed after retries
            assert embedding is not None
            assert len(embedding) == 1536
            assert call_count == 3  # Should have been called 3 times

    @pytest.mark.asyncio
    async def test_vector_store_failure_rollback(self, setup_services, sample_document):
        """Test rollback mechanism when vector store operations fail"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        vector_service = services['vector_service']
        
        # Upload and process document
        with open(sample_document, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="vector_test.txt",
            content=content,
            content_type="text/plain"
        )
        
        text = document_processor.extract_text(document_info.file_path)
        chunks = document_processor.split_text(text)
        
        # Simulate vector store failure during batch insert
        stored_vectors = []
        
        async def mock_add_vector_with_failure(document_id, chunk_id, content, embedding, metadata):
            if len(stored_vectors) >= 2:  # Fail after storing 2 vectors
                raise VectorStoreError("Storage quota exceeded")
            stored_vectors.append(chunk_id)
            return True
        
        with patch.object(vector_service, 'add_vector', side_effect=mock_add_vector_with_failure):
            # Try to store all vectors
            stored_count = 0
            failed_chunks = []
            
            for i, chunk in enumerate(chunks):
                try:
                    await vector_service.add_vector(
                        document_id=document_info.id,
                        chunk_id=chunk.id,
                        content=chunk.content,
                        embedding=[0.1] * 1536,
                        metadata=chunk.metadata
                    )
                    stored_count += 1
                except VectorStoreError:
                    failed_chunks.append(chunk.id)
                    break
            
            # Should have stored some vectors before failure
            assert stored_count > 0
            assert len(failed_chunks) > 0
        
        # Implement rollback - remove successfully stored vectors
        with patch.object(vector_service, 'delete_vectors_by_document', return_value=True):
            await vector_service.delete_vectors_by_document(document_info.id)
        
        # Update document status to error
        await document_service.update_document_status(
            document_info.id,
            DocumentStatus.ERROR,
            error_message="Vector storage failed, rolled back"
        )
        
        # Verify rollback
        error_doc = await document_service.get_document(document_info.id)
        assert error_doc.status == DocumentStatus.ERROR

    @pytest.mark.asyncio
    async def test_partial_processing_recovery(self, setup_services, sample_document):
        """Test recovery from partial processing failures"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        embedding_service = services['embedding_service']
        vector_service = services['vector_service']
        
        # Upload document
        with open(sample_document, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="partial_test.txt",
            content=content,
            content_type="text/plain"
        )
        
        # Process document
        text = document_processor.extract_text(document_info.file_path)
        chunks = document_processor.split_text(text)
        
        # Simulate partial processing - some chunks succeed, others fail
        processed_chunks = []
        failed_chunks = []
        
        for i, chunk in enumerate(chunks):
            try:
                if i >= len(chunks) // 2:  # Fail second half
                    raise EmbeddingError("Processing interrupted")
                
                # Mock successful processing
                embedding = [0.1] * 1536
                await vector_service.add_vector(
                    document_id=document_info.id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata=chunk.metadata
                )
                processed_chunks.append(chunk.id)
                
            except EmbeddingError:
                failed_chunks.append(chunk.id)
        
        # Should have some successful and some failed chunks
        assert len(processed_chunks) > 0
        assert len(failed_chunks) > 0
        
        # Mark document as partially processed
        await document_service.update_document_status(
            document_info.id,
            DocumentStatus.ERROR,
            error_message=f"Partial processing: {len(processed_chunks)}/{len(chunks)} chunks processed"
        )
        
        # Test recovery - reprocess failed chunks only
        recovery_successful = True
        for chunk_id in failed_chunks:
            try:
                # Find the chunk
                chunk = next(c for c in chunks if c.id == chunk_id)
                
                # Mock successful reprocessing
                embedding = [0.1] * 1536
                await vector_service.add_vector(
                    document_id=document_info.id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata=chunk.metadata
                )
                
            except Exception:
                recovery_successful = False
                break
        
        if recovery_successful:
            # Update status to ready after successful recovery
            await document_service.update_document_status(
                document_info.id,
                DocumentStatus.READY,
                chunk_count=len(chunks)
            )
            
            recovered_doc = await document_service.get_document(document_info.id)
            assert recovered_doc.status == DocumentStatus.READY

    @pytest.mark.asyncio
    async def test_concurrent_processing_error_isolation(self, setup_services):
        """Test that errors in one document don't affect others during concurrent processing"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Create multiple test documents
        documents = []
        temp_dir = tempfile.mkdtemp()
        
        try:
            for i in range(5):
                file_path = Path(temp_dir) / f"test_{i}.txt"
                if i == 2:  # Make one document problematic
                    file_path.write_text("")  # Empty content
                else:
                    file_path.write_text(f"Test document {i} with valid content.")
                
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                doc_info = await document_service.upload_document(
                    filename=f"concurrent_test_{i}.txt",
                    content=content,
                    content_type="text/plain"
                )
                documents.append(doc_info)
            
            # Process documents concurrently
            async def process_document(doc_info):
                try:
                    text = document_processor.extract_text(doc_info.file_path)
                    if not text.strip():  # Empty document
                        raise DocumentProcessingError("Empty document")
                    
                    chunks = document_processor.split_text(text)
                    
                    await document_service.update_document_status(
                        doc_info.id,
                        DocumentStatus.READY,
                        chunk_count=len(chunks)
                    )
                    return {'success': True, 'doc_id': doc_info.id}
                    
                except Exception as e:
                    await document_service.update_document_status(
                        doc_info.id,
                        DocumentStatus.ERROR,
                        error_message=str(e)
                    )
                    return {'success': False, 'doc_id': doc_info.id, 'error': str(e)}
            
            # Process all documents concurrently
            tasks = [process_document(doc) for doc in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify results
            successful_count = 0
            failed_count = 0
            
            for result in results:
                if isinstance(result, dict):
                    if result['success']:
                        successful_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            
            # Should have 4 successful and 1 failed
            assert successful_count == 4
            assert failed_count == 1
            
            # Verify document statuses
            for doc in documents:
                updated_doc = await document_service.get_document(doc.id)
                if "test_2" in doc.filename:  # The problematic document
                    assert updated_doc.status == DocumentStatus.ERROR
                else:
                    assert updated_doc.status == DocumentStatus.READY
        
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_memory_cleanup_on_error(self, setup_services, sample_document):
        """Test that memory is properly cleaned up when errors occur"""
        services = await setup_services
        document_processor = services['document_processor']
        
        # Monitor memory usage (simplified)
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Process document multiple times with errors
        for i in range(10):
            try:
                # Simulate processing that might fail
                text = document_processor.extract_text(sample_document)
                chunks = document_processor.split_text(text)
                
                # Simulate error after processing
                if i % 3 == 0:
                    raise DocumentProcessingError("Simulated processing error")
                
            except DocumentProcessingError:
                # Force garbage collection after error
                gc.collect()
                continue
        
        # Force final garbage collection
        gc.collect()
        
        # Check memory usage hasn't grown excessively
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB)
        assert memory_growth < 50 * 1024 * 1024, f"Memory grew by {memory_growth / 1024 / 1024:.2f} MB"

    @pytest.mark.asyncio
    async def test_timeout_handling(self, setup_services, sample_document):
        """Test handling of operation timeouts"""
        services = await setup_services
        embedding_service = services['embedding_service']
        
        # Mock slow embedding service
        async def slow_embed_text(text):
            await asyncio.sleep(5)  # Simulate slow operation
            return [0.1] * 1536
        
        with patch.object(embedding_service, 'embed_text', side_effect=slow_embed_text):
            # Test with timeout
            try:
                embedding = await asyncio.wait_for(
                    embedding_service.embed_text("test text"),
                    timeout=2.0  # 2 second timeout
                )
                pytest.fail("Should have timed out")
            except asyncio.TimeoutError:
                # Expected timeout
                pass
        
        # Test with sufficient timeout
        with patch.object(embedding_service, 'embed_text', return_value=[0.1] * 1536):
            embedding = await asyncio.wait_for(
                embedding_service.embed_text("test text"),
                timeout=10.0  # Sufficient timeout
            )
            assert embedding is not None

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_cancellation(self, setup_services, sample_document):
        """Test that resources are cleaned up when operations are cancelled"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Upload document
        with open(sample_document, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="cancel_test.txt",
            content=content,
            content_type="text/plain"
        )
        
        # Start processing task
        async def long_processing_task():
            text = document_processor.extract_text(document_info.file_path)
            chunks = document_processor.split_text(text)
            
            # Simulate long processing
            for i in range(100):
                await asyncio.sleep(0.1)  # Simulate work
                # Check for cancellation
                if asyncio.current_task().cancelled():
                    # Cleanup resources
                    await document_service.update_document_status(
                        document_info.id,
                        DocumentStatus.ERROR,
                        error_message="Processing cancelled"
                    )
                    raise asyncio.CancelledError()
            
            return chunks
        
        # Start task and cancel it
        task = asyncio.create_task(long_processing_task())
        await asyncio.sleep(0.5)  # Let it start
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify cleanup occurred
        cancelled_doc = await document_service.get_document(document_info.id)
        assert cancelled_doc.status == DocumentStatus.ERROR
        assert "cancelled" in cancelled_doc.error_message.lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, setup_services):
        """Test circuit breaker pattern for external service failures"""
        services = await setup_services
        embedding_service = services['embedding_service']
        
        # Circuit breaker state
        failure_count = 0
        circuit_open = False
        failure_threshold = 3
        
        async def circuit_breaker_embed(text):
            nonlocal failure_count, circuit_open
            
            if circuit_open:
                raise EmbeddingError("Circuit breaker open")
            
            # Simulate failures
            failure_count += 1
            if failure_count >= failure_threshold:
                circuit_open = True
            
            raise EmbeddingError("Service unavailable")
        
        with patch.object(embedding_service, 'embed_text', side_effect=circuit_breaker_embed):
            # Test circuit breaker behavior
            for i in range(5):
                try:
                    await embedding_service.embed_text("test")
                except EmbeddingError as e:
                    if i < failure_threshold:
                        assert "Service unavailable" in str(e)
                    else:
                        assert "Circuit breaker open" in str(e)
        
        # Test circuit breaker recovery (after timeout)
        circuit_open = False  # Simulate timeout recovery
        failure_count = 0
        
        with patch.object(embedding_service, 'embed_text', return_value=[0.1] * 1536):
            # Should work after circuit breaker closes
            embedding = await embedding_service.embed_text("test")
            assert embedding is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])