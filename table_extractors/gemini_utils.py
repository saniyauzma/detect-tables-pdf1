import os
import json
import logging
import google.generativeai as genai
from typing import List, Dict, Any
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables!")

genai.configure(api_key=GOOGLE_API_KEY)

def extract_tables_gemini(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables from PDF using Gemini API.
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Create prompt for table extraction
        prompt = """
        Please analyze this PDF document and extract all tables with their titles.
        For each table, provide:
        1. The table title
        2. The page number
        3. The table data in a structured format
        
        Format the response as a JSON array of objects with the following structure:
        [
            {
                "title": "Table Title",
                "page": page_number,
                "data": [table_data_as_2d_array]
            }
        ]
        """
        
        # Generate content
        response = model.generate_content([prompt, pdf_data])
        
        # Parse response
        try:
            tables = json.loads(response.text)
            if not isinstance(tables, list):
                raise ValueError("Response is not a list")
            
            # Validate and clean each table
            cleaned_tables = []
            for table in tables:
                if validate_table_data(table.get('data', [])):
                    cleaned_tables.append({
                        'title': clean_table_title(table.get('title', '')),
                        'page': table.get('page', 1),
                        'data': table.get('data', [])
                    })
            
            return cleaned_tables
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error in Gemini table extraction: {str(e)}")
        return []

def clean_table_title(title: str, default: str = 'Untitled Table') -> str:
    """
    Clean and validate table title.
    """
    if not title or not title.strip():
        return default
        
    # Remove extra whitespace and newlines
    title = ' '.join(title.split())
    
    # Remove common prefixes/suffixes
    prefixes = ['Table', 'Table:', 'Table -', 'Table - ']
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
            
    return title if title else default

def validate_table_data(data: List[List[str]]) -> bool:
    """
    Validate table data structure.
    """
    if not data or not isinstance(data, list):
        return False
        
    # Check if all rows have the same number of columns
    if len(data) < 2:  # At least header and one data row
        return False
        
    num_cols = len(data[0])
    return all(len(row) == num_cols for row in data)

def classify_table(data: List[List[str]]) -> Dict[str, str]:
    """
    Classify the type of table based on its content.
    """
    if not data or len(data) < 2:
        return {'classification': 'Unknown'}
        
    # Get header row
    header = [str(cell).lower() for cell in data[0]]
    
    # Common financial statement indicators
    financial_indicators = {
        'balance_sheet': ['assets', 'liabilities', 'equity', 'capital'],
        'income_statement': ['revenue', 'income', 'expenses', 'profit', 'loss'],
        'cash_flow': ['cash', 'flow', 'operating', 'investing', 'financing'],
        'notes': ['note', 'accounting', 'policy', 'disclosure']
    }
    
    # Check for indicators in header
    for table_type, indicators in financial_indicators.items():
        if any(indicator in ' '.join(header) for indicator in indicators):
            return {'classification': table_type.replace('_', ' ').title()}
            
    return {'classification': 'Other'} 