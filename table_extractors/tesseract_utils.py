import pytesseract
from PIL import Image
import logging
import os
import tempfile
import fitz  # PyMuPDF
import time

def ocr_image_tesseract(image_path):
    """
    Perform OCR on an image using Tesseract.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Extracted text from the image
    """
    try:
        # Read the image
        image = Image.open(image_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        return text
    except Exception as e:
        logging.error(f"Error performing OCR with Tesseract on {image_path}: {str(e)}")
        return ""

def extract_tables_tesseract(pdf_path):
    """
    Extract tables from a scanned PDF using Tesseract OCR.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dictionaries containing table data and metadata
    """
    try:
        # Open PDF with PyMuPDF
        pdf_document = fitz.open(pdf_path)
        
        tables = []
        for page_num in range(len(pdf_document)):
            # Get page
            page = pdf_document[page_num]
            
            # Convert page to image
            pix = page.get_pixmap()
            img_data = pix.samples
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
            
            # Create a unique temporary file name
            temp_file_path = os.path.join(tempfile.gettempdir(), f'tesseract_temp_{time.time()}_{page_num}.png')
            
            try:
                # Save image to temporary file
                img.save(temp_file_path)
                time.sleep(0.1)  # Small delay to ensure file is written
                
                # Perform OCR
                text = pytesseract.image_to_string(Image.open(temp_file_path))
                
                # Process OCR results to find tables
                lines = text.split('\n')
                rows = []
                current_row = []
                
                for line in lines:
                    line = line.strip()
                    if line:
                        # Split line by multiple spaces to get columns
                        columns = [col.strip() for col in line.split('  ') if col.strip()]
                        if columns:
                            current_row.extend(columns)
                    elif current_row:
                        rows.append(current_row)
                        current_row = []
                
                if current_row:
                    rows.append(current_row)
                
                if rows:
                    tables.append({
                        'data': rows,
                        'page': page_num + 1,
                        'rows': len(rows),
                        'columns': len(rows[0]) if rows else 0,
                        'tool': 'Tesseract'
                    })
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except Exception as e:
                    logging.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")
        
        pdf_document.close()
        return tables
    except Exception as e:
        logging.error(f"Error extracting tables with Tesseract from {pdf_path}: {str(e)}")
        return [] 