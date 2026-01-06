import os
import faiss
import numpy as np
import pickle
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from parser import HebrewPDFParser
from dotenv import load_dotenv

load_dotenv()

# --- Pydantic Models from Spec ---

class DocumentMetadata(BaseModel):
    doc_id: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    type: str = "text"

class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    metadata: Optional[dict] = None

class RAGSearchResponse(BaseModel):
    answer: str
    sources: List[RetrievedChunk]

# --- RAG Engine Class ---

class HebrewRAGEngine:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        print(f"Loading embedding model: {model_name}...")
        self.embedding_model = SentenceTransformer(model_name)
        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata_store = []
        self.parser = HebrewPDFParser()
        
        # Configure LLM (Gemini with Groq fallback)
        self.llm_provider = None
        self.llm_client = None
        
        google_key = os.getenv("GOOGLE_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        
        if google_key:
            genai.configure(api_key=google_key)
            self.llm_client = genai.GenerativeModel('gemini-1.5-flash')
            self.llm_provider = "google"
            self.groq_fallback_client = None
            if groq_key:
                try:
                    from groq import Groq
                    self.groq_fallback_client = Groq(api_key=groq_key)
                except ImportError:
                    pass
            print("Using Google Gemini Flash.")
        elif groq_key:
            try:
                from groq import Groq
                self.llm_client = Groq(api_key=groq_key)
                self.llm_provider = "groq"
                print("Using Groq (Llama-3).")
            except ImportError:
                print("Warning: Groq library not installed. Falling back to retrieval only.")
        else:
            print("Warning: No LLM API keys found (GOOGLE_API_KEY or GROQ_API_KEY).")

    def chunk_content(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def _add_chunks_to_index(self, chunks: List[str], metas: List[dict]):
        if chunks:
            embeddings = self.embedding_model.encode(chunks)
            self.index.add(np.array(embeddings).astype('float32'))
            self.metadata_store.extend(metas)
            print(f"Added {len(chunks)} chunks to index.")

    def add_document(self, pdf_path: str, doc_id: str):
        print(f"Processing document: {pdf_path}")
        content_items = self.parser.extract_content(pdf_path)
        
        all_chunks = []
        all_metas = []
        
        for item in content_items:
            content = item['content']
            page_num = item['page']
            content_type = item['type']
            
            if content_type == "table":
                chunks = [content]
            else:
                chunks = self.chunk_content(content)
            
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metas.append({
                    "doc_id": doc_id,
                    "page": page_num,
                    "type": content_type,
                    "text": chunk
                })
        
        self._add_chunks_to_index(all_chunks, all_metas)

    def add_text(self, text: str, doc_id: str, metadata: dict = None, chunk_size=800, overlap=100):
        # Even if it's text, we run it through the Hebrew fixer to be safe
        # (Though usually text from API is already logical)
        fixed_text = self.parser.fix_hebrew_text(text)
        chunks = self.chunk_content(fixed_text, chunk_size, overlap)
        
        all_metas = []
        for chunk in chunks:
            all_metas.append({
                "doc_id": doc_id,
                "page": 1,
                "type": "text",
                "text": chunk,
                "metadata": metadata or {}
            })
            
        self._add_chunks_to_index(chunks, all_metas)

    def search(self, query: str, top_k: int = 5) -> RAGSearchResponse:
        # 1. Embed Query
        query_vec = self.embedding_model.encode([query]).astype('float32')
        
        # 2. Vector Search
        distances, indices = self.index.search(query_vec, top_k)
        
        sources = []
        context_parts = []
        
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata_store):
                meta = self.metadata_store[idx]
                chunk = RetrievedChunk(
                    chunk_id=str(idx),
                    doc_id=meta['doc_id'],
                    text=meta['text'],
                    score=float(dist),
                    metadata=meta
                )
                sources.append(chunk)
                context_parts.append(f"[מקור: {meta['doc_id']}, עמוד: {meta['page']}]\n{meta['text']}")
        
        # 3. Generate Answer
        context_text = "\n\n".join(context_parts)
        prompt = f"""
### 🧠 הוראות למערכת ה-RAG
אתה מומחה לניתוח מסמכים רגולטוריים ומשפטיים. תפקידך לספק תשובה **מקיפה, מדויקת ומובנית** בעברית, המבוססת אך ורק על הקונטקסט המצורף למטה.

### � כללי עבודה מחייבים:
1.  **היצמדות לקונטקסט**: ענה אך ורק על סמך המידע הניתון. אל תשתמש בידע קודם.
2.  **מקיפות**: אם המידע מופיע במספר מקומות בקונטקסט, שלב את כולם לתשובה אחת שלמה.
3.  **מבנה**: השתמש בנקודות (bullet points) או במספור במידה ויש רשימת תנאים או דרישות.
4.  **חוסר מידע**: אם הקונטקסט אינו מכיל מספיק מידע כדי לענות על השאלה במלואה, ציין זאת במפורש. השב: "המידע אינו מופיע במסמכים שנסרקו".
5.  **דיוק לשוני**: השתמש בשפה מקצועית ועניינית התואמת את אופי המסמכים (חקיקה, רגולציה).

### 📄 ציון מקורות (חובה):
בסוף התשובה, הוסף פסקה בשם "מקורות:" ופרט את מספרי העמודים והמסמכים עליהם התבססת.
דוגמה: *מקורות: עמודים 14, 15 (מתוך food_regulation).*

---
### 🔎 CONTEXT (מידע מהמסמכים):
{context_text}

---
### ❓ QUESTION (השאלה):
{query}

### ✅ ANSWER (התשובה המקיפה):
"""
        answer = "LLM not configured."
        if self.llm_provider == "google":
            try:
                response = self.llm_client.generate_content(prompt)
                answer = response.text
            except Exception as e:
                print(f"Gemini error: {e}")
                if self.groq_fallback_client:
                    print("Falling back to Groq...")
                    chat_completion = self.groq_fallback_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.3-70b-versatile",
                    )
                    answer = chat_completion.choices[0].message.content
                else:
                    answer = f"Gemini error and no fallback: {e}"
        elif self.llm_provider == "groq":
            chat_completion = self.llm_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            answer = chat_completion.choices[0].message.content
            
        return RAGSearchResponse(answer=answer, sources=sources)

    def save_index(self, path="faiss_index"):
        faiss.write_index(self.index, f"{path}.index")
        with open(f"{path}_meta.pkl", "wb") as f:
            pickle.dump(self.metadata_store, f)

    def load_index(self, path="faiss_index"):
        if os.path.exists(f"{path}.index"):
            self.index = faiss.read_index(f"{path}.index")
            with open(f"{path}_meta.pkl", "rb") as f:
                self.metadata_store = pickle.load(f)
            print("Index loaded.")

if __name__ == "__main__":
    # Quick functional test
    engine = HebrewRAGEngine()
    # engine.add_document("1169_2011_food_information_HE.pdf", "food_reg")
    # res = engine.search("מהן הדרישות לסימון אלרגנים?")
    # print(res.answer)
