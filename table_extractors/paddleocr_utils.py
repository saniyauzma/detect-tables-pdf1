from paddleocr import PaddleOCR
import logging
import os
import tempfile
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import time

def extract_tables_paddleocr(pdf_path):
    """
    Extract tables from a scanned PDF using PaddleOCR.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dictionaries containing table data and metadata
    """
    try:
        # Initialize PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
        
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
            temp_file_path = os.path.join(tempfile.gettempdir(), f'paddleocr_temp_{time.time()}_{page_num}.png')
            
            try:
                # Save image to temporary file
                img.save(temp_file_path)
                time.sleep(0.1)  # Small delay to ensure file is written
                
                # Perform OCR
                result = ocr.ocr(temp_file_path, cls=True)
                
                # Process OCR results to find tables
                if result:
                    # Group text by vertical position to find rows
                    rows = {}
                    for line in result[0]:
                        text = line[1][0]  # Get text
                        box = line[0]  # Get bounding box
                        y_pos = (box[0][1] + box[2][1]) / 2  # Average y position
                        
                        # Group text into rows based on y position
                        found_row = False
                        for row_y in rows:
                            if abs(row_y - y_pos) < 20:  # 20 pixels threshold
                                rows[row_y].append((box[0][0], text))  # Store x position and text
                                found_row = True
                                break
                        if not found_row:
                            rows[y_pos] = [(box[0][0], text)]
                    
                    # Sort rows by y position
                    sorted_rows = []
                    for y_pos in sorted(rows.keys()):
                        # Sort text in row by x position
                        row_text = [text for _, text in sorted(rows[y_pos])]
                        sorted_rows.append(row_text)
                    
                    if sorted_rows:
                        tables.append({
                            'data': sorted_rows,
                            'page': page_num + 1,
                            'rows': len(sorted_rows),
                            'columns': len(sorted_rows[0]) if sorted_rows else 0,
                            'tool': 'PaddleOCR'
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
        logging.error(f"Error extracting tables with PaddleOCR from {pdf_path}: {str(e)}")
        return [] 