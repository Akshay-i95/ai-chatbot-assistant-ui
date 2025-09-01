"""
AI Chatbot Backend - Streamlit API Server
Provides REST API functionality for the AI chatbot frontend
"""

import streamlit as st
import json
import os
import sys
import logging
from typing import Dict, List, Optional

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

# Import services with graceful fallbacks
@st.cache_resource
def initialize_services():
    """Initialize all backend services"""
    try:
        # Import LLM service
        from llm_service import LLMService
        
        # Configuration
        config = {
            'groq_api_key': os.getenv('GROQ_API_KEY'),
            'groq_model': 'groq/mixtral-8x7b-32768',
            'azure_storage_connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
            'azure_storage_account_name': os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
            'azure_container_name': os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'edifydocumentcontainer'),
            'azure_blob_folder_path': os.getenv('AZURE_BLOB_FOLDER_PATH', 'edipedia/2025-2026/'),
            'edify_api_url': os.getenv('EDIFY_API_BASE_URL', 'https://api.edifyschool.in/v1'),
            'edify_api_key': os.getenv('EDIFY_API_KEY', 'no_auth_required'),
            'edify_api_endpoint': os.getenv('EDIFY_API_ENDPOINT', '/edi-pedia/sop-all')
        }
        
        # Initialize LLM service
        llm_service = LLMService(config)
        
        # Try to initialize enhanced services
        vector_db = None
        chatbot = None
        azure_service = None
        
        try:
            from vector_db import EnhancedVectorDBManager
            vector_db = EnhancedVectorDBManager(config)
            logger.info("✅ Vector DB initialized")
        except Exception as e:
            logger.warning(f"Vector DB not available: {e}")
        
        try:
            from azure_blob_service import create_azure_download_service
            if config.get('azure_storage_connection_string'):
                azure_service = create_azure_download_service(config)
                logger.info("✅ Azure service initialized")
        except Exception as e:
            logger.warning(f"Azure service not available: {e}")
        
        try:
            from chatbot import AIChhatbotInterface
            if vector_db:
                chatbot = AIChhatbotInterface(vector_db, config)
                logger.info("✅ Full chatbot initialized")
        except Exception as e:
            logger.warning(f"Full chatbot not available: {e}")
        
        return {
            'llm_service': llm_service,
            'vector_db': vector_db,
            'chatbot': chatbot,
            'azure_service': azure_service,
            'config': config,
            'status': 'initialized'
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
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
                "content": "I apologize, but the AI service is currently unavailable. Please try again later.",
                "reasoning": "",
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
        if services['chatbot']:
            # Use full chatbot with vector search
            response = services['chatbot'].process_user_query(content, conversation_history)
        else:
            # Fallback to LLM service only
            response = services['llm_service'].generate_response(
                message=content,
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

# Main Streamlit App
def main():
    st.title("🤖 AI Chatbot Backend API")
    st.markdown("**Streamlit-powered backend for AI chatbot**")
    
    # Check if this is an API call
    query_params = st.experimental_get_query_params()
    
    if 'api' in query_params and query_params['api'][0] == 'chat':
        # API endpoint mode
        st.subheader("📡 API Endpoint")
        st.markdown("This is the REST API endpoint for the chatbot.")
        
        # Show API documentation
        app_url = "https://your-streamlit-app.streamlit.app"
        st.code(f"""
# API Endpoint:
POST {app_url}/?api=chat

# Request body:
{{
  "messages": [
    {{"role": "user", "content": "Your question here"}}
  ]
}}

# Response:
{{
  "ai_message": {{
    "content": "AI response",
    "reasoning": "Thought process",
    "metadata": {{"sources": [], "confidence": 0.8}}
  }}
}}
        """)
        
        # API test form
        with st.form("api_test"):
            st.markdown("**Test the API:**")
            test_input = st.text_area(
                "Messages JSON:",
                value='[{"role": "user", "content": "Hello! How can you help me today?"}]',
                height=100
            )
            
            if st.form_submit_button("Test API"):
                try:
                    messages = json.loads(test_input)
                    
                    with st.spinner("Processing..."):
                        response = process_chat_message(messages)
                    
                    st.markdown("**API Response:**")
                    st.json(response)
                    
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON format")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        return
    
    # Main dashboard
    st.subheader("🚀 Backend Status")
    
    # Initialize and show status
    with st.spinner("Initializing services..."):
        services = initialize_services()
    
    if services['status'] == 'initialized':
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("LLM Service", "✅ Active" if services['llm_service'] else "❌ Failed")
        
        with col2:
            st.metric("Vector DB", "✅ Active" if services['vector_db'] else "⚠️ Fallback")
        
        with col3:
            st.metric("Azure Storage", "✅ Active" if services['azure_service'] else "⚠️ Disabled")
        
        with col4:
            st.metric("Full Chatbot", "✅ Active" if services['chatbot'] else "⚠️ Simple Mode")
        
        st.success("🎉 Backend services are ready!")
    else:
        st.error(f"❌ Service initialization failed: {services.get('error', 'Unknown error')}")
    
    # Environment variables status
    st.subheader("🔧 Configuration")
    
    required_vars = {
        'GROQ_API_KEY': 'AI Language Model',
        'AZURE_STORAGE_CONNECTION_STRING': 'Document Storage',
        'EDIFY_API_BASE_URL': 'Document Search API'
    }
    
    for var, description in required_vars.items():
        if os.getenv(var):
            st.success(f"✅ {description} ({var})")
        else:
            st.error(f"❌ {description} ({var}) - Missing")
    
    # API Information
    st.subheader("📋 API Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Primary Endpoint:**")
        st.code("/?api=chat")
        
        st.markdown("**For Vercel Frontend:**")
        if 'streamlit_url' in st.secrets:
            backend_url = st.secrets['streamlit_url']
        else:
            backend_url = "https://your-app-name.streamlit.app"
        
        st.code(f"NEXT_PUBLIC_BACKEND_URL={backend_url}")
    
    with col2:
        st.markdown("**Request Format:**")
        st.code('''{
  "messages": [
    {"role": "user", "content": "question"}
  ]
}''')
    
    # Quick test
    st.subheader("🧪 Quick Test")
    
    with st.form("quick_test"):
        test_question = st.text_input(
            "Test question:", 
            placeholder="What can you help me with?"
        )
        
        if st.form_submit_button("Send Test"):
            if test_question:
                messages = [{"role": "user", "content": test_question}]
                
                with st.spinner("Processing..."):
                    response = process_chat_message(messages)
                
                if 'error' not in response:
                    st.success("✅ Test successful!")
                    
                    # Show response
                    st.markdown("**AI Response:**")
                    st.write(response['ai_message']['content'])
                    
                    # Show metadata
                    metadata = response['ai_message']['metadata']
                    if metadata['sources']:
                        with st.expander(f"📁 Sources ({len(metadata['sources'])})"):
                            for i, source in enumerate(metadata['sources']):
                                st.markdown(f"**{i+1}. {source.get('title', 'Document')}**")
                    
                    if response['ai_message']['reasoning']:
                        with st.expander("🧠 Reasoning"):
                            st.write(response['ai_message']['reasoning'])
                else:
                    st.error(f"❌ Test failed: {response.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
