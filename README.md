# Hebrew RAG API & UI

A Retrieval-Augmented Generation (RAG) system specialized for Hebrew documents. This project consists of a FastAPI backend using `sentence-transformers` and `faiss` for semantic search, and a modern, responsive frontend built with vanilla HTML, CSS, and JavaScript.

## Features

- **Document Ingestion**: Upload PDF files with automatic Hebrew text extraction and correction.
- **Semantic Search**: Find relevant information within uploaded documents using vector similarity.
- **Chat Interface**: Ask questions in natural Hebrew and get answers based on the document context (RAG).
- **Source Attribution**: Answers include citations to the specific document and page number.
- **Model Support**: Supports Google Gemini and Groq (Llama-3) as LLM backends.

## Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- An API key for Google Gemini (`GOOGLE_API_KEY`) or Groq (`GROQ_API_KEY`).

## Installation

1.  **Clone the repository** (if applicable) or navigate to the project directory:
    ```bash
    cd HEBREW
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Create a `.env` file in the root directory if it doesn't exist.
2.  Add your API keys to the `.env` file:
    ```env
    GOOGLE_API_KEY=your_google_api_key_here
    GROQ_API_KEY=your_groq_api_key_here
    ```
    *Note: You only need one of the above keys, but providing both enables fallback.*

## Running the Application

1.  **Start the server**:
    You can run the application using `uvicorn` (recommended for development) or directly via Python.

    **Using Uvicorn:**
    ```bash
    uvicorn main:app --reload
    ```

    **Using Python:**
    ```bash
    python main.py
    ```

2.  **Access the Application**:
    Open your web browser and navigate to:
    [http://localhost:8000](http://localhost:8000)

## Usage

1.  **Upload**: Go to the "Upload" tab to upload Hebrew PDF documents.
2.  **Chat**: Switch to the "Chat" tab to ask questions about the uploaded content.
3.  **Search**: Use the "Search" tab for direct query-based retrieval.
