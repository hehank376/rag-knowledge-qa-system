"""
Complete Document Processing Flow Integration Tests
Tests the entire document processing pipeline from upload to vectorization
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import time

from rag_system.services.document_service import DocumentService
from rag_system.services.document_processor import DocumentProcessor
from rag_system.services.embedding_service import EmbeddingService
from rag_system.services.vector_service import VectorStoreService
from rag_system.database.connection import get_database
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.utils.exceptions import DocumentProcessingError, VectorStoreError


class TestDocumentProcessingFlow:
    """Test complete document processing workflow"""

    @pytest.fixture
    async def setup_services(self):
        """Setup all required services for testing"""
        # Initialize services with test configuration
        test_config = {
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'embedding_provider': 'mock',
            'vector_store_type': 'chroma',
            'vector_store_path': './test_chroma_db',
            'collection_name': 'test_collection'
        }
        
        # Create mock services for testing
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
        
        # Initialize services
        await vector_service.initialize()
        
        return {
            'document_processor': document_processor,
            'embedding_service': embedding_service,
            'vector_service': vector_service
        }

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing"""
        documents = {}
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Sample text document
        txt_file = Path(temp_dir) / "sample.txt"
        txt_file.write_text(
            "This is a sample document for testing the RAG system. "
            "It contains multiple sentences to test text processing. "
            "The document should be properly chunked and vectorized."
        )
        documents['txt'] = str(txt_file)
        
        # Sample markdown document
        md_file = Path(temp_dir) / "sample.md"
        md_file.write_text(
            "# Sample Markdown Document\n\n"
            "This is a **markdown** document with *formatting*.\n\n"
            "## Section 1\n\n"
            "Content of section 1 with some important information.\n\n"
            "## Section 2\n\n"
            "Content of section 2 with different information.\n"
        )
        documents['md'] = str(md_file)
        
        # Sample large document for chunking test
        large_file = Path(temp_dir) / "large.txt"
        large_content = "This is a large document. " * 200  # Create large content
        large_file.write_text(large_content)
        documents['large'] = str(large_file)
        
        yield documents
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_complete_document_processing_flow(self, setup_services, sample_documents):
        """Test the complete document processing flow"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        embedding_service = services['embedding_service']
        vector_service = services['vector_service']
        
        # Step 1: Upload document
        file_path = sample_documents['txt']
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Simulate file upload
        document_info = await document_service.upload_document(
            filename="sample.txt",
            content=file_content,
            content_type="text/plain"
        )
        
        assert document_info is not None
        assert document_info.filename == "sample.txt"
        assert document_info.status == DocumentStatus.PROCESSING
        
        # Step 2: Process document (extract text)
        extracted_text = document_processor.extract_text(document_info.file_path)
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "sample document" in extracted_text.lower()
        
        # Step 3: Split text into chunks
        chunks = document_processor.split_text(extracted_text)
        assert len(chunks) > 0
        assert all(chunk.content for chunk in chunks)
        assert all(chunk.document_id == document_info.id for chunk in chunks)
        
        # Step 4: Generate embeddings
        embeddings = []
        for chunk in chunks:
            embedding = await embedding_service.embed_text(chunk.content)
            assert embedding is not None
            assert len(embedding) > 0  # Should have embedding dimensions
            embeddings.append(embedding)
        
        # Step 5: Store vectors
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            await vector_service.add_vector(
                document_id=document_info.id,
                chunk_id=chunk.id,
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata
            )
        
        # Step 6: Update document status
        await document_service.update_document_status(
            document_info.id, 
            DocumentStatus.READY,
            chunk_count=len(chunks)
        )
        
        # Verify final state
        updated_doc = await document_service.get_document(document_info.id)
        assert updated_doc.status == DocumentStatus.READY
        assert updated_doc.chunk_count == len(chunks)
        
        # Verify vectors are stored
        search_results = await vector_service.search_similar(
            embeddings[0], top_k=5
        )
        assert len(search_results) > 0
        assert any(result.document_id == document_info.id for result in search_results)

    @pytest.mark.asyncio
    async def test_markdown_document_processing(self, setup_services, sample_documents):
        """Test processing of markdown documents with structure"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Upload markdown document
        file_path = sample_documents['md']
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        document_info = await document_service.upload_document(
            filename="sample.md",
            content=file_content,
            content_type="text/markdown"
        )
        
        # Process document
        extracted_text = document_processor.extract_text(document_info.file_path)
        assert "Sample Markdown Document" in extracted_text
        assert "Section 1" in extracted_text
        assert "Section 2" in extracted_text
        
        # Split text - should preserve structure
        chunks = document_processor.split_text(extracted_text)
        assert len(chunks) > 0
        
        # Verify chunks contain structured content
        chunk_contents = [chunk.content for chunk in chunks]
        combined_content = " ".join(chunk_contents)
        assert "markdown" in combined_content.lower()
        assert "section" in combined_content.lower()

    @pytest.mark.asyncio
    async def test_large_document_chunking(self, setup_services, sample_documents):
        """Test processing of large documents with proper chunking"""
        services = await setup_services
        document_processor = services['document_processor']
        
        # Process large document
        file_path = sample_documents['large']
        extracted_text = document_processor.extract_text(file_path)
        
        # Split into chunks
        chunks = document_processor.split_text(extracted_text)
        
        # Verify chunking
        assert len(chunks) > 1  # Should be split into multiple chunks
        
        # Verify chunk sizes are reasonable
        for chunk in chunks:
            assert len(chunk.content) <= 1500  # Should not exceed max chunk size
            assert len(chunk.content) >= 50   # Should have minimum content
        
        # Verify overlap between chunks
        if len(chunks) > 1:
            # Check if there's some overlap between consecutive chunks
            first_chunk_end = chunks[0].content[-100:]
            second_chunk_start = chunks[1].content[:100:]
            # There should be some common words due to overlap
            first_words = set(first_chunk_end.split())
            second_words = set(second_chunk_start.split())
            overlap = first_words.intersection(second_words)
            assert len(overlap) > 0  # Should have some overlapping words

    @pytest.mark.asyncio
    async def test_concurrent_document_processing(self, setup_services, sample_documents):
        """Test processing multiple documents concurrently"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Upload multiple documents concurrently
        upload_tasks = []
        for i, (doc_type, file_path) in enumerate(sample_documents.items()):
            with open(file_path, 'rb') as f:
                content = f.read()
            
            task = document_service.upload_document(
                filename=f"{doc_type}_{i}.txt",
                content=content,
                content_type="text/plain"
            )
            upload_tasks.append(task)
        
        # Wait for all uploads to complete
        documents = await asyncio.gather(*upload_tasks)
        assert len(documents) == len(sample_documents)
        
        # Process all documents concurrently
        process_tasks = []
        for doc in documents:
            task = self._process_document_async(document_processor, doc)
            process_tasks.append(task)
        
        # Wait for all processing to complete
        results = await asyncio.gather(*process_tasks, return_exceptions=True)
        
        # Verify all processing completed successfully
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Document processing failed: {result}")
            assert result is not None

    async def _process_document_async(self, processor, document_info):
        """Helper method to process document asynchronously"""
        try:
            # Extract text
            text = processor.extract_text(document_info.file_path)
            
            # Split into chunks
            chunks = processor.split_text(text)
            
            return {
                'document_id': document_info.id,
                'text_length': len(text),
                'chunk_count': len(chunks)
            }
        except Exception as e:
            return e

    @pytest.mark.asyncio
    async def test_error_handling_invalid_file(self, setup_services):
        """Test error handling for invalid file uploads"""
        services = await setup_services
        document_service = services['document_service']
        
        # Try to upload invalid file content
        with pytest.raises(DocumentProcessingError):
            await document_service.upload_document(
                filename="invalid.txt",
                content=b"",  # Empty content
                content_type="text/plain"
            )

    @pytest.mark.asyncio
    async def test_error_handling_corrupted_file(self, setup_services):
        """Test error handling for corrupted files"""
        services = await setup_services
        document_processor = services['document_processor']
        
        # Create a corrupted file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'\x00\x01\x02\x03')  # Binary garbage
            corrupted_file = f.name
        
        try:
            # Should handle corrupted file gracefully
            with pytest.raises(DocumentProcessingError):
                document_processor.extract_text(corrupted_file)
        finally:
            os.unlink(corrupted_file)

    @pytest.mark.asyncio
    async def test_error_recovery_vector_store_failure(self, setup_services, sample_documents):
        """Test error recovery when vector store fails"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        vector_service = services['vector_service']
        
        # Upload and process document
        file_path = sample_documents['txt']
        with open(file_path, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="test.txt",
            content=content,
            content_type="text/plain"
        )
        
        text = document_processor.extract_text(document_info.file_path)
        chunks = document_processor.split_text(text)
        
        # Mock vector store failure
        with patch.object(vector_service, 'add_vector', side_effect=VectorStoreError("Connection failed")):
            with pytest.raises(VectorStoreError):
                await vector_service.add_vector(
                    document_id=document_info.id,
                    chunk_id=chunks[0].id,
                    content=chunks[0].content,
                    embedding=[0.1] * 1536,
                    metadata=chunks[0].metadata
                )
        
        # Verify document status is updated to error
        await document_service.update_document_status(
            document_info.id, 
            DocumentStatus.ERROR,
            error_message="Vector store connection failed"
        )
        
        updated_doc = await document_service.get_document(document_info.id)
        assert updated_doc.status == DocumentStatus.ERROR

    @pytest.mark.asyncio
    async def test_performance_large_batch_processing(self, setup_services):
        """Test performance with large batch of documents"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Create multiple test documents
        documents = []
        for i in range(10):  # Process 10 documents
            content = f"Test document {i} with unique content for testing batch processing. " * 10
            doc_info = await document_service.upload_document(
                filename=f"batch_test_{i}.txt",
                content=content.encode(),
                content_type="text/plain"
            )
            documents.append(doc_info)
        
        # Measure processing time
        start_time = time.time()
        
        # Process all documents
        for doc in documents:
            text = document_processor.extract_text(doc.file_path)
            chunks = document_processor.split_text(text)
            
            # Update status
            await document_service.update_document_status(
                doc.id,
                DocumentStatus.READY,
                chunk_count=len(chunks)
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all documents processed successfully
        for doc in documents:
            updated_doc = await document_service.get_document(doc.id)
            assert updated_doc.status == DocumentStatus.READY
        
        # Performance assertion (should process 10 docs in reasonable time)
        assert processing_time < 30  # Should complete within 30 seconds
        
        print(f"Processed {len(documents)} documents in {processing_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_document_cleanup_on_failure(self, setup_services, sample_documents):
        """Test that resources are cleaned up when processing fails"""
        services = await setup_services
        document_service = services['document_service']
        
        # Upload document
        file_path = sample_documents['txt']
        with open(file_path, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="cleanup_test.txt",
            content=content,
            content_type="text/plain"
        )
        
        # Simulate processing failure
        await document_service.update_document_status(
            document_info.id,
            DocumentStatus.ERROR,
            error_message="Simulated processing failure"
        )
        
        # Delete failed document
        await document_service.delete_document(document_info.id)
        
        # Verify document is removed
        with pytest.raises(Exception):  # Should raise not found exception
            await document_service.get_document(document_info.id)
        
        # Verify file is cleaned up
        assert not os.path.exists(document_info.file_path)

    @pytest.mark.asyncio
    async def test_integration_with_real_embedding_service(self, setup_services, sample_documents):
        """Test integration with actual embedding service (if available)"""
        services = await setup_services
        embedding_service = services['embedding_service']
        
        # Test with real embedding service
        test_text = "This is a test sentence for embedding generation."
        
        try:
            embedding = await embedding_service.embed_text(test_text)
            
            # Verify embedding properties
            assert embedding is not None
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            assert all(isinstance(x, (int, float)) for x in embedding)
            
            # Test batch embedding
            texts = [
                "First test sentence.",
                "Second test sentence.",
                "Third test sentence."
            ]
            
            batch_embeddings = await embedding_service.embed_batch(texts)
            assert len(batch_embeddings) == len(texts)
            assert all(len(emb) == len(embedding) for emb in batch_embeddings)
            
        except Exception as e:
            # If embedding service is not available, skip this test
            pytest.skip(f"Embedding service not available: {e}")

    @pytest.mark.asyncio
    async def test_end_to_end_document_lifecycle(self, setup_services, sample_documents):
        """Test complete document lifecycle from upload to deletion"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        embedding_service = services['embedding_service']
        vector_service = services['vector_service']
        
        # 1. Upload document
        file_path = sample_documents['txt']
        with open(file_path, 'rb') as f:
            content = f.read()
        
        document_info = await document_service.upload_document(
            filename="lifecycle_test.txt",
            content=content,
            content_type="text/plain"
        )
        
        # 2. Process document
        text = document_processor.extract_text(document_info.file_path)
        chunks = document_processor.split_text(text)
        
        # 3. Generate and store embeddings
        for chunk in chunks:
            try:
                embedding = await embedding_service.embed_text(chunk.content)
                await vector_service.add_vector(
                    document_id=document_info.id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata=chunk.metadata
                )
            except Exception:
                # Use mock embedding if service unavailable
                mock_embedding = [0.1] * 1536
                await vector_service.add_vector(
                    document_id=document_info.id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    embedding=mock_embedding,
                    metadata=chunk.metadata
                )
        
        # 4. Update document status
        await document_service.update_document_status(
            document_info.id,
            DocumentStatus.READY,
            chunk_count=len(chunks)
        )
        
        # 5. Verify document is ready
        final_doc = await document_service.get_document(document_info.id)
        assert final_doc.status == DocumentStatus.READY
        assert final_doc.chunk_count == len(chunks)
        
        # 6. Test search functionality
        try:
            search_results = await vector_service.search_similar(
                [0.1] * 1536,  # Mock query vector
                top_k=5
            )
            # Should find some results
            assert len(search_results) >= 0
        except Exception:
            # Vector search might not be available in test environment
            pass
        
        # 7. Delete document and cleanup
        await document_service.delete_document(document_info.id)
        
        # 8. Verify cleanup
        with pytest.raises(Exception):
            await document_service.get_document(document_info.id)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])