"""PDF chapter splitting utility"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def split_pdf_by_chapters(pdf_path, chapters_json, output_dir):
    """Split PDF into chapters based on JSON metadata

    Args:
        pdf_path: Path to source PDF file
        chapters_json: List of chapter dicts with format:
            [
                {"chapter": 1, "name": "Introduction", "start_page": 1, "end_page": 10},
                {"chapter": 2, "name": "Methods", "start_page": 11, "end_page": 25},
                ...
            ]
        output_dir: Directory to save chapter PDFs

    Returns:
        list: List of created file paths
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    created_files = []

    for chapter_info in chapters_json:
        chapter_num = chapter_info.get('chapter', '?')
        chapter_name = chapter_info.get('name') or 'Untitled'  # Handle None explicitly
        start_page = chapter_info.get('start_page', 1)
        end_page = chapter_info.get('end_page', start_page)

        # Validate page numbers
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            print(f"[WARNING] Skipping invalid chapter {chapter_num}: pages {start_page}-{end_page} (PDF has {total_pages} pages)")
            continue

        # Sanitize chapter name for filename
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in chapter_name)
        filename = f"Chapter_{chapter_num}_{safe_name}.pdf"
        output_path = os.path.join(output_dir, filename)

        # Create PDF writer for this chapter
        writer = PdfWriter()

        # Add pages (PyPDF2 uses 0-based indexing)
        for page_num in range(start_page - 1, end_page):
            writer.add_page(reader.pages[page_num])

        # Save chapter PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        created_files.append(output_path)
        print(f"[SPLIT] Chapter {chapter_num}: {chapter_name} → {filename} ({end_page - start_page + 1} pages)")

    return created_files


def sanitize_filename(name):
    """Sanitize string for use as filename"""
    return "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name)


if __name__ == "__main__":
    # Test example
    test_chapters = [
        {"chapter": 1, "name": "Introduction to Biology", "start_page": 1, "end_page": 15},
        {"chapter": 2, "name": "Cell Structure & Function", "start_page": 16, "end_page": 35},
    ]

    print("Test chapters:")
    print(json.dumps(test_chapters, indent=2))
