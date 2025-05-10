import camelot
import logging
from typing import List, Dict, Any

def is_valid_table(table):
    """
    Validate if the extracted table meets our criteria.
    """
    # Check if table has enough rows and columns
    if len(table.df.index) < 2 or len(table.df.columns) < 2:
        return False
    
    # Check if table has enough non-empty cells
    non_empty_cells = table.df.notna().sum().sum()
    total_cells = len(table.df.index) * len(table.df.columns)
    if non_empty_cells / total_cells < 0.3:  # At least 30% cells should be non-empty
        return False
    
    # Check for consistent column structure
    col_lengths = table.df.apply(lambda x: x.notna().sum())
    if col_lengths.std() / col_lengths.mean() > 0.5:  # Column lengths shouldn't vary too much
        return False
    
    return True

def extract_tables_camelot(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables from a PDF using Camelot.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dictionaries containing table data and metadata
    """
    try:
        # Try both lattice and stream modes
        tables = []
        
        # Lattice mode (for tables with borders)
        lattice_tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        for table in lattice_tables:
            if table.parsing_report['accuracy'] > 80:  # Only keep high-accuracy tables
                tables.append({
                    'title': table.title if hasattr(table, 'title') else '',
                    'page': table.page,
                    'data': table.df.values.tolist(),
                    'tool': 'Camelot-Lattice',
                    'confidence': table.parsing_report['accuracy'] / 100,
                    'table_type': 'lattice'
                })
        
        # Stream mode (for tables without borders)
        stream_tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
        for table in stream_tables:
            if table.parsing_report['accuracy'] > 80:  # Only keep high-accuracy tables
                tables.append({
                    'title': table.title if hasattr(table, 'title') else '',
                    'page': table.page,
                    'data': table.df.values.tolist(),
                    'tool': 'Camelot-Stream',
                    'confidence': table.parsing_report['accuracy'] / 100,
                    'table_type': 'stream'
                })
        
        return tables
    except Exception as e:
        logging.error(f"Error extracting tables with Camelot from {pdf_path}: {str(e)}")
        return [] 