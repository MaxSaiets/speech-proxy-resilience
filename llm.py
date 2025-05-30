"""
LLM-powered summary for transcripts.
- Uses OpenAI GPT-4o for summarization.
"""
import os
from openai import OpenAI
import logging

logger = logging.getLogger("speech-proxy.llm")

def llm_summary(text: str) -> str:
    """
    Summarize transcript using OpenAI GPT-4o.
    Returns summary string or None on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not text:
        return None
    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Summarize the following transcript in 1-2 sentences."},
                      {"role": "user", "content": text}]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM summary error: {e}")
        return None 