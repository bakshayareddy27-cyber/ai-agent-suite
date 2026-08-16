"""
Central LLM client factory.

Both agents pull their model from here so there's exactly one place
that knows how to talk to the provider. Keeping this separate also
makes it trivial to swap providers later without touching agent logic.

Provider is selected via env vars:
  ANTHROPIC_API_KEY  -> uses Claude (default, recommended)
  OPENAI_API_KEY      -> falls back to OpenAI if Anthropic key absent

Both keys are read from the environment only. Nothing is hard-coded.
"""

import os
from functools import lru_cache


def _get_provider() -> str:
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    raise RuntimeError(
        "No LLM API key found. Set ANTHROPIC_API_KEY (recommended) or "
        "OPENAI_API_KEY in your environment / .env file."
    )


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.2):
    """
    Returns a LangChain chat model instance.
    Cached so repeated calls within a run don't re-init clients.
    """
    provider = _get_provider()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            max_tokens=2048,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    from langchain_openai import ChatOpenAI

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


@lru_cache(maxsize=1)
def get_embeddings():
    """
    Local, free, no-API-key embeddings model. This is what makes RAG
    work out of the box on Render without needing a separate embeddings
    key or paying per-embedding-call. Runs on CPU, ~90MB model.
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
