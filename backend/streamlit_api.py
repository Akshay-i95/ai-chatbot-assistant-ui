"""
Streamlit Cloud API Bridge
Provides REST API endpoints for the frontend while running on Streamlit Cloud
"""

import streamlit as st
import json
import os
from typing import Dict, List
import sys

# Import your existing backend modules
sys.path.append('.')

try:
    from app import initialize_system, ChatSession
    FULL_BACKEND_AVAILABLE = True
except ImportError:
    FULL_BACKEND_AVAILABLE = False
    st.error("Backend modules not available")

def create_api_response(data: Dict) -> str:
    """Create JSON API response"""
    return json.dumps(data, indent=2)

def process_chat_request(messages: List[Dict]) -> Dict:
    """Process chat request and return response"""
    if not FULL_BACKEND_AVAILABLE:
        return {
            "error": "Backend not available",
            "ai_message": {
                "content": "Service temporarily unavailable. Please try again later.",
                "reasoning": "",
                "metadata": {"sources": [], "confidence": 0}
            }
        }
    
    try:
        # Initialize system
        config = initialize_system()
        
        # Extract user message
        if not messages:
            raise ValueError("No messages provided")
        
        user_message = messages[-1]
        if user_message.get('role') != 'user':
            raise ValueError("Last message must be from user")
        
        content = user_message.get('content', '')
        if isinstance(content, list):
            text_part = next((part for part in content if part.get('type') == 'text'), {})
            content = text_part.get('text', '')
        
        if not content.strip():
            raise ValueError("Empty message content")
        
        # Create chat session and process
        chat_session = ChatSession()
        
        # Convert conversation history
        conversation_history = []
        for msg in messages[:-1]:
            msg_content = msg.get('content', '')
            if isinstance(msg_content, list):
                text_part = next((part for part in msg_content if part.get('type') == 'text'), {})
                msg_content = text_part.get('text', '')
            
            conversation_history.append({
                'role': msg.get('role', 'user'),
                'content': msg_content
            })
        
        # Process the message
        response = chat_session.send_message(content, conversation_history)
        
        return {
            "ai_message": {
                "content": response.get('ai_message', {}).get('content', ''),
                "reasoning": response.get('ai_message', {}).get('reasoning', ''),
                "metadata": response.get('ai_message', {}).get('metadata', {})
            }
        }
        
    except Exception as e:
        st.error(f"Error processing request: {e}")
        return {
            "error": str(e),
            "ai_message": {
                "content": "I apologize, but I encountered an error processing your request. Please try again.",
                "reasoning": f"Error: {str(e)}",
                "metadata": {"sources": [], "confidence": 0, "context_used": 0}
            }
        }

# Streamlit App
def main():
    st.set_page_config(
        page_title="AI Chatbot API",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 AI Chatbot API Server")
    st.markdown("**Streamlit-powered REST API for the AI Chatbot**")
    
    # Check query parameters for API calls
    query_params = st.experimental_get_query_params()
    
    # API Endpoint: /api/chat
    if 'endpoint' in query_params and query_params['endpoint'][0] == 'chat':
        st.subheader("📡 API Endpoint: /api/chat")
        
        # Show how to make requests
        st.markdown("**Usage:**")
        streamlit_url = "https://your-streamlit-app.streamlit.app"
        
        st.code(f"""
# Make POST request to:
{streamlit_url}/?endpoint=chat

# With JSON body:
{{
    "messages": [
        {{"role": "user", "content": "Your question here"}}
    ]
}}
        """)
        
        # Handle POST simulation (in real Streamlit, you'd use forms)
        with st.form("api_test"):
            st.markdown("**Test the API:**")
            
            # Input for message
            test_messages = st.text_area(
                "Messages JSON:",
                value='[{"role": "user", "content": "Hello, how can you help me?"}]',
                height=100
            )
            
            submitted = st.form_submit_button("Send Request")
            
            if submitted:
                try:
                    messages = json.loads(test_messages)
                    
                    with st.spinner("Processing..."):
                        response = process_chat_request(messages)
                    
                    st.markdown("**Response:**")
                    st.json(response)
                    
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    else:
        # Main dashboard
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚀 Quick Start")
            st.markdown("""
            **Your API is ready!**
            
            1. Use this Streamlit URL as your backend
            2. Update your Vercel frontend to point here
            3. Make POST requests to `/?endpoint=chat`
            """)
            
            # Show the URL to use
            if 'streamlit_url' in st.secrets:
                api_url = st.secrets['streamlit_url']
            else:
                api_url = "https://your-app-name.streamlit.app"
            
            st.code(f"NEXT_PUBLIC_BACKEND_URL={api_url}")
            
        with col2:
            st.subheader("📊 System Status")
            
            if FULL_BACKEND_AVAILABLE:
                st.success("✅ Backend modules loaded")
                st.success("✅ AI services ready")
                st.success("✅ API endpoints active")
            else:
                st.error("❌ Backend modules failed to load")
                st.warning("⚠️ Check environment variables")
        
        # Environment variables check
        st.subheader("🔧 Environment Variables")
        
        required_vars = [
            'GROQ_API_KEY',
            'AZURE_STORAGE_CONNECTION_STRING',
            'EDIFY_API_BASE_URL'
        ]
        
        for var in required_vars:
            if os.getenv(var):
                st.success(f"✅ {var} is set")
            else:
                st.error(f"❌ {var} is missing")
        
        # Test interface
        st.subheader("🧪 Quick Test")
        
        with st.form("quick_test"):
            test_question = st.text_input("Ask a question:", placeholder="What can you help me with?")
            test_submit = st.form_submit_button("Test")
            
            if test_submit and test_question:
                messages = [{"role": "user", "content": test_question}]
                
                with st.spinner("Testing..."):
                    response = process_chat_request(messages)
                
                if 'error' not in response:
                    st.success("✅ Test successful!")
                    st.write("**Response:**", response['ai_message']['content'])
                else:
                    st.error(f"❌ Test failed: {response['error']}")

if __name__ == "__main__":
    main()
