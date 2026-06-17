# Repair AI Assistant

A powerful, agentic AI coding assistant designed to help users with device repairs by providing step-by-step guides with integrated photos and real-time status tracking.

## 🚀 Key Features

- **Real-time Repair Guides**: Streams repair instructions directly from iFixit.
- **Integrated Visuals**: Photos are displayed inline with steps as they are retrieved.
- **"Thinking" Indicator**: Provides immediate feedback and status updates (e.g., "🔍 Searching iFixit...") during tool execution.
- **Persistent History**: Full chat history and session management powered by Neon PostgreSQL.
- **Agentic Intelligence**: Uses Google's Gemini LLM with LangGraph for advanced reasoning and tool use.

## 🛠 Tech Stack

### Frontend
- **React + TypeScript + Vite**: Fast, modern UI development.
- **Tailwind CSS**: Sleek, mobile-responsive design.
- **Lucide React**: Premium icon set.
- **SSE (Server-Sent Events)**: Fluid token-by-token streaming and status updates.

### Backend
- **FastAPI**: High-performance Python web framework.
- **LangGraph + LangChain**: Orchestration layer for the AI repair agent.
- **Gemini 1.5 Flash**: Optimized LLM for fast reasoning and helpful responses.
- **Neon PostgreSQL**: Serverless PostgreSQL for scalable data storage.

## 🏗 Architecture

The application follows a modular agentic architecture:
1. **Query Normalization**: Cleanly extracts device names and issues.
2. **iFixit Integration**: Special tools search for devices and fetch detailed guides.
3. **Context Management**: Combines structured data and photos into a unified context.
4. **Markdown Formatting**: LLM formats the response into a friendly, professional repair guide.

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- Neon PostgreSQL account (for `NEON_URL`)
- Gemini API Key

### Backend Setup
1. Navigate to the `backend` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up `.env` with your API keys.

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. Run the development server:
   ```bash
   pnpm dev
   ```

## 📜 Database Schema

The project recently migrated from MongoDB to Neon PostgreSQL. The schema includes:
- `users`: Authentication and profile data.
- `conversations`: Thread-based message history with image support.
- `refresh_tokens`: Session persistence.
- `user_usage`: Token analytics and tracking.

---
*Created with ❤️ by the Repair AI team.*
