import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from main import app
import asyncio

@pytest.mark.asyncio
async def test_transcribe_async():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        files = {"file": ("test.wav", b"RIFF....WAVEfmt ", "audio/wav")}
        response = await ac.post("/transcribe_async", files=files, data={"provider": "openai"})
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

@pytest.mark.asyncio
async def test_job_status_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/job_status/doesnotexist")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_history():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_providers():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/providers")
        assert response.status_code == 200
        assert "providers" in response.json()

@pytest.mark.asyncio
async def test_ws_transcribe_stream():
    client = TestClient(app)
    with client.websocket_connect("/ws/transcribe_stream") as ws:
        ws.send_bytes(b"dummy audio chunk")
        data = ws.receive_json()
        assert "partial" in data or "error" in data 