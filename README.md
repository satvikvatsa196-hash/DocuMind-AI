# DocuMind AI Knowledge Assistant

An AI Knowledge Assistant built with RAG (Retrieval-Augmented Generation). Users can upload documents, and the system retrieves relevant information to answer questions using an LLM.

## Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: Django + Django REST Framework
- **Database**: PostgreSQL
- **Vector Database**: ChromaDB
- **AI**: LangChain, Sentence Transformers, OpenAI/Gemini API

## Project Structure

- `frontend/`: React application containing components for authentication, dashboard, documents management, and chat interface.
- `backend/`: Django backend with apps for users, documents, chat, and the core AI engine.

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Setup

1. Clone the repository.
2. Ensure Docker daemon is running.
3. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

### Accessing the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Database**: Port 5432
- **Vector DB (ChromaDB)**: Port 8001
