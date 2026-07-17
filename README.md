# DocuMind AI

DocuMind AI is a Retrieval-Augmented Generation (RAG) based document intelligence assistant that allows users to upload documents and interact with them using natural language queries.

The system combines document processing, semantic search, embeddings, vector databases, and Large Language Models (LLMs) to generate accurate answers grounded in user-provided documents with relevant source citations.

## Key Features

- Upload and process PDF, DOCX, and TXT documents
- Generate embeddings for semantic document search
- Retrieve relevant document context using vector similarity search
- Ask questions and receive AI-generated answers
- Provide source citations for generated responses
- Manage multiple document collections
- Maintain chat history
- Secure authentication using JWT.

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
