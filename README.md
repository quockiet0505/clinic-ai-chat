# 🤖 Clinic Management System - AI & Chatbot Services

This repository contains the Artificial Intelligence (AI) and Natural Language Processing (NLP) services for the Clinic Management System. It powers the smart chatbot, handles Retrieval-Augmented Generation (RAG) for clinic inquiries, and performs AI-based review moderation.

## 🚀 Tech Stack
- **Framework:** Python, FastAPI
- **LLM Engine:** Qwen 
- **Vector Database:** ChromaDB
- **Techniques:** Retrieval-Augmented Generation (RAG), Prompt Engineering, Text Embedding

## 📂 Project Structure
- `/app`: Main FastAPI application, routing, and controller logic.
- `/vector_db`: ChromaDB persistent storage for embedded clinic knowledge (specialties, doctor info, FAQs).
- `/prompts`: System prompts and templates guiding the AI's behavior.
- `/data` & `/knowledge`: Raw knowledge files used for data ingestion and chunking.
- `/scripts`: Utility scripts for data ingestion, log analysis (`analyze_logs.py`), and testing.
- `/llama-bin` & `/llama.cpp`: Binaries and dependencies for running local models.

## 🛠️ Getting Started

### Prerequisites
- Python 3.9+
- pip (Python Package Installer)

### 1. Installation

```bash
# Navigate to the ai-chat directory
cd clinic-ai-chat

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file (you can copy from `.env.example`):
```env
# Example .env configuration
HOST=0.0.0.0
PORT=8000
# Add your specific model paths, API keys, or DB configs here
```

### 3. Running the Service
You can run the FastAPI server using the provided batch script or manually:

**Option A (Using the provided script for Windows):**
```bash
run_local.bat
```

**Option B (Manual execution):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at `http://localhost:8000`. You can view the interactive Swagger UI documentation at `http://localhost:8000/docs`.

### 4. Public Access (Ngrok)
If you need to expose this local API to a public URL (e.g., for Webhook integration or external testing), use the provided script:
```bash
run_ngrok.bat
```

## 🧠 Core Features
1. **RAG-based Chatbot:** Accurately answers patient questions based on real clinic data stored in ChromaDB, minimizing hallucinations.
2. **Context-Aware Assistance:** Extracts intent from messages to recommend specialties, fetch doctor schedules, and assist in appointment booking.
3. **AI Review Moderation:** Automatically analyzes patient feedback to filter inappropriate content and categorize sentiments.
