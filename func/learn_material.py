#!/usr/bin/env python3
"""
Learn Material - AI-powered study material analysis
Generates markdown reports for various file types
"""
import os
import sys
import tempfile
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


# Default prompts (主英文 + 专业术语中文对照)
DEFAULT_TEXT_PROMPT = """You are an expert educational assistant (教育助手). Analyze this {file_type} file and create a HIGH-DENSITY learning guide (高信息密度学习指南).

File: {filename}

```{file_type_lower}
{content}
```

**CRITICAL REQUIREMENTS:**
- Write in English with Chinese translations for technical terms (专业术语)
- HIGH information density (高信息密度) - be concise but complete
- Include example (例题) with solution (答案) for EVERY key concept
- If formulas exist, create a formula reference table with ALL symbol definitions

Create a detailed markdown report:

# 📚 {filename}

## Brief Overview (简介)
Provide a dense, information-packed summary covering:
- Core purpose and scope
- Key concepts (核心概念) at a glance
- Main takeaways in 3-5 bullet points

## Formula Reference (公式表)
**Include this section ONLY if formulas/equations exist**

| Formula | Definition | Symbols |
|---------|------------|---------|
| `formula` | Description | `var1`: meaning, `var2`: meaning |

## Main Content (主要内容)

For EACH knowledge point (知识点):

### [Knowledge Point Name]
**Core Concept (核心概念):**
- Dense explanation with technical terms (专业术语中文)

**Example (例题):**
```
[Concrete example problem]
```

**Solution (答案):**
```
[Step-by-step solution with explanations]
```

**Key Notes (注意事项):**
- Important details, edge cases (边界情况), common mistakes (常见错误)

---

[Repeat for all knowledge points]

## Summary (总结)
Provide a HIGH-DENSITY recap:
- Core concepts (核心概念) in condensed form
- Critical formulas (关键公式) or patterns (模式)
- Must-remember points (必记要点)

Format with proper markdown: code blocks, tables, bullet points, emphasis."""

DEFAULT_PDF_PROMPT = """You are an expert educational assistant (教育助手). Analyze this PDF document and create a HIGH-DENSITY learning guide (高信息密度学习指南).

File: {filename}

**CRITICAL REQUIREMENTS:**
- Write in English with Chinese translations for technical terms (专业术语)
- HIGH information density (高信息密度) - be concise but complete
- Include example (例题) with solution (答案) for EVERY key concept
- If formulas exist, create a formula reference table with ALL symbol definitions

Create a detailed markdown report:

# 📚 {filename}

## Brief Overview (简介)
Provide a dense, information-packed summary covering:
- Core topics (主题) and scope
- Key concepts (核心概念) at a glance
- Main takeaways in 3-5 bullet points

## Formula Reference (公式表)
**Include this section ONLY if formulas/equations exist in the document**

| Formula | Definition | Symbols |
|---------|------------|---------|
| `formula` | Description | `var1`: meaning, `var2`: meaning |

## Main Content (主要内容)

For EACH knowledge point (知识点) from the PDF:

### [Knowledge Point Name]
**Core Concept (核心概念):**
- Dense explanation with technical terms (专业术语中文)
- Reference page numbers if important

**Example (例题):**
```
[Concrete example from PDF or create one]
```

**Solution (答案):**
```
[Step-by-step solution with explanations]
```

**Key Notes (注意事项):**
- Important details, diagrams (图表) mentioned, edge cases (边界情况)
- Common mistakes (常见错误) if mentioned in PDF

---

[Repeat for all major knowledge points]

## Summary (总结)
Provide a HIGH-DENSITY recap:
- Core concepts (核心概念) in condensed form
- Critical formulas (关键公式) or theorems (定理)
- Must-remember points (必记要点)
- Important pages (重要页码) to review

Format with proper markdown: code blocks, tables, bullet points, emphasis."""

DEFAULT_CSV_PROMPT = """You are an expert educational assistant (教育助手). Analyze this CSV data file and create a HIGH-DENSITY learning guide (高信息密度学习指南).

File: {filename}

Preview of data:
```csv
{csv_preview}
```

**CRITICAL REQUIREMENTS:**
- Write in English with Chinese translations for technical terms (专业术语)
- HIGH information density (高信息密度) - be concise but complete
- Include example analysis (分析例题) with solution (答案) for key data patterns
- If statistical formulas are used, create a formula reference table

Create a detailed markdown report:

# 📚 {filename}

## Brief Overview (简介)
Provide a dense, information-packed summary covering:
- Dataset purpose and scope
- Column structure (列结构) and data types (数据类型)
- Key insights (关键洞察) in 3-5 bullet points

## Formula Reference (公式表)
**Include this section ONLY if statistical formulas/calculations are relevant**

| Formula | Definition | Symbols |
|---------|------------|---------|
| `formula` | Description | `var`: meaning |

## Main Content (主要内容)

### Data Structure (数据结构)
**Core Concept (核心概念):**
- Detailed column descriptions with types and ranges
- Data quality notes (数据质量), missing values (缺失值)

### [Pattern/Insight 1]
**Core Concept (核心概念):**
- Dense explanation of the pattern (模式) or trend (趋势)

**Example Analysis (分析例题):**
```
[Concrete analysis question about the data]
```

**Solution (答案):**
```
[Step-by-step analysis with calculations/code if applicable]
```

**Key Notes (注意事项):**
- Statistical significance (统计显著性), outliers (异常值), limitations (局限性)

---

[Repeat for other major patterns/insights]

## Summary (总结)
Provide a HIGH-DENSITY recap:
- Core findings (核心发现) in condensed form
- Critical statistics (关键统计) or correlations (相关性)
- Must-remember insights (必记洞察)
- Suggested visualizations (建议可视化)

Format with proper markdown: code blocks, tables, bullet points, emphasis."""


def get_learn_dir(course_dir):
    """Get or create Learn directory for course"""
    learn_dir = os.path.join(course_dir, 'Learn')
    os.makedirs(learn_dir, exist_ok=True)

    reports_dir = os.path.join(learn_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    return learn_dir, reports_dir


def get_default_prompt(file_path):
    """
    Get appropriate default prompt template for file type

    Args:
        file_path: Path to file

    Returns:
        Default prompt template string
    """
    ext = os.path.splitext(file_path)[1].lower()

    # Text files
    text_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs',
                      '.txt', '.md', '.json', '.xml', '.html', '.css', '.sh']

    if ext in text_extensions:
        return DEFAULT_TEXT_PROMPT
    elif ext == '.csv':
        return DEFAULT_CSV_PROMPT
    else:  # PDF and Office files converted to PDF
        return DEFAULT_PDF_PROMPT


def process_text_file(file_path, output_md_path, console=None, custom_prompt=None):
    """
    Process text files (py, js, txt, etc.) with Claude

    Args:
        file_path: Path to input file
        output_md_path: Path to output markdown report
        console: Optional console widget for output
        custom_prompt: Optional custom prompt template (overrides default)
    """
    def log(msg):
        if console:
            console.append(msg)
        else:
            print(msg)

    try:
        from model_selector import get_best_anthropic_model, get_model_display_name
        from upPromptFiles import call_ai

        log(f"📄 Processing text file: {os.path.basename(file_path)}")

        # Get best Claude model
        try:
            best_model = get_best_anthropic_model()
            model_name = get_model_display_name(best_model)
            log(f"✓ Model: {model_name}")
        except Exception as e:
            model_name = 'claude-sonnet-4-20250514'
            log(f"! Fallback model: {model_name}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Detect file type
        ext = os.path.splitext(file_path)[1].lower()
        file_type_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust',
            '.txt': 'Text',
            '.md': 'Markdown',
            '.json': 'JSON',
            '.xml': 'XML',
            '.html': 'HTML',
            '.css': 'CSS',
        }
        file_type = file_type_map.get(ext, 'Code')

        # Generate prompt
        if custom_prompt:
            prompt = custom_prompt.format(
                file_type=file_type,
                filename=os.path.basename(file_path),
                file_type_lower=file_type.lower(),
                content=content
            )
        else:
            prompt = DEFAULT_TEXT_PROMPT.format(
                file_type=file_type,
                filename=os.path.basename(file_path),
                file_type_lower=file_type.lower(),
                content=content
            )

        log("🤖 Generating analysis with Claude...")
        result = call_ai(prompt, 'Claude', model_name)

        # Save report
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(result)

        log(f"✓ Report saved: {output_md_path}")
        return True

    except Exception as e:
        log(f"✗ Error processing text file: {e}")
        import traceback
        log(traceback.format_exc())
        return False


def convert_office_to_pdf(file_path, console=None):
    """
    Convert Office files (docx, pptx, xlsx) to PDF/CSV

    Args:
        file_path: Path to input file
        console: Optional console widget

    Returns:
        Path to converted file, or None if failed
    """
    def log(msg):
        if console:
            console.append(msg)
        else:
            print(msg)

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == '.xlsx':
            # Convert Excel to CSV
            import pandas as pd
            log(f"📊 Converting Excel to CSV...")

            # Read Excel (first sheet)
            df = pd.read_excel(file_path, sheet_name=0)

            # Save as CSV
            output_path = file_path.rsplit('.', 1)[0] + '_converted.csv'
            df.to_csv(output_path, index=False)

            log(f"✓ Converted to CSV: {output_path}")
            return output_path

        elif ext in ['.docx', '.pptx']:
            # Convert to PDF using LibreOffice
            log(f"📄 Converting {ext} to PDF...")

            output_dir = os.path.dirname(file_path)

            # Try LibreOffice command
            try:
                subprocess.run([
                    'soffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', output_dir,
                    file_path
                ], check=True, capture_output=True, timeout=60)

                output_path = file_path.rsplit('.', 1)[0] + '.pdf'
                if os.path.exists(output_path):
                    log(f"✓ Converted to PDF: {output_path}")
                    return output_path
                else:
                    log("! Conversion succeeded but PDF not found")
                    return None

            except FileNotFoundError:
                log("! LibreOffice not found - trying python-docx fallback")

                if ext == '.docx':
                    # Fallback: Extract text from docx
                    from docx import Document
                    doc = Document(file_path)

                    text_output = file_path.rsplit('.', 1)[0] + '_extracted.txt'
                    with open(text_output, 'w', encoding='utf-8') as f:
                        for para in doc.paragraphs:
                            f.write(para.text + '\n')

                    log(f"✓ Extracted text: {text_output}")
                    return text_output
                else:
                    log("! No fallback available for pptx")
                    return None

    except Exception as e:
        log(f"✗ Conversion failed: {e}")
        import traceback
        log(traceback.format_exc())
        return None


def process_pdf_or_csv(file_path, output_md_path, console=None, custom_prompt=None):
    """
    Process PDF or CSV files with Gemini

    Args:
        file_path: Path to input file (PDF or CSV)
        output_md_path: Path to output markdown report
        console: Optional console widget
        custom_prompt: Optional custom prompt template (overrides default)
    """
    def log(msg):
        if console:
            console.append(msg)
        else:
            print(msg)

    try:
        from model_selector import get_best_gemini_model, get_model_display_name
        from upPromptFiles import upload_files, call_ai

        ext = os.path.splitext(file_path)[1].lower()
        log(f"📄 Processing {ext.upper()} file: {os.path.basename(file_path)}")

        # Get best Gemini model
        try:
            best_model = get_best_gemini_model()
            model_name = get_model_display_name(best_model)
            log(f"✓ Model: {model_name}")
        except Exception as e:
            model_name = 'gemini-2.0-flash-exp'
            log(f"! Fallback model: {model_name}")

        # Upload file
        log("📤 Uploading file to Gemini...")
        uploaded_info = upload_files([file_path], 'Gemini')

        # Generate prompt
        if custom_prompt:
            # For custom prompts, check if it needs csv_preview
            if ext == '.csv' and '{csv_preview}' in custom_prompt:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    csv_preview = f.read(5000)
                prompt = custom_prompt.format(
                    filename=os.path.basename(file_path),
                    csv_preview=csv_preview
                )
            else:
                prompt = custom_prompt.format(filename=os.path.basename(file_path))
        else:
            # Use default prompts
            if ext == '.pdf':
                prompt = DEFAULT_PDF_PROMPT.format(filename=os.path.basename(file_path))
            else:  # CSV
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    csv_preview = f.read(5000)
                prompt = DEFAULT_CSV_PROMPT.format(
                    filename=os.path.basename(file_path),
                    csv_preview=csv_preview
                )

        log("🤖 Generating analysis with Gemini...")
        result = call_ai(prompt, 'Gemini', model_name, uploaded_info=uploaded_info)

        # Save report
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(result)

        log(f"✓ Report saved: {output_md_path}")
        return True

    except Exception as e:
        log(f"✗ Error processing file: {e}")
        import traceback
        log(traceback.format_exc())
        return False


def learn_material(file_path, course_dir, console=None, custom_prompt=None):
    """
    Main entry point: Analyze any study material and generate markdown report

    Workflow:
    1. Detect file type
    2. For text files (py, js, etc.) → Use Claude directly
    3. For Office files (docx, pptx, xlsx) → Convert to PDF/CSV first
    4. For PDF/CSV → Use Gemini with file upload
    5. Save report to Learn/reports/

    Args:
        file_path: Path to input file
        course_dir: Course directory (e.g., Courses/course_name)
        console: Optional console widget
        custom_prompt: Optional custom prompt template (overrides default)

    Returns:
        Path to generated report, or None if failed
    """
    def log(msg):
        if console:
            console.append(msg)
        else:
            print(msg)

    try:
        # Setup directories
        learn_dir, reports_dir = get_learn_dir(course_dir)

        # Generate output filename
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_md_path = os.path.join(reports_dir, f"{base_name}.md")

        log(f"=" * 80)
        log(f"📚 Learn Material: {os.path.basename(file_path)}")
        log(f"=" * 80)

        ext = os.path.splitext(file_path)[1].lower()

        # Text files → Claude
        text_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs',
                          '.txt', '.md', '.json', '.xml', '.html', '.css', '.sh']

        if ext in text_extensions:
            log("📝 Text file detected → Using Claude")
            success = process_text_file(file_path, output_md_path, console, custom_prompt)

        # Office files → Convert first
        elif ext in ['.docx', '.pptx', '.xlsx']:
            log(f"📄 Office file detected → Converting to {'PDF' if ext != '.xlsx' else 'CSV'}")
            converted_path = convert_office_to_pdf(file_path, console)

            if converted_path:
                log(f"✓ Conversion successful → Processing with Gemini")
                success = process_pdf_or_csv(converted_path, output_md_path, console, custom_prompt)

                # Cleanup temporary converted file if different from original
                if converted_path != file_path and '_converted' in converted_path:
                    try:
                        os.unlink(converted_path)
                        log("✓ Cleaned up temporary file")
                    except:
                        pass
            else:
                log("✗ Conversion failed")
                success = False

        # PDF/CSV → Gemini directly
        elif ext in ['.pdf', '.csv']:
            log("📄 PDF/CSV file detected → Using Gemini")
            success = process_pdf_or_csv(file_path, output_md_path, console, custom_prompt)

        else:
            log(f"✗ Unsupported file type: {ext}")
            log(f"  Supported: {', '.join(text_extensions + ['.docx', '.pptx', '.xlsx', '.pdf', '.csv'])}")
            return None

        if success:
            log(f"\n{'=' * 80}")
            log(f"✅ Learning guide generated successfully!")
            log(f"📄 Report: {output_md_path}")
            log(f"{'=' * 80}")
            return output_md_path
        else:
            return None

    except Exception as e:
        log(f"✗ Error: {e}")
        import traceback
        log(traceback.format_exc())
        return None


def load_from_decon(course_dir, console=None):
    """
    Load all decon chapter PDFs to Learn directory

    Args:
        course_dir: Course directory
        console: Optional console widget

    Returns:
        List of copied file paths
    """
    def log(msg):
        if console:
            console.append(msg)
        else:
            print(msg)

    try:
        import shutil

        learn_dir, _ = get_learn_dir(course_dir)
        decon_dir = os.path.join(course_dir, 'Files', 'Textbook', 'decon')

        if not os.path.exists(decon_dir):
            log(f"! No decon directory found: {decon_dir}")
            return []

        log(f"📚 Loading decon chapters to Learn...")
        log(f"Source: {decon_dir}")
        log(f"Target: {learn_dir}")

        # Find all chapter PDFs
        chapter_pdfs = sorted([
            f for f in os.listdir(decon_dir)
            if f.startswith('Chapter_') and f.endswith('.pdf')
        ])

        if not chapter_pdfs:
            log(f"! No chapter PDFs found in decon directory")
            return []

        log(f"Found {len(chapter_pdfs)} chapters")

        # Copy files
        copied_files = []
        for pdf in chapter_pdfs:
            src = os.path.join(decon_dir, pdf)
            dst = os.path.join(learn_dir, pdf)

            shutil.copy2(src, dst)
            copied_files.append(dst)
            log(f"  ✓ {pdf}")

        log(f"\n✓ Loaded {len(copied_files)} chapters to Learn directory")
        return copied_files

    except Exception as e:
        log(f"✗ Error loading from decon: {e}")
        import traceback
        log(traceback.format_exc())
        return []


if __name__ == '__main__':
    # Test
    import sys

    if len(sys.argv) < 3:
        print("Usage: python learn_material.py <file_path> <course_dir>")
        sys.exit(1)

    file_path = sys.argv[1]
    course_dir = sys.argv[2]

    result = learn_material(file_path, course_dir)

    if result:
        print(f"\nSuccess! Report: {result}")
    else:
        print("\nFailed to generate report")
