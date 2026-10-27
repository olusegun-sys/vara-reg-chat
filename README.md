# Regulatory Knowledge Base Chat (POC)

A retrieval-augmented generation (RAG) chat interface for querying regulatory rulebooks.
Designed for multi-jurisdiction expansion. VARA (Dubai) is the first case study.

## Architecture

- **Backend:** FastAPI (Python) — async API, provider-agnostic LLM calls
- **Vector Store:** ChromaDB (POC) — swappable to Qdrant for production without changing the retrieval interface
- **Embeddings:** sentence-transformers (local, free, no API cost)
- **LLM:** Groq (POC, free tier) — OpenAI-compatible, swap to DeepSeek/OpenAI via `.env`
- **Frontend:** React + Vite + Tailwind — responsive across devices

## Project Structure
