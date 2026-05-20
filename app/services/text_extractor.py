import io
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument


class TextExtractor:

    @staticmethod
    def from_pdf(content: bytes) -> str:
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    @staticmethod
    def from_docx(content: bytes) -> str:
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    @staticmethod
    def from_text(content: bytes) -> str:
        return content.decode("utf-8", errors="replace")

    @staticmethod
    def from_url(url: str) -> str:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def extract(file_type: str, content: bytes | None = None, url: str | None = None) -> str:
        if file_type == "url":
            return TextExtractor.from_url(url)
        elif file_type == "pdf":
            return TextExtractor.from_pdf(content)
        elif file_type == "docx":
            return TextExtractor.from_docx(content)
        elif file_type in ("txt", "md"):
            return TextExtractor.from_text(content)
        raise ValueError(f"Unsupported file type: {file_type}")
