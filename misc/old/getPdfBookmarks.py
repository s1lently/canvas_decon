#!/usr/bin/env python3
"""Extract PDF chapter bookmarks only"""
import re
from PyPDF2 import PdfReader

pdf_path = 'Courses/chem 110__2405803/Files/Textbook/Chemistry The Central Science in SI Units 15th Global Edition.pdf'

reader = PdfReader(pdf_path)
outlines = reader.outline

def extract_chapters(items):
    """Extract only top-level chapter bookmarks"""
    chapters = []
    for item in items:
        if isinstance(item, list):
            continue  # Skip nested items

        title = item.get('/Title', '')

        # Only chapters (format: "Chapter N: Title")
        if title.startswith('Chapter ') and ':' in title:
            # Get page number
            try:
                page_num = reader.get_destination_page_number(item) + 1
            except:
                page_num = None

            # Parse chapter number and name
            match = re.match(r'Chapter (\d+):\s*(.+)', title)
            if match:
                chapters.append({
                    'chapter': int(match.group(1)),
                    'name': match.group(2),
                    'pdf_page': page_num
                })

    return chapters

chapters = extract_chapters(outlines)
chapters.sort(key=lambda x: x['chapter'])

print(f"{'='*80}")
print(f"Found {len(chapters)} chapters")
print(f"{'='*80}\n")

for ch in chapters:
    print(f"Chapter {ch['chapter']:>2}: {ch['name']:<60} Page {ch['pdf_page']}")

print(f"\n{'='*80}")
print(f"Total PDF pages: {len(reader.pages)}")
print(f"{'='*80}")
