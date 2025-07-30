"""
Pinecone Index Management Script
Helps manage Pinecone indexes - create, delete, list
"""

import os
import sys
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

def get_pinecone_client():
    """Get Pinecone client"""
    try:
        from pinecone import Pinecone
        
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        
        return Pinecone(api_key=api_key)
    except Exception as e:
        logger.error(f"❌ Failed to create Pinecone client: {str(e)}")
        return None

def list_indexes():
    """List all Pinecone indexes"""
    try:
        pc = get_pinecone_client()
        if not pc:
            return False
        
        indexes = list(pc.list_indexes())
        
        if not indexes:
            logger.info("📋 No indexes found")
            return True
        
        logger.info("📋 Available indexes:")
        for index in indexes:
            logger.info(f"   - Name: {index.name}")
            logger.info(f"     Dimension: {index.dimension}")
            logger.info(f"     Metric: {index.metric}")
            logger.info(f"     Status: {index.status.state}")
            logger.info(f"     Host: {index.host}")
            logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to list indexes: {str(e)}")
        return False

def delete_index(index_name):
    """Delete a Pinecone index"""
    try:
        pc = get_pinecone_client()
        if not pc:
            return False
        
        logger.info(f"🗑️ Deleting index: {index_name}")
        pc.delete_index(index_name)
        
        logger.info(f"✅ Index '{index_name}' deleted successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to delete index '{index_name}': {str(e)}")
        return False

def create_index(index_name, dimension=384, metric='cosine'):
    """Create a new Pinecone index"""
    try:
        from pinecone import ServerlessSpec
        pc = get_pinecone_client()
        if not pc:
            return False
        
        environment = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1-aws')
        
        logger.info(f"🌲 Creating index: {index_name}")
        logger.info(f"   Dimension: {dimension}")
        logger.info(f"   Metric: {metric}")
        logger.info(f"   Environment: {environment}")
        
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud='aws',
                region=environment
            )
        )
        
        logger.info(f"✅ Index '{index_name}' created successfully")
        logger.info("⏳ Waiting for index to be ready...")
        
        # Wait for index to be ready
        import time
        time.sleep(10)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create index '{index_name}': {str(e)}")
        return False

def get_index_stats(index_name):
    """Get statistics for a specific index"""
    try:
        pc = get_pinecone_client()
        if not pc:
            return False
        
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        
        logger.info(f"📊 Statistics for index '{index_name}':")
        logger.info(f"   Total vectors: {stats.get('total_vector_count', 0)}")
        logger.info(f"   Index fullness: {stats.get('index_fullness', 0):.2%}")
        
        namespaces = stats.get('namespaces', {})
        if namespaces:
            logger.info("   Namespaces:")
            for ns_name, ns_stats in namespaces.items():
                logger.info(f"     - {ns_name}: {ns_stats.get('vector_count', 0)} vectors")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats for index '{index_name}': {str(e)}")
        return False

def recreate_index_with_correct_dimensions():
    """Recreate the chatbot index with correct dimensions for all-MiniLM-L6-v2"""
    try:
        index_name = os.getenv('PINECONE_INDEX_NAME', 'chatbot-chunks')
        
        logger.info(f"🔄 Recreating index '{index_name}' with correct dimensions...")
        
        # Check if index exists
        pc = get_pinecone_client()
        if not pc:
            return False
        
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        
        if index_name in existing_indexes:
            logger.info(f"🗑️ Deleting existing index '{index_name}'...")
            if not delete_index(index_name):
                return False
            
            # Wait for deletion to complete
            import time
            time.sleep(10)
        
        # Create new index with 384 dimensions (for all-MiniLM-L6-v2)
        logger.info(f"🌲 Creating new index with 384 dimensions...")
        success = create_index(index_name, dimension=384, metric='cosine')
        
        if success:
            logger.info("🎉 Index recreated successfully!")
            logger.info("💡 You can now run your tests with the correct dimensions")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Failed to recreate index: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pinecone Index Management Tool")
    parser.add_argument("--list", action="store_true", help="List all indexes")
    parser.add_argument("--delete", type=str, help="Delete specified index")
    parser.add_argument("--create", type=str, help="Create new index with specified name")
    parser.add_argument("--dimension", type=int, default=384, help="Dimension for new index (default: 384)")
    parser.add_argument("--metric", type=str, default="cosine", help="Metric for new index (default: cosine)")
    parser.add_argument("--stats", type=str, help="Get stats for specified index")
    parser.add_argument("--recreate", action="store_true", help="Recreate chatbot index with correct dimensions")
    
    args = parser.parse_args()
    
    if args.list:
        success = list_indexes()
        sys.exit(0 if success else 1)
    elif args.delete:
        success = delete_index(args.delete)
        sys.exit(0 if success else 1)
    elif args.create:
        success = create_index(args.create, args.dimension, args.metric)
        sys.exit(0 if success else 1)
    elif args.stats:
        success = get_index_stats(args.stats)
        sys.exit(0 if success else 1)
    elif args.recreate:
        success = recreate_index_with_correct_dimensions()
        sys.exit(0 if success else 1)
    else:
        print("Usage:")
        print("  python manage_pinecone_index.py --list                    # List all indexes")
        print("  python manage_pinecone_index.py --delete <name>           # Delete index")
        print("  python manage_pinecone_index.py --create <name>           # Create index")
        print("  python manage_pinecone_index.py --stats <name>            # Get index stats")
        print("  python manage_pinecone_index.py --recreate                # Recreate chatbot index")
        print("")
        print("Options for --create:")
        print("  --dimension <int>     Embedding dimension (default: 384)")
        print("  --metric <str>        Similarity metric (default: cosine)")
        sys.exit(1)
