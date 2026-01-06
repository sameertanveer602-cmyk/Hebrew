from rag_engine import HebrewRAGEngine
import os

def initialize_system():
    engine = HebrewRAGEngine()
    
    pdfs = {
        "1169_2011_food_information_HE.pdf": "food_regulation",
        "DOC-20251225-WA0003..pdf": "guideline_tolerance"
    }
    
    for filename, doc_id in pdfs.items():
        if os.path.exists(filename):
            engine.add_document(filename, doc_id)
        else:
            print(f"File {filename} not found, skipping.")
            
    engine.save_index("hebrew_rag_index")
    print("System initialized and index saved to 'hebrew_rag_index'.")

if __name__ == "__main__":
    initialize_system()
