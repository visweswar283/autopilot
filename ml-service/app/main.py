from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import fitz  # PyMuPDF
from loguru import logger

from app.models.loader import ModelRegistry
from app.routers import score, skills


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load all ML models once at startup
    logger.info("ApplyPilot ML Service starting...")
    ModelRegistry.get()
    yield
    logger.info("ML Service shutting down")


app = FastAPI(
    title="ApplyPilot ML Service",
    description="Job scoring, skill extraction, and resume parsing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(score.router,  tags=["Scoring"])
app.include_router(skills.router, tags=["Skills"])


@app.get("/health")
async def health():
    return {"status": "ok", "models_loaded": ModelRegistry._instance is not None}


@app.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    """
    Extract text from an uploaded PDF resume.
    Call this first, then pass the text to /score or /parse-resume.
    """
    contents = await file.read()
    doc = fitz.open(stream=contents, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()

    if not text.strip():
        return {"error": "Could not extract text from PDF"}

    return {"text": text, "pages": len(doc)}
