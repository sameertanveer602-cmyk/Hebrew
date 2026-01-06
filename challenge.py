from rag_engine import HebrewRAGEngine
import os

def run_challenge():
    engine = HebrewRAGEngine()
    if os.path.exists("hebrew_rag_index.index"):
        engine.load_index("hebrew_rag_index")
    else:
        print("Index not found.")
        return

    # A simple question based on the requirements
    query =  "שם המזון"
    print(f"\n--- Challenge Query: '{query}' ---")
    
    # Use the full search (including LLM if key is there, but focusing on retrieval)
    response = engine.search(query, top_k=7)
    
    print("\n[LLM Answer]")
    print(response.answer)
    
    print("\n[Top Retrieved Sources]")
    for i, source in enumerate(response.sources):
        print(f"{i+1}. Page {source.metadata['page']} (Score: {source.score:.4f})")
        print(f"Content: {source.text[:500]}...")
        print("-" * 30)

if __name__ == "__main__":
    run_challenge()
