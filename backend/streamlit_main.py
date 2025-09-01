"""
AI Chatbot - Streamlit Deployment App
Simple Streamlit wrapper for the AI chatbot backend functionality
Designed for Streamlit Cloud deployment
"""

import streamlit as st
import json
import os
import sys
import logging
from typing import Dict, List, Optional
import requests
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Chatbot API",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load environment variables from Streamlit secrets or .env
def get_config():
    """Get configuration from Streamlit secrets or environment variables"""
    config = {}
    
    # Try Streamlit secrets first (for deployment)
    if hasattr(st, 'secrets'):
        try:
            config.update({
                'groq_api_key': st.secrets.get('GROQ_API_KEY', os.getenv('GROQ_API_KEY')),
                'groq_model': st.secrets.get('GROQ_MODEL', os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')),
                'azure_storage_connection_string': st.secrets.get('AZURE_STORAGE_CONNECTION_STRING', os.getenv('AZURE_STORAGE_CONNECTION_STRING')),
                'azure_storage_account_name': st.secrets.get('AZURE_STORAGE_ACCOUNT_NAME', os.getenv('AZURE_STORAGE_ACCOUNT_NAME')),
                'azure_container_name': st.secrets.get('AZURE_STORAGE_CONTAINER_NAME', os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'edifydocumentcontainer')),
                'azure_blob_folder_path': st.secrets.get('AZURE_BLOB_FOLDER_PATH', os.getenv('AZURE_BLOB_FOLDER_PATH', 'edipedia/2025-2026/')),
                'edify_api_url': st.secrets.get('EDIFY_API_BASE_URL', os.getenv('EDIFY_API_BASE_URL', 'https://api.edifyschool.in/v1')),
                'edify_api_key': st.secrets.get('EDIFY_API_KEY', os.getenv('EDIFY_API_KEY', 'no_auth_required')),
                'edify_api_endpoint': st.secrets.get('EDIFY_API_ENDPOINT', os.getenv('EDIFY_API_ENDPOINT', '/edi-pedia/sop-all')),
                'pinecone_api_key': st.secrets.get('PINECONE_API_KEY', os.getenv('PINECONE_API_KEY')),
                'pinecone_environment': st.secrets.get('PINECONE_ENVIRONMENT', os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')),
                'pinecone_index_name': st.secrets.get('PINECONE_INDEX_NAME', os.getenv('PINECONE_INDEX_NAME', 'edify-chatbot')),
                'vector_db_type': st.secrets.get('VECTOR_DB_TYPE', os.getenv('VECTOR_DB_TYPE', 'pinecone'))
            })
        except:
            pass
    
    # Fallback to environment variables
    if not config.get('groq_api_key'):
        config.update({
            'groq_api_key': os.getenv('GROQ_API_KEY'),
            'groq_model': os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile'),
            'azure_storage_connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
            'azure_storage_account_name': os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
            'azure_container_name': os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'edifydocumentcontainer'),
            'azure_blob_folder_path': os.getenv('AZURE_BLOB_FOLDER_PATH', 'edipedia/2025-2026/'),
            'edify_api_url': os.getenv('EDIFY_API_BASE_URL', 'https://api.edifyschool.in/v1'),
            'edify_api_key': os.getenv('EDIFY_API_KEY', 'no_auth_required'),
            'edify_api_endpoint': os.getenv('EDIFY_API_ENDPOINT', '/edi-pedia/sop-all'),
            'pinecone_api_key': os.getenv('PINECONE_API_KEY'),
            'pinecone_environment': os.getenv('PINECONE_ENVIRONMENT', 'us-east-1'),
            'pinecone_index_name': os.getenv('PINECONE_INDEX_NAME', 'edify-chatbot'),
            'vector_db_type': os.getenv('VECTOR_DB_TYPE', 'pinecone')
        })
    
    return config

# Initialize services with caching
@st.cache_resource
def initialize_services():
    """Initialize all backend services with proper error handling"""
    config = get_config()
    
    if not config.get('groq_api_key'):
        return {
            'status': 'failed',
            'error': 'Missing GROQ_API_KEY - Please configure in Streamlit secrets or environment variables'
        }
    
    try:
        # Import services
        from llm_service import LLMService
        
        # Initialize LLM service
        llm_service = LLMService(config)
        
        # Initialize other services
        services = {
            'llm_service': llm_service,
            'config': config,
            'status': 'initialized'
        }
        
        # Try to initialize vector DB
        try:
            from vector_db import EnhancedVectorDBManager
            if config.get('pinecone_api_key'):
                vector_db = EnhancedVectorDBManager(config)
                services['vector_db'] = vector_db
                logger.info("✅ Vector DB initialized")
            else:
                logger.warning("Pinecone API key not found - vector search disabled")
        except Exception as e:
            logger.warning(f"Vector DB initialization failed: {e}")
        
        # Try to initialize Azure service
        try:
            from azure_blob_service import create_azure_download_service
            if config.get('azure_storage_connection_string'):
                azure_service = create_azure_download_service(config)
                services['azure_service'] = azure_service
                logger.info("✅ Azure service initialized")
        except Exception as e:
            logger.warning(f"Azure service initialization failed: {e}")
        
        # Try to initialize full chatbot
        try:
            from chatbot import AIChhatbotInterface
            if services.get('vector_db'):
                chatbot = AIChhatbotInterface(services['vector_db'], config)
                services['chatbot'] = chatbot
                logger.info("✅ Full chatbot initialized")
        except Exception as e:
            logger.warning(f"Full chatbot initialization failed: {e}")
        
        return services
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        }

def process_chat_message(messages: List[Dict]) -> Dict:
    """Process chat message and return AI response"""
    services = initialize_services()
    
    if services['status'] == 'failed':
        return {
            "error": f"Service initialization failed: {services.get('error', 'Unknown error')}",
            "ai_message": {
                "content": "I apologize, but the AI service is currently unavailable. Please check the configuration.",
                "reasoning": f"Error: {services.get('error', 'Unknown error')}",
                "metadata": {"sources": [], "confidence": 0, "context_used": 0}
            }
        }
    
    try:
        # Extract user message
        if not messages:
            raise ValueError("No messages provided")
        
        user_message = messages[-1]
        if user_message.get('role') != 'user':
            raise ValueError("Last message must be from user")
        
        content = user_message.get('content', '')
        if isinstance(content, list):
            # Handle array format (OpenAI style)
            text_part = next((part for part in content if part.get('type') == 'text'), {})
            content = text_part.get('text', '')
        
        if not content.strip():
            raise ValueError("Empty message content")
        
        # Convert conversation history
        conversation_history = []
        for msg in messages[:-1]:  # Exclude current message
            msg_content = msg.get('content', '')
            if isinstance(msg_content, list):
                text_part = next((part for part in msg_content if part.get('type') == 'text'), {})
                msg_content = text_part.get('text', '')
            
            conversation_history.append({
                'role': msg.get('role', 'user'),
                'content': msg_content
            })
        
        # Process with available services
        if services.get('chatbot'):
            # Use full chatbot with vector search
            response = services['chatbot'].process_user_query(content, conversation_history)
        else:
            # Fallback to LLM service only
            response = services['llm_service'].generate_response(
                query=content,
                context="",
                conversation_history=conversation_history
            )
        
        # Standardize response format
        ai_content = response.get('content', response.get('response', 'No response generated'))
        reasoning = response.get('reasoning', '')
        sources = response.get('sources', [])
        confidence = response.get('confidence', 0.8)
        context_used = response.get('context_chunks_used', len(sources))
        
        return {
            "ai_message": {
                "content": ai_content,
                "reasoning": reasoning,
                "metadata": {
                    "sources": sources,
                    "confidence": confidence,
                    "context_used": context_used
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return {
            "error": str(e),
            "ai_message": {
                "content": "I apologize, but I encountered an error processing your request. Please try again.",
                "reasoning": f"Error: {str(e)}",
                "metadata": {"sources": [], "confidence": 0, "context_used": 0}
            }
        }

# API endpoint handler
def handle_api_request():
    """Handle API requests for chat functionality"""
    st.header("🔗 API Endpoint")
    
    # Show API documentation
    st.markdown("""
    **This is the REST API endpoint for the AI chatbot.**
    
    Use this URL in your frontend application:
    """)
    
    app_url = st.secrets.get("app_url", "https://your-app-name.streamlit.app") if hasattr(st, 'secrets') else "https://your-app-name.streamlit.app"
    st.code(f"{app_url}/?api=chat", language="bash")
    
    st.markdown("**Request Format:**")
    st.code('''POST /?api=chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Your question here"}
  ]
}''', language="json")
    
    st.markdown("**Response Format:**")
    st.code('''{
  "ai_message": {
    "content": "AI response text",
    "reasoning": "AI thought process",
    "metadata": {
      "sources": [...],
      "confidence": 0.8,
      "context_used": 2
    }
  }
}''', language="json")
    
    # Test interface
    st.subheader("🧪 Test API")
    
    with st.form("api_test"):
        test_message = st.text_area(
            "Test Message:",
            value="Hello! How can you help me with school-related questions?",
            height=100
        )
        
        if st.form_submit_button("Send Test Message"):
            if test_message:
                messages = [{"role": "user", "content": test_message}]
                
                with st.spinner("Processing..."):
                    response = process_chat_message(messages)
                
                st.markdown("**API Response:**")
                st.json(response)
            else:
                st.error("Please enter a test message")

# Main dashboard
def show_dashboard():
    """Show the main dashboard with service status"""
    st.header("🤖 AI Chatbot Backend")
    st.markdown("**Streamlit-powered backend for AI chatbot applications**")
    
    # Service status
    st.subheader("🚀 Service Status")
    
    with st.spinner("Checking services..."):
        services = initialize_services()
    
    if services['status'] == 'initialized':
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🤖 LLM Service", "✅ Active" if services.get('llm_service') else "❌ Failed")
        
        with col2:
            st.metric("🔍 Vector Search", "✅ Active" if services.get('vector_db') else "⚠️ Disabled")
        
        with col3:
            st.metric("☁️ Azure Storage", "✅ Active" if services.get('azure_service') else "⚠️ Disabled")
        
        with col4:
            st.metric("🧠 Full Chatbot", "✅ Active" if services.get('chatbot') else "⚠️ Simple Mode")
        
        st.success("🎉 Backend services are operational!")
        
    else:
        st.error(f"❌ Service initialization failed: {services.get('error', 'Unknown error')}")
        st.markdown("**Please check your environment variables or Streamlit secrets configuration.**")
    
    # Configuration status
    st.subheader("⚙️ Configuration")
    
    config = get_config()
    
    config_checks = [
        ('GROQ_API_KEY', 'AI Language Model', config.get('groq_api_key')),
        ('PINECONE_API_KEY', 'Vector Search Database', config.get('pinecone_api_key')),
        ('AZURE_STORAGE_CONNECTION_STRING', 'Document Storage', config.get('azure_storage_connection_string')),
        ('EDIFY_API_BASE_URL', 'Document Search API', config.get('edify_api_url'))
    ]
    
    for var_name, description, value in config_checks:
        if value:
            st.success(f"✅ {description} ({var_name})")
        else:
            st.warning(f"⚠️ {description} ({var_name}) - Not configured")
    
    # Quick test
    st.subheader("🧪 Quick Test")
    
    with st.form("quick_test"):
        test_question = st.text_input(
            "Test Question:", 
            placeholder="What can you help me with today?"
        )
        
        if st.form_submit_button("Test Chatbot"):
            if test_question:
                messages = [{"role": "user", "content": test_question}]
                
                with st.spinner("Processing..."):
                    response = process_chat_message(messages)
                
                if 'error' not in response:
                    st.success("✅ Test successful!")
                    
                    # Show response
                    st.markdown("**AI Response:**")
                    st.write(response['ai_message']['content'])
                    
                    # Show reasoning if available
                    if response['ai_message']['reasoning']:
                        with st.expander("🧠 AI Reasoning"):
                            st.write(response['ai_message']['reasoning'])
                    
                    # Show sources if available
                    metadata = response['ai_message']['metadata']
                    if metadata['sources']:
                        with st.expander(f"📁 Sources ({len(metadata['sources'])})"):
                            for i, source in enumerate(metadata['sources'], 1):
                                st.markdown(f"**{i}. {source.get('title', f'Source {i}')}**")
                                if source.get('content'):
                                    st.text(source['content'][:200] + "..." if len(source.get('content', '')) > 200 else source['content'])
                else:
                    st.error(f"❌ Test failed: {response.get('error', 'Unknown error')}")
            else:
                st.warning("Please enter a test question")

def main():
    """Main Streamlit application"""
    
    # Check for API mode
    query_params = st.query_params
    
    if 'api' in query_params and query_params['api'] == 'chat':
        # API endpoint mode
        handle_api_request()
    else:
        # Dashboard mode
        show_dashboard()
    
    # Footer
    st.markdown("---")
    st.markdown(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
