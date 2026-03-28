"""
Loads all ML models once at startup and keeps them in memory.
All endpoints share the same model instances — no repeated loading.
"""
from sentence_transformers import SentenceTransformer
from transformers import pipeline as hf_pipeline
import spacy
from loguru import logger


class ModelRegistry:
    _instance = None

    def __init__(self):
        logger.info("Loading ML models — this may take a minute on first run...")

        # Model 1: Sentence similarity — job ↔ resume matching
        logger.info("Loading sentence-transformers (all-MiniLM-L6-v2)...")
        self.similarity_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Model 2: spaCy — resume NLP (skill/title/education extraction)
        logger.info("Loading spaCy (en_core_web_sm)...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
            self.nlp = spacy.load("en_core_web_sm")

        # Model 3: JobBERT — JD skill extraction (NER)
        logger.info("Loading JobBERT (jjzha/jobbert-base-cased)...")
        self.jobbert = hf_pipeline(
            "token-classification",
            model="jjzha/jobbert-base-cased",
            aggregation_strategy="simple",
            device=-1,   # CPU; change to 0 for GPU
        )

        logger.info("All ML models loaded successfully")

    @classmethod
    def get(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = ModelRegistry()
        return cls._instance
