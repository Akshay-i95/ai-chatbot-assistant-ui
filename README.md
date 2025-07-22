# 🤖 **Edify AI Chatbot**

Modern AI-powered document analysis with beautiful React interface and Flask backend.

## 🚀 **Quick Start**

### Backend (Flask API)
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

Visit: **http://localhost:3000**

## ✨ **Features**

- � **Modern Chat Interface** - ChatGPT-style responsive design
- �🔍 **Smart Document Search** - Vector-based similarity search
- 🤖 **AI-Powered Responses** - Gemini/OpenRouter LLM integration  
- 📚 **Source Attribution** - Always shows source documents with download links
- � **Conversation Memory** - Persistent chat history with SQLite
- ⚡ **Real-time Responses** - Fast API with streaming support
- 🎨 **Beautiful Interface** - Modern React UI with animations
- 📱 **Responsive Design** - Works on desktop and mobile
- 🔄 **Session Management** - Multiple chat sessions support

## 🏗️ **Architecture**

```
🌐 React Frontend (Vite + TypeScript)
    ↓ REST API
🐍 Flask Backend (Python)
    ↓
🤖 AI Chatbot (chatbot.py)  
    ↓
🗄️ Vector Database (vector_db.py)
    ↓
📄 PDF Processor (pdf_processor.py)
```

## 🔧 **Configuration**

Add your API keys to `.env` in the backend directory:
```
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

## 💾 **Database**

- **Chat Sessions**: Stored in SQLite with automatic titles
- **Messages**: Full conversation history with metadata
- **Sources**: Link to original documents with download support

## 🎯 **Production Ready**

- Clean, scalable architecture
- Error handling and logging
- API rate limiting support
- Responsive mobile-first design
- Modern TypeScript codebase
- Performance optimized

## 📱 **Modern Features**

- **ChatGPT-style Interface**: Clean, modern chat bubbles
- **Markdown Support**: Rich text formatting in responses
- **Source Downloads**: One-click PDF downloads
- **Copy Messages**: Easy message copying
- **Typing Indicators**: Real-time response feedback
- **Session Management**: Multiple conversation threads
- **Responsive Design**: Mobile and desktop optimized

## � **Development**

### Tech Stack
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Backend**: Flask, SQLAlchemy, SQLite
- **AI**: Gemini AI, OpenRouter, Vector Search
- **Icons**: Lucide React
- **Styling**: Tailwind CSS with custom animations

### Project Structure
```
chatbot/
├── backend/           # Flask API server
│   ├── app.py        # Main Flask application
│   ├── chatbot.py    # AI chatbot logic
│   ├── llm_service.py # LLM integration
│   └── vector_db.py  # Vector database
├── frontend/         # React application
│   ├── src/
│   │   ├── components/ # React components
│   │   ├── lib/       # API services
│   │   └── App.tsx    # Main app
│   └── package.json
└── vector_store*/    # Vector databases
```
