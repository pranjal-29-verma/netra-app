import litellm
from typing import AsyncIterator
from app.core.config import settings

litellm.drop_params = True  # ignore unsupported params per provider silently

# Pydantic-settings loads .env into the settings object but does NOT put values into
# os.environ, which is where LiteLLM looks for API keys. We resolve the right key
# here based on the model prefix so switching providers = one .env line change.
_PROVIDER_KEY_MAP = {
    "gemini/":    lambda: settings.GEMINI_API_KEY,
    "claude":     lambda: settings.ANTHROPIC_API_KEY,
    "gpt-":       lambda: settings.OPENAI_API_KEY,
    "mistral":    lambda: settings.MISTRAL_API_KEY,
    "openai/":    lambda: settings.OPENAI_API_KEY,
    "anthropic/": lambda: settings.ANTHROPIC_API_KEY,
}


def _resolve_api_key() -> str | None:
    model = settings.LLM_MODEL
    for prefix, key_fn in _PROVIDER_KEY_MAP.items():
        if model.startswith(prefix):
            return key_fn()
    return None

_SYSTEM_PROMPT = """You are Netra, a personal AI knowledge assistant. You help users find answers from their uploaded documents and knowledge base.

{context}

Guidelines:
- When context is provided, base your answer on it and cite the source document by name
- If the context does not contain enough information, answer from general knowledge and say so clearly
- Be concise, accurate, and helpful
- Use markdown formatting where appropriate (headings, bullets, code blocks)"""

_NO_CONTEXT = (
    "No relevant documents found in the knowledge base for this query. "
    "Answering from general knowledge."
)


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return _NO_CONTEXT
    lines = ["RELEVANT CONTEXT FROM YOUR DOCUMENTS:", "---"]
    for chunk in chunks:
        lines.append(f"[Source: {chunk['filename']}]")
        lines.append(chunk["content"])
        lines.append("")
    lines.append("---")
    return "\n".join(lines)


def _build_messages(user_content: str, history: list[dict], chunks: list[dict]) -> list[dict]:
    system = _SYSTEM_PROMPT.format(context=_build_context(chunks))
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_content})
    return messages


async def stream_response(
    user_content: str,
    history: list[dict],
    chunks: list[dict],
) -> AsyncIterator[str]:
    from app.services.llm_config_service import get_active_llm
    custom_model, custom_key = get_active_llm()

    model   = custom_model if custom_model else settings.LLM_MODEL
    api_key = custom_key   if custom_key   else _resolve_api_key()

    messages = _build_messages(user_content, history, chunks)
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        stream=True,
        max_tokens=2048,
        api_key=api_key,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
