# Jarvis AI Assistant - Render Deployment Guide

## 🚀 Deploy to Render

This guide will help you deploy Jarvis to Render.com for production use.

### Prerequisites

1. **GitHub Repository**: Ensure your Jarvis code is in a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **Google OAuth Credentials**: Already configured in this project

### Step 1: Prepare Repository

1. Push this entire `jarvis-chatbot` directory to your GitHub repository
2. Ensure all files are committed, especially:
   - `requirements_render.txt`
   - `Procfile`
   - `runtime.txt`
   - `render.yaml`

### Step 2: Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository containing Jarvis

### Step 3: Configure Deployment Settings

**Basic Settings:**
- **Name**: `jarvis-backend` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: `Oregon` (or closest to your location)
- **Branch**: `main` (or your default branch)

**Build & Deploy:**
- **Build Command**: `pip install -r requirements_render.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT src.main:app --timeout 120 --workers 2`

### Step 4: Environment Variables

Add these environment variables in Render Dashboard:

```
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_CLIENT_ID=786875816540-rgbl1fmkpnjcvqik9ato443vrbvyj29.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
SESSION_SECRET=jarvis-secure-session-key-2024-render
ENABLED_TOOLS=run_code,weather,scrape,file_analysis,web_search
AUTH_MODE=google
MEMORY_PROVIDER=local
ENABLE_LOGS=true
FLASK_ENV=production
CORS_ORIGINS=*
```

### Step 5: Update Google OAuth Settings

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Edit your "Jarvis AI Assistant" OAuth client
3. Add your Render URL to **Authorized redirect URIs**:
   - `https://your-app-name.onrender.com/auth/callback`
4. Add your Render domain to **Authorized JavaScript origins**:
   - `https://your-app-name.onrender.com`

### Step 6: Deploy

1. Click "Create Web Service" in Render
2. Wait for the build and deployment to complete
3. Your Jarvis backend will be available at: `https://your-app-name.onrender.com`

### Step 7: Test Deployment

1. Visit `https://your-app-name.onrender.com/health`
2. You should see a JSON response with system status
3. Test Google OAuth by visiting `https://your-app-name.onrender.com/auth/login`

## 🔧 Configuration Details

### Files Included for Render:

- **`requirements_render.txt`**: Optimized dependencies for Render
- **`Procfile`**: Gunicorn startup command
- **`runtime.txt`**: Python version specification
- **`render.yaml`**: Render service configuration
- **`.env.render`**: Environment variables template

### Features Enabled:

✅ **Google OAuth Authentication**
✅ **Command Execution Logging**
✅ **File Upload & Processing**
✅ **Mode Switching System**
✅ **Plugin Management**
✅ **System Diagnostics**
✅ **Workflow Automation**
✅ **ChatRelay Webhooks**

### Database & Storage:

- **Database**: SQLite (stored in `/tmp/jarvis.db`)
- **File Storage**: Ephemeral storage in `/tmp/jarvis/`
- **Logs**: Persistent logging to database and files

### Security:

- **Authentication**: Google OAuth required
- **CORS**: Configured for cross-origin requests
- **Session Management**: Secure session handling
- **Input Validation**: Comprehensive input sanitization

## 🎯 Post-Deployment

After successful deployment:

1. **Test all features** through the web interface
2. **Verify Google OAuth** login works correctly
3. **Check system diagnostics** via `/diagnose` endpoint
4. **Monitor logs** for any issues

Your Jarvis AI Assistant is now live and ready for production use! 🎉

## 📞 Support

If you encounter issues:
1. Check Render deployment logs
2. Verify environment variables are set correctly
3. Ensure Google OAuth redirect URIs are updated
4. Test the `/health` endpoint for system status

