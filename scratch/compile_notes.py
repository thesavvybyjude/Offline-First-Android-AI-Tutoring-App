import os
from pathlib import Path
import sys

# Add project root to sys.path so we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.rag_pipeline import RAGPipeline

def main():
    print("Initializing RAG Pipeline for compilation...")
    data_dir = Path(os.environ.get("APPDATA", ".")) / "tutor" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    rag = RAGPipeline(data_dir=data_dir)
    rag.load(model_cache_dir=Path(os.environ.get("APPDATA", ".")) / "tutor" / "models" / "embeddings")

    documents = [
        # --- BIOLOGY ---
        {
            "text": "Cell Structure: A cell is the basic structural and functional unit of life. Plant cells have a rigid cell wall made of cellulose, while animal cells only have a cell membrane. Both contain a nucleus which controls cellular activities, and mitochondria which are the powerhouses of the cell where respiration occurs.",
            "source": "Biology_SS1_Cell_Structure",
            "subject": "Biology"
        },
        {
            "text": "Photosynthesis: Photosynthesis is the process by which green plants manufacture their food using sunlight, water, and carbon dioxide. The process takes place in the chloroplasts, which contain the green pigment chlorophyll. The overall equation is 6CO2 + 6H2O + light energy -> C6H12O6 + 6O2. Factors affecting photosynthesis include light intensity, carbon dioxide concentration, and temperature.",
            "source": "Biology_SS1_Photosynthesis",
            "subject": "Biology"
        },
        {
            "text": "Respiratory System: Respiration is the breakdown of glucose to release energy. In humans, the respiratory system includes the trachea, bronchi, and lungs. Gaseous exchange occurs in the alveoli of the lungs, where oxygen diffuses into the blood and carbon dioxide diffuses out. Aerobic respiration requires oxygen, while anaerobic respiration occurs without oxygen.",
            "source": "Biology_SS1_Respiration",
            "subject": "Biology"
        },
        # --- ENGLISH ---
        {
            "text": "Parts of Speech: In the English language, words are categorized into eight parts of speech. Nouns are naming words (e.g., Lagos, John, table). Verbs are action words (e.g., run, write). Adjectives describe nouns (e.g., beautiful, tall). Adverbs describe verbs, adjectives, or other adverbs (e.g., quickly, very). Pronouns replace nouns (e.g., he, she, it). Prepositions show relationships (e.g., in, on, under). Conjunctions join words or clauses (e.g., and, but, or). Interjections express strong emotion (e.g., Wow!, Oh!).",
            "source": "English_SS1_Parts_of_Speech",
            "subject": "English"
        },
        {
            "text": "Essay Writing: Essay writing involves structuring thoughts logically. An essay consists of an introduction, body paragraphs, and a conclusion. The introduction must contain a thesis statement which outlines the main point. Each body paragraph should start with a topic sentence and provide supporting details. The conclusion summarizes the main points and restates the thesis. Types of essays include narrative, descriptive, expository, and argumentative.",
            "source": "English_SS1_Essay_Writing",
            "subject": "English"
        },
        {
            "text": "Comprehension: Comprehension is the ability to read and understand a passage. To excel in comprehension, a student must skim the passage for the main idea, then scan for specific details when answering questions. Pay attention to the context of words to understand their meaning. Always read the questions carefully before returning to the text to find the exact answers.",
            "source": "English_SS1_Comprehension",
            "subject": "English"
        }
    ]

    print("Ingesting documents into FAISS index...")
    rag.ingest_documents(documents)
    print("Compilation successful! Notes are now indexed.")

if __name__ == "__main__":
    main()
