"""CourseDetail Window Handler - Manages CourseDetail window (17 methods)"""
import sys, os, json, threading, re, tempfile
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt
from bs4 import BeautifulSoup
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import config
from gui.qt_utils.base_handler import BaseHandler
from gui.details.mgrCourseDetail import CourseDetailManager
from gui.learn.rdrLearnSitting import LearnSittingWidget
from gui.widgets import rdrDelegates as delegates
from gui.learn import utilFormatters as formatters


class CourseDetailWindowHandler(BaseHandler):
    """Handles CourseDetail window operations"""

    def open(self):
        """Open course detail window"""
        ci, ii = self.main_window.categoryList.currentRow(), self.main_window.itemList.currentRow()
        if ci != 0:
            return QMessageBox.warning(self.app, "Invalid", "Please select a Course first.")
        if ii < 0:
            return QMessageBox.warning(self.app, "No Selection", "Please select a course first.")
        courses = self.dm.get('courses')
        if ii >= len(courses):
            return QMessageBox.warning(self.app, "Error", "Invalid course selection.")
        self.app.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'), self.dm.get('history_todos'))
        self.populate_window()
        self.stacked_widget.setCurrentWidget(self.course_detail_window)

    def populate_window(self):
        """Populate CourseDetail window"""
        if not self.course_detail_mgr:
            return
        cdw = self.course_detail_window
        try:
            cdw.categoryList.currentRowChanged.disconnect()
            cdw.itemList.currentRowChanged.disconnect()
        except:
            pass
        cdw.courseNameLabel.setText(self.course_detail_mgr.get_course_name())
        for w in [cdw.categoryList, cdw.itemList, cdw.detailView]:
            w.clear()
        categories = self.course_detail_mgr.get_categories()
        cdw.categoryList.addItems(categories)
        cdw.categoryList.currentRowChanged.connect(self.on_category_changed)
        cdw.itemList.currentRowChanged.connect(self.on_item_changed)
        self.prefetch_all_tabs()
        if categories:
            cdw.categoryList.setCurrentRow(0)
            cdw.categoryList.setFocus()

    def on_category_changed(self, index):
        """Handle category selection change"""
        if index < 0 or not self.course_detail_mgr:
            return
        cdw = self.course_detail_window
        cdw.itemList.clear()
        cdw.detailView.clear()
        category = cdw.categoryList.item(index).text()
        cdw.openTextbookFolderBtn.setVisible(category == 'Textbook')
        cdw.deconTextbookBtn.setVisible(category == 'Textbook')
        cdw.loadFromDeconBtn.setVisible(category == 'Learn')
        cdw.learnMaterialBtn.setVisible(category == 'Learn')

        # Special handling for Textbook category: show 3-tab sitting widget
        if category == 'Textbook':
            if self.app.learn_sitting_widget:
                cdw.detailView.setParent(None)
                self.app.learn_sitting_widget.setParent(None)
                self.app.learn_sitting_widget.deleteLater()
                self.app.learn_sitting_widget = None

            self.app.learn_sitting_widget = LearnSittingWidget(self.app, self.course_detail_mgr, cdw)
            layout = cdw.centralwidget.layout().itemAt(1).layout()
            layout.removeWidget(cdw.detailView)
            cdw.detailView.setVisible(False)
            layout.addWidget(self.app.learn_sitting_widget)
            cdw.itemList.setVisible(False)
            return
        else:
            if self.app.learn_sitting_widget:
                layout = cdw.centralwidget.layout().itemAt(1).layout()
                layout.removeWidget(self.app.learn_sitting_widget)
                self.app.learn_sitting_widget.setParent(None)
                self.app.learn_sitting_widget.deleteLater()
                self.app.learn_sitting_widget = None
                cdw.detailView.setVisible(True)
                layout.addWidget(cdw.detailView)
            cdw.itemList.setVisible(True)

        items = self.course_detail_mgr.get_items_for_category(category)
        for item_data in items:
            item = QListWidgetItem(item_data['name'])
            item.setData(Qt.ItemDataRole.UserRole, item_data.get('has_file', False))
            item.setData(Qt.ItemDataRole.UserRole + 1, item_data)
            if item_data.get('is_done', False):
                item.setForeground(Qt.GlobalColor.gray)
            cdw.itemList.addItem(item)
        cdw.itemList.setItemDelegate(delegates.FileItemDelegate(cdw.itemList) if category in ['Syllabus', 'Textbook', 'Learn'] else QStyledItemDelegate())
        cdw.itemList.viewport().update()

    def on_item_changed(self, index):
        """Handle item selection change"""
        if index < 0 or not self.course_detail_mgr:
            return
        cdw = self.course_detail_window
        item_data = cdw.itemList.item(index).data(Qt.ItemDataRole.UserRole + 1)
        if not item_data:
            return
        item_type, data = item_data.get('type'), item_data.get('data')
        if item_type == 'tab':
            tab_name, url = data.get('tab_name'), data.get('url')
            if tab_name and url:
                self.load_or_fetch_tab(tab_name, url)
            return
        html_map = {
            'intro': lambda: formatters.format_course(data),
            'todo': lambda: formatters.format_todo(data),
            'syllabus': lambda: f"<h2 style='color: #22c55e;'>Syllabus</h2><p><a href='{data['url']}'>{data['url']}</a></p><p>Folder: {data['local_dir']}</p>",
            'textbook_file': lambda: f"<h2>{data['filename']}</h2><p>{data['path']}</p>",
            'learn_file': lambda: f"<h2 style='color: #3b82f6;'>📚 {data['filename']}</h2><p><strong>Path:</strong> {data['path']}</p>" +
                                 (f"<p><strong>Report:</strong> <a href='file://{data['report_path']}'>{os.path.basename(data['report_path'])}</a> ✅</p>" if data.get('report_path') else
                                  "<p><strong>Report:</strong> Not generated yet. Click 'Learn This Material' to generate.</p>"),
            'placeholder': lambda: f"<p>No files</p><p>Folder: {data['folder']}</p>"
        }
        cdw.detailView.setHtml(html_map.get(item_type, lambda: "<p>No details</p>")())

    def on_item_double_clicked(self, item):
        """Handle double-click on item"""
        if not self.course_detail_mgr:
            return
        item_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if not item_data:
            return
        item_type, data = item_data.get('type'), item_data.get('data')
        if item_type == 'syllabus' and item_data.get('has_file'):
            syll_dir = data.get('local_dir')
            if syll_dir and os.path.exists(syll_dir):
                self.app._open_folder(syll_dir)
        elif item_type == 'textbook_file':
            file_path = data.get('path')
            if file_path and os.path.exists(file_path):
                self.app._open_folder(os.path.dirname(file_path))

    def on_open_syllabus_folder_clicked(self):
        """Open syllabus folder"""
        if not self.course_detail_mgr:
            return
        self.app._open_folder(self.course_detail_mgr.get_syll_dir())

    def on_open_textbook_folder_clicked(self):
        """Open textbook folder"""
        if not self.course_detail_mgr:
            return
        self.app._open_folder(self.course_detail_mgr.get_textbook_dir())

    def on_decon_textbook_clicked(self):
        """Decon textbook PDFs using LLM - analyze chapters and split PDF"""
        if not self.course_detail_mgr:
            return QMessageBox.warning(self.course_detail_window, "Error", "No course selected.")

        textbook_dir = self.course_detail_mgr.get_textbook_dir()
        if not os.path.exists(textbook_dir):
            return QMessageBox.warning(self.course_detail_window, "Error", "Textbook folder does not exist.")

        pdf_files = [f for f in os.listdir(textbook_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return QMessageBox.warning(self.course_detail_window, "Error", "No PDF files found in Textbook folder.")

        selected_file, ok = QInputDialog.getItem(
            self.course_detail_window,
            "Select Textbook",
            "Choose a PDF to decon:",
            pdf_files,
            0,
            False
        )
        if not ok or not selected_file:
            return

        reply = QMessageBox.question(
            self.course_detail_window,
            "Decon Textbook",
            f"This will:\n"
            f"1. Analyze chapter structure using Gemini AI\n"
            f"2. Split PDF into individual chapter files\n"
            f"3. Save to: {textbook_dir}/decon/\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path = os.path.join(textbook_dir, selected_file)

        def run_decon(console, progress):
            try:
                progress.update_progress(1, 7, "Step 1/7: Selecting model...")

                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'func'))
                from utilPromptFiles import upload_files, call_ai
                from utilModelSelector import get_best_gemini_model, get_model_display_name
                from utilPdfSplitter import split_pdf_by_chapters
                from utilPdfBookmark import extract_chapters_from_bookmarks, format_bookmark_chapters, repair_pdf_references
                from PyPDF2 import PdfReader, PdfWriter
                from gui.learn.cfgLearnPrefs import get_product, get_model as get_pref_model

                # Get user's model preference from Learn Preferences
                pref_product = get_product()
                pref_model = get_pref_model()

                # Resolve model based on preferences
                try:
                    if pref_product == 'Auto' or pref_model == 'Auto':
                        # Auto mode: use best available Gemini model
                        best_model = get_best_gemini_model()
                        model_name = get_model_display_name(best_model)
                        console.append(f"✓ Model: {model_name} (Auto-selected)")
                    elif pref_product == 'Gemini':
                        # Use user-selected Gemini model
                        model_name = pref_model
                        console.append(f"✓ Model: {model_name} (User-selected)")
                    else:
                        # Decon only supports Gemini, fallback to best Gemini
                        console.append(f"! Decon requires Gemini, but {pref_product} selected in preferences")
                        best_model = get_best_gemini_model()
                        model_name = get_model_display_name(best_model)
                        console.append(f"✓ Using Gemini fallback: {model_name}")
                except Exception as e:
                    console.append(f"[ERROR] Failed to select model: {e}")
                    console.append("Please check your Gemini API key in Settings")
                    return

                progress.update_progress(2, 7, "Step 2/7: Loading PDF...")
                reader = PdfReader(file_path)
                total_pages = len(reader.pages)
                console.append(f"✓ PDF has {total_pages} pages")

                repaired_pdf_path = None

                console.append("\n📖 Checking for embedded bookmarks...")
                all_chapters = extract_chapters_from_bookmarks(file_path, total_pages)

                if all_chapters:
                    console.append("✓ Found valid chapter bookmarks (continuous from Chapter 1)")
                    console.append(format_bookmark_chapters(all_chapters))
                    console.append("\n⚡ Skipping AI analysis - using bookmark data")

                    console.append("")
                    repaired_pdf_path = repair_pdf_references(file_path, console)

                    if repaired_pdf_path and repaired_pdf_path != file_path:
                        reader = PdfReader(repaired_pdf_path)
                        pdf_to_split = repaired_pdf_path
                    else:
                        pdf_to_split = file_path

                    all_chapters = [
                        {
                            'chapter': ch['chapter_number'],
                            'name': ch['chapter_name'],
                            'start_page': ch['start_page'],
                            'end_page': ch['end_page']
                        }
                        for ch in all_chapters
                    ]

                else:
                    console.append("! No valid bookmarks found - falling back to AI analysis")
                    pdf_to_split = file_path

                    TOC_PAGES = min(80, total_pages)
                    writer = PdfWriter()
                    for i in range(TOC_PAGES):
                        writer.add_page(reader.pages[i])

                    temp_toc_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='_toc.pdf')
                    writer.write(temp_toc_pdf)
                    temp_toc_pdf.close()
                    console.append(f"✓ Extracted first {TOC_PAGES} pages")

                    progress.update_progress(3, 7, "Step 3/7: Analyzing TOC...")
                    uploaded_info = upload_files([temp_toc_pdf.name], 'Gemini')
                    
                    # Callback for status updates (e.g. 429 retries)
                    status_cb = lambda msg: console.append(msg)

                    toc_prompt = """Analyze this textbook PDF (first 80 pages) and extract the Table of Contents.

Your task has TWO CRITICAL STEPS:

STEP 1: Read the Table of Contents
- Find all chapter entries with page numbers
- Record what page number the TOC says each chapter starts on

STEP 2: Find the ACTUAL start of Chapter 1
- Scroll through the PDF to find where Chapter 1 ACTUALLY begins
- Look for the actual chapter title page (e.g., "Chapter 1: Introduction")
- Note which PDF page number this is (count from the start of THIS file)
- This is critical because the book may have covers, prefaces, etc. before Chapter 1

STEP 3: Calculate delta
- delta = (book_page_of_chapter_1 - pdf_page_where_chapter_1_actually_starts)
- Example: If TOC says "Chapter 1, Page 1" but Chapter 1 title appears on PDF page 17:
  delta = 1 - 17 = -16

Return ONLY a valid JSON object:
{
  "delta": -16,
  "chapter_1_pdf_page": 17,
  "chapter_1_book_page": 1,
  "chapters": [
    {"chapter": 1, "name": "Introduction", "book_page": 1},
    {"chapter": 2, "name": "Cell Biology", "book_page": 25}
  ]
}

CRITICAL RULES:
1. "delta" MUST be calculated from the ACTUAL Chapter 1 title page, NOT just the TOC entry
2. "chapter_1_pdf_page": The PDF page number where Chapter 1 ACTUALLY starts (for verification)
3. "chapter_1_book_page": What page number the TOC says Chapter 1 starts on (usually 1)
4. "chapters": ONLY include chapters with actual page numbers. Skip "online", "web", or numberless entries
5. Return ONLY the JSON object, no markdown, no explanations"""

                    result = call_ai(toc_prompt, 'Gemini', model_name, uploaded_info=uploaded_info, status_callback=status_cb)
                    os.unlink(temp_toc_pdf.name)

                    progress.update_progress(4, 7, "Step 4/7: Parsing TOC...")
                    result_clean = result.strip()
                    if result_clean.startswith('```'):
                        lines = result_clean.split('\n')
                        result_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_clean

                    try:
                        toc_data = json.loads(result_clean)
                    except json.JSONDecodeError as e:
                        console.append(f"[ERROR] JSON parse failed: {e}")
                        console.append(f"Raw: {result_clean[:300]}...")
                        raise

                    delta = toc_data.get('delta', 0)
                    toc_chapters = toc_data.get('chapters', [])

                    ch1_pdf = toc_data.get('chapter_1_pdf_page')
                    ch1_book = toc_data.get('chapter_1_book_page')

                    if ch1_pdf and ch1_book:
                        expected_delta = ch1_book - ch1_pdf
                        if expected_delta != delta:
                            console.append(f"! Delta verification failed:")
                            console.append(f"  AI reported delta={delta}")
                            console.append(f"  But Chapter 1: book_page={ch1_book}, pdf_page={ch1_pdf}")
                            console.append(f"  Expected delta={expected_delta}")
                            console.append(f"  → Auto-correcting to delta={expected_delta}")
                            delta = expected_delta
                        else:
                            console.append(f"✓ Delta verified: {delta} (Ch1: book_p{ch1_book} = pdf_p{ch1_pdf})")
                        console.append(f"✓ Found {len(toc_chapters)} chapters from TOC")
                    else:
                        console.append(f"✓ Found {len(toc_chapters)} chapters from TOC, delta={delta}")
                        if toc_chapters:
                            first_ch = toc_chapters[0]
                            if first_ch.get('chapter') == 1:
                                predicted_pdf_page = first_ch.get('book_page', 1) - delta
                                console.append(f"  → Predicted Chapter 1 at PDF page {predicted_pdf_page}")
                                console.append(f"  ! Please verify this is correct (check if off by ~16-17 pages)")

                    progress.update_progress(5, 7, "Step 5/7: Converting to PDF pages...")
                    all_chapters = []
                    last_toc_book_page = 0

                    for ch in toc_chapters:
                        book_page = ch.get('book_page', 0)
                        pdf_start = book_page - delta
                        last_toc_book_page = max(last_toc_book_page, book_page)

                        all_chapters.append({
                            'chapter': ch.get('chapter'),
                            'name': ch.get('name'),
                            'start_page': pdf_start,
                            'end_page': None
                        })

                    scan_start_book_page = last_toc_book_page + 50
                    scan_start_pdf_page = scan_start_book_page - delta

                    console.append(f"✓ Converted {len(all_chapters)} chapters")
                    console.append(f"  Last TOC book page: {last_toc_book_page} → PDF page {last_toc_book_page - delta}")

                    remaining_pages = total_pages - scan_start_pdf_page
                    if remaining_pages > 0 and remaining_pages < 500:
                        console.append(f"\n! Scanning {remaining_pages} remaining pages (from PDF page {scan_start_pdf_page})...")
                        progress.update_progress(5, 7, f"Step 5/7: Scanning {remaining_pages} remaining pages...")

                        writer = PdfWriter()
                        for i in range(scan_start_pdf_page - 1, total_pages):
                            writer.add_page(reader.pages[i])

                        temp_tail_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='_tail.pdf')
                        writer.write(temp_tail_pdf)
                        temp_tail_pdf.close()

                        tail_uploaded = upload_files([temp_tail_pdf.name], 'Gemini')
                        tail_prompt = f"""Analyze this PDF section (pages {scan_start_pdf_page}-{total_pages} of the full textbook).
Identify all formal chapters that START in this section, and find where each chapter ENDS.

Return ONLY a valid JSON array:
[
  {{"chapter": 16, "name": "First-Order Differential Equations", "start_page": 1, "end_page": 34}},
  {{"chapter": 17, "name": "Second-Order Differential Equations", "start_page": 35, "end_page": 60}}
]

IMPORTANT:
- start_page and end_page are relative to THIS section (1 = first page = PDF page {scan_start_pdf_page})
- end_page should be the LAST page of the chapter (before practice exercises, or next chapter, or appendix)
- ONLY include formal numbered chapters with format "Chapter NN: Title"
- DO NOT include: Appendices (Appendix A/B/C), Index, Answers, Table of Contents, or any unnumbered sections
- Return ONLY the JSON array"""

                        tail_result = call_ai(tail_prompt, 'Gemini', model_name, uploaded_info=tail_uploaded, status_callback=status_cb)
                        os.unlink(temp_tail_pdf.name)

                        tail_clean = tail_result.strip()
                        if tail_clean.startswith('```'):
                            lines = tail_clean.split('\n')
                            tail_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else tail_clean

                        try:
                            tail_chapters = json.loads(tail_clean)
                            if isinstance(tail_chapters, list):
                                for ch in tail_chapters:
                                    relative_start = ch.get('start_page', 1)
                                    relative_end = ch.get('end_page')

                                    pdf_start = scan_start_pdf_page + relative_start - 1
                                    pdf_end = scan_start_pdf_page + relative_end - 1 if relative_end else None

                                    all_chapters.append({
                                        'chapter': ch.get('chapter'),
                                        'name': ch.get('name'),
                                        'start_page': pdf_start,
                                        'end_page': pdf_end
                                    })
                                console.append(f"  ✓ Found {len(tail_chapters)} additional chapters")
                        except:
                            console.append(f"  ! Failed to parse tail chapters, skipping")

                    seen_chapters = set()
                    unique_chapters = []
                    for ch in all_chapters:
                        ch_num = ch.get('chapter')
                        if ch_num not in seen_chapters:
                            seen_chapters.add(ch_num)
                            unique_chapters.append(ch)
                    all_chapters = unique_chapters

                    all_chapters.sort(key=lambda x: x['start_page'])
                    for i in range(len(all_chapters)):
                        if all_chapters[i]['end_page'] is None:
                            if i < len(all_chapters) - 1:
                                all_chapters[i]['end_page'] = all_chapters[i + 1]['start_page'] - 1
                            else:
                                all_chapters[i]['end_page'] = total_pages

                    console.append(f"✓ Total: {len(all_chapters)} chapters")

                progress.update_progress(6, 7, "Step 6/7: Validating boundaries...")
                for i in range(len(all_chapters) - 1):
                    current = all_chapters[i]
                    next_ch = all_chapters[i + 1]
                    if current.get('end_page', 0) >= next_ch.get('start_page', 0):
                        current['end_page'] = next_ch['start_page'] - 1
                console.append(f"✓ Validated {len(all_chapters)} chapters")

                progress.update_progress(7, 7, f"Step 7/7: Splitting into {len(all_chapters)} PDFs...")
                decon_dir = os.path.join(textbook_dir, 'decon')
                os.makedirs(decon_dir, exist_ok=True)

                metadata_file = os.path.join(decon_dir, f"{os.path.splitext(selected_file)[0]}_chapters.json")
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(all_chapters, f, indent=2, ensure_ascii=False)

                created_files = split_pdf_by_chapters(pdf_to_split, all_chapters, decon_dir)

                progress.update_progress(7, 7, f"✓ Complete: {len(created_files)} chapters")
                console.append(f"\n✓ Decon complete: {len(created_files)} chapter PDFs")
                console.append(f"  Output: {decon_dir}")

                if repaired_pdf_path and repaired_pdf_path != file_path and os.path.exists(repaired_pdf_path):
                    try:
                        os.unlink(repaired_pdf_path)
                        console.append("✓ Cleaned up temporary repaired PDF")
                    except:
                        pass

            except Exception as e:
                import traceback
                progress.set_text_only(f"✗ Failed: {str(e)[:50]}")
                console.append(f"\n[ERROR] {e}")
                console.append(traceback.format_exc())

                if 'repaired_pdf_path' in locals() and repaired_pdf_path and repaired_pdf_path != file_path:
                    try:
                        os.unlink(repaired_pdf_path)
                    except:
                        pass
                
                raise e  # Re-raise to notify caller of failure

        from gui.core import utilQtInteract as qt_interact
        console, progress = qt_interact._create_console_tab(self.course_detail_window.consoleTabWidget, f"Decon: {selected_file}", with_progress=True)

        def run_with_progress(c):
            run_decon(c, progress)

        qt_interact._run_in_thread(run_with_progress, console, "Decon Textbook")

    def drag_enter(self, event):
        """Handle drag enter event for course detail itemList"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drag_move(self, event):
        """Handle drag move event for course detail itemList"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drag_drop(self, event):
        """Handle drop event for course detail itemList (for Textbook and Learn categories)"""
        if not self.course_detail_mgr:
            return

        current_category = self.course_detail_window.categoryList.currentItem()
        if not current_category:
            return

        category_text = current_category.text()

        if category_text not in ['Textbook', 'Learn']:
            QMessageBox.warning(self.course_detail_window, "Invalid Drop",
                              "Files can only be dropped in the Textbook or Learn category.")
            return

        if event.mimeData().hasUrls():
            import shutil

            if category_text == 'Textbook':
                target_dir = self.course_detail_mgr.get_textbook_dir()
            else:
                target_dir = self.course_detail_mgr.get_learn_dir()

            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(target_dir, filename)
                    try:
                        shutil.copy2(file_path, dest_path)
                        print(f"[DRAG-DROP] Copied: {filename} → {target_dir}")
                    except Exception as e:
                        print(f"[DRAG-DROP] Error copying {filename}: {e}")

            event.acceptProposedAction()
            self.on_category_changed(self.course_detail_window.categoryList.currentRow())

    def prefetch_all_tabs(self):
        """Prefetch all missing tabs in background"""
        def worker():
            from gui.qt_utils.content_processors.html_processor import HTMLProcessor
            processor = HTMLProcessor(self.app)
            tabs = self.course_detail_mgr.course.get('tabs', {})
            tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
            os.makedirs(tabs_dir, exist_ok=True)
            s = processor.create_session()
            for name, path in tabs.items():
                safe = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in name)
                md_path = os.path.join(tabs_dir, f"{safe}.md")
                if os.path.exists(md_path):
                    continue
                try:
                    url = f"{config.CANVAS_BASE_URL}{path}"
                    r = s.get(url, timeout=10)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    md = processor.parse_special_page(name, r.text, soup) if 'grades' in name.lower() or processor.is_modules_page(r.text, soup) else processor.html_to_md(soup)
                    if md:
                        with open(md_path, 'w', encoding='utf-8') as f:
                            f.write(f"# {name}\n\nSource: {url}\n\n---\n\n{md}")
                        print(f"[INFO] Prefetched {name}")
                except:
                    pass
        threading.Thread(target=worker, daemon=True).start()

    def load_or_fetch_tab(self, tab_name, url):
        """Load tab content from cache or fetch from server"""
        safe_tab_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
        md_path = os.path.join(self.course_detail_mgr.course_dir, 'Tabs', f"{safe_tab_name}.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    self.app.tab_content_signal.update_html.emit(f"MARKDOWN:{f.read()}")
            except Exception as e:
                self.course_detail_window.detailView.setHtml(f"<h2 style='color: #ef4444;'>Error</h2><p>{e}</p>")
        else:
            self.course_detail_window.detailView.setHtml(f"<h2 style='color: #eab308;'>Loading...</h2><p>Fetching {tab_name}...</p>")
            self.fetch_tab_content(tab_name, url)

    def fetch_tab_content(self, tab_name, url):
        """Fetch tab content from server in background thread"""
        def fetch_worker():
            try:
                from gui.qt_utils.content_processors.html_processor import HTMLProcessor
                processor = HTMLProcessor(self.app)
                session = processor.create_session()
                print(f"[INFO] Fetching {tab_name} from {url}")
                response = session.get(url, timeout=10)
                response.raise_for_status()
                if response.history:
                    print(f"[INFO] Server redirects detected for {tab_name}")
                if "window.location.href" in response.text:
                    js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
                    if js_redirect:
                        redirect_url = js_redirect.group(1)
                        if redirect_url.startswith('/'):
                            redirect_url = f"https://psu.instructure.com{redirect_url}"
                        print(f"[INFO] Following JS redirect to: {redirect_url}")
                        response = session.get(redirect_url, timeout=10)
                        response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                markdown = processor.parse_special_page(tab_name, response.text, soup) if ('grades' in url.lower() or 'Grades' in tab_name or processor.is_modules_page(response.text, soup)) else processor.html_to_md(soup)
                if markdown:
                    safe_tab_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
                    tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
                    os.makedirs(tabs_dir, exist_ok=True)
                    save_path = os.path.join(tabs_dir, f"{safe_tab_name}.md")
                    full_markdown = f"# {tab_name}\n\nSource: {url}\n\n---\n\n{markdown}"
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(full_markdown)
                    self.app.tab_content_signal.update_html.emit(f"MARKDOWN:{full_markdown}")
                    print(f"[INFO] Saved {tab_name} to {save_path}")
                else:
                    self.app.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>No content found for {tab_name}</p>")
            except Exception as e:
                self.app.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>Failed to fetch {tab_name}: {str(e)}</p>")
                print(f"[ERROR] Failed to fetch {tab_name}: {e}")
        threading.Thread(target=fetch_worker, daemon=True).start()

    def update_html(self, html):
        """Update course detail HTML view"""
        if html.startswith("MARKDOWN:"):
            import markdown as md_lib
            md_content = html[9:]
            lines = md_content.split('\n', 1)
            title = lines[0].strip('# ')
            body = lines[1] if len(lines) > 1 else ''
            html_body = md_lib.markdown(body, extensions=['extra', 'nl2br', 'tables'])
            styled_html = f"""<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.6;color:#e0e0e0}}
h1{{color:#3b82f6;border-bottom:2px solid #3b82f6;padding-bottom:8px}}
h2{{color:#60a5fa;margin-top:24px}}h3{{color:#93c5fd;margin-top:20px}}
a{{color:#60a5fa;text-decoration:none}}a:hover{{text-decoration:underline}}
table{{border-collapse:collapse;width:100%;margin:16px 0;background-color:#1a1a1a;border-radius:8px;overflow:hidden}}
th{{background-color:#2563eb;color:white;font-weight:600;padding:12px 16px;text-align:left;border-bottom:2px solid #3b82f6}}
td{{padding:10px 16px;border-bottom:1px solid #333}}
tr:hover{{background-color:#262626}}tr:last-child td{{border-bottom:none}}
code{{background-color:#2a2a2a;padding:2px 6px;border-radius:4px;font-family:'Consolas','Monaco',monospace;color:#22c55e}}
pre{{background-color:#1a1a1a;padding:16px;border-radius:8px;overflow-x:auto;border-left:4px solid #3b82f6}}
blockquote{{border-left:4px solid #3b82f6;padding-left:16px;margin:16px 0;color:#9ca3af}}
ul,ol{{padding-left:24px}}li{{margin:4px 0}}
</style><h1>{title}</h1>{html_body}"""
            self.course_detail_window.detailView.setHtml(styled_html)
        else:
            self.course_detail_window.detailView.setHtml(html)

    def refresh_current_category(self):
        """Refresh current category in CourseDetail window"""
        if not self.course_detail_mgr:
            return
        cdw = self.course_detail_window
        current_row = cdw.categoryList.currentRow()
        if current_row >= 0:
            self.on_category_changed(current_row)
