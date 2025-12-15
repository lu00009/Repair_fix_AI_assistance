# Repair Assistant Frontend

A modern, ChatGPT-like UI for the Repair Assistant application built with React, TypeScript, Vite, and Tailwind CSS.

## ✨ Features

- **ChatGPT-like UI**: Dark theme with silver, black, and white color scheme
- **Real-time Streaming**: Messages stream token-by-token for a responsive feel
- **Markdown Rendering**: Beautiful rendering of repair steps, code blocks, lists, and more
- **Session Management**: Persistent chat history across sessions
- **Authentication**: Secure login/signup system
- **Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

### Install Dependencies

```bash
cd frontend
npm install
```

### Configure Environment

Create a `.env` file (or use the existing one):

```bash
VITE_API_URL=http://localhost:8000
```

### Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:5173

## 📦 Dependencies

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Utility-first CSS
- **react-markdown** - Markdown rendering
- **remark-gfm** - GitHub Flavored Markdown support
- **lucide-react** - Icon library

## 🎨 UI Components

### Message Component
Renders chat messages with:
- User/Assistant avatars
- Markdown formatting (headings, lists, code blocks, links)
- Syntax highlighting for code
- Images and blockquotes
- Streaming cursor animation

### Chat Input
- Auto-resizing textarea
- Send on Enter (Shift+Enter for new line)
- Character limit UI feedback
- Disabled state during processing

### Login/Signup
- Email/password authentication
- Toggle between login and signup
- Error handling
- Loading states

## 🔌 API Integration

The frontend communicates with the backend API:

### Authentication
- `POST /login` - User login
- `POST /signup` - User registration

### Chat
- `POST /chat` - Send message (standard)
- `POST /chat/stream` - Send message (streaming)
- `GET /chat/history` - Get conversation history
- `DELETE /chat/history` - Clear conversation history

## 🎯 Usage

### Login

1. Open http://localhost:5173
2. Enter your credentials or create an account
3. Click "Log in" or "Sign up"

### Chat

1. Type your repair question in the input box
2. Press Enter or click Send
3. Watch the response stream in real-time
4. Click suggestions to quick-start conversations

### Markdown Examples

The assistant can respond with:

**Bold text**: `**Step 1: Remove the battery**`  
*Italic text*: `_Be careful with the connector_`  
`Code`: `` `sudo apt install tool` ``  
Links: `[iFixit Guide](https://ifixit.com)`  
Lists: `- Item 1\n- Item 2`  
Images: `![Alt text](image-url.jpg)`

## 🛠️ Build for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat.tsx           # Main chat interface
│   │   ├── Message.tsx        # Message bubble with markdown
│   │   ├── ChatInput.tsx      # Message input component
│   │   └── Login.tsx          # Authentication screen
│   ├── services/
│   │   └── api.ts             # API service layer
│   ├── lib/
│   │   └── utils.ts           # Utility functions
│   ├── App.tsx                # Main app component
│   ├── main.tsx               # Entry point
│   └── index.css              # Global styles
├── tailwind.config.js         # Tailwind configuration
├── postcss.config.js          # PostCSS configuration
├── vite.config.ts             # Vite configuration
└── package.json               # Dependencies
```

## 🎨 Color Scheme (ChatGPT-like)

```css
Background: #212121 (dark gray)
Sidebar: #171717 (darker gray)
Input: #2f2f2f (medium gray)
User Message: #2f2f2f
Assistant Message: #212121
Text: #ececf1 (light gray)
Text Secondary: #c5c5d2 (muted gray)
Accent: #10a37f (green - for buttons/icons)
```

## 🔧 Development Tips

### Hot Reload
Vite provides instant hot module replacement (HMR) - save any file and see changes immediately.

### TypeScript
The project uses strict TypeScript. Run type checking:

```bash
npm run build
```

### Linting
```bash
npm run lint
```

## 🌐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

## 📝 API Response Format

### Chat Response (Non-streaming)
```json
{
  "response": "To fix your iPhone screen...",
  "thread_id": "user-123"
}
```

### Stream Events (SSE)
```
data: {"type": "status", "content": "🔍 Searching iFixit..."}
data: {"type": "token", "content": "To"}
data: {"type": "token", "content": " fix"}
data: {"type": "done", "thread_id": "user-123"}
```

## 🐛 Troubleshooting

### CORS Errors
Make sure the backend has CORS enabled for your frontend URL.

### Authentication Fails
- Check that the backend is running on the correct port
- Verify the API_URL in `.env`
- Check browser console for error details

### Streaming Doesn't Work
- Ensure your browser supports Server-Sent Events (SSE)
- Check network tab for connection issues
- Verify the backend `/chat/stream` endpoint is working

## 📄 License

Part of the Repair Assistant project.
