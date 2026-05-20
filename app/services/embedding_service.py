import voyageai
from app.core.config import settings

_client: voyageai.Client | None = None

MODEL = "voyage-3"
DIMENSION = 1024


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client


class EmbeddingService:

    @staticmethod
    def embed_documents(texts: list[str]) -> list[list[float]]:
        result = _get_client().embed(texts, model=MODEL, input_type="document")
        return result.embeddings

    @staticmethod
    def embed_query(query: str) -> list[float]:
        result = _get_client().embed([query], model=MODEL, input_type="query")
        return result.embeddings[0]
