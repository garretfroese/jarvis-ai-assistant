# Jarvis - Custom ChatGPT-Style AI Assistant

A standalone, browser-based chatbot interface that uses OpenAI's API to provide a ChatGPT-like experience with custom system prompts and conversation management.

## Overview

Jarvis is a full-stack web application that replicates the ChatGPT interface while giving you complete control over the AI's behavior through custom system prompts. Built with React and Flask, it provides a seamless chat experience with features like conversation memory, streaming responses, and a modern dark/light theme interface.

## Features

### Core Functionality
- **ChatGPT-Style Interface**: Clean, responsive design that mirrors the ChatGPT experience
- **Custom System Prompts**: Configure the AI's personality and behavior through the settings panel
- **Conversation Memory**: Maintains context across messages within a conversation
- **Multiple Conversations**: Create and manage multiple chat sessions
- **Streaming Responses**: Real-time message streaming with typing indicators
- **Dark/Light Theme**: Toggle between themes for comfortable viewing

### Technical Features
- **OpenAI API Integration**: Supports multiple models (GPT-4.1 Mini, GPT-4.1 Nano, Gemini 2.5 Flash)
- **Secure API Key Storage**: API keys are stored locally in the browser
- **CORS Enabled**: Full cross-origin support for frontend-backend communication
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Modern UI Components**: Built with Tailwind CSS and shadcn/ui components

## Architecture

### Frontend (React)
- **Framework**: React with Vite build system
- **Styling**: Tailwind CSS with shadcn/ui components
- **Icons**: Lucide React icons
- **State Management**: React hooks for local state management
- **API Communication**: Fetch API with streaming support

### Backend (Flask)
- **Framework**: Flask with CORS support
- **API Endpoints**: RESTful API for chat, conversations, and settings
- **Database**: SQLite for conversation storage (optional)
- **Environment**: Python-dotenv for configuration management

## Installation and Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- OpenAI API key

### Local Development Setup

1. **Clone or extract the project**:
   ```bash
   cd jarvis-chatbot
   ```

2. **Backend Setup**:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Environment Configuration**:
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   DEFAULT_SYSTEM_PROMPT=You are Jarvis, Garret's AI assistant. You are helpful, knowledgeable, and ready to assist with any questions or tasks.
   MODEL=gpt-4.1-mini
   SESSION_MEMORY_ENABLED=true
   PORT=5000
   FLASK_ENV=development
   ```

4. **Frontend Setup** (if modifying):
   ```bash
   cd ../jarvis-frontend
   npm install
   npm run build
   cp -r dist/* ../jarvis-chatbot/src/static/
   ```

5. **Run the Application**:
   ```bash
   cd jarvis-chatbot
   source venv/bin/activate
   python src/main.py
   ```

6. **Access the Application**:
   Open your browser and navigate to `http://localhost:5000`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `DEFAULT_SYSTEM_PROMPT` | Default system prompt for the AI | "You are Jarvis..." |
| `MODEL` | OpenAI model to use | gpt-4.1-mini |
| `SESSION_MEMORY_ENABLED` | Enable conversation memory | true |
| `PORT` | Server port | 5000 |
| `FLASK_ENV` | Flask environment | development |

### Supported Models

The application supports the following OpenAI models:
- **gpt-4.1-mini**: Fast and cost-effective
- **gpt-4.1-nano**: Ultra-fast responses
- **gemini-2.5-flash**: Google's Gemini model

### System Prompt Customization

You can customize the AI's behavior by modifying the system prompt through:
1. **Settings Panel**: Click the Settings button in the sidebar
2. **Environment Variable**: Set `DEFAULT_SYSTEM_PROMPT` in your `.env` file
3. **API Endpoint**: POST to `/api/system-prompt` with a JSON payload

## Usage

### Getting Started

1. **Configure API Key**: Click the Settings button and enter your OpenAI API key
2. **Select Model**: Choose your preferred model from the dropdown
3. **Customize System Prompt**: Modify the system prompt to define the AI's behavior
4. **Start Chatting**: Type your message in the input field and press Enter

### Managing Conversations

- **New Chat**: Click the "New Chat" button to start a fresh conversation
- **Switch Conversations**: Click on any conversation in the sidebar to switch to it
- **Delete Conversations**: Hover over a conversation and click the delete button

### Settings Panel

The settings panel allows you to configure:
- **OpenAI API Key**: Your personal API key (stored locally)
- **Model Selection**: Choose between available models
- **System Prompt**: Define the AI's personality and behavior
- **Memory Settings**: Enable/disable conversation memory

## API Documentation

### Chat Endpoint

**POST** `/api/chat`

Send a message to the AI and receive a response.

**Request Body**:
```json
{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "conversation_id": "default",
  "apiKey": "your-api-key",
  "systemPrompt": "You are a helpful assistant",
  "model": "gpt-4.1-mini"
}
```

**Response**:
```json
{
  "message": "Hello! How can I help you today?",
  "conversation_id": "default"
}
```

### Conversation Management

**GET** `/api/conversations/<conversation_id>`
- Retrieve conversation history

**DELETE** `/api/conversations/<conversation_id>`
- Clear conversation history

**GET** `/api/conversations`
- List all conversation IDs

### System Prompt Management

**GET** `/api/system-prompt`
- Get current system prompt

**POST** `/api/system-prompt`
- Update system prompt

## Deployment

### Manual Deployment Options

#### Option 1: Traditional Web Hosting
1. Build the React frontend: `npm run build`
2. Copy built files to Flask static directory
3. Deploy Flask application to your hosting provider
4. Configure environment variables on the server

#### Option 2: Docker Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "src/main.py"]
```

#### Option 3: Platform-as-a-Service
Deploy to platforms like:
- **Heroku**: Use the included `requirements.txt`
- **Railway**: Connect your GitHub repository
- **Render**: Deploy directly from the project folder

### Environment Variables for Production

Ensure these environment variables are set in your production environment:
```env
OPENAI_API_KEY=your_production_api_key
DEFAULT_SYSTEM_PROMPT=Your production system prompt
MODEL=gpt-4.1-mini
SESSION_MEMORY_ENABLED=true
PORT=5000
FLASK_ENV=production
```

## Development

### Project Structure

```
jarvis-chatbot/
├── src/
│   ├── models/          # Database models
│   ├── routes/          # API routes
│   │   ├── chat.py      # Original chat route with streaming
│   │   ├── chat_simple.py # Simplified chat route for deployment
│   │   └── user.py      # User management routes
│   ├── static/          # Frontend build files
│   ├── database/        # SQLite database
│   └── main.py          # Flask application entry point
├── venv/                # Python virtual environment
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
└── README.md           # This file

jarvis-frontend/
├── src/
│   ├── components/      # React components
│   │   ├── ChatMessage.jsx
│   │   ├── ChatInput.jsx
│   │   ├── Sidebar.jsx
│   │   └── SettingsModal.jsx
│   ├── hooks/           # Custom React hooks
│   │   └── useChat.js
│   ├── App.jsx          # Main React component
│   └── main.jsx         # React entry point
├── dist/                # Built frontend files
└── package.json         # Node.js dependencies
```

### Adding New Features

#### Adding a New API Endpoint
1. Create a new route in `src/routes/`
2. Import and register the blueprint in `src/main.py`
3. Update the frontend to call the new endpoint

#### Modifying the UI
1. Edit React components in `jarvis-frontend/src/components/`
2. Rebuild the frontend: `npm run build`
3. Copy built files to Flask static directory

#### Adding New Models
1. Update the model options in `SettingsModal.jsx`
2. Ensure the model is supported by your OpenAI API key
3. Test the integration

### Testing

#### Backend Testing
```bash
# Test API endpoints
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"apiKey":"your-key"}'
```

#### Frontend Testing
1. Start the development server: `python src/main.py`
2. Open browser to `http://localhost:5000`
3. Test all features through the UI

## Troubleshooting

### Common Issues

#### API Key Not Working
- Ensure your OpenAI API key is valid and has sufficient credits
- Check that the key is properly entered in the settings panel
- Verify the model you're using is available with your API key

#### Deployment Issues
- Check that all environment variables are set correctly
- Ensure the production server has internet access to reach OpenAI's API
- Verify that the Flask application is listening on `0.0.0.0` not `localhost`

#### Frontend Not Loading
- Ensure the React build files are in the `src/static/` directory
- Check that Flask is serving static files correctly
- Verify there are no JavaScript errors in the browser console

#### Model Not Supported
- Update the model options in the frontend to match available models
- Check OpenAI's documentation for the latest supported models
- Ensure your API key has access to the selected model

### Debug Mode

To enable debug mode for development:
1. Set `FLASK_ENV=development` in your `.env` file
2. The application will restart automatically on code changes
3. Detailed error messages will be displayed

## Security Considerations

### API Key Security
- API keys are stored locally in the browser's localStorage
- Keys are never sent to the backend server logs
- Consider implementing server-side key management for production use

### CORS Configuration
- The application allows all origins by default for development
- Restrict CORS origins in production: `CORS(app, origins=["https://yourdomain.com"])`

### Environment Variables
- Never commit `.env` files to version control
- Use secure environment variable management in production
- Rotate API keys regularly

## Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Follow PEP 8 for Python code
- Use ESLint and Prettier for JavaScript/React code
- Write descriptive commit messages
- Include tests for new features

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the API documentation
3. Create an issue in the project repository

## Acknowledgments

- Built with React, Flask, and OpenAI's API
- UI components from shadcn/ui
- Icons from Lucide React
- Styling with Tailwind CSS

---

**Created by Manus AI** - A powerful, customizable ChatGPT alternative that puts you in control.

