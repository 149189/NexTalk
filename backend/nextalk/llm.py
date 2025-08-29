# nextalk/llm.py
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try to import the official Google Generative SDK, but don't fail if it's missing.
try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None
    logger.debug("google.generativeai SDK not available; falling back to local stub behavior.")

# Read API key lazily from env; do NOT raise on import
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Lazy client holder
_client = None

def _init_client():
    """
    Lazily configure and return a genai.Client().
    Returns None if genai SDK or API key is not available.
    """
    global _client, genai, _GEMINI_API_KEY
    if _client is not None:
        return _client

    if genai is None:
        return None

    if not _GEMINI_API_KEY:
        # Do not raise here; caller will handle fallback
        logger.info("GEMINI_API_KEY not set; Gemini calls will fallback to local behavior.")
        return None

    try:
        genai.configure(api_key=_GEMINI_API_KEY)
        _client = genai.Client()
        return _client
    except Exception as e:
        logger.exception("Failed to initialize Gemini client: %s", e)
        _client = None
        return None

# === Public API ===

def call_llm(prompt: str, model: str = "gemini-2.0-flash-001") -> str:
    """
    Generate text for the prompt using Gemini (if available) or a safe fallback.
    This function never raises on missing API key / SDK; it logs and falls back.
    """
    client = _init_client()
    if client:
        try:
            # Gemini SDK supports passing a string or structured contents.
            resp = client.models.generate_content(model=model, contents=prompt)
            # Some SDK versions return an object with `.text`, others return a dict.
            if hasattr(resp, "text"):
                return resp.text.strip()
            # fallback: try to access dict-like
            if isinstance(resp, dict):
                # may contain choices / text variants; try reasonable keys
                if "candidates" in resp and resp["candidates"]:
                    first = resp["candidates"][0]
                    return first.get("content", first.get("text", "")).strip()
                return str(resp)
            return str(resp).strip()
        except Exception as e:
            logger.exception("Gemini call failed, falling back to echo. Error: %s", e)

    # Fallback behaviour (safe for tests)
    truncated = prompt[:500].replace("\n", " ")
    return f"LLM fallback echo: {truncated}"

def get_embedding(text: str, model: str = "text-embedding-004") -> List[float]:
    """
    Return embedding vector for the given text using Gemini embeddings if available.
    Falls back to a deterministic simple numeric vector so tests and FAISS flows can run.
    """
    client = _init_client()
    if client:
        try:
            emb_resp = client.models.embed_content(model=model, contents=text)
            # SDK often returns an object or dict with 'embeddings' list
            if hasattr(emb_resp, "embeddings") and emb_resp.embeddings:
                # SDK embeddings objects may store vector in .values or .embedding
                first = emb_resp.embeddings[0]
                if hasattr(first, "values"):
                    return list(first.values)
                if isinstance(first, dict) and "values" in first:
                    return list(first["values"])
                if isinstance(first, dict) and "embedding" in first:
                    return list(first["embedding"])
            if isinstance(emb_resp, dict) and "data" in emb_resp and emb_resp["data"]:
                return list(emb_resp["data"][0].get("embedding", []))
        except Exception as e:
            logger.exception("Gemini embedding call failed, falling back. Error: %s", e)

    # Deterministic fallback embedding (small, stable)
    vec: List[float] = []
    # produce a small fixed-length vector derived from chars for deterministic tests
    max_len = 128
    for i, ch in enumerate(text[:max_len]):
        vec.append(float(ord(ch) % 97) / 97.0)
    # pad to fixed length for simplicity
    if len(vec) < max_len:
        vec.extend([0.0] * (max_len - len(vec)))
    return vec

# Optional helper to allow tests to override API key at runtime
def set_gemini_api_key(key: Optional[str]):
    """
    Set GEMINI_API_KEY at runtime (useful for tests). This will reset lazy client.
    """
    global _GEMINI_API_KEY, _client
    _GEMINI_API_KEY = key
    _client = None
    logger.info("GEMINI_API_KEY updated via set_gemini_api_key(); client will re-init on next call.")


def chat_with_llm(message: str) -> str:
    """
    Call your LLM API (OpenAI, Gemini, or HuggingFace).
    For now, return a mock reply.
    """
    # Example mock response
    return f"You said: {message}. (This is a mock LLM response)"
