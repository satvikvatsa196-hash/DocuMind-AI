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

## Docker Deployment (Local / AWS EC2)

The easiest way to run DocuMind AI is using Docker Compose. It automatically spins up the React Frontend, Django Backend, PostgreSQL DB, and ChromaDB Vector Store.

### Prerequisites
- Docker and Docker Compose installed.
- An OpenAI API Key (`OPENAI_API_KEY`).

### Startup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/satvikvatsa196-hash/DocuMind-AI.git
   cd DocuMind-AI
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory and add your keys:
   ```env
   OPENAI_API_KEY=sk-your-openai-key-here
   ```

3. **Start the containers**:
   ```bash
   docker-compose up --build -d
   ```

4. **Run Database Migrations** (The backend container does this automatically, but you can trigger it manually if needed):
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create a Superuser** (Optional, to access Django Admin):
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access the Application**:
   - Frontend: `http://localhost:5173`
   - Backend API: `http://localhost:8000`
   - ChromaDB: `http://localhost:8001`

---

## Deploying to Render (PaaS)

If you prefer a managed PaaS instead of a raw EC2 instance, you can easily deploy to Render.

### 1. PostgreSQL Database
- In the Render Dashboard, create a new **PostgreSQL** instance.
- Copy the internal database URL.

### 2. Backend (Django)
- Create a new **Web Service** hooked to this GitHub repository.
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- **Environment Variables**:
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (From your Render Postgres)
  - `OPENAI_API_KEY`
  - `CHROMA_DB_URL` (URL of your deployed ChromaDB instance)

### 3. Frontend (React)
- Create a new **Static Site** on Render.
- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `frontend/dist`
- **Environment Variables**:
  - `VITE_API_URL` (URL of your Render Django Backend API)

### 4. ChromaDB
- Deploy the `chromadb/chroma` Docker image using Render's **Web Service** (Docker environment).
- Link the internal URL to your Django Backend environment variables.
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
