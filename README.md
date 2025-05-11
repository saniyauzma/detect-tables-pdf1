# PDF Table Title Extractor

A simple Python script that uses Google's Gemini API to extract table titles from PDF documents.

## Features

- Extracts table titles from PDF documents
- Works with both digital and scanned PDFs
- Saves results in both JSON and CSV formats
- Handles multiple tables per page
- Provides confidence levels for extracted titles

## Requirements

- Python 3.8+
- Google Gemini API key
- Poppler (for PDF processing)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Poppler:
   - Windows: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - Linux: `sudo apt-get install poppler-utils`
   - macOS: `brew install poppler`

4. Create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_api_key_here
   PDF_DPI=200
   ```

## Usage

1. Place your PDF files in the `input` directory.

2. Run the script:
   ```bash
   python gemini_table_titles.py
   ```

3. Results will be saved in the `output` directory:
   - JSON file: Contains all extracted table information
   - CSV file: Contains the same data in tabular format

## Output Format

### JSON Output
```json
[
  {
    "title": "Table Title",
    "page_number": 1,
    "confidence": "high"
  }
]
```

### CSV Output
- title: The extracted table title
- page_number: The page number where the table was found
- confidence: Confidence level of the extraction (high/medium/low)

## Error Handling

- If a table title cannot be extracted, it will be marked as "Unknown"
- Errors during processing are logged and included in the output
- The script continues processing even if some pages fail

## License

MIT License 