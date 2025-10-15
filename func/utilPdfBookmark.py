#!/usr/bin/env python3
"""Extract and validate PDF chapter bookmarks for Decon Textbook"""
import re
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter


def repair_pdf_references(pdf_path, console=None):
    """
    Repair PDF object references to prevent thousands of repair warnings.

    This fixes "Object ID X,0 ref repaired" warnings that can occur when
    splitting PDFs with broken references. Uses pikepdf for robust repair.

    Args:
        pdf_path: Path to source PDF
        console: Optional console widget for output

    Returns:
        Path to repaired PDF (temporary file), or original path if repair fails
    """
    def log(msg):
        if console:
            console.append(msg)
        else:
            print(msg)

    try:
        log("🔧 Repairing PDF references...")

        # Try pikepdf first (more robust)
        try:
            import pikepdf

            # Open and save (pikepdf auto-repairs structure)
            temp_fd, temp_path = tempfile.mkstemp(suffix='_repaired.pdf')
            os.close(temp_fd)

            with pikepdf.open(pdf_path, allow_overwriting_input=False) as pdf:
                pdf.save(temp_path)

            log(f"✓ PDF repaired with pikepdf: {os.path.getsize(temp_path) // 1024} KB")
            return temp_path

        except ImportError:
            log("! pikepdf not available, trying PyPDF2...")

            # Fallback to PyPDF2
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            temp_fd, temp_path = tempfile.mkstemp(suffix='_repaired.pdf')
            os.close(temp_fd)

            with open(temp_path, 'wb') as f:
                writer.write(f)

            log(f"✓ PDF repaired with PyPDF2: {os.path.getsize(temp_path) // 1024} KB")
            return temp_path

    except Exception as e:
        log(f"! PDF repair failed: {e}")
        log("! Using original PDF (may see reference warnings)")
        return pdf_path


def extract_chapters_from_bookmarks(pdf_path, total_pages):
    """
    Extract chapter structure from PDF bookmarks with continuity validation.

    Rules:
    1. Only accept chapters starting from 1 with continuous numbering
    2. If any discontinuity found, stop and return None (fall back to AI)
    3. Calculate end_page as next_chapter_start - 1
    4. Last chapter end_page = total PDF pages

    Args:
        pdf_path: Path to PDF file
        total_pages: Total pages in PDF

    Returns:
        List of chapter dicts with format:
        [
            {
                "chapter_number": 1,
                "chapter_name": "Introduction",
                "start_page": 48,
                "end_page": 90
            },
            ...
        ]
        Returns None if no valid continuous chapters found
    """
    try:
        reader = PdfReader(pdf_path)
        outlines = reader.outline

        if not outlines:
            return None

        # Extract all chapter bookmarks
        raw_chapters = []
        for item in outlines:
            if isinstance(item, list):
                continue  # Skip nested items

            title = item.get('/Title', '')

            # Only chapters (format: "Chapter N: Title")
            if title.startswith('Chapter ') and ':' in title:
                try:
                    page_num = reader.get_destination_page_number(item) + 1
                except:
                    continue

                # Parse chapter number and name
                match = re.match(r'Chapter (\d+):\s*(.+)', title)
                if match:
                    raw_chapters.append({
                        'chapter': int(match.group(1)),
                        'name': match.group(2).strip(),
                        'pdf_page': page_num
                    })

        if not raw_chapters:
            return None

        # Sort by chapter number
        raw_chapters.sort(key=lambda x: x['chapter'])

        # Validate: must start from 1 and be continuous
        if raw_chapters[0]['chapter'] != 1:
            return None  # Must start from Chapter 1

        # Check continuity
        valid_chapters = []
        for i, ch in enumerate(raw_chapters):
            expected_num = i + 1
            if ch['chapter'] != expected_num:
                # Discontinuity found - stop here
                break
            valid_chapters.append(ch)

        if not valid_chapters:
            return None

        # Build final chapter structure with end_page
        chapters = []
        for i, ch in enumerate(valid_chapters):
            start_page = ch['pdf_page']

            # Calculate end_page
            if i + 1 < len(valid_chapters):
                end_page = valid_chapters[i + 1]['pdf_page'] - 1
            else:
                end_page = total_pages

            chapters.append({
                'chapter_number': ch['chapter'],
                'chapter_name': ch['name'],
                'start_page': start_page,
                'end_page': end_page
            })

        return chapters

    except Exception as e:
        # On any error, return None to fall back to AI
        return None


def format_bookmark_chapters(chapters):
    """Format bookmark chapters for console output"""
    if not chapters:
        return "No valid bookmark chapters found"

    lines = []
    lines.append("=" * 80)
    lines.append(f"Extracted {len(chapters)} chapters from bookmarks")
    lines.append("=" * 80)
    lines.append("")

    for ch in chapters:
        lines.append(
            f"Chapter {ch['chapter_number']:>2}: {ch['chapter_name']:<50} "
            f"Pages {ch['start_page']:>4}-{ch['end_page']:<4}"
        )

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


if __name__ == '__main__':
    # Test with Chemistry PDF
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    pdf_path = 'Courses/chem 110__2405803/Files/Textbook/Chemistry The Central Science in SI Units 15th Global Edition.pdf'

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    chapters = extract_chapters_from_bookmarks(pdf_path, total_pages)

    if chapters:
        print(format_bookmark_chapters(chapters))

        # Output JSON format
        import json
        print("\nJSON Output:")
        print(json.dumps(chapters, indent=2, ensure_ascii=False))
    else:
        print("No valid continuous chapters found - would fall back to AI analysis")
