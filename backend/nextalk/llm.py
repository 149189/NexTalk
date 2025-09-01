# nextalk/llm.py
import os
import logging
from typing import List, Optional, Union, Dict

logger = logging.getLogger(__name__)

# Try to import the official Google Generative SDK, but don't fail if it's missing.
try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None
    logger.debug("google.generativeai SDK not available; falling back to local stub behavior.")

# Read API key lazily from env; do NOT raise on import
_GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

# Lazy holders (kept simple — recreated if API key changes)
_model_cache = {}

# Helpers --------------------------------------------------------------------

def _make_prompt(input_: Union[str, List[Dict[str, str]]]) -> str:
    """
    Convert either a plain prompt (str) or a list of role/text dicts into a single string prompt.
    Example of list format: [{"role":"system","text":"You are helpful."}, {"role":"user","text":"hi"}]
    """
    if isinstance(input_, str):
        return input_
    # join messages in a readable format for LLM
    parts: List[str] = []
    for m in input_:
        role = m.get("role", "user")
        text = m.get("text") or m.get("content") or ""
        parts.append(f"{role}: {text}")
    return "\n".join(parts)


def _has_api_key() -> bool:
    return bool(_GEMINI_API_KEY)


def _ensure_configured():
    """
    Try to call configure(api_key=...) if available on the imported genai module.
    Safe no-op if genai is None or configure not present.
    """
    if not genai or not _GEMINI_API_KEY:
        return
    try:
        if hasattr(genai, "configure"):
            # some genai variants expose configure()
            try:
                genai.configure(api_key=_GEMINI_API_KEY)
            except Exception:
                # older/newer variants may raise — log and continue
                logger.debug("genai.configure call failed or not required.")
    except Exception:
        logger.debug("Ignored exception in _ensure_configured", exc_info=True)


# Public API -----------------------------------------------------------------

def call_llm(
    prompt_or_messages: Union[str, List[Dict[str, str]]],
    model: str = "gemini-2.0-flash-001",
) -> str:
    """
    Generate text for the prompt (or messages list) using Gemini if available, otherwise fallback.
    - prompt_or_messages: either a string prompt or a list of {"role": "...", "text": "..."} dicts.
    - model: model id to use (best-effort).
    """
    prompt = _make_prompt(prompt_or_messages)

    # If SDK unavailable or API key missing, return deterministic fallback
    if not genai or not _has_api_key():
        truncated = prompt[:500].replace("\n", " ")
        return f"LLM fallback echo: {truncated}"

    # Try multiple invocation patterns depending on SDK shape
    try:
        _ensure_configured()

        # Pattern A: genai.GenerativeModel (some SDK versions)
        if hasattr(genai, "GenerativeModel"):
            try:
                # cache per model name
                gm = _model_cache.get(model)
                if gm is None:
                    gm = genai.GenerativeModel(model)
                    _model_cache[model] = gm
                resp = gm.generate_content(prompt)
                if hasattr(resp, "text") and resp.text:
                    return str(resp.text).strip()
                # try common dict shapes
                if isinstance(resp, dict):
                    # attempt to extract text from common keys
                    if "candidates" in resp and resp["candidates"]:
                        first = resp["candidates"][0]
                        return first.get("content", first.get("text", "")) or str(resp)
                    if "output" in resp and isinstance(resp["output"], str):
                        return resp["output"]
                    return str(resp)
                return str(resp).strip()
            except Exception as e:
                logger.exception("genai.GenerativeModel invocation failed: %s", e)

        # Pattern B: genai.Client with models.generate_content (alternate SDK)
        if hasattr(genai, "Client"):
            try:
                # Some SDK variants allow Client(api_key=...)
                client = None
                try:
                    client = genai.Client(api_key=_GEMINI_API_KEY)  # type: ignore
                except Exception:
                    # Some variants require configure() already called and expose Client() without args
                    try:
                        client = genai.Client()  # type: ignore
                    except Exception:
                        client = None

                if client:
                    # try call that pattern
                    resp = client.models.generate_content(model=model, contents=prompt)  # type: ignore
                    if hasattr(resp, "text") and resp.text:
                        return str(resp.text).strip()
                    if isinstance(resp, dict):
                        if "candidates" in resp and resp["candidates"]:
                            first = resp["candidates"][0]
                            return first.get("content", first.get("text", "")) or str(resp)
                        return str(resp)
                    return str(resp).strip()
            except Exception as e:
                logger.exception("genai.Client invocation failed: %s", e)

        # Pattern C: top-level helper (some distributions)
        if hasattr(genai, "generate_text") or hasattr(genai, "generate"):
            try:
                # Try a few common helper names
                if hasattr(genai, "generate_text"):
                    resp = genai.generate_text(model=model, prompt=prompt)  # type: ignore
                    # many helpers return object with .text or str()
                    if hasattr(resp, "text"):
                        return str(resp.text).strip()
                    if isinstance(resp, dict) and "output" in resp:
                        return str(resp["output"])
                    return str(resp)
                if hasattr(genai, "generate"):
                    resp = genai.generate(model=model, prompt=prompt)  # type: ignore
                    if hasattr(resp, "text"):
                        return str(resp.text).strip()
                    if isinstance(resp, dict) and "candidates" in resp:
                        first = resp["candidates"][0]
                        return first.get("content", first.get("text", "")) or str(resp)
            except Exception as e:
                logger.exception("genai helper invocation failed: %s", e)

    except Exception as e:
        logger.exception("Unexpected error during Gemini call: %s", e)

    # Final fallback if all SDK attempts failed
    truncated = prompt[:500].replace("\n", " ")
    return f"LLM fallback echo: {truncated}"


def get_embedding(text: str, model: str = "text-embedding-004") -> List[float]:
    """
    Get an embedding vector for the supplied text.
    Tries multiple SDK shapes and falls back to deterministic vector if unavailable.
    """
    # If SDK not present or no API key, fallback
    if not genai or not _has_api_key():
        # deterministic simple vector for testing/dev
        vec: List[float] = []
        max_len = 128
        for i, ch in enumerate(text[:max_len]):
            vec.append(float(ord(ch) % 97) / 97.0)
        if len(vec) < max_len:
            vec.extend([0.0] * (max_len - len(vec)))
        return vec

    try:
        _ensure_configured()

        # Pattern A: genai.embed_content (some SDKs)
        if hasattr(genai, "embed_content"):
            try:
                emb_resp = genai.embed_content(model=model, content=text)  # type: ignore
                # common shapes
                if hasattr(emb_resp, "embedding"):
                    return list(emb_resp.embedding)
                if isinstance(emb_resp, dict):
                    # Cloud/other SDK may use data/embedding
                    if "data" in emb_resp and emb_resp["data"]:
                        e = emb_resp["data"][0]
                        if isinstance(e, dict) and "embedding" in e:
                            return list(e["embedding"])
                    if "embedding" in emb_resp:
                        return list(emb_resp["embedding"])
            except Exception as e:
                logger.exception("genai.embed_content failed: %s", e)

        # Pattern B: client.models.embed_content
        if hasattr(genai, "Client"):
            try:
                client = None
                try:
                    client = genai.Client(api_key=_GEMINI_API_KEY)  # type: ignore
                except Exception:
                    try:
                        client = genai.Client()
                    except Exception:
                        client = None

                if client:
                    emb_resp = client.models.embed_content(model=model, contents=text)  # type: ignore
                    # try to parse response
                    if hasattr(emb_resp, "embeddings") and emb_resp.embeddings:
                        first = emb_resp.embeddings[0]
                        if hasattr(first, "values"):
                            return list(first.values)
                        if isinstance(first, dict) and "values" in first:
                            return list(first["values"])
                    if isinstance(emb_resp, dict) and "data" in emb_resp and emb_resp["data"]:
                        return list(emb_resp["data"][0].get("embedding", []))
            except Exception as e:
                logger.exception("client.models.embed_content failed: %s", e)

    except Exception as e:
        logger.exception("Unexpected error during embedding call: %s", e)

    # Deterministic fallback embedding (if everything else fails)
    vec: List[float] = []
    max_len = 128
    for i, ch in enumerate(text[:max_len]):
        vec.append(float(ord(ch) % 97) / 97.0)
    if len(vec) < max_len:
        vec.extend([0.0] * (max_len - len(vec)))
    return vec


def set_gemini_api_key(key: Optional[str]):
    """
    Set GEMINI_API_KEY at runtime (useful for tests) and clear cached models.
    """
    global _GEMINI_API_KEY, _model_cache
    _GEMINI_API_KEY = key
    _model_cache = {}
    logger.info("GEMINI_API_KEY updated; model cache cleared.")


# Convenience wrapper used by views
def chat_with_llm(message_or_messages: Union[str, List[Dict[str, str]]]) -> str:
    """
    Simple wrapper that calls call_llm and returns text. Keeps interface stable for the rest of the app.
    """
    return call_llm(message_or_messages)
