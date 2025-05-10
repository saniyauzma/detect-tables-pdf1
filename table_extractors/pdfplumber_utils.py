import pdfplumber
import logging
from typing import List, Dict, Any

def extract_tables_pdfplumber(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables from a PDF using Pdfplumber.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dictionaries containing table data and metadata
    """
    try:
        tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract tables from the page
                page_tables = page.extract_tables()
                
                # Get text above the table for potential title
                text_above = page.extract_text()
                
                for table_num, table in enumerate(page_tables):
                    if table:  # If table is not empty
                        # Try to find title by looking at text above the table
                        title = ""
                        if text_above:
                            # Get the last paragraph before the table
                            paragraphs = text_above.split('\n\n')
                            if paragraphs:
                                title = paragraphs[-1].strip()
                        
                        tables.append({
                            'title': title,
                            'page': page_num + 1,
                            'data': table,
                            'tool': 'Pdfplumber',
                            'confidence': 0.8,  # High confidence for digital PDFs
                            'table_type': 'digital'
                        })
        
        return tables
    except Exception as e:
        logging.error(f"Error extracting tables with Pdfplumber from {pdf_path}: {str(e)}")
        return []

def extract_text_pdfplumber(pdf_path):
    """Extract all text from all pages using pdfplumber.
    
    Returns:
        dict: Dictionary mapping page numbers (1-based) to text content
    """
    text_by_page = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text_by_page[i] = page.extract_text() or ''
    return text_by_page 