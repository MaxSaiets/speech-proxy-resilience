"""
Celery worker for async transcription jobs.
- Uses Redis as broker.
- Modular provider logic (imported from providers.py).
- Saves results to DB (imported from db.py).
- LLM summary (imported from llm.py).
- Webhook notification (imported from webhook.py).
- Retries on failure.
"""
import os
from celery import Celery
from providers import PROVIDER_MAP
from llm import llm_summary
from db import SessionLocal, TranscriptionHistory
from webhook import send_webhook

celery_app = Celery('worker', broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'))

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_transcription_job(self, job_id, audio_bytes, filename, provider_name, webhook_url, user_id=None):
    session = SessionLocal()
    provider = PROVIDER_MAP.get(provider_name)
    status = "failed"
    text = None
    summary = None
    try:
        text = provider.transcribe(audio_bytes, filename)
        if text:
            summary = llm_summary(text)
            status = "completed"
    except Exception as e:
        self.retry(exc=e)
    hist = TranscriptionHistory(id=job_id, filename=filename, provider=provider_name, status=status, text=text, summary=summary, webhook_url=webhook_url, user_id=user_id)
    session.merge(hist)
    session.commit()
    session.close()
    if webhook_url:
        send_webhook(webhook_url, {"job_id": job_id, "status": status, "text": text, "summary": summary}) 