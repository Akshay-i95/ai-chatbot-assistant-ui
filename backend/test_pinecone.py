"""
Quick Test Script for Pinecone Integration
Tests basic Pinecone functionality with sample data
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pinecone_basic_operations():
    """Test basic Pinecone operations with sample data"""
    try:
        logger.info("🧪 Starting Pinecone basic operations test...")
        
        # Configuration
        config = {
            'vector_db_type': 'pinecone',
            'collection_name': 'test_chunks',
            'embedding_model': 'all-MiniLM-L6-v2',
            'pinecone_api_key': os.getenv('PINECONE_API_KEY'),
            'pinecone_environment': os.getenv('PINECONE_ENVIRONMENT', 'us-east-1-aws'),
            'pinecone_index_name': os.getenv('PINECONE_INDEX_NAME', 'chatbot-chunks')
        }
        
        if not config['pinecone_api_key']:
            logger.error("❌ PINECONE_API_KEY not found. Please set it in your .env file")
            return False
        
        # Initialize vector database
        from vector_db import EnhancedVectorDBManager
        db = EnhancedVectorDBManager(config)
        
        # Test 1: Store sample chunks
        logger.info("📦 Test 1: Storing sample chunks...")
        sample_chunks = [
            {
                'chunk_id': 'test_chunk_1',
                'text': 'Artificial intelligence (AI) refers to the simulation of human intelligence in machines.',
                'filename': 'test_doc.pdf',
                'chunk_index': 0,
                'section_index': 0,
                'content_type': 'definition',
                'chunk_tokens': 50,
                'preview': 'Artificial intelligence refers to...',
                'file_pages': 1,
                'extraction_method': 'test',
                'created_at': time.time()
            },
            {
                'chunk_id': 'test_chunk_2', 
                'text': 'Machine learning is a subset of AI that enables computers to learn without being explicitly programmed.',
                'filename': 'test_doc.pdf',
                'chunk_index': 1,
                'section_index': 0,
                'content_type': 'explanation',
                'chunk_tokens': 45,
                'preview': 'Machine learning is a subset...',
                'file_pages': 1,
                'extraction_method': 'test',
                'created_at': time.time()
            },
            {
                'chunk_id': 'test_chunk_3',
                'text': 'Deep learning uses neural networks with multiple layers to analyze data and make predictions.',
                'filename': 'test_doc.pdf',
                'chunk_index': 2,
                'section_index': 1,
                'content_type': 'technical',
                'chunk_tokens': 40,
                'preview': 'Deep learning uses neural networks...',
                'file_pages': 1,
                'extraction_method': 'test',
                'created_at': time.time()
            }
        ]
        
        success = db.store_chunks_batch(sample_chunks)
        if not success:
            logger.error("❌ Failed to store sample chunks")
            return False
        
        logger.info("✅ Sample chunks stored successfully")
        
        # Wait a moment for indexing
        time.sleep(2)
        
        # Test 2: Search for similar content
        logger.info("🔍 Test 2: Searching for similar content...")
        
        test_queries = [
            "What is artificial intelligence?",
            "Tell me about machine learning",
            "How do neural networks work?"
        ]
        
        for query in test_queries:
            logger.info(f"🔍 Query: '{query}'")
            results = db.search_similar_chunks(query, top_k=2)
            
            if results:
                logger.info(f"✅ Found {len(results)} results")
                for i, result in enumerate(results, 1):
                    logger.info(f"  {i}. Score: {result['similarity_score']:.3f} - {result['text'][:100]}...")
            else:
                logger.warning(f"⚠️ No results found for query")
        
        # Test 3: Get collection statistics
        logger.info("📊 Test 3: Getting collection statistics...")
        stats = db.get_collection_stats()
        logger.info(f"✅ Collection stats:")
        logger.info(f"   Database type: {stats.get('database_type')}")
        logger.info(f"   Total chunks: {stats.get('total_chunks')}")
        logger.info(f"   Embedding dimension: {stats.get('embedding_dimension')}")
        logger.info(f"   Average query time: {stats.get('average_query_time_ms', 0):.2f}ms")
        
        # Test 4: Filter search
        logger.info("🎯 Test 4: Testing filtered search...")
        filtered_results = db.search_similar_chunks(
            "artificial intelligence", 
            top_k=5, 
            filters={'content_type': 'definition'}
        )
        logger.info(f"✅ Filtered search returned {len(filtered_results)} results")
        
        # Test 5: Delete test data (cleanup)
        logger.info("🧹 Test 5: Cleaning up test data...")
        cleanup_success = db.delete_chunks_by_filename('test_doc.pdf')
        if cleanup_success:
            logger.info("✅ Test data cleaned up successfully")
        else:
            logger.warning("⚠️ Cleanup might have failed (this is okay for testing)")
        
        logger.info("🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_pinecone_performance():
    """Test Pinecone performance with larger dataset"""
    try:
        logger.info("⚡ Starting Pinecone performance test...")
        
        config = {
            'vector_db_type': 'pinecone',
            'collection_name': 'test_chunks',
            'embedding_model': 'all-MiniLM-L6-v2',
            'pinecone_api_key': os.getenv('PINECONE_API_KEY'),
            'pinecone_environment': os.getenv('PINECONE_ENVIRONMENT', 'us-east-1-aws'),
            'pinecone_index_name': os.getenv('PINECONE_INDEX_NAME', 'chatbot-chunks')
        }
        
        from vector_db import EnhancedVectorDBManager
        db = EnhancedVectorDBManager(config)
        
        # Generate test data
        logger.info("📦 Generating test data...")
        import uuid
        
        large_chunks = []
        topics = [
            "machine learning algorithms and their applications",
            "deep neural networks and backpropagation",
            "natural language processing and transformers",
            "computer vision and convolutional networks", 
            "reinforcement learning and game theory",
            "data science and statistical analysis",
            "cloud computing and distributed systems",
            "cybersecurity and encryption methods",
            "blockchain technology and cryptocurrencies",
            "quantum computing and quantum algorithms"
        ]
        
        for i in range(50):  # Create 50 test chunks
            topic = topics[i % len(topics)]
            chunk = {
                'chunk_id': f'perf_test_{uuid.uuid4().hex[:8]}',
                'text': f'This is a detailed explanation about {topic}. ' * 10,  # Longer text
                'filename': f'performance_test_{i // 10}.pdf',
                'chunk_index': i % 10,
                'section_index': i // 25,
                'content_type': 'educational',
                'chunk_tokens': 100,
                'preview': f'This is a detailed explanation about {topic}...',
                'file_pages': 5,
                'extraction_method': 'performance_test',
                'created_at': time.time()
            }
            large_chunks.append(chunk)
        
        # Test batch upload performance
        logger.info("⏱️ Testing batch upload performance...")
        start_time = time.time()
        success = db.store_chunks_batch(large_chunks)
        upload_time = time.time() - start_time
        
        if success:
            logger.info(f"✅ Uploaded {len(large_chunks)} chunks in {upload_time:.2f}s")
            logger.info(f"📊 Upload rate: {len(large_chunks)/upload_time:.1f} chunks/second")
        else:
            logger.error("❌ Batch upload failed")
            return False
        
        # Wait for indexing
        time.sleep(3)
        
        # Test search performance
        logger.info("⏱️ Testing search performance...")
        test_queries = [
            "machine learning algorithms",
            "neural networks and deep learning", 
            "natural language processing",
            "computer vision applications",
            "quantum computing principles"
        ]
        
        total_search_time = 0
        total_queries = len(test_queries)
        
        for query in test_queries:
            start_time = time.time()
            results = db.search_similar_chunks(query, top_k=10)
            search_time = time.time() - start_time
            total_search_time += search_time
            
            logger.info(f"🔍 Query '{query[:30]}...' took {search_time*1000:.1f}ms, found {len(results)} results")
        
        avg_search_time = total_search_time / total_queries
        logger.info(f"📊 Average search time: {avg_search_time*1000:.1f}ms")
        
        # Cleanup
        logger.info("🧹 Cleaning up performance test data...")
        for i in range(5):  # Clean up the test files we created
            db.delete_chunks_by_filename(f'performance_test_{i}.pdf')
        
        logger.info("🎉 Performance test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pinecone Integration Test Suite")
    parser.add_argument("--basic", action="store_true", help="Run basic functionality tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.all or args.basic:
        logger.info("🚀 Running basic functionality tests...")
        basic_success = test_pinecone_basic_operations()
        if not basic_success:
            sys.exit(1)
    
    if args.all or args.performance:
        logger.info("🚀 Running performance tests...")
        perf_success = test_pinecone_performance()
        if not perf_success:
            sys.exit(1)
    
    if not any([args.basic, args.performance, args.all]):
        print("Usage:")
        print("  python test_pinecone.py --basic       # Test basic functionality")
        print("  python test_pinecone.py --performance # Test performance")
        print("  python test_pinecone.py --all         # Run all tests")
        sys.exit(1)
    
    logger.info("✅ All tests passed!")
