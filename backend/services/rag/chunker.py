"""Document text extraction and semantic chunking service."""
import io
import re
from typing import List

import structlog

logger = structlog.get_logger(__name__)

# PDF extraction library imports (supports both pypdf and PyPDF2)
try:
    import pypdf as pdf_lib
except ImportError:
    try:
        import PyPDF2 as pdf_lib
    except ImportError:
        pdf_lib = None

# DOCX extraction library
try:
    import docx
except ImportError:
    docx = None


class DocumentExtractionError(Exception):
    """Raised when document parsing fails."""
    pass


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks without breaking words where possible.
    
    Args:
        text: Source text string.
        chunk_size: Target character length per chunk.
        overlap: Number of characters to overlap between adjacent chunks.

    Returns:
        List of text chunks.
    """
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []

    if len(clean) <= chunk_size:
        return [clean]

    chunks: List[str] = []
    start = 0
    text_length = len(clean)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            # Look for sentence boundary (. ? !) or word boundary near end
            last_period = clean.rfind(". ", start, end)
            if last_period != -1 and last_period > start + (chunk_size // 2):
                end = last_period + 1
            else:
                last_space = clean.rfind(" ", start, end)
                if last_space != -1 and last_space > start:
                    end = last_space

        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(start + 1, end - overlap)

    return chunks


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF document bytes.
    
    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        Extracted plain text.
    """
    if pdf_lib is None:
        raise DocumentExtractionError("PyPDF2 or pypdf is not installed.")

    try:
        reader = pdf_lib.PdfReader(io.BytesIO(file_bytes))
        extracted_pages = []
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text.strip())

        return "\n\n".join(extracted_pages)
    except Exception as e:
        raise DocumentExtractionError(f"Failed to extract text from PDF: {e}") from e


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from Microsoft Word (.docx) bytes.
    
    Args:
        file_bytes: Raw DOCX bytes.

    Returns:
        Extracted plain text.
    """
    if docx is None:
        raise DocumentExtractionError("python-docx is not installed.")

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        return "\n\n".join(paragraphs)
    except Exception as e:
        raise DocumentExtractionError(f"Failed to extract text from DOCX: {e}") from e


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from plain text or markdown bytes supporting multiple encodings.
    
    Args:
        file_bytes: Raw text file bytes.

    Returns:
        Decoded text string.
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


def extract_text(file_bytes: bytes, content_type: str) -> str:
    """Dispatch document text extraction based on MIME type or file characteristics.
    
    Args:
        file_bytes: Raw document payload.
        content_type: MIME type string (e.g., 'application/pdf', 'text/plain').

    Returns:
        Extracted text content.
    """
    ct = content_type.lower().strip()

    if "pdf" in ct:
        return extract_text_from_pdf(file_bytes)
    elif "word" in ct or "docx" in ct or "officedocument" in ct:
        return extract_text_from_docx(file_bytes)
    elif "text" in ct or "plain" in ct or "markdown" in ct:
        return extract_text_from_txt(file_bytes)

    # Fallback heuristic: check magic bytes
    if file_bytes.startswith(b"%PDF"):
        return extract_text_from_pdf(file_bytes)
    elif file_bytes.startswith(b"PK\x03\x04"):
        try:
            return extract_text_from_docx(file_bytes)
        except Exception:
            pass

    return extract_text_from_txt(file_bytes)
