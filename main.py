"""
Main FastAPI app for Speech-to-Text Proxy (modular).
- Imports providers, db, llm, webhook from separate modules.
- Handles API, WebSocket, analytics, validation, Celery integration.
- Clean, production-ready, with English docstrings.
"""
import os
import io
import uuid
import wave
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from celery import Celery
from sqlalchemy import func
from providers import PROVIDERS, PROVIDER_MAP
from db import SessionLocal, TranscriptionHistory
from llm import llm_summary
from webhook import send_webhook
from typing import Optional, List

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
logger = logging.getLogger("speech-proxy.main")

app = FastAPI(title="Speech-to-Text Proxy API", version="5.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator().instrument(app).expose(app)
celery_app = Celery('main', broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'))

# --- Validation ---
MIN_FILE_SIZE = 100
MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".m4a", ".ogg")
def validate_audio_file(file: UploadFile) -> bytes:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    audio_bytes = file.file.read()
    if not audio_bytes or len(audio_bytes) < MIN_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File is empty or too small.")
    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File is too large.")
    if ext == ".wav":
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wavf:
                duration = wavf.getnframes() / float(wavf.getframerate())
                if duration < 1.0:
                    raise HTTPException(status_code=400, detail="Audio too short.")
                if duration > 300.0:
                    raise HTTPException(status_code=400, detail="Audio too long.")
                if wavf.getframerate() < 8000:
                    raise HTTPException(status_code=400, detail="Sample rate too low.")
        except Exception:
            raise HTTPException(status_code=400, detail="Corrupted or invalid WAV file.")
    return audio_bytes

# --- WebSocket Streaming STT ---
@app.websocket("/ws/transcribe_stream")
async def websocket_transcribe_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming STT.
    Accepts binary audio chunks, returns partial transcripts.
    """
    await websocket.accept()
    buffer = b''
    provider = PROVIDER_MAP['openai']
    try:
        while True:
            chunk = await websocket.receive_bytes()
            buffer += chunk
            if len(buffer) > 16000:
                text = provider.transcribe(buffer, 'stream.wav')
                await websocket.send_json({"partial": text})
                buffer = b''
    except WebSocketDisconnect:
        await websocket.close()
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()

# --- API Models ---
class SubmitJobResponse(BaseModel):
    job_id: str
    status: str
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    provider: str
    text: Optional[str]
    summary: Optional[str]
    created_at: Optional[str]
class HistoryItem(BaseModel):
    job_id: str
    filename: str
    provider: str
    status: str
    created_at: str

# --- API Endpoints ---
@app.post("/transcribe_async", response_model=SubmitJobResponse)
async def transcribe_async(
    file: UploadFile = File(...),
    provider: str = Form("openai"),
    webhook_url: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """
    Submit an async transcription job via Celery. Notifies via webhook if provided.
    """
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=400, detail="Unknown provider.")
    audio_bytes = validate_audio_file(file)
    job_id = str(uuid.uuid4())
    celery_app.send_task('celery_worker.process_transcription_job', args=[job_id, audio_bytes, file.filename, provider, webhook_url, user_id])
    return SubmitJobResponse(job_id=job_id, status="queued")

@app.get("/job_status/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str):
    session = SessionLocal()
    hist = session.query(TranscriptionHistory).filter_by(id=job_id).first()
    session.close()
    if not hist:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(
        job_id=hist.id,
        status=hist.status,
        provider=hist.provider,
        text=hist.text,
        summary=hist.summary,
        created_at=hist.created_at.isoformat() if hist.created_at else None
    )

@app.get("/history", response_model=List[HistoryItem])
def get_history():
    session = SessionLocal()
    items = session.query(TranscriptionHistory).order_by(TranscriptionHistory.created_at.desc()).all()
    session.close()
    return [HistoryItem(
        job_id=it.id,
        filename=it.filename,
        provider=it.provider,
        status=it.status,
        created_at=it.created_at.isoformat() if it.created_at else None
    ) for it in items]

@app.get("/providers")
def list_providers():
    return {"providers": [p.name for p in PROVIDERS]}

# --- Analytics Endpoints ---
@app.get("/analytics/providers")
def analytics_providers():
    session = SessionLocal()
    data = session.query(TranscriptionHistory.provider, func.count()).group_by(TranscriptionHistory.provider).all()
    session.close()
    return {"provider_counts": dict(data)}

@app.get("/analytics/errors")
def analytics_errors():
    session = SessionLocal()
    data = session.query(TranscriptionHistory.provider, func.count()).filter(TranscriptionHistory.status != 'completed').group_by(TranscriptionHistory.provider).all()
    session.close()
    return {"error_counts": dict(data)}

@app.get("/analytics/users")
def analytics_users():
    session = SessionLocal()
    data = session.execute('SELECT user_id, COUNT(*) FROM transcription_history GROUP BY user_id').fetchall()
    session.close()
    return {"user_counts": dict(data)} 