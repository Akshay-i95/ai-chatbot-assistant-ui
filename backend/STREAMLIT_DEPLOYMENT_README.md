# AI Chatbot - Streamlit Backend Deployment

This is the Streamlit-powered backend for the AI chatbot application, designed for easy deployment on Streamlit Cloud.

## 🚀 Quick Deployment to Streamlit Cloud

### 1. **Deploy to Streamlit Cloud**

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set the main file path: `backend/streamlit_main.py`
5. Configure your secrets (see below)

### 2. **Configure Secrets**

In your Streamlit Cloud app settings, add these secrets:

```toml
# Required - AI Service
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL = "llama-3.1-70b-versatile"

# Required - Vector Database  
PINECONE_API_KEY = "your_pinecone_api_key_here"
PINECONE_ENVIRONMENT = "us-east-1"
PINECONE_INDEX_NAME = "edify-chatbot"

# Optional - Azure Storage
AZURE_STORAGE_CONNECTION_STRING = "your_azure_connection_string"
AZURE_STORAGE_ACCOUNT_NAME = "your_storage_account"
AZURE_STORAGE_CONTAINER_NAME = "edifydocumentcontainer"
AZURE_BLOB_FOLDER_PATH = "edipedia/2025-2026/"

# Optional - Edify API
EDIFY_API_BASE_URL = "https://api.edifyschool.in/v1"
EDIFY_API_KEY = "no_auth_required"
EDIFY_API_ENDPOINT = "/edi-pedia/sop-all"

# App URL (update after deployment)
app_url = "https://your-app-name.streamlit.app"
```

### 3. **Update Frontend Configuration**

After deployment, update your Vercel frontend environment variable:

```bash
NEXT_PUBLIC_BACKEND_URL=https://your-streamlit-app-name.streamlit.app
```

## 📋 API Endpoints

### Chat API
- **URL**: `https://your-app-name.streamlit.app/?api=chat`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Your question here"}
  ]
}
```

**Response:**
```json
{
  "ai_message": {
    "content": "AI response text",
    "reasoning": "AI thought process", 
    "metadata": {
      "sources": [...],
      "confidence": 0.8,
      "context_used": 2
    }
  }
}
```

## 🧪 Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements_streamlit.txt
   ```

2. **Set up environment variables:**
   Copy `.env.example` to `.env` and fill in your API keys

3. **Run locally:**
   ```bash
   streamlit run streamlit_main.py
   ```

4. **Test the API:**
   - Visit `http://localhost:8501` for the dashboard
   - Visit `http://localhost:8501/?api=chat` for API documentation

## 🔧 Features

- **Full AI Chatbot**: Vector search with Pinecone, document processing
- **Fallback Mode**: Works with just Groq API if other services unavailable  
- **Status Dashboard**: Real-time service health monitoring
- **API Testing**: Built-in testing interface
- **Error Handling**: Graceful degradation when services are unavailable

## 📁 Files

- `streamlit_main.py` - Main Streamlit application
- `requirements_streamlit.txt` - Streamlit-specific dependencies
- `.streamlit/config.toml` - Streamlit configuration
- `.streamlit_secrets_template.toml` - Template for secrets configuration

## 🔗 Integration

This backend is designed to work with:
- **Frontend**: Next.js app deployed on Vercel
- **Database**: Pinecone vector database
- **Storage**: Azure Blob Storage (optional)
- **AI**: Groq API with Llama models

## 🐛 Troubleshooting

### Common Issues:

1. **Service initialization failed**
   - Check that GROQ_API_KEY is set in secrets
   - Verify API key is valid and has credits

2. **Vector search disabled**  
   - Check PINECONE_API_KEY is set
   - Verify Pinecone index exists and is accessible

3. **Azure storage disabled**
   - Azure services are optional
   - Chatbot will work without Azure if Pinecone is available

### Deployment Issues:

1. **Build timeout**
   - Streamlit Cloud has generous timeouts for ML packages
   - Check requirements.txt for any problematic dependencies

2. **Memory issues**
   - Remove unnecessary transformers/torch if not needed
   - Use lighter model alternatives

## 📞 Support

If you encounter issues:
1. Check the status dashboard for service health
2. Test with simple questions first
3. Verify all required environment variables are set
4. Check Streamlit Cloud logs for detailed error messages
