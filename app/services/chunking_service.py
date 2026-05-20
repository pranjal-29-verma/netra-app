CHUNK_SIZE = 1000   # characters
CHUNK_OVERLAP = 100  # characters


class ChunkingService:

    @staticmethod
    def chunk(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        text = text.strip()
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Prefer breaking at a natural boundary rather than mid-word
            if end < len(text):
                for separator in ("\n\n", ". ", "? ", "! ", "\n"):
                    pos = chunk.rfind(separator)
                    if pos > chunk_size // 2:
                        end = start + pos + len(separator)
                        chunk = text[start:end]
                        break

            if chunk.strip():
                chunks.append(chunk.strip())

            start = end - overlap

        return chunks
