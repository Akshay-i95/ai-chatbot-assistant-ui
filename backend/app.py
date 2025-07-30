"""
Flask Backend for AI Chatbot with Assistant UI
Provides REST API endpoints for chat functionality, history management, and file operations
"""

import os
import sys
import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# CORS configuration for React frontend
CORS(app, origins=[
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
])

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///chatbot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class ChatSession(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')

class ChatMessage(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('chat_session.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    message_metadata = db.Column(db.JSON, nullable=True)  # For sources, tokens, etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Global components
chatbot_system = None
logger = logging.getLogger(__name__)

def initialize_system():
    """Initialize the chatbot system components"""
    global chatbot_system
    try:
        logger.info("🔄 Initializing system components...")
        
        # Configuration from environment variables
        config = {
            'vector_db_type': os.getenv('VECTOR_DB_TYPE', 'faiss'),
            'vector_db_path': os.getenv('VECTOR_DB_PATH', './vector_store_faiss'),
            'collection_name': os.getenv('COLLECTION_NAME', 'pdf_chunks'),
            'embedding_model': os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
            'max_context_chunks': int(os.getenv('MAX_CONTEXT_CHUNKS', '2')),
            'min_similarity_threshold': float(os.getenv('MIN_SIMILARITY_THRESHOLD', '0.65')),
            'enable_citations': os.getenv('ENABLE_CITATIONS', 'true').lower() == 'true',
            'enable_context_expansion': os.getenv('ENABLE_CONTEXT_EXPANSION', 'false').lower() == 'true',
            'max_context_length': int(os.getenv('MAX_CONTEXT_LENGTH', '2000')),
            # Azure configuration
            'azure_connection_string': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
            'azure_account_name': os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
            'azure_account_key': os.getenv('AZURE_STORAGE_ACCOUNT_KEY'),
            'azure_container_name': os.getenv('AZURE_STORAGE_CONTAINER_NAME'),
            'azure_folder_path': os.getenv('AZURE_BLOB_FOLDER_PATH'),
            # Pinecone configuration
            'pinecone_api_key': os.getenv('PINECONE_API_KEY'),
            'pinecone_environment': os.getenv('PINECONE_ENVIRONMENT', 'us-east-1-aws'),
            'pinecone_index_name': os.getenv('PINECONE_INDEX_NAME', 'chatbot-chunks')
        }
        
        # Initialize Vector Database
        from vector_db import EnhancedVectorDBManager
        vector_db = EnhancedVectorDBManager(config)
        
        # Initialize AI Chatbot
        from chatbot import AIChhatbotInterface
        chatbot = AIChhatbotInterface(vector_db, config)
        
        # Initialize LLM Service
        from llm_service import LLMService
        llm_service = LLMService(config)
        
        # Connect LLM service to chatbot
        chatbot.llm_service = llm_service
        
        chatbot_system = {
            'vector_db': vector_db,
            'chatbot': chatbot,
            'llm_service': llm_service,
            'config': config,
            'status': 'ready'
        }
        
        logger.info("✅ System components loaded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load system components: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# API Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'system_ready': chatbot_system is not None and chatbot_system.get('status') == 'ready'
    })

@app.route('/api/chat/sessions', methods=['GET'])
def get_chat_sessions():
    """Get all chat sessions"""
    try:
        sessions = ChatSession.query.order_by(ChatSession.updated_at.desc()).all()
        return jsonify([{
            'id': session.id,
            'title': session.title,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'message_count': len(session.messages)
        } for session in sessions])
    except Exception as e:
        logger.error(f"Error getting chat sessions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/sessions', methods=['POST'])
def create_chat_session():
    """Create a new chat session"""
    try:
        data = request.get_json() or {}
        title = data.get('title', 'New Chat')
        
        session = ChatSession(title=title)
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'id': session.id,
            'title': session.title,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'message_count': 0
        }), 201
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/sessions/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    """Get a specific chat session with messages"""
    try:
        session = ChatSession.query.get_or_404(session_id)
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
        
        return jsonify({
            'session': {
                'id': session.id,
                'title': session.title,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat()
            },
            'messages': [{
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'metadata': msg.message_metadata,
                'created_at': msg.created_at.isoformat()
            } for msg in messages]
        })
    except Exception as e:
        logger.error(f"Error getting chat session {session_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/sessions/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete a chat session"""
    try:
        session = ChatSession.query.get_or_404(session_id)
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({'message': 'Session deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/sessions/<session_id>/messages', methods=['POST'])
def send_message(session_id):
    """Send a message and get AI response"""
    try:
        if not chatbot_system or chatbot_system.get('status') != 'ready':
            return jsonify({'error': 'System not ready'}), 503
        
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Message content is required'}), 400
        
        user_message = data['content']
        
        # Get session
        session = ChatSession.query.get_or_404(session_id)
        
        # Get conversation history for context
        recent_messages = ChatMessage.query.filter_by(session_id=session_id)\
            .order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        conversation_history = []
        for msg in reversed(recent_messages):
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })
        
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role='user',
            content=user_message
        )
        db.session.add(user_msg)
        
        # Get AI response
        chatbot = chatbot_system['chatbot']
        llm_service = chatbot_system['llm_service']
        
        # Process with chatbot (includes vector search and conversation history)
        response_data = chatbot.process_query(
            user_query=user_message,
            include_context=True,
            conversation_history=conversation_history
        )
        
        ai_content = response_data.get('response', 'I apologize, but I encountered an error processing your request.')
        metadata = {
            'sources': response_data.get('sources', []),
            'context_used': response_data.get('context_used', False),
            'processing_time': response_data.get('processing_time', 0),
            'model_used': response_data.get('model_used', 'unknown'),
            'reasoning': response_data.get('reasoning', ''),
            'confidence': response_data.get('confidence', 0),
            'is_follow_up': response_data.get('is_follow_up', False),
            'follow_up_context': response_data.get('follow_up_context', None)
        }
        
        # Save AI response
        ai_msg = ChatMessage(
            session_id=session_id,
            role='assistant',
            content=ai_content,
            message_metadata=metadata
        )
        db.session.add(ai_msg)
        
        # Update session timestamp
        session.updated_at = datetime.now(timezone.utc)
        
        # Auto-generate title if this is the first exchange
        if len(conversation_history) == 0:
            # Generate a title from the first user message
            title_prompt = f"Generate a short, descriptive title (max 5 words) for a conversation that starts with: '{user_message[:100]}...'"
            try:
                title_response = llm_service.generate_response(title_prompt)
                if title_response.get('success') and title_response.get('response'):
                    clean_title = title_response['response'].strip().strip('"\'')
                    if len(clean_title) <= 50:
                        session.title = clean_title
            except:
                pass  # Keep default title if generation fails
        
        db.session.commit()
        
        return jsonify({
            'user_message': {
                'id': user_msg.id,
                'role': 'user',
                'content': user_message,
                'created_at': user_msg.created_at.isoformat()
            },
            'ai_message': {
                'id': ai_msg.id,
                'role': 'assistant',
                'content': ai_content,
                'metadata': metadata,
                'created_at': ai_msg.created_at.isoformat()
            },
            'session': {
                'id': session.id,
                'title': session.title,
                'updated_at': session.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/download/<filename>')
def download_file(filename):
    """Download a file from Azure storage"""
    try:
        if not chatbot_system or not chatbot_system['chatbot'].azure_service:
            return jsonify({'error': 'Azure download service not available'}), 503
        
        azure_service = chatbot_system['chatbot'].azure_service
        file_data = azure_service.download_pdf(filename)
        
        if file_data:
            return send_file(
                file_data,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Get system status and configuration"""
    try:
        if not chatbot_system:
            return jsonify({
                'status': 'not_initialized',
                'components': {}
            })
        
        config = chatbot_system.get('config', {})
        
        return jsonify({
            'status': chatbot_system.get('status', 'unknown'),
            'components': {
                'vector_db': chatbot_system.get('vector_db') is not None,
                'chatbot': chatbot_system.get('chatbot') is not None,
                'llm_service': chatbot_system.get('llm_service') is not None,
                'azure_service': chatbot_system.get('chatbot') and 
                               chatbot_system['chatbot'].azure_service is not None
            },
            'configuration': {
                'vector_db_type': config.get('vector_db_type'),
                'embedding_model': config.get('embedding_model'),
                'max_context_chunks': config.get('max_context_chunks'),
                'enable_citations': config.get('enable_citations'),
                'enable_context_expansion': config.get('enable_context_expansion'),
                'pinecone_index_name': config.get('pinecone_index_name') if config.get('vector_db_type') == 'pinecone' else None,
                'pinecone_environment': config.get('pinecone_environment') if config.get('vector_db_type') == 'pinecone' else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Initialize system
    initialize_system()
    
    # Run the app
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
