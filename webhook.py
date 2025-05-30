"""
Webhook/callback notification logic.
- Sends POST request to webhook_url with job result.
"""
import logging
import httpx

logger = logging.getLogger("speech-proxy.webhook")

def send_webhook(webhook_url: str, payload: dict):
    """
    Send POST request to webhook_url with payload.
    """
    try:
        httpx.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Webhook failed: {e}") 