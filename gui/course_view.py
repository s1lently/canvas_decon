"""Course View - CourseDetail Window (merged from handlers/course_detail.py)"""
import sys, os, json, threading, re, tempfile, shutil
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from gui._internal.mgrCourseDetail import CourseDetailManager
from gui.widgets import FileItemDelegate
from gui.learn import format_course, format_todo


class CourseView:
    """Handles CourseDetail window operations"""

    def __init__(self, app):
        self.app = app
        self.cdw = app.course_detail_window

    @property
    def mgr(self):
        return self.app.course_detail_mgr

    def open(self):
        """Open course detail from main window"""
        mw = self.app.main_window
        ci, ii = mw.categoryList.currentRow(), mw.itemList.currentRow()

        if ci != 0:
            return QMessageBox.warning(self.app, "Invalid", "Please select a Course first.")
        if ii < 0:
            return QMessageBox.warning(self.app, "No Selection", "Please select a course first.")

        courses = self.app.dm.get('courses')
        if ii >= len(courses):
            return QMessageBox.warning(self.app, "Error", "Invalid course selection.")

        self.app.course_detail_mgr = CourseDetailManager(courses[ii], self.app.dm.get('todos'), self.app.dm.get('history_todos'))
        self.populate_window()
        self.app.stacked_widget.setCurrentWidget(self.cdw)

    def populate_window(self):
        """Populate CourseDetail window"""
        if not self.mgr:
            return

        try:
            self.cdw.categoryList.currentRowChanged.disconnect()
            self.cdw.itemList.currentRowChanged.disconnect()
        except Exception:
            pass

        self.cdw.courseNameLabel.setText(self.mgr.get_course_name())
        for w in [self.cdw.categoryList, self.cdw.itemList, self.cdw.detailView]:
            w.clear()

        categories = self.mgr.get_categories()
        self.cdw.categoryList.addItems(categories)
        self.cdw.categoryList.currentRowChanged.connect(self.on_category_changed)
        self.cdw.itemList.currentRowChanged.connect(self.on_item_changed)

        self._prefetch_all_tabs()

        if categories:
            self.cdw.categoryList.setCurrentRow(0)
            self.cdw.categoryList.setFocus()

    def on_category_changed(self, index):
        """Handle category selection"""
        if index < 0 or not self.mgr:
            return

        self.cdw.itemList.clear()
        self.cdw.detailView.clear()

        category = self.cdw.categoryList.item(index).text()

        # Button visibility
        self.cdw.openTextbookFolderBtn.setVisible(category == 'Textbook')
        self.cdw.deconTextbookBtn.setVisible(category == 'Textbook')
        self.cdw.loadFromDeconBtn.setVisible(category == 'Learn')
        self.cdw.learnMaterialBtn.setVisible(category == 'Learn')

        # Textbook: show learn sitting widget
        if category == 'Textbook':
            self._show_learn_widget()
            return
        else:
            self._hide_learn_widget()

        # Populate items
        items = self.mgr.get_items_for_category(category)
        for item_data in items:
            item = QListWidgetItem(item_data['name'])
            item.setData(Qt.ItemDataRole.UserRole, item_data.get('has_file', False))
            item.setData(Qt.ItemDataRole.UserRole + 1, item_data)
            if item_data.get('is_done', False):
                item.setForeground(Qt.GlobalColor.gray)
            self.cdw.itemList.addItem(item)

        # Delegate
        delegate = FileItemDelegate(self.cdw.itemList) if category in ['Syllabus', 'Textbook', 'Learn'] else QStyledItemDelegate()
        self.cdw.itemList.setItemDelegate(delegate)
        self.cdw.itemList.viewport().update()

    def _show_learn_widget(self):
        """Show learn sitting widget for Textbook category"""
        from gui.learn import LearnSittingWidget

        if self.app.learn_sitting_widget:
            self.cdw.detailView.setParent(None)
            self.app.learn_sitting_widget.setParent(None)
            self.app.learn_sitting_widget.deleteLater()
            self.app.learn_sitting_widget = None

        self.app.learn_sitting_widget = LearnSittingWidget(self.app, self.mgr, self.cdw)
        layout = self.cdw.centralwidget.layout().itemAt(1).layout()
        layout.removeWidget(self.cdw.detailView)
        self.cdw.detailView.setVisible(False)
        layout.addWidget(self.app.learn_sitting_widget)
        self.cdw.itemList.setVisible(False)

    def _hide_learn_widget(self):
        """Hide learn sitting widget"""
        if self.app.learn_sitting_widget:
            layout = self.cdw.centralwidget.layout().itemAt(1).layout()
            layout.removeWidget(self.app.learn_sitting_widget)
            self.app.learn_sitting_widget.setParent(None)
            self.app.learn_sitting_widget.deleteLater()
            self.app.learn_sitting_widget = None
            self.cdw.detailView.setVisible(True)
            layout.addWidget(self.cdw.detailView)
        self.cdw.itemList.setVisible(True)

    def on_item_changed(self, index):
        """Handle item selection"""
        if index < 0 or not self.mgr:
            return

        item_data = self.cdw.itemList.item(index).data(Qt.ItemDataRole.UserRole + 1)
        if not item_data:
            return

        item_type, data = item_data.get('type'), item_data.get('data')

        if item_type == 'tab':
            tab_name, url = data.get('tab_name'), data.get('url')
            if tab_name and url:
                self._load_or_fetch_tab(tab_name, url)
            return

        html_map = {
            'intro': lambda: format_course(data),
            'todo': lambda: format_todo(data),
            'syllabus': lambda: f"<h2 style='color: #22c55e;'>Syllabus</h2><p><a href='{data['url']}'>{data['url']}</a></p><p>Folder: {data['local_dir']}</p>",
            'textbook_file': lambda: f"<h2>{data['filename']}</h2><p>{data['path']}</p>",
            'learn_file': lambda: f"<h2 style='color: #3b82f6;'>{data['filename']}</h2><p><strong>Path:</strong> {data['path']}</p>" +
                                 (f"<p><strong>Report:</strong> <a href='file://{data['report_path']}'>{os.path.basename(data['report_path'])}</a></p>" if data.get('report_path') else
                                  "<p><strong>Report:</strong> Not generated yet. Click 'Learn This Material' to generate.</p>"),
            'placeholder': lambda: f"<p>No files</p><p>Folder: {data['folder']}</p>"
        }
        self.cdw.detailView.setHtml(html_map.get(item_type, lambda: "<p>No details</p>")())

    def on_item_double_clicked(self, item):
        """Handle double-click"""
        if not self.mgr:
            return

        item_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if not item_data:
            return

        item_type, data = item_data.get('type'), item_data.get('data')

        if item_type == 'syllabus' and item_data.get('has_file'):
            syll_dir = data.get('local_dir')
            if syll_dir and os.path.exists(syll_dir):
                self.app.open_folder(syll_dir)
        elif item_type == 'textbook_file':
            file_path = data.get('path')
            if file_path and os.path.exists(file_path):
                self.app.open_folder(os.path.dirname(file_path))

    def on_open_syllabus_folder(self):
        """Open syllabus folder"""
        if self.mgr:
            self.app.open_folder(self.mgr.get_syll_dir())

    def on_open_textbook_folder(self):
        """Open textbook folder"""
        if self.mgr:
            self.app.open_folder(self.mgr.get_textbook_dir())

    def on_decon_textbook(self):
        """Decon textbook PDFs"""
        if not self.mgr:
            return QMessageBox.warning(self.cdw, "Error", "No course selected.")

        textbook_dir = self.mgr.get_textbook_dir()
        if not os.path.exists(textbook_dir):
            return QMessageBox.warning(self.cdw, "Error", "Textbook folder does not exist.")

        pdf_files = [f for f in os.listdir(textbook_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return QMessageBox.warning(self.cdw, "Error", "No PDF files found in Textbook folder.")

        selected_file, ok = QInputDialog.getItem(self.cdw, "Select Textbook", "Choose a PDF to decon:", pdf_files, 0, False)
        if not ok or not selected_file:
            return

        reply = QMessageBox.question(
            self.cdw, "Decon Textbook",
            f"This will:\n1. Analyze chapter structure using Gemini AI\n2. Split PDF into individual chapter files\n3. Save to: {textbook_dir}/decon/\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path = os.path.join(textbook_dir, selected_file)
        self._run_decon_task(file_path, selected_file, textbook_dir)

    def _run_decon_task(self, file_path, selected_file, textbook_dir):
        """Run decon task with Mission Control"""
        def run_decon(progress):
            try:
                progress.update(progress=14, status="Step 1/7: Selecting model...")

                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
                from ai import upload_files, call_ai, get_best_gemini_model
                from utilPdfSplitter import split_pdf_by_chapters
                from utilPdfBookmark import extract_chapters_from_bookmarks, format_bookmark_chapters, repair_pdf_references
                from PyPDF2 import PdfReader, PdfWriter
                from gui.learn import get_product, get_model as get_pref_model

                pref_product, pref_model = get_product(), get_pref_model()

                if pref_product == 'Auto' or pref_model == 'Auto':
                    model_name = get_best_gemini_model()
                elif pref_product == 'Gemini':
                    model_name = pref_model
                else:
                    model_name = get_best_gemini_model()

                progress.update(progress=28, status="Step 2/7: Loading PDF...")
                reader = PdfReader(file_path)
                total_pages = len(reader.pages)

                repaired_pdf_path = None
                all_chapters = extract_chapters_from_bookmarks(file_path, total_pages)

                if all_chapters:
                    print("Found valid chapter bookmarks")
                    repaired_pdf_path = repair_pdf_references(file_path, None)
                    pdf_to_split = repaired_pdf_path if repaired_pdf_path and repaired_pdf_path != file_path else file_path

                    if repaired_pdf_path and repaired_pdf_path != file_path:
                        reader = PdfReader(repaired_pdf_path)

                    all_chapters = [
                        {'chapter': ch['chapter_number'], 'name': ch['chapter_name'],
                         'start_page': ch['start_page'], 'end_page': ch['end_page']}
                        for ch in all_chapters
                    ]
                else:
                    pdf_to_split = file_path
                    all_chapters = self._analyze_toc_with_ai(file_path, reader, total_pages, model_name, progress)

                progress.update(progress=85, status="Step 6/7: Validating...")
                for i in range(len(all_chapters) - 1):
                    if all_chapters[i].get('end_page', 0) >= all_chapters[i + 1].get('start_page', 0):
                        all_chapters[i]['end_page'] = all_chapters[i + 1]['start_page'] - 1

                progress.update(progress=95, status=f"Step 7/7: Splitting {len(all_chapters)} PDFs...")
                decon_dir = os.path.join(textbook_dir, 'decon')
                os.makedirs(decon_dir, exist_ok=True)

                metadata_file = os.path.join(decon_dir, f"{os.path.splitext(selected_file)[0]}_chapters.json")
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(all_chapters, f, indent=2, ensure_ascii=False)

                created_files = split_pdf_by_chapters(pdf_to_split, all_chapters, decon_dir)
                progress.finish(f"Done: {len(created_files)} chapters")

                if repaired_pdf_path and repaired_pdf_path != file_path and os.path.exists(repaired_pdf_path):
                    try:
                        os.unlink(repaired_pdf_path)
                    except Exception:
                        pass

            except Exception as e:
                import traceback
                progress.update(status=f"Error: {str(e)[:40]}", error=True)
                traceback.print_exc()
                raise

        self.app.mission_control.start_task(f"Decon: {selected_file}", run_decon)

    def _analyze_toc_with_ai(self, file_path, reader, total_pages, model_name, progress):
        """Analyze TOC with AI (fallback when no bookmarks)"""
        from func.ai import upload_files, call_ai
        from PyPDF2 import PdfWriter

        TOC_PAGES = min(80, total_pages)
        writer = PdfWriter()
        for i in range(TOC_PAGES):
            writer.add_page(reader.pages[i])

        temp_toc_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='_toc.pdf')
        writer.write(temp_toc_pdf)
        temp_toc_pdf.close()

        progress.update(progress=42, status="Step 3/7: Analyzing TOC...")
        uploaded_info = upload_files([temp_toc_pdf.name], 'Gemini')

        toc_prompt = """Analyze this textbook PDF and extract the Table of Contents.
Return ONLY a valid JSON object with chapters and delta (page offset).
{"delta": -16, "chapters": [{"chapter": 1, "name": "Introduction", "book_page": 1}]}"""

        result = call_ai(toc_prompt, 'Gemini', model_name, uploaded_info=uploaded_info)
        os.unlink(temp_toc_pdf.name)

        progress.update(progress=57, status="Step 4/7: Parsing TOC...")
        result_clean = result.strip()
        if result_clean.startswith('```'):
            lines = result_clean.split('\n')
            result_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_clean

        toc_data = json.loads(result_clean)
        delta = toc_data.get('delta', 0)
        toc_chapters = toc_data.get('chapters', [])

        progress.update(progress=71, status="Step 5/7: Converting pages...")
        all_chapters = []
        for ch in toc_chapters:
            book_page = ch.get('book_page', 0)
            pdf_start = book_page - delta
            all_chapters.append({
                'chapter': ch.get('chapter'),
                'name': ch.get('name') or 'Untitled',
                'start_page': pdf_start,
                'end_page': None
            })

        all_chapters.sort(key=lambda x: x['start_page'])
        for i in range(len(all_chapters)):
            if all_chapters[i]['end_page'] is None:
                all_chapters[i]['end_page'] = all_chapters[i + 1]['start_page'] - 1 if i < len(all_chapters) - 1 else total_pages

        return all_chapters

    # === DRAG & DROP ===
    def drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drag_move(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def drag_drop(self, event):
        if not self.mgr:
            return

        category = self.cdw.categoryList.currentItem()
        if not category or category.text() not in ['Textbook', 'Learn']:
            QMessageBox.warning(self.cdw, "Invalid Drop", "Files can only be dropped in Textbook or Learn category.")
            return

        if event.mimeData().hasUrls():
            target_dir = self.mgr.get_textbook_dir() if category.text() == 'Textbook' else self.mgr.get_learn_dir()

            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    try:
                        shutil.copy2(file_path, os.path.join(target_dir, os.path.basename(file_path)))
                    except Exception as e:
                        print(f"[DRAG-DROP] Error: {e}")

            event.acceptProposedAction()
            self.on_category_changed(self.cdw.categoryList.currentRow())

    # === TAB CONTENT ===
    def _prefetch_all_tabs(self):
        """Prefetch all tabs in background"""
        def worker():
            from gui.processors import HTMLProcessor
            processor = HTMLProcessor(self.app)
            tabs = self.mgr.course.get('tabs', {})
            tabs_dir = os.path.join(self.mgr.course_dir, 'Tabs')
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
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _load_or_fetch_tab(self, tab_name, url):
        """Load tab from cache or fetch"""
        safe = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
        md_path = os.path.join(self.mgr.course_dir, 'Tabs', f"{safe}.md")

        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    self.app.signals.tab_content_update.emit(f"MARKDOWN:{f.read()}")
            except Exception as e:
                self.cdw.detailView.setHtml(f"<h2 style='color: #ef4444;'>Error</h2><p>{e}</p>")
        else:
            self.cdw.detailView.setHtml(f"<h2 style='color: #eab308;'>Loading...</h2><p>Fetching {tab_name}...</p>")
            self._fetch_tab_content(tab_name, url)

    def _fetch_tab_content(self, tab_name, url):
        """Fetch tab content in background"""
        def fetch():
            try:
                from gui.processors import HTMLProcessor
                processor = HTMLProcessor(self.app)
                session = processor.create_session()
                response = session.get(url, timeout=10)
                response.raise_for_status()

                if "window.location.href" in response.text:
                    js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
                    if js_redirect:
                        redirect_url = js_redirect.group(1)
                        if redirect_url.startswith('/'):
                            redirect_url = f"https://psu.instructure.com{redirect_url}"
                        response = session.get(redirect_url, timeout=10)

                soup = BeautifulSoup(response.text, 'html.parser')
                is_special = 'grades' in url.lower() or 'Grades' in tab_name or processor.is_modules_page(response.text, soup)
                markdown = processor.parse_special_page(tab_name, response.text, soup) if is_special else processor.html_to_md(soup)

                if markdown:
                    safe = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
                    tabs_dir = os.path.join(self.mgr.course_dir, 'Tabs')
                    os.makedirs(tabs_dir, exist_ok=True)
                    full_md = f"# {tab_name}\n\nSource: {url}\n\n---\n\n{markdown}"
                    with open(os.path.join(tabs_dir, f"{safe}.md"), 'w', encoding='utf-8') as f:
                        f.write(full_md)
                    self.app.signals.tab_content_update.emit(f"MARKDOWN:{full_md}")
                else:
                    self.app.signals.tab_content_update.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>No content for {tab_name}</p>")

            except Exception as e:
                self.app.signals.tab_content_update.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>Failed: {str(e)}</p>")

        threading.Thread(target=fetch, daemon=True).start()

    def update_html(self, html):
        """Update detail view with HTML or markdown"""
        if html.startswith("MARKDOWN:"):
            import markdown as md_lib
            md_content = html[9:]
            lines = md_content.split('\n', 1)
            title = lines[0].strip('# ')
            body = lines[1] if len(lines) > 1 else ''
            html_body = md_lib.markdown(body, extensions=['extra', 'nl2br', 'tables'])
            styled = f"""<style>
body{{font-family:-apple-system,sans-serif;line-height:1.6;color:#e0e0e0}}
h1{{color:#3b82f6;border-bottom:2px solid #3b82f6;padding-bottom:8px}}
h2{{color:#60a5fa;margin-top:24px}}
a{{color:#60a5fa;text-decoration:none}}
table{{border-collapse:collapse;width:100%;margin:16px 0;background:#1a1a1a;border-radius:8px}}
th{{background:#2563eb;color:white;padding:12px 16px;text-align:left}}
td{{padding:10px 16px;border-bottom:1px solid #333}}
code{{background:#2a2a2a;padding:2px 6px;border-radius:4px;color:#22c55e}}
</style><h1>{title}</h1>{html_body}"""
            self.cdw.detailView.setHtml(styled)
        else:
            self.cdw.detailView.setHtml(html)

    def refresh_category(self):
        """Refresh current category"""
        if self.mgr:
            row = self.cdw.categoryList.currentRow()
            if row >= 0:
                self.on_category_changed(row)
