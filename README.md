# Speech-to-Text Proxy Resilience (Enterprise)

A robust, enterprise-grade mini-system for reliable speech-to-text transcription using OpenAI, ElevenLabs, and Google Speech-to-Text APIs, with automatic fallback, provider selection, advanced validation, and monitoring.

## Features
- Proxy for speech-to-text (OpenAI Whisper, ElevenLabs, Google)
- Advanced error handling, timeouts, retries, and fallback
- Healthcheck and metrics endpoints
- Provider listing endpoint and provider selection (via frontend)
- Modern, interactive, user-friendly frontend
- Structured logging, request/response logging, and input validation (file type, size, duration, sample rate, corruption)
- Detailed metrics: per-provider, per-filetype, per-error, average latency
- Easily extensible for new providers

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables:
   - `OPENAI_API_KEY` — your OpenAI API key
   - `ELEVENLABS_API_KEY` — your ElevenLabs API key
   - `GOOGLE_API_KEY` — your Google Speech-to-Text API key (optional, see code for integration)
3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
4. Open `frontend.html` in your browser.

## Endpoints
- `POST /transcribe` — Upload an audio file and get the transcribed text (auto-fallback or provider selection)
- `GET /health` — Healthcheck (API keys presence)
- `GET /metrics` — Advanced in-memory metrics (requests, success, fail, per-provider, per-filetype, per-error, avg latency)
- `GET /providers` — List all supported and available providers

## Reliability & Validation
- File type, size, duration, sample rate, and corruption validation
- Per-provider timeouts and retries with exponential backoff
- Automatic fallback between OpenAI, ElevenLabs, and Google
- Structured logging and error reporting
- Request/response logging for auditability

## Extensibility
- Add new providers by implementing a new function and adding to the provider list
- All logic is modular and ready for integration into larger systems

## Architecture
- **main.py** — FastAPI backend, proxy logic, validation, health, metrics, provider listing
- **frontend.html** — Modern HTML+JS frontend with provider selection and advanced metrics
- **requirements.txt** — Python dependencies

## Example .env
```
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## License
MIT 