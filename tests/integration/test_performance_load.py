"""
Performance and Load Testing for Document Processing
Tests system performance under various load conditions
"""

import pytest
import asyncio
import tempfile
import time
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from rag_system.services.document_service import DocumentService
from rag_system.services.document_processor import DocumentProcessor
from rag_system.services.embedding_service import EmbeddingService
from rag_system.services.vector_service import VectorStoreService
from rag_system.database.connection import get_database
from rag_system.models.document import DocumentStatus


class TestPerformanceLoad:
    """Performance and load testing suite"""

    def _create_vector_service(self):
        """Create vector service with test configuration"""
        from rag_system.models.config import VectorStoreConfig
        vector_config = VectorStoreConfig(
            type="chroma",
            persist_directory="./test_chroma_db",
            collection_name="test_collection"
        )
        return VectorStoreService(vector_config)

    @pytest.fixture
    async def setup_services(self):
        """Setup services for performance testing"""
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
        
        return {
            'db': db,
            'document_service': DocumentService(test_config),
            'document_processor': DocumentProcessor(test_config),
            'embedding_service': EmbeddingService(test_config),
            'vector_service': self._create_vector_service()
        }

    @pytest.fixture
    def performance_documents(self):
        """Create documents of various sizes for performance testing"""
        temp_dir = tempfile.mkdtemp()
        documents = {}
        
        # Small document (1KB)
        small_content = "This is a small test document. " * 30
        small_file = Path(temp_dir) / "small.txt"
        small_file.write_text(small_content)
        documents['small'] = str(small_file)
        
        # Medium document (10KB)
        medium_content = "This is a medium test document with more content. " * 200
        medium_file = Path(temp_dir) / "medium.txt"
        medium_file.write_text(medium_content)
        documents['medium'] = str(medium_file)
        
        # Large document (100KB)
        large_content = "This is a large test document with substantial content for testing performance. " * 1000
        large_file = Path(temp_dir) / "large.txt"
        large_file.write_text(large_content)
        documents['large'] = str(large_file)
        
        # Very large document (1MB)
        very_large_content = "This is a very large document for stress testing the system performance and memory usage. " * 10000
        very_large_file = Path(temp_dir) / "very_large.txt"
        very_large_file.write_text(very_large_content)
        documents['very_large'] = str(very_large_file)
        
        yield documents
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_single_document_processing_performance(self, setup_services, performance_documents):
        """Test performance of processing single documents of different sizes"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        performance_results = {}
        
        for size, file_path in performance_documents.items():
            # Measure processing time
            start_time = time.time()
            
            # Upload document
            with open(file_path, 'rb') as f:
                content = f.read()
            
            upload_start = time.time()
            document_info = await document_service.upload_document(
                filename=f"perf_{size}.txt",
                content=content,
                content_type="text/plain"
            )
            upload_time = time.time() - upload_start
            
            # Extract text
            extract_start = time.time()
            text = document_processor.extract_text(document_info.file_path)
            extract_time = time.time() - extract_start
            
            # Split text
            split_start = time.time()
            chunks = document_processor.split_text(text)
            split_time = time.time() - split_start
            
            total_time = time.time() - start_time
            
            performance_results[size] = {
                'file_size': len(content),
                'text_length': len(text),
                'chunk_count': len(chunks),
                'upload_time': upload_time,
                'extract_time': extract_time,
                'split_time': split_time,
                'total_time': total_time,
                'throughput_mb_per_sec': (len(content) / 1024 / 1024) / total_time
            }
            
            # Update document status
            await document_service.update_document_status(
                document_info.id,
                DocumentStatus.READY,
                chunk_count=len(chunks)
            )
        
        # Verify performance expectations
        assert performance_results['small']['total_time'] < 1.0  # Small docs should process quickly
        assert performance_results['medium']['total_time'] < 5.0  # Medium docs should be reasonable
        assert performance_results['large']['total_time'] < 15.0  # Large docs should complete in reasonable time
        
        # Print performance results
        print("\nDocument Processing Performance Results:")
        for size, results in performance_results.items():
            print(f"{size.upper()}: {results['file_size']/1024:.1f}KB, "
                  f"{results['total_time']:.3f}s, "
                  f"{results['throughput_mb_per_sec']:.2f} MB/s")

    @pytest.mark.asyncio
    async def test_concurrent_document_processing_load(self, setup_services, performance_documents):
        """Test system performance under concurrent document processing load"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Test with different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"\nTesting concurrency level: {concurrency}")
            
            # Create tasks for concurrent processing
            tasks = []
            start_time = time.time()
            
            for i in range(concurrency):
                # Use medium-sized documents for load testing
                file_path = performance_documents['medium']
                task = self._process_document_concurrent(
                    services, file_path, f"concurrent_{concurrency}_{i}.txt"
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            successful_tasks = [r for r in task_results if not isinstance(r, Exception)]
            failed_tasks = [r for r in task_results if isinstance(r, Exception)]
            
            avg_processing_time = statistics.mean([r['processing_time'] for r in successful_tasks]) if successful_tasks else 0
            
            results[concurrency] = {
                'total_time': total_time,
                'successful_count': len(successful_tasks),
                'failed_count': len(failed_tasks),
                'avg_processing_time': avg_processing_time,
                'throughput_docs_per_sec': len(successful_tasks) / total_time if total_time > 0 else 0
            }
            
            # Verify most tasks succeeded
            assert len(successful_tasks) >= concurrency * 0.8  # At least 80% success rate
        
        # Print concurrency results
        print("\nConcurrency Performance Results:")
        for level, result in results.items():
            print(f"Concurrency {level}: {result['successful_count']}/{level} successful, "
                  f"{result['throughput_docs_per_sec']:.2f} docs/sec")

    async def _process_document_concurrent(self, services, file_path, filename):
        """Helper method for concurrent document processing"""
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        start_time = time.time()
        
        try:
            # Upload document
            with open(file_path, 'rb') as f:
                content = f.read()
            
            document_info = await document_service.upload_document(
                filename=filename,
                content=content,
                content_type="text/plain"
            )
            
            # Process document
            text = document_processor.extract_text(document_info.file_path)
            chunks = document_processor.split_text(text)
            
            # Update status
            await document_service.update_document_status(
                document_info.id,
                DocumentStatus.READY,
                chunk_count=len(chunks)
            )
            
            processing_time = time.time() - start_time
            
            return {
                'document_id': document_info.id,
                'processing_time': processing_time,
                'chunk_count': len(chunks),
                'success': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'processing_time': time.time() - start_time,
                'success': False
            }

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, setup_services, performance_documents):
        """Test memory usage during heavy document processing"""
        services = await setup_services
        document_service = services['document_service']
        document_processor = services['document_processor']
        
        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        memory_samples = [initial_memory]
        
        # Process multiple large documents
        for i in range(10):
            file_path = performance_documents['large']
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            document_info = await document_service.upload_document(
                filename=f"memory_test_{i}.txt",
                content=content,
                content_type="text/plain"
            )
            
            text = document_processor.extract_text(document_info.file_path)
            chunks = document_processor.split_text(text)
            
            await document_service.update_document_status(
                document_info.id,
                DocumentStatus.READY,
                chunk_count=len(chunks)
            )
            
            # Sample memory usage
            current_memory = process.memory_info().rss
            memory_samples.append(current_memory)
            
            # Force garbage collection periodically
            if i % 3 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        final_memory = process.memory_info().rss
        
        # Analyze memory usage
        max_memory = max(memory_samples)
        memory_growth = final_memory - initial_memory
        peak_growth = max_memory - initial_memory
        
        print(f"\nMemory Usage Analysis:")
        print(f"Initial: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"Final: {final_memory / 1024 / 1024:.2f} MB")
        print(f"Peak: {max_memory / 1024 / 1024:.2f} MB")
        print(f"Net Growth: {memory_growth / 1024 / 1024:.2f} MB")
        print(f"Peak Growth: {peak_growth / 1024 / 1024:.2f} MB")
        
        # Memory growth should be reasonable (less than 200MB)
        assert memory_growth < 200 * 1024 * 1024, f"Memory grew by {memory_growth / 1024 / 1024:.2f} MB"
        assert peak_growth < 500 * 1024 * 1024, f"Peak memory growth was {peak_growth / 1024 / 1024:.2f} MB"

    @pytest.mark.asyncio
    async def test_database_performance_under_load(self, setup_services):
        """Test database performance under high load"""
        services = await setup_services
        document_service = services['document_service']
        
        # Test database operations performance
        operation_times = {
            'insert': [],
            'select': [],
            'update': [],
            'delete': []
        }
        
        document_ids = []
        
        # Test insert performance
        for i in range(50):
            start_time = time.time()
            
            document_info = await document_service.upload_document(
                filename=f"db_perf_{i}.txt",
                content=f"Test document {i} content".encode(),
                content_type="text/plain"
            )
            
            insert_time = time.time() - start_time
            operation_times['insert'].append(insert_time)
            document_ids.append(document_info.id)
        
        # Test select performance
        for doc_id in document_ids[:20]:  # Test subset for select
            start_time = time.time()
            
            await document_service.get_document(doc_id)
            
            select_time = time.time() - start_time
            operation_times['select'].append(select_time)
        
        # Test update performance
        for doc_id in document_ids[:20]:  # Test subset for update
            start_time = time.time()
            
            await document_service.update_document_status(
                doc_id,
                DocumentStatus.READY,
                chunk_count=5
            )
            
            update_time = time.time() - start_time
            operation_times['update'].append(update_time)
        
        # Test delete performance
        for doc_id in document_ids[:10]:  # Test subset for delete
            start_time = time.time()
            
            await document_service.delete_document(doc_id)
            
            delete_time = time.time() - start_time
            operation_times['delete'].append(delete_time)
        
        # Analyze performance
        print("\nDatabase Performance Results:")
        for operation, times in operation_times.items():
            if times:
                avg_time = statistics.mean(times)
                max_time = max(times)
                min_time = min(times)
                print(f"{operation.upper()}: avg={avg_time*1000:.2f}ms, "
                      f"max={max_time*1000:.2f}ms, min={min_time*1000:.2f}ms")
                
                # Performance assertions
                assert avg_time < 1.0, f"{operation} average time too high: {avg_time:.3f}s"
                assert max_time < 5.0, f"{operation} max time too high: {max_time:.3f}s"

    @pytest.mark.asyncio
    async def test_vector_operations_performance(self, setup_services):
        """Test vector operations performance"""
        services = await setup_services
        vector_service = services['vector_service']
        
        # Generate test vectors
        test_vectors = []
        vector_dim = 1536
        
        for i in range(100):
            vector = [0.1 * (i % 10)] * vector_dim  # Simple test vectors
            test_vectors.append({
                'document_id': f"doc_{i}",
                'chunk_id': f"chunk_{i}",
                'content': f"Test content {i}",
                'embedding': vector,
                'metadata': {'index': i}
            })
        
        # Test vector insertion performance
        insert_times = []
        for vector_data in test_vectors:
            start_time = time.time()
            
            await vector_service.add_vector(
                document_id=vector_data['document_id'],
                chunk_id=vector_data['chunk_id'],
                content=vector_data['content'],
                embedding=vector_data['embedding'],
                metadata=vector_data['metadata']
            )
            
            insert_time = time.time() - start_time
            insert_times.append(insert_time)
        
        # Test vector search performance
        search_times = []
        query_vector = [0.1] * vector_dim
        
        for _ in range(20):  # Multiple search tests
            start_time = time.time()
            
            results = await vector_service.search_similar(
                query_vector,
                top_k=10
            )
            
            search_time = time.time() - start_time
            search_times.append(search_time)
        
        # Analyze vector performance
        avg_insert_time = statistics.mean(insert_times)
        avg_search_time = statistics.mean(search_times)
        
        print(f"\nVector Operations Performance:")
        print(f"Average insert time: {avg_insert_time*1000:.2f}ms")
        print(f"Average search time: {avg_search_time*1000:.2f}ms")
        print(f"Insert throughput: {1/avg_insert_time:.2f} vectors/sec")
        print(f"Search throughput: {1/avg_search_time:.2f} searches/sec")
        
        # Performance assertions
        assert avg_insert_time < 0.1, f"Vector insert too slow: {avg_insert_time:.3f}s"
        assert avg_search_time < 0.5, f"Vector search too slow: {avg_search_time:.3f}s"

    @pytest.mark.asyncio
    async def test_end_to_end_throughput(self, setup_services, performance_documents):
        """Test end-to-end system throughput"""
        services = await setup_services
        
        # Process multiple documents end-to-end
        document_count = 20
        start_time = time.time()
        
        tasks = []
        for i in range(document_count):
            # Alternate between different document sizes
            size_key = ['small', 'medium'][i % 2]
            file_path = performance_documents[size_key]
            
            task = self._process_document_end_to_end(
                services, file_path, f"throughput_{i}.txt"
            )
            tasks.append(task)
        
        # Process all documents
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze throughput
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        throughput = len(successful_results) / total_time
        avg_processing_time = statistics.mean([r['total_time'] for r in successful_results]) if successful_results else 0
        
        print(f"\nEnd-to-End Throughput Results:")
        print(f"Processed: {len(successful_results)}/{document_count} documents")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} documents/sec")
        print(f"Average processing time: {avg_processing_time:.2f}s")
        print(f"Failed: {len(failed_results)} documents")
        
        # Throughput assertions
        assert len(successful_results) >= document_count * 0.9  # 90% success rate
        assert throughput >= 0.5  # At least 0.5 documents per second
        assert avg_processing_time < 10.0  # Average processing under 10 seconds

    async def _process_document_end_to_end(self, services, file_path, filename):
        """Process document through complete pipeline"""
        document_service = services['document_service']
        document_processor = services['document_processor']
        embedding_service = services['embedding_service']
        vector_service = services['vector_service']
        
        start_time = time.time()
        
        try:
            # Upload
            with open(file_path, 'rb') as f:
                content = f.read()
            
            document_info = await document_service.upload_document(
                filename=filename,
                content=content,
                content_type="text/plain"
            )
            
            # Process
            text = document_processor.extract_text(document_info.file_path)
            chunks = document_processor.split_text(text)
            
            # Vectorize and store (mock for performance testing)
            for chunk in chunks:
                # Use mock embedding for performance testing
                mock_embedding = [0.1] * 1536
                await vector_service.add_vector(
                    document_id=document_info.id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    embedding=mock_embedding,
                    metadata=chunk.metadata
                )
            
            # Update status
            await document_service.update_document_status(
                document_info.id,
                DocumentStatus.READY,
                chunk_count=len(chunks)
            )
            
            total_time = time.time() - start_time
            
            return {
                'document_id': document_info.id,
                'total_time': total_time,
                'chunk_count': len(chunks),
                'success': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'total_time': time.time() - start_time,
                'success': False
            }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])