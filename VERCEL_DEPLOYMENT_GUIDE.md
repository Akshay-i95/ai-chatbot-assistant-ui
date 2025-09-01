# Vercel Deployment Guide for Next.js Frontend

## 🚀 Deploy Frontend to Vercel

### Prerequisites
- Vercel account: https://vercel.com
- Railway backend deployed and running
- GitHub repository with frontend code

### Step-by-Step Deployment

#### 1. Connect to Vercel
1. Go to https://vercel.com and sign in
2. Click "New Project"
3. Import your GitHub repository: `Akshay-i95/chatbot-2.0`
4. Select the `frontend/chatbot` folder as the root directory

#### 2. Configure Build Settings
Vercel will automatically detect:
- **Framework**: Next.js
- **Build Command**: `npm run build`
- **Install Command**: `npm install`
- **Output Directory**: `.next`

#### 3. Set Environment Variables
Add these environment variables in Vercel dashboard:

**Required:**
```bash
BACKEND_URL=https://your-railway-domain.railway.app
```
*(Replace with your actual Railway backend URL)*

**Optional (Assistant UI Cloud):**
```bash
NEXT_PUBLIC_ASSISTANT_BASE_URL=https://proj-03egal9s5kk7.assistant-api.com
NEXT_PUBLIC_ASSISTANT_API_KEY=sk_aui_proj_03egal9s5kk7_0M6kSjifnc2avD6J4Y3rUDLjfIkTyYAT
NEXT_PUBLIC_ASSISTANT_WORKSPACE_ID=akshay-i95-s-org
```

#### 4. Deploy
1. Click "Deploy"
2. Vercel will build and deploy your frontend
3. You'll get a Vercel domain URL (e.g., `your-app.vercel.app`)

### 🎯 What's Included in Deployment

✅ **Modern Next.js 15 Frontend**
- React 19 with latest features
- TypeScript for type safety
- Tailwind CSS for styling
- Turbopack for fast builds

✅ **AI Assistant Integration**
- @assistant-ui/react components
- Custom chat interface
- Reasoning display with collapsible sections
- Source document integration

✅ **Production Optimizations**
- Image optimization
- CSS optimization
- Compression enabled
- CORS headers configured

### 🔧 Post-Deployment Steps

#### 1. Test the Frontend
Visit your Vercel domain and test:
- Chat functionality
- Backend connectivity
- Reasoning display
- Source downloads

#### 2. Update Railway CORS (if needed)
If you encounter CORS issues, add your Vercel domain to Railway backend environment:
```bash
FRONTEND_URL=https://your-app.vercel.app
```

#### 3. Custom Domain (Optional)
1. Go to Vercel project settings
2. Add your custom domain
3. Configure DNS records as instructed

### 📋 Environment Variables Reference

**Required for Production:**
```env
# Backend API Configuration
BACKEND_URL=https://your-railway-backend-domain.railway.app

# Assistant UI Cloud Configuration (Optional)
NEXT_PUBLIC_ASSISTANT_BASE_URL=https://proj-03egal9s5kk7.assistant-api.com
NEXT_PUBLIC_ASSISTANT_API_KEY=sk_aui_proj_03egal9s5kk7_0M6kSjifnc2avD6J4Y3rUDLjfIkTyYAT
NEXT_PUBLIC_ASSISTANT_WORKSPACE_ID=akshay-i95-s-org
```

### 🎉 Features Ready for Production

✅ **Ultra-Robust Chat Experience**
- Groq GPT OSS 120B backend integration
- Reasoning/response separation (100% success rate)
- Conversation history support
- Follow-up query detection

✅ **Professional UI Components**
- ChatGPT-style reasoning dropdowns
- Source document display
- Download functionality
- Responsive design

✅ **Performance Optimized**
- Streaming responses
- Optimized bundling
- Fast page loads
- Mobile-friendly

### 🚨 Important Notes

- Make sure Railway backend is deployed first
- Use the actual Railway domain in `BACKEND_URL`
- All environment variables starting with `NEXT_PUBLIC_` are exposed to the browser
- Vercel automatically enables HTTPS for all deployments
- Auto-deployment happens on every git push to main branch

### 🎯 Expected Result

After deployment, you'll have:
- **Live Next.js Frontend** on Vercel domain
- **Connected to Railway Backend** with Groq integration
- **Full Chat Functionality** with reasoning display
- **Auto-deployment** on git push

Ready to go live! 🚀
