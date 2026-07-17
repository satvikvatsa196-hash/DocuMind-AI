# DocuMind AI

![DocuMind AI Banner](https://via.placeholder.com/1200x400/4161a8/ffffff?text=DocuMind+AI+-+Intelligent+Document+Assistant)

DocuMind AI is a state-of-the-art **Retrieval-Augmented Generation (RAG)** document intelligence assistant. It empowers users to securely upload documents, organize them into collections, and interact with them using natural language queries.

By orchestrating document processing, semantic search via embeddings, Vector Databases, and Large Language Models (LLMs), DocuMind AI generates highly accurate answers grounded entirely in user-provided context—complete with precise source citations.

---

## 🏗 Architecture Diagram

```mermaid
graph TD
    subgraph Frontend [React + Vite App]
        UI[User Interface]
        ReactQuery[React Query Caching]
        Axios[Axios JWT Interceptor]
        UI --> ReactQuery
        ReactQuery --> Axios
    end

    subgraph Backend [Django REST Framework]
        API[API Endpoints]
        JWT[SimpleJWT Auth]
        UploadService[Document Upload Service]
        DocProcessor[Document Extraction Service]
        Chunker[LangChain Text Splitter]
        LLM[OpenAI / Gemini LLM Service]
        Retriever[ChromaDB Retriever Service]
        
        Axios -- REST API --> API
        API --> JWT
        API --> UploadService
        UploadService --> DocProcessor
        DocProcessor --> Chunker
    end

    subgraph Data Layer
        Postgres[(PostgreSQL)]
        Chroma[(ChromaDB Vector Store)]
        
        JWT --> Postgres
        UploadService --> Postgres
        Chunker --> Chroma
        Retriever --> Chroma
    end

    API --> Retriever
    Retriever --> LLM
    LLM --> API
```

---

## ✨ Core Features

- **Multi-Format Processing**: Effortlessly ingest `.pdf`, `.docx`, and `.txt` documents.
- **Semantic Vector Search**: Automatically generates `all-MiniLM-L6-v2` embeddings for semantic similarity retrieval.
- **RAG Generation**: Asks intelligent questions and receives AI-generated answers grounded *strictly* in your documents.
- **Precise Citations**: Every AI response includes direct citations tracking the document source and page number.
- **Document Collections**: Organize your workspaces (e.g., "Machine Learning Notes").
- **Strict Tenant Isolation**: Robust Django ORM restrictions ensure users can *never* query or access documents owned by other users.
- **Conversational Memory**: Chat sessions remember the last 5 turns of history for seamless conversation flow.
- **Secure Authentication**: Protected via JWT Access/Refresh tokens.

---

## 🛠 Technology Stack

### Frontend
- **React 18** with **TypeScript** & **Vite**
- **Tailwind CSS v3** (Custom Glassmorphism & Micro-animations)
- **React Query (@tanstack/react-query)** for server state
- **React Router v6**

### Backend
- **Python 3.11** & **Django 5**
- **Django REST Framework (DRF)**
- **PyMuPDF** & **python-docx** for rapid document extraction

### Artificial Intelligence & Database
- **LangChain** (RAG Orchestration, Text Splitting)
- **Sentence Transformers** (Embeddings)
- **OpenAI API** / **Google Gemini API** (LLMs)
- **ChromaDB** (Vector Store)
- **PostgreSQL** (Relational Metadata & Auth Storage)

---

## 🚀 Setup & Installation (Docker)

The easiest way to run DocuMind AI locally is via Docker Compose.

### Prerequisites
- Docker & Docker Compose
- An OpenAI API Key

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/satvikvatsa196-hash/DocuMind-AI.git
   cd DocuMind-AI
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=sk-your-openai-key-here
   ```

3. **Spin up the stack**:
   ```bash
   docker-compose up --build -d
   ```

4. **Access the Application**:
   - **Frontend UI**: `http://localhost:5173`
   - **Backend API Docs (Swagger)**: `http://localhost:8000/api/docs/`
   - **ChromaDB**: `http://localhost:8001`

---

## 📚 API Overview (Swagger UI)

DocuMind AI ships with auto-generated OpenAPI documentation using `drf-spectacular`. 
Once running, visit `http://localhost:8000/api/docs/` to interactively test endpoints:

- `POST /api/users/login/` - Obtain JWT tokens
- `POST /api/documents/upload/` - Upload PDF/DOCX
- `POST /api/chat/query/` - Execute a RAG query

### Example RAG Request
```json
{
  "query": "What are the core concepts of Machine Learning?",
  "collection_id": 2,
  "session_id": 5
}
```

### Example RAG Response
```json
{
  "answer": "Machine Learning core concepts include Supervised Learning, Unsupervised Learning, and Reinforcement Learning.",
  "citations": [
    {
      "document_name": "ML_Notes.pdf",
      "page_number": "4"
    }
  ]
}
```

---

## 🧗 Challenges Faced & Solutions

1. **Vector Database Tenant Isolation**
   - *Challenge*: ChromaDB does not inherently understand User roles. A bad actor could potentially query another user's vector embeddings.
   - *Solution*: Built a strict security layer in Django that intercepts every RAG query, fetches a whitelist of PostgreSQL `document_id`s owned by the authenticated user, and binds the Vector Search securely within those boundaries.
2. **Context Window Limitations**
   - *Challenge*: Feeding massive PDFs directly into the LLM exceeds token limits and causes hallucinations.
   - *Solution*: Implemented LangChain's `RecursiveCharacterTextSplitter` to dynamically chunk documents into 1000-character blocks with a 200-character overlap, ensuring sentences aren't cleanly severed.

---

## 🔮 Future Improvements

- **Celery / Redis Queues**: Offload document extraction and embedding generation to asynchronous distributed task queues for massive scalability.
- **WebSockets**: Stream LLM responses token-by-token directly to the React frontend.
- **Advanced Chunking**: Implement semantic chunking instead of naive character chunking.
- **GraphRAG**: Integrate knowledge graphs to understand complex relationships across disparate documents.
