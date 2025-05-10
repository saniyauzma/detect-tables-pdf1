from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
import os
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
from table_extractors.gemini_utils import (
    extract_tables_gemini,
    clean_table_title,
    validate_table_data,
    classify_table
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file from same directory as this script
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY not found in .env file!")

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

    title_markers = [
        'BALANCE SHEET',
        'PROFIT AND LOSS ACCOUNT',
        'CASH FLOW STATEMENT',
        'NOTES TO ACCOUNTS',
        'SIGNIFICANT ACCOUNTING POLICIES',
        'RELATED PARTY TRANSACTIONS',
        'REVENUE FROM OPERATIONS',
        'EXPENDITURE IN FOREIGN CURRENCY',
        'SHAREHOLDERS INFORMATION',
        'DIRECTORS REPORT',
        'AUDITORS REPORT'
    ]

    lines = title.split('\n')

    for line in lines:
        for marker in title_markers:
            if marker in line.upper():
                return line.strip()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) > 60:
            continue
        if 'March' in line and ('2021' in line or '2022' in line):
            continue
        if line.replace('.', '').replace(',', '').replace(' ', '').isdigit():
            continue
        if len(line.split()) <= 1:
            continue
        if all(c in '-~' for c in line):
            continue
        if 'HYBRID SEEDS' in line.upper():
            continue
        if (line.isupper() or
            line.endswith(':') or
            line.startswith('Note') or
            line.startswith('Schedule') or
            'Statement' in line or
            'Report' in line or
            'Particulars' in line or
            'Details' in line or
            'Description' in line or
            'Transaction' in line or
            'Revenue' in line or
            'Expenditure' in line or
            'Profit' in line or
            'Loss' in line):
            return line

    return 'Untitled Table'

def extract_tables_with_titles(pdf_path: str) -> List[Dict[str, Any]]:
    results = []
    scanned = is_scanned_pdf(pdf_path)
    logger.info(f"PDF '{pdf_path}' detected as {'scanned' if scanned else 'digital'}.")

    # Try Gemini API first
    try:
        logger.info("Attempting table extraction with Gemini API")
        gemini_results = extract_tables_gemini(pdf_path)
        if gemini_results:
            results.extend(gemini_results)
            logger.info(f"Successfully extracted {len(gemini_results)} tables using Gemini API")
    except Exception as e:
        logger.warning(f"Gemini API extraction failed: {str(e)}")

    # Fallback to other methods if Gemini didn't find tables
    if not results:
        if scanned:
            results.extend(extract_tables_tesseract(pdf_path))
            results.extend(extract_tables_paddleocr(pdf_path))
        else:
            results.extend(extract_tables_pdfplumber(pdf_path))
            results.extend(extract_tables_camelot(pdf_path))

    doc_name = Path(pdf_path).name
    for r in results:
        if 'data' in r and r['data']:
            if 'title' in r:
                r['title'] = clean_table_title(r['title'], '')
            validation = validate_table_data(r['data'])
            if 'validation' in validation:
                r['validation'] = validation['validation']
            classification = classify_table(r['data'])
            if 'classification' in classification:
                r['classification'] = classification['classification']
        r['document'] = doc_name

    results = [r for r in results if r.get('title') and r['title'] != 'Untitled Table']
    results = deduplicate_tables(results)
    return results

def save_results(all_results: List[Dict[str, Any]], output_dir: Path):
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / 'doc3_results.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Table Title', 'Page Number', 'Document', 'Table Type', 'Validation'])
            writer.writeheader()
            for result in all_results:
                writer.writerow({
                    'Table Title': result.get('title', ''),
                    'Page Number': result.get('page', ''),
                    'Document': result.get('document', ''),
                    'Table Type': result.get('classification', '').split('\n')[0] if 'classification' in result else '',
                    'Validation': result.get('validation', '').split('\n')[0] if 'validation' in result else ''
                })
        logger.info(f"CSV results saved to {csv_path}")

        json_path = output_dir / 'doc3_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON results saved to {json_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        raise

def main():
    input_path = Path(INPUT_DIR) / 'Document3.pdf'
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = extract_tables_with_titles(str(input_path))
    save_results(results, output_dir)

if __name__ == "__main__":
    main()
