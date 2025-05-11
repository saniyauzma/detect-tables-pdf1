import os
import google.generativeai as genai
from pdf2image import convert_from_path
from PIL import Image
import json
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def get_api_key() -> str:
    """Get API key from environment variable"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables.\n"
            "Please create a .env file with your API key or set it in your environment.\n"
            "See .env.example for required variables."
        )
    if api_key == "your_api_key_here":
        raise ValueError(
            "Please replace 'your_api_key_here' in the .env file with your actual Gemini API key.\n"
            "You can get an API key from: https://makersuite.google.com/app/apikey"
        )
    return api_key

def get_pdf_dpi() -> int:
    """Get PDF DPI from environment variable with default"""
    return int(os.getenv("PDF_DPI", "200"))

# Configure Gemini
try:
    genai.configure(api_key=get_api_key())
    model = genai.GenerativeModel("models/gemini-1.5-flash")
except Exception as e:
    raise RuntimeError(
        f"Failed to configure Gemini API: {str(e)}\n"
        "Please check your API key and try again."
    )

def convert_pdf_to_images(pdf_path: str, dpi: int = None) -> List[Image.Image]:
    """Convert PDF to image per page"""
    if dpi is None:
        dpi = get_pdf_dpi()
        
    try:
        return convert_from_path(pdf_path, dpi=dpi)
    except Exception as e:
        raise RuntimeError(f"Error converting PDF to images: {str(e)}")

def extract_table_info(image: Image.Image, page_number: int) -> List[Dict[str, Any]]:
    """Process image with Gemini to extract tables + titles"""
    try:
        prompt = (
            "You are a JSON-only response system. Your task is to analyze this PDF page image and identify tables.\n\n"
            "INSTRUCTIONS:\n"
            "1. Look for any tables in the image\n"
            "2. For each table found, identify its title (text above or near the table)\n"
            "3. If no clear title is found, use 'Unknown' as the title\n\n"
            "RESPONSE FORMAT:\n"
            "You must respond with ONLY a JSON array. No other text or explanation.\n"
            "Example response format:\n"
            '[\n'
            '  {\n'
            '    "title": "Table Title or Unknown",\n'
            '    "page_number": 1\n'
            '  }\n'
            ']\n\n'
            "IMPORTANT:\n"
            "- Respond with ONLY the JSON array\n"
            "- Do not include any other text or explanation\n"
            "- Ensure the JSON is properly formatted\n"
            "- If no tables are found, return an empty array []"
        )

        response = model.generate_content([prompt, image])
        
        if not response.text:
            return [{
                "title": "Unknown",
                "page_number": page_number,
                "error": "Empty response from model"
            }]

        try:
            # Clean the response text to ensure it's valid JSON
            cleaned_text = response.text.strip()
            # Remove any markdown code block indicators if present
            cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(cleaned_text)
            if not isinstance(result, list):
                result = [result]
            
            # Ensure each entry has the correct structure
            for entry in result:
                if "title" not in entry:
                    entry["title"] = "Unknown"
                entry["page_number"] = page_number
            
            return result
        except json.JSONDecodeError as e:
            return [{
                "title": "Unknown",
                "page_number": page_number,
                "error": f"Invalid JSON response: {str(e)}"
            }]

    except Exception as e:
        return [{
            "title": "Unknown",
            "page_number": page_number,
            "error": f"Error processing page: {str(e)}"
        }]

def save_results(results: List[Dict[str, Any]], pdf_path: str) -> None:
    """Save results to both JSON and CSV files in the output directory"""
    try:
        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Save JSON
        json_path = os.path.join(output_dir, f"{base_filename}_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Save CSV
        csv_path = os.path.join(output_dir, f"{base_filename}_{timestamp}.csv")
        df = pd.DataFrame(results)
        df.to_csv(csv_path, index=False, encoding='utf-8')

    except Exception as e:
        raise RuntimeError(f"Error saving results: {str(e)}")

def process_pdf_with_gemini(pdf_path: str) -> List[Dict[str, Any]]:
    """Main workflow for processing PDFs"""
    try:
        # Convert PDF to images
        images = convert_pdf_to_images(pdf_path)
        if not images:
            raise RuntimeError("No images could be extracted from the PDF")
            
        output = []

        for i, img in enumerate(images):
            page_number = i + 1
            try:
                # Process with Gemini
                results = extract_table_info(img, page_number)
                output.extend(results)
            except Exception as e:
                output.append({
                    "title": "Unknown",
                    "page_number": page_number,
                    "error": str(e)
                })
            finally:
                # Clean up image
                img.close()

        # Save results to files
        save_results(output, pdf_path)
        
        return output
    except Exception as e:
        raise RuntimeError(f"Error in main PDF processing workflow: {str(e)}")

if __name__ == "__main__":
    # Example usage: process all PDFs in the input directory
    input_dir = "input"
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files to process.")
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_dir, pdf_file)
        print(f"\nProcessing {pdf_file}...")
        try:
            results = process_pdf_with_gemini(pdf_path)
            print(f"Extracted table info for {pdf_file}: {results}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}") 