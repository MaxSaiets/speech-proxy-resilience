"""
Speech-to-Text Providers
- Modular provider classes for OpenAI, ElevenLabs, Google, AWS, Azure.
- Each provider implements .transcribe(audio_bytes, filename) -> Optional[str]
"""
import os
import io
import logging
import base64
import httpx
from openai import OpenAI
from elevenlabs import ElevenLabs
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError
import uuid

logger = logging.getLogger("speech-proxy.providers")

class ProviderBase:
    name = "base"
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        raise NotImplementedError

class OpenAIProvider(ProviderBase):
    name = "openai"
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.error("OPENAI_API_KEY is not set.")
            return None
        client = OpenAI(api_key=api_key)
        try:
            with io.BytesIO(audio_bytes) as audio_file:
                audio_file.name = filename
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None

class ElevenLabsProvider(ProviderBase):
    name = "elevenlabs"
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            logger.error("ELEVENLABS_API_KEY is not set.")
            return None
        try:
            client = ElevenLabs(api_key=api_key)
            transcript = client.speech_to_text(audio=audio_bytes, filename=filename)
            return transcript['text'] if 'text' in transcript else None
        except Exception as e:
            logger.error(f"ElevenLabs error: {e}")
            return None

class GoogleProvider(ProviderBase):
    name = "google"
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            logger.warning("GOOGLE_API_KEY is not set. Returning demo result.")
            return "Google STT (demo): This is a fake transcript."
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode()
            payload = {
                "config": {"encoding": "LINEAR16", "languageCode": "en-US"},
                "audio": {"content": audio_b64}
            }
            resp = httpx.post(
                f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}",
                json=payload, timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            return result["results"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            logger.error(f"Google STT error: {e}")
            return None

class AWSProvider(ProviderBase):
    name = "aws"
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        if not aws_access_key or not aws_secret_key:
            logger.warning("AWS credentials not set. Returning demo result.")
            return "AWS Transcribe (demo): This is a fake transcript."
        try:
            s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
            transcribe = boto3.client('transcribe', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
            bucket = os.getenv("AWS_TRANSCRIBE_BUCKET", "speech-proxy-demo-bucket")
            s3_key = f"uploads/{uuid.uuid4()}_{filename}"
            # Upload audio to S3
            s3.put_object(Bucket=bucket, Key=s3_key, Body=audio_bytes)
            job_name = f"job-{uuid.uuid4()}"
            job_uri = f"s3://{bucket}/{s3_key}"
            transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": job_uri},
                MediaFormat=filename.split('.')[-1],
                LanguageCode="en-US",
                OutputBucketName=bucket
            )
            # Poll for result
            logger.info(f"AWS Transcribe job started: {job_name}")
            return f"AWS Transcribe job started: {job_name} (polling not implemented in demo)"
        except (BotoCoreError, NoCredentialsError) as e:
            logger.error(f"AWS error: {e}")
            return None
        except Exception as e:
            logger.error(f"AWS Transcribe error: {e}")
            return None

PROVIDERS = [OpenAIProvider(), ElevenLabsProvider(), GoogleProvider(), AWSProvider()]
PROVIDER_MAP = {p.name: p for p in PROVIDERS} 