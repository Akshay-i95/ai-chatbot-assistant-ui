"""
Simple script to check Pinecone database contents and diagnose issues
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

def check_pinecone_status():
    """Check current status of Pinecone database"""
    try:
        print("🔍 Checking Pinecone database status...")
        
        # Configuration
        config = {
            'vector_db_type': 'pinecone',
            'collection_name': 'pdf_chunks',
            'embedding_model': 'all-MiniLM-L6-v2',
            'pinecone_api_key': os.getenv('PINECONE_API_KEY'),
            'pinecone_environment': os.getenv('PINECONE_ENVIRONMENT', 'us-east-1'),
            'pinecone_index_name': os.getenv('PINECONE_INDEX_NAME', 'chatbot-chunks')
        }
        
        from vector_db import EnhancedVectorDBManager
        db = EnhancedVectorDBManager(config)
        
        # Get current stats
        stats = db.get_collection_stats()
        print(f"📊 Current Database Status:")
        print(f"   Database type: {stats.get('database_type')}")
        print(f"   Total chunks: {stats.get('total_chunks')}")
        print(f"   Embedding dimension: {stats.get('embedding_dimension')}")
        print(f"   Embedding model: {stats.get('embedding_model')}")
        
        # Check if index exists and is accessible
        if hasattr(db, 'pinecone_index'):
            index_stats = db.pinecone_index.describe_index_stats()
            print(f"   Index vectors: {index_stats.get('total_vector_count', 0)}")
            print(f"   Index dimension: {index_stats.get('dimension', 'unknown')}")
            
            # List namespaces if any
            namespaces = index_stats.get('namespaces', {})
            if namespaces:
                print(f"   Namespaces: {list(namespaces.keys())}")
            else:
                print(f"   Namespaces: None (using default)")
        
        total_vectors = stats.get('total_chunks', 0)
        
        if total_vectors == 0:
            print("\n❌ ISSUE FOUND: No vectors in database!")
            print("   This means no documents have been processed and stored.")
            print("   You need to:")
            print("   1. Process documents from Azure Blob Storage, OR")
            print("   2. Process existing local documents if you have any, OR") 
            print("   3. Migrate data from FAISS if you had it before")
            
            # Check if there are FAISS files to migrate
            faiss_path = "./vector_store_faiss/enhanced_chunks.index"
            if os.path.exists(faiss_path):
                print(f"\n💡 Found FAISS database at: {faiss_path}")
                print("   Run migration: python migrate_to_pinecone.py --migrate")
            else:
                print(f"\n💡 No existing FAISS database found.")
                print("   You need to process new documents from your Azure storage or local files.")
        else:
            print(f"\n✅ Database looks good with {total_vectors} vectors!")
            
            # Test a simple search
            print("\n🔍 Testing search functionality...")
            results = db.search_similar_chunks("test query", top_k=3)
            print(f"   Search returned {len(results)} results")
            
            if results:
                print("   Sample results:")
                for i, result in enumerate(results[:2], 1):
                    text_preview = result.get('text', '')[:100]
                    score = result.get('similarity_score', 0)
                    print(f"   {i}. Score: {score:.3f} - {text_preview}...")
        
        return total_vectors > 0
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    check_pinecone_status()
