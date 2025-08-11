#!/usr/bin/env python3
"""
Complete QA Flow Integration Test
Tests the complete question-answering flow from question input to answer generation
"""

import pytest
import tempfile
import os
import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCompleteQAFlow:
    """Test complete question-answering flow"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_documents = {}
        self.setup_test_documents()
        
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def setup_test_documents(self):
        """Create test documents with different content"""
        documents = {
            'python_basics.txt': """
            Python Programming Basics
            
            Python is a high-level, interpreted programming language known for its simplicity and readability.
            It was created by Guido van Rossum and first released in 1991.
            
            Key Features:
            - Easy to learn and use
            - Interpreted language
            - Object-oriented programming support
            - Large standard library
            - Cross-platform compatibility
            
            Basic Syntax:
            Variables are created by assignment: x = 5
            Functions are defined with 'def' keyword
            Indentation is used for code blocks
            """,
            
            'machine_learning.txt': """
            Machine Learning Overview
            
            Machine learning is a subset of artificial intelligence that enables computers to learn
            and make decisions from data without being explicitly programmed.
            
            Types of Machine Learning:
            1. Supervised Learning - Learning with labeled data
            2. Unsupervised Learning - Finding patterns in unlabeled data  
            3. Reinforcement Learning - Learning through interaction and rewards
            
            Common Algorithms:
            - Linear Regression
            - Decision Trees
            - Neural Networks
            - Support Vector Machines
            
            Applications:
            - Image recognition
            - Natural language processing
            - Recommendation systems
            - Autonomous vehicles
            """,
            
            'web_development.txt': """
            Web Development Fundamentals
            
            Web development involves creating websites and web applications for the internet.
            It consists of front-end and back-end development.
            
            Front-end Technologies:
            - HTML: Structure and content
            - CSS: Styling and layout
            - JavaScript: Interactivity and behavior
            
            Back-end Technologies:
            - Server-side languages (Python, Java, Node.js)
            - Databases (MySQL, PostgreSQL, MongoDB)
            - Web frameworks (Django, Flask, Express)
            
            Development Process:
            1. Planning and design
            2. Front-end development
            3. Back-end development
            4. Testing and debugging
            5. Deployment and maintenance
            """
        }
        
        for filename, content in documents.items():
            file_path = Path(self.temp_dir) / filename
            file_path.write_text(content.strip())
            self.test_documents[filename] = {
                'path': str(file_path),
                'content': content.strip()
            }

    def create_mock_services(self):
        """Create mock services for testing"""
        
        # Mock Document Processor
        class MockDocumentProcessor:
            def extract_text(self, file_path):
                # Read actual file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            def split_text(self, text, chunk_size=200, chunk_overlap=50):
                chunks = []
                words = text.split()
                
                for i in range(0, len(words), chunk_size - chunk_overlap):
                    chunk_words = words[i:i + chunk_size]
                    chunk_content = ' '.join(chunk_words)
                    
                    chunks.append({
                        'id': f'chunk_{len(chunks)}',
                        'content': chunk_content,
                        'metadata': {
                            'start_word': i,
                            'end_word': i + len(chunk_words),
                            'word_count': len(chunk_words)
                        }
                    })
                
                return chunks
        
        # Mock Embedding Service
        class MockEmbeddingService:
            def __init__(self, dimension=384):
                self.dimension = dimension
            
            def embed_text(self, text):
                # Generate deterministic embedding based on text content
                import hashlib
                
                # Create hash from text
                text_hash = hashlib.md5(text.encode()).hexdigest()
                
                # Convert hash to embedding vector
                embedding = []
                for i in range(0, len(text_hash), 2):
                    if len(embedding) >= self.dimension:
                        break
                    val = int(text_hash[i:i+2], 16) / 255.0
                    embedding.append(val)
                
                # Pad to desired dimension
                while len(embedding) < self.dimension:
                    embedding.append(0.0)
                
                return embedding[:self.dimension]
            
            def embed_batch(self, texts):
                return [self.embed_text(text) for text in texts]
        
        # Mock Vector Store
        class MockVectorStore:
            def __init__(self):
                self.vectors = []
                self.metadata_store = {}
            
            def add_vector(self, vector_id, content, embedding, metadata=None):
                vector_record = {
                    'id': vector_id,
                    'content': content,
                    'embedding': embedding,
                    'metadata': metadata or {}
                }
                self.vectors.append(vector_record)
                self.metadata_store[vector_id] = vector_record
                return vector_id
            
            def search_similar(self, query_embedding, top_k=5, threshold=0.0):
                # Calculate cosine similarity
                import math
                
                def cosine_similarity(a, b):
                    if len(a) != len(b):
                        return 0.0
                    
                    dot_product = sum(x * y for x, y in zip(a, b))
                    magnitude_a = math.sqrt(sum(x * x for x in a))
                    magnitude_b = math.sqrt(sum(x * x for x in b))
                    
                    if magnitude_a == 0 or magnitude_b == 0:
                        return 0.0
                    
                    return dot_product / (magnitude_a * magnitude_b)
                
                results = []
                for vector in self.vectors:
                    similarity = cosine_similarity(query_embedding, vector['embedding'])
                    if similarity >= threshold:
                        results.append({
                            'id': vector['id'],
                            'content': vector['content'],
                            'similarity': similarity,
                            'metadata': vector['metadata']
                        })
                
                # Sort by similarity and return top_k
                results.sort(key=lambda x: x['similarity'], reverse=True)
                return results[:top_k]
        
        # Mock LLM Service
        class MockLLMService:
            def generate_answer(self, question, context_chunks, max_tokens=500):
                # Create a mock answer based on the context
                context_text = "\n".join([chunk['content'] for chunk in context_chunks])
                
                # Simple keyword matching for more realistic responses
                question_lower = question.lower()
                context_lower = context_text.lower()
                
                # Check for Python-related questions
                if 'python' in question_lower and 'python' in context_lower:
                    return {
                        'answer': "Based on the provided context, Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991. Python features easy-to-learn syntax, object-oriented programming support, and a large standard library.",
                        'confidence': 0.9,
                        'sources_used': len(context_chunks)
                    }
                # Check for machine learning questions
                elif ('machine learning' in question_lower or 'ml' in question_lower) and 'machine learning' in context_lower:
                    return {
                        'answer': "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed. It includes supervised learning, unsupervised learning, and reinforcement learning, with applications in image recognition, natural language processing, and recommendation systems.",
                        'confidence': 0.85,
                        'sources_used': len(context_chunks)
                    }
                # Check for web development questions
                elif ('web' in question_lower or 'front-end' in question_lower or 'front end' in question_lower or 'html' in question_lower or 'css' in question_lower or 'javascript' in question_lower) and 'web' in context_lower:
                    return {
                        'answer': "Web development involves creating websites and web applications for the internet. It consists of front-end technologies like HTML, CSS, and JavaScript, and back-end technologies including server-side languages and databases. The development process includes planning, development, testing, and deployment.",
                        'confidence': 0.8,
                        'sources_used': len(context_chunks)
                    }
                # Check for programming-related questions
                elif ('programming' in question_lower or 'learn' in question_lower or 'language' in question_lower) and ('python' in context_lower or 'programming' in context_lower):
                    return {
                        'answer': "Programming involves writing instructions for computers to execute. Python is an excellent language for beginners due to its readable syntax and extensive libraries. The learning process involves understanding basic concepts, practicing with examples, and building projects.",
                        'confidence': 0.7,
                        'sources_used': len(context_chunks)
                    }
                # Check for development process questions
                elif ('development' in question_lower or 'process' in question_lower) and 'development' in context_lower:
                    return {
                        'answer': "Software development typically follows a structured process including planning, design, implementation, testing, and deployment. Different methodologies like Agile or Waterfall can be used depending on project requirements.",
                        'confidence': 0.6,
                        'sources_used': len(context_chunks)
                    }
                # Generic response for questions with some context match
                elif len(context_chunks) > 0:
                    return {
                        'answer': f"Based on the available context, I can provide some information related to your question. The context contains relevant information about programming, web development, and machine learning topics.",
                        'confidence': 0.4,
                        'sources_used': len(context_chunks)
                    }
                else:
                    return {
                        'answer': f"I don't have enough relevant information in the current knowledge base to answer your question about '{question}'. Please try asking about Python programming, machine learning, or web development topics.",
                        'confidence': 0.1,
                        'sources_used': len(context_chunks)
                    }
        
        return {
            'document_processor': MockDocumentProcessor(),
            'embedding_service': MockEmbeddingService(),
            'vector_store': MockVectorStore(),
            'llm_service': MockLLMService()
        }

    def test_document_indexing_flow(self):
        """Test the complete document indexing flow"""
        print("\n🚀 Testing Document Indexing Flow...")
        
        services = self.create_mock_services()
        
        # Step 1: Process all documents
        indexed_documents = {}
        
        for doc_name, doc_info in self.test_documents.items():
            print(f"\n📄 Processing document: {doc_name}")
            
            # Extract text
            extracted_text = services['document_processor'].extract_text(doc_info['path'])
            assert len(extracted_text) > 0
            print(f"  ✓ Extracted {len(extracted_text)} characters")
            
            # Split into chunks
            chunks = services['document_processor'].split_text(extracted_text)
            assert len(chunks) > 0
            print(f"  ✓ Split into {len(chunks)} chunks")
            
            # Generate embeddings
            embeddings = []
            for chunk in chunks:
                embedding = services['embedding_service'].embed_text(chunk['content'])
                embeddings.append(embedding)
            
            assert len(embeddings) == len(chunks)
            print(f"  ✓ Generated {len(embeddings)} embeddings")
            
            # Store in vector database
            vector_ids = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{doc_name}_chunk_{i}"
                services['vector_store'].add_vector(
                    vector_id=vector_id,
                    content=chunk['content'],
                    embedding=embedding,
                    metadata={
                        'document': doc_name,
                        'chunk_index': i,
                        **chunk['metadata']
                    }
                )
                vector_ids.append(vector_id)
            
            print(f"  ✓ Stored {len(vector_ids)} vectors")
            
            indexed_documents[doc_name] = {
                'chunks': chunks,
                'embeddings': embeddings,
                'vector_ids': vector_ids
            }
        
        # Verify indexing results
        total_vectors = len(services['vector_store'].vectors)
        expected_vectors = sum(len(doc['vector_ids']) for doc in indexed_documents.values())
        assert total_vectors == expected_vectors
        
        print(f"\n🎉 Document indexing completed successfully!")
        print(f"   📚 Documents processed: {len(indexed_documents)}")
        print(f"   🧩 Total chunks: {sum(len(doc['chunks']) for doc in indexed_documents.values())}")
        print(f"   🔢 Total vectors: {total_vectors}")
        
        return services, indexed_documents

    def test_question_answering_flow(self):
        """Test the complete question-answering flow"""
        print("\n🚀 Testing Question-Answering Flow...")
        
        # First index the documents
        services, indexed_documents = self.test_document_indexing_flow()
        
        # Test questions
        test_questions = [
            {
                'question': "What is Python programming language?",
                'expected_topic': 'python',
                'min_confidence': 0.7
            },
            {
                'question': "Explain machine learning types",
                'expected_topic': 'machine learning',
                'min_confidence': 0.7
            },
            {
                'question': "What are front-end web technologies?",
                'expected_topic': 'web development',
                'min_confidence': 0.5
            },
            {
                'question': "How does quantum computing work?",
                'expected_topic': 'unknown',
                'min_confidence': 0.0
            }
        ]
        
        qa_results = []
        
        for i, test_case in enumerate(test_questions):
            question = test_case['question']
            print(f"\n❓ Question {i+1}: {question}")
            
            # Step 1: Generate question embedding
            question_embedding = services['embedding_service'].embed_text(question)
            assert len(question_embedding) > 0
            print(f"  ✓ Generated question embedding ({len(question_embedding)} dimensions)")
            
            # Step 2: Search for relevant chunks
            search_results = services['vector_store'].search_similar(
                query_embedding=question_embedding,
                top_k=3,
                threshold=0.1
            )
            print(f"  ✓ Found {len(search_results)} relevant chunks")
            
            # Step 3: Generate answer
            if search_results:
                answer_result = services['llm_service'].generate_answer(
                    question=question,
                    context_chunks=search_results
                )
                
                print(f"  ✓ Generated answer (confidence: {answer_result['confidence']:.2f})")
                print(f"    Answer preview: {answer_result['answer'][:100]}...")
                
                # Verify answer quality
                if test_case['expected_topic'] != 'unknown':
                    assert answer_result['confidence'] >= test_case['min_confidence']
                    assert len(answer_result['answer']) > 50
                
                qa_results.append({
                    'question': question,
                    'answer': answer_result['answer'],
                    'confidence': answer_result['confidence'],
                    'sources_count': len(search_results),
                    'search_results': search_results
                })
            else:
                print("  ⚠️ No relevant chunks found")
                qa_results.append({
                    'question': question,
                    'answer': "I don't have enough information to answer this question.",
                    'confidence': 0.0,
                    'sources_count': 0,
                    'search_results': []
                })
        
        print(f"\n🎉 Question-answering flow completed successfully!")
        print(f"   ❓ Questions processed: {len(qa_results)}")
        print(f"   ✅ Successful answers: {sum(1 for r in qa_results if r['confidence'] > 0.5)}")
        print(f"   📊 Average confidence: {sum(r['confidence'] for r in qa_results) / len(qa_results):.2f}")
        
        return qa_results

    def test_concurrent_qa_performance(self):
        """Test concurrent question-answering performance"""
        print("\n🚀 Testing Concurrent QA Performance...")
        
        # Setup services and index documents
        services, indexed_documents = self.test_document_indexing_flow()
        
        # Create multiple questions for concurrent testing
        questions = [
            "What is Python?",
            "Explain machine learning",
            "What is web development?",
            "How to learn programming?",
            "What are Python features?",
            "Types of machine learning",
            "Front-end technologies",
            "Back-end development",
            "Programming languages",
            "Software development process"
        ]
        
        def process_question(question):
            """Process a single question"""
            start_time = time.time()
            
            # Generate embedding
            question_embedding = services['embedding_service'].embed_text(question)
            
            # Search for relevant chunks
            search_results = services['vector_store'].search_similar(
                query_embedding=question_embedding,
                top_k=3
            )
            
            # Generate answer
            if search_results:
                answer_result = services['llm_service'].generate_answer(
                    question=question,
                    context_chunks=search_results
                )
            else:
                answer_result = {
                    'answer': "No relevant information found.",
                    'confidence': 0.0,
                    'sources_used': 0
                }
            
            processing_time = time.time() - start_time
            
            return {
                'question': question,
                'answer': answer_result['answer'],
                'confidence': answer_result['confidence'],
                'processing_time': processing_time,
                'sources_count': len(search_results)
            }
        
        # Test concurrent processing
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_question = {
                executor.submit(process_question, question): question 
                for question in questions
            }
            
            results = []
            for future in as_completed(future_to_question):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # Analyze performance
        processing_times = [r['processing_time'] for r in results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        min_processing_time = min(processing_times)
        
        successful_answers = sum(1 for r in results if r['confidence'] > 0.3)
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        
        print(f"\n🎉 Concurrent QA performance test completed!")
        print(f"   ⏱️ Total time: {total_time:.2f}s")
        print(f"   📊 Questions processed: {len(results)}")
        print(f"   ⚡ Average processing time: {avg_processing_time:.3f}s")
        print(f"   🚀 Min processing time: {min_processing_time:.3f}s")
        print(f"   🐌 Max processing time: {max_processing_time:.3f}s")
        print(f"   ✅ Successful answers: {successful_answers}/{len(results)}")
        print(f"   🎯 Average confidence: {avg_confidence:.2f}")
        
        # Performance assertions
        assert avg_processing_time < 1.0, "Average processing time should be under 1 second"
        assert successful_answers >= len(results) * 0.5, "At least 50% of questions should get good answers"
        assert total_time < len(questions) * 0.5, "Concurrent processing should be faster than sequential"
        
        return results

    def test_answer_quality_and_relevance(self):
        """Test answer quality and relevance"""
        print("\n🚀 Testing Answer Quality and Relevance...")
        
        # Setup services and index documents
        services, indexed_documents = self.test_document_indexing_flow()
        
        # Test cases with expected answer characteristics
        quality_test_cases = [
            {
                'question': "What programming language was created by Guido van Rossum?",
                'expected_keywords': ['python', 'guido', 'van rossum'],
                'min_confidence': 0.6,
                'category': 'factual'
            },
            {
                'question': "What are the main types of machine learning?",
                'expected_keywords': ['supervised', 'unsupervised', 'reinforcement'],
                'min_confidence': 0.6,
                'category': 'categorical'
            },
            {
                'question': "What technologies are used in front-end web development?",
                'expected_keywords': ['html', 'css', 'javascript'],
                'min_confidence': 0.6,
                'category': 'technical'
            }
        ]
        
        quality_results = []
        
        for test_case in quality_test_cases:
            question = test_case['question']
            print(f"\n❓ Testing: {question}")
            
            # Process question
            question_embedding = services['embedding_service'].embed_text(question)
            search_results = services['vector_store'].search_similar(
                query_embedding=question_embedding,
                top_k=5
            )
            
            if search_results:
                answer_result = services['llm_service'].generate_answer(
                    question=question,
                    context_chunks=search_results
                )
                
                answer = answer_result['answer'].lower()
                confidence = answer_result['confidence']
                
                # Check for expected keywords
                keywords_found = sum(1 for keyword in test_case['expected_keywords'] 
                                   if keyword in answer)
                keyword_coverage = keywords_found / len(test_case['expected_keywords'])
                
                # Evaluate answer quality
                quality_score = (confidence + keyword_coverage) / 2
                
                print(f"  ✓ Answer confidence: {confidence:.2f}")
                print(f"  ✓ Keyword coverage: {keyword_coverage:.2f} ({keywords_found}/{len(test_case['expected_keywords'])})")
                print(f"  ✓ Quality score: {quality_score:.2f}")
                
                # Verify quality meets expectations
                assert confidence >= test_case['min_confidence'], f"Confidence too low: {confidence}"
                assert keyword_coverage >= 0.3, f"Keyword coverage too low: {keyword_coverage}"
                
                quality_results.append({
                    'question': question,
                    'answer': answer_result['answer'],
                    'confidence': confidence,
                    'keyword_coverage': keyword_coverage,
                    'quality_score': quality_score,
                    'category': test_case['category'],
                    'sources_count': len(search_results)
                })
            else:
                print("  ❌ No relevant sources found")
                quality_results.append({
                    'question': question,
                    'answer': "No relevant information available.",
                    'confidence': 0.0,
                    'keyword_coverage': 0.0,
                    'quality_score': 0.0,
                    'category': test_case['category'],
                    'sources_count': 0
                })
        
        # Calculate overall quality metrics
        avg_confidence = sum(r['confidence'] for r in quality_results) / len(quality_results)
        avg_keyword_coverage = sum(r['keyword_coverage'] for r in quality_results) / len(quality_results)
        avg_quality_score = sum(r['quality_score'] for r in quality_results) / len(quality_results)
        
        print(f"\n🎉 Answer quality test completed!")
        print(f"   📊 Test cases: {len(quality_results)}")
        print(f"   🎯 Average confidence: {avg_confidence:.2f}")
        print(f"   🔍 Average keyword coverage: {avg_keyword_coverage:.2f}")
        print(f"   ⭐ Average quality score: {avg_quality_score:.2f}")
        
        return quality_results

    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases"""
        print("\n🚀 Testing Error Handling and Edge Cases...")
        
        services = self.create_mock_services()
        
        edge_cases = [
            {
                'name': 'Empty question',
                'question': '',
                'expected_behavior': 'handle_gracefully'
            },
            {
                'name': 'Very long question',
                'question': 'What is ' + 'very ' * 100 + 'long question about programming?',
                'expected_behavior': 'handle_gracefully'
            },
            {
                'name': 'Special characters',
                'question': 'What is Python? @#$%^&*()[]{}|\\:";\'<>?,./`~',
                'expected_behavior': 'handle_gracefully'
            },
            {
                'name': 'Non-English question',
                'question': '什么是Python编程语言？',
                'expected_behavior': 'handle_gracefully'
            },
            {
                'name': 'Question with no context',
                'question': 'What is quantum entanglement in parallel universes?',
                'expected_behavior': 'low_confidence'
            }
        ]
        
        edge_case_results = []
        
        for case in edge_cases:
            print(f"\n🧪 Testing: {case['name']}")
            
            try:
                # Process the edge case
                if case['question']:
                    question_embedding = services['embedding_service'].embed_text(case['question'])
                    search_results = services['vector_store'].search_similar(
                        query_embedding=question_embedding,
                        top_k=3
                    )
                    
                    if search_results:
                        answer_result = services['llm_service'].generate_answer(
                            question=case['question'],
                            context_chunks=search_results
                        )
                    else:
                        answer_result = {
                            'answer': "I don't have relevant information to answer this question.",
                            'confidence': 0.0,
                            'sources_used': 0
                        }
                else:
                    # Handle empty question
                    answer_result = {
                        'answer': "Please provide a valid question.",
                        'confidence': 0.0,
                        'sources_used': 0
                    }
                
                print(f"  ✓ Handled gracefully")
                print(f"  ✓ Answer: {answer_result['answer'][:50]}...")
                print(f"  ✓ Confidence: {answer_result['confidence']:.2f}")
                
                edge_case_results.append({
                    'case': case['name'],
                    'question': case['question'],
                    'answer': answer_result['answer'],
                    'confidence': answer_result['confidence'],
                    'handled_successfully': True
                })
                
            except Exception as e:
                print(f"  ❌ Error occurred: {e}")
                edge_case_results.append({
                    'case': case['name'],
                    'question': case['question'],
                    'answer': f"Error: {str(e)}",
                    'confidence': 0.0,
                    'handled_successfully': False
                })
        
        # Verify all edge cases were handled
        successful_handling = sum(1 for r in edge_case_results if r['handled_successfully'])
        
        print(f"\n🎉 Edge case testing completed!")
        print(f"   🧪 Test cases: {len(edge_case_results)}")
        print(f"   ✅ Successfully handled: {successful_handling}/{len(edge_case_results)}")
        
        assert successful_handling == len(edge_case_results), "All edge cases should be handled gracefully"
        
        return edge_case_results

    def test_complete_qa_integration(self):
        """Test the complete QA system integration"""
        print("\n🚀 Running Complete QA System Integration Test...")
        
        # Run all test components
        print("\n" + "="*60)
        print("PHASE 1: DOCUMENT INDEXING")
        print("="*60)
        services, indexed_docs = self.test_document_indexing_flow()
        
        print("\n" + "="*60)
        print("PHASE 2: QUESTION ANSWERING")
        print("="*60)
        qa_results = self.test_question_answering_flow()
        
        print("\n" + "="*60)
        print("PHASE 3: PERFORMANCE TESTING")
        print("="*60)
        performance_results = self.test_concurrent_qa_performance()
        
        print("\n" + "="*60)
        print("PHASE 4: QUALITY ASSESSMENT")
        print("="*60)
        quality_results = self.test_answer_quality_and_relevance()
        
        print("\n" + "="*60)
        print("PHASE 5: ERROR HANDLING")
        print("="*60)
        edge_case_results = self.test_error_handling_and_edge_cases()
        
        # Generate comprehensive report
        print("\n" + "="*60)
        print("INTEGRATION TEST SUMMARY")
        print("="*60)
        
        total_vectors = len(services['vector_store'].vectors)
        successful_qa = sum(1 for r in qa_results if r['confidence'] > 0.5)
        avg_performance = sum(r['processing_time'] for r in performance_results) / len(performance_results)
        avg_quality = sum(r['quality_score'] for r in quality_results) / len(quality_results)
        edge_cases_handled = sum(1 for r in edge_case_results if r['handled_successfully'])
        
        print(f"📚 Documents indexed: {len(indexed_docs)}")
        print(f"🔢 Total vectors stored: {total_vectors}")
        print(f"❓ Questions answered: {len(qa_results)}")
        print(f"✅ Successful answers: {successful_qa}/{len(qa_results)} ({successful_qa/len(qa_results)*100:.1f}%)")
        print(f"⚡ Average response time: {avg_performance:.3f}s")
        print(f"⭐ Average quality score: {avg_quality:.2f}")
        print(f"🛡️ Edge cases handled: {edge_cases_handled}/{len(edge_case_results)} ({edge_cases_handled/len(edge_case_results)*100:.1f}%)")
        
        # Overall system health check
        system_health_score = (
            (successful_qa / len(qa_results)) * 0.3 +  # Answer success rate
            (min(1.0, 1.0 / avg_performance)) * 0.2 +  # Performance score
            avg_quality * 0.3 +  # Quality score
            (edge_cases_handled / len(edge_case_results)) * 0.2  # Error handling
        )
        
        print(f"\n🏥 System Health Score: {system_health_score:.2f}/1.00")
        
        if system_health_score >= 0.8:
            print("🎉 EXCELLENT - System is performing exceptionally well!")
        elif system_health_score >= 0.6:
            print("✅ GOOD - System is performing well with minor areas for improvement")
        elif system_health_score >= 0.4:
            print("⚠️ FAIR - System needs improvement in several areas")
        else:
            print("❌ POOR - System requires significant improvements")
        
        # Assertions for integration test
        assert total_vectors > 0, "Should have indexed documents"
        assert successful_qa >= len(qa_results) * 0.6, "Should answer at least 60% of questions successfully"
        assert avg_performance < 2.0, "Average response time should be under 2 seconds"
        assert avg_quality >= 0.4, "Average quality score should be at least 0.4"
        assert edge_cases_handled == len(edge_case_results), "Should handle all edge cases"
        assert system_health_score >= 0.5, "Overall system health should be at least 0.5"
        
        print(f"\n🎊 Complete QA Integration Test PASSED!")
        
        return {
            'indexed_documents': len(indexed_docs),
            'total_vectors': total_vectors,
            'qa_results': qa_results,
            'performance_results': performance_results,
            'quality_results': quality_results,
            'edge_case_results': edge_case_results,
            'system_health_score': system_health_score
        }


if __name__ == "__main__":
    # Run the complete QA flow test
    test_instance = TestCompleteQAFlow()
    
    print("🧪 RAG System Complete QA Flow Integration Test")
    print("=" * 60)
    
    try:
        test_instance.setup_method()
        result = test_instance.test_complete_qa_integration()
        
        print(f"\n🎉 All tests completed successfully!")
        print(f"System Health Score: {result['system_health_score']:.2f}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_instance.teardown_method()