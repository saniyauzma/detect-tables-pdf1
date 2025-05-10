import fitz

def is_scanned_pdf(pdf_path):
    """Return True if the PDF is likely scanned (no extractable text), else False."""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            if page.get_text().strip():
                return False
    return True

def extract_text_metadata(pdf_path):
    """Extract all text and metadata from the PDF."""
    with fitz.open(pdf_path) as doc:
        text = '\n'.join([page.get_text() for page in doc])
        metadata = doc.metadata
    return text, metadata 