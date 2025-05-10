import os
from dotenv import load_dotenv
load_dotenv()
import json
import csv
import logging
from typing import List, Dict, Any
from pathlib import Path
from table_extractors.pymupdf_utils import is_scanned_pdf
from table_extractors.pdfplumber_utils import extract_tables_pdfplumber
from table_extractors.camelot_utils import extract_tables_camelot
from table_extractors.tesseract_utils import extract_tables_tesseract
from table_extractors.paddleocr_utils import extract_tables_paddleocr

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'

def deduplicate_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for t in tables:
        key = (t.get('title', '').strip().lower(), t.get('page', ''), t.get('document', ''))
        if key not in seen:
            seen.add(key)
            deduped.append(t)
    return deduped

def clean_title(title: str) -> str:
    if not title or not title.strip():
        return 'Untitled Table'
    
    # Look for key table titles
    title_markers = [
        'BALANCE SHEET',
        'CAPITAL ACCOUNT',
        'PROFIT AND LOSS ACCOUNT',
        'TRADING ACCOUNT',
        'INCOME STATEMENT',
        'CASH FLOW STATEMENT',
        'SCHEDULE',
        'NOTES TO ACCOUNTS',
        'AUDITORS REPORT',
        'DIRECTORS REPORT',
        'ANNUAL REPORT',
        'FINANCIAL STATEMENTS',
        'CONSOLIDATED FINANCIAL STATEMENTS',
        'STANDALONE FINANCIAL STATEMENTS',
        'REVENUE ACCOUNT',
        'EXPENDITURE ACCOUNT',
        'RECEIPTS AND PAYMENTS ACCOUNT',
        'INCOME AND EXPENDITURE ACCOUNT',
        'FUND FLOW STATEMENT',
        'CASH FLOW STATEMENT',
        'SCHEDULE OF FIXED ASSETS',
        'SCHEDULE OF INVESTMENTS',
        'SCHEDULE OF LOANS AND ADVANCES',
        'SCHEDULE OF CURRENT ASSETS',
        'SCHEDULE OF CURRENT LIABILITIES',
        'SCHEDULE OF PROVISIONS',
        'SCHEDULE OF CONTINGENT LIABILITIES',
        'SCHEDULE OF CAPITAL WORK IN PROGRESS',
        'SCHEDULE OF INTANGIBLE ASSETS',
        'SCHEDULE OF DEFERRED TAX ASSETS',
        'SCHEDULE OF DEFERRED TAX LIABILITIES',
        'SCHEDULE OF OTHER ASSETS',
        'SCHEDULE OF OTHER LIABILITIES',
        'SCHEDULE OF RESERVES AND SURPLUS',
        'SCHEDULE OF SHARE CAPITAL',
        'SCHEDULE OF BORROWINGS',
        'SCHEDULE OF TRADE PAYABLES',
        'SCHEDULE OF TRADE RECEIVABLES',
        'SCHEDULE OF INVENTORY',
        'SCHEDULE OF CASH AND CASH EQUIVALENTS',
        'SCHEDULE OF SHORT TERM LOANS AND ADVANCES',
        'SCHEDULE OF LONG TERM LOANS AND ADVANCES',
        'SCHEDULE OF FIXED DEPOSITS',
        'SCHEDULE OF INVESTMENTS IN SUBSIDIARIES',
        'SCHEDULE OF INVESTMENTS IN ASSOCIATES',
        'SCHEDULE OF INVESTMENTS IN JOINT VENTURES',
        'SCHEDULE OF INVESTMENTS IN MUTUAL FUNDS',
        'SCHEDULE OF INVESTMENTS IN BONDS',
        'SCHEDULE OF INVESTMENTS IN DEBENTURES',
        'SCHEDULE OF INVESTMENTS IN EQUITY SHARES',
        'SCHEDULE OF INVESTMENTS IN PREFERENCE SHARES',
        'SCHEDULE OF INVESTMENTS IN GOVERNMENT SECURITIES',
        'SCHEDULE OF INVESTMENTS IN COMMERCIAL PAPERS',
        'SCHEDULE OF INVESTMENTS IN CERTIFICATES OF DEPOSIT',
        'SCHEDULE OF INVESTMENTS IN TREASURY BILLS',
        'SCHEDULE OF INVESTMENTS IN MONEY MARKET INSTRUMENTS',
        'SCHEDULE OF INVESTMENTS IN DERIVATIVES',
        'SCHEDULE OF INVESTMENTS IN FOREIGN CURRENCY',
        'SCHEDULE OF INVESTMENTS IN FOREIGN SECURITIES',
        'SCHEDULE OF INVESTMENTS IN FOREIGN MUTUAL FUNDS',
        'SCHEDULE OF INVESTMENTS IN FOREIGN BONDS',
        'SCHEDULE OF INVESTMENTS IN FOREIGN DEBENTURES',
        'SCHEDULE OF INVESTMENTS IN FOREIGN EQUITY SHARES',
        'SCHEDULE OF INVESTMENTS IN FOREIGN PREFERENCE SHARES',
        'SCHEDULE OF INVESTMENTS IN FOREIGN GOVERNMENT SECURITIES',
        'SCHEDULE OF INVESTMENTS IN FOREIGN COMMERCIAL PAPERS',
        'SCHEDULE OF INVESTMENTS IN FOREIGN CERTIFICATES OF DEPOSIT',
        'SCHEDULE OF INVESTMENTS IN FOREIGN TREASURY BILLS',
        'SCHEDULE OF INVESTMENTS IN FOREIGN MONEY MARKET INSTRUMENTS',
        'SCHEDULE OF INVESTMENTS IN FOREIGN DERIVATIVES'
    ]
    
    # First try to find exact matches
    lines = title.split('\n')
    for line in lines:
        line = line.strip().upper()
        for marker in title_markers:
            if marker in line:
                return line.strip()
    
    # If no exact match, try partial matches
    for line in lines:
        line = line.strip().upper()
        for marker in title_markers:
            marker_words = marker.split()
            if all(word in line for word in marker_words):
                return line.strip()
    
    # If still no match, look for financial keywords
    financial_keywords = [
        'ACCOUNT', 'STATEMENT', 'SCHEDULE', 'REPORT', 'BALANCE',
        'INCOME', 'EXPENSE', 'REVENUE', 'ASSET', 'LIABILITY',
        'EQUITY', 'CAPITAL', 'PROFIT', 'LOSS', 'CASH',
        'FLOW', 'FUND', 'INVESTMENT', 'LOAN', 'ADVANCE',
        'RECEIVABLE', 'PAYABLE', 'INVENTORY', 'DEPRECIATION',
        'AMORTIZATION', 'PROVISION', 'RESERVE', 'SURPLUS',
        'DEFICIT', 'BUDGET', 'FORECAST', 'PROJECTION', 'PLAN'
    ]
    
    for line in lines:
        line = line.strip().upper()
        if any(keyword in line for keyword in financial_keywords):
            return line.strip()
    
    # If no specific title found, return first non-empty line
    for line in lines:
        if line.strip():
            return line.strip()
    
    return 'Untitled Table'

def extract_tables_with_titles(pdf_path: str) -> List[Dict[str, Any]]:
    results = []
    scanned = is_scanned_pdf(pdf_path)
    logger.info(f"PDF '{pdf_path}' detected as {'scanned' if scanned else 'digital'}.")
    
    if scanned:
        # Use OCR-based methods for scanned PDFs
        logger.info("Using OCR-based methods (Tesseract and PaddleOCR) for scanned PDF")
        results.extend(extract_tables_tesseract(pdf_path))
        results.extend(extract_tables_paddleocr(pdf_path))
    else:
        # Use digital PDF methods
        logger.info("Using digital PDF methods (pdfplumber and camelot)")
        results.extend(extract_tables_pdfplumber(pdf_path))
        results.extend(extract_tables_camelot(pdf_path))
    
    # Add document name and clean titles
    doc_name = Path(pdf_path).name
    enhanced_results = []
    
    for table in results:
        try:
            # Clean table title
            raw_title = table.get('title', '')
            cleaned_title = clean_title(raw_title)
            
            # Create enhanced table result
            enhanced_table = {
                'title': cleaned_title,
                'page': table.get('page', ''),
                'document': doc_name,
                'type': 'scanned' if scanned else 'digital',
                'data': table.get('data', []),
                'position': table.get('position', ''),
                'content_type': table.get('type', ''),
                'content_description': table.get('content', '')
            }
            enhanced_results.append(enhanced_table)
                
        except Exception as e:
            logger.error(f"Error processing table: {str(e)}")
            # Keep original table if processing fails
            table['title'] = clean_title(table.get('title', ''))
            table['document'] = doc_name
            table['type'] = 'scanned' if scanned else 'digital'
            enhanced_results.append(table)
    
    results = deduplicate_tables(enhanced_results)
    return results

def save_results(all_results: List[Dict[str, Any]], output_dir: Path):
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save CSV with table information
        csv_path = output_dir / 'results.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Table Title', 
                'Page Number', 
                'Document',
                'PDF Type',
                'Position',
                'Content Type',
                'Content Description'
            ])
            writer.writeheader()
            for result in all_results:
                writer.writerow({
                    'Table Title': result.get('title', ''),
                    'Page Number': result.get('page', ''),
                    'Document': result.get('document', ''),
                    'PDF Type': result.get('type', 'unknown'),
                    'Position': result.get('position', ''),
                    'Content Type': result.get('content_type', ''),
                    'Content Description': result.get('content_description', '')
                })
        logger.info(f"CSV results saved to {csv_path}")
        
        # Save JSON with full details
        json_path = output_dir / 'results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON results saved to {json_path}")

    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        raise

def process_file(input_path: Path) -> List[Dict[str, Any]]:
    try:
        results = extract_tables_with_titles(str(input_path))
        logger.info(f"Successfully processed {input_path}")
        return results
    except Exception as e:
        logger.error(f"Error processing {input_path}: {str(e)}")
        return []

def process_directory(input_dir: Path) -> List[Dict[str, Any]]:
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return []
    
    all_results = []
    for pdf_file in pdf_files:
        results = process_file(pdf_file)
        all_results.extend(results)
    
    logger.info(f"Successfully processed {len(pdf_files)} files")
    return all_results

def main():
    input_path = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process all PDF files in input directory
    all_results = process_directory(input_path)
    
    # Save all results
    save_results(all_results, output_dir)

if __name__ == "__main__":
    main() 