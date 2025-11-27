# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gui/ui/*.ui', 'gui/ui'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.uic',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome.service',
        'webdriver_manager',
        'webdriver_manager.chrome',
        'requests',
        'pyotp',
        'lxml',
        'lxml.html',
        'google.genai',
        'anthropic',
        'docx',
        'pypandoc',
        'PIL',
        'html2text',
        'markdownify',
        'markdown',
        'PyPDF2',
        'pikepdf',
        # Dynamically imported func/ modules
        'func.getTodos',
        'func.getHistoryTodos',
        'func.getCourses',
        'func.getSyll',
        'func.getHomework',
        'func.getQuiz_ultra',
        'func.procLearnMaterial',
        'func.mgrHistory',
        'func.utilPromptFiles',
        'func.utilModels',
        'func.getQuizStatus',
        'func.utilPdfBookmark',
        'func.utilPdfSplitter',
        # Dynamically imported login/ modules
        'login.getCookie',
        'login.getTotp',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CanvasDecon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CanvasDecon',
)

app = BUNDLE(
    coll,
    name='CanvasDecon.app',
    icon=None,
    bundle_identifier='com.canvas.decon',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
    },
)
