# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for PDF ADA Processor.

This configuration bundles all Python dependencies and Node.js libraries needed
for the CLI entry point (python/src/main.py).

Build with: pyinstaller pdf-ada.spec --clean
Output: dist/pdf-ada.exe (Windows), .dmg (macOS)

Key features:
- Bundles pikepdf, Pillow, requests, pywin32 for Python operations
- Includes express and pdf-lib for Node.js server access
- Handles multiprocessing for parallel processing tools
"""


a = Analysis(
    ['python/src/main.py'],  # Entry point for .exe executable
    pathex=[],               # No relative paths in build output
    binaries=[],             # No native binaries to bundle (except via deps)
    datas=[
        ('adobe_credentials.json.template', '.'),  # Adobe API credentials template
        ('server.js', '.'),                         # Web server for browser UI access
        ('pipelines/*.py', '.'),                    # Pipeline scripts for batch processing
        ('specs/spec.md', '.'),                     # Architecture documentation
    ],
    hiddenimports=[
        'express',         # Node.js web server framework (used by bundled server.js)
        'pdf-lib',         # PDF manipulation library (for metadata reading in UI)
        'multiprocessing', # Parallel processing for batch tools (pdf_fix_single, deep_scan)
        'pikepdf',         # Primary Python PDF library (metadata fix, structure modification)
        'PIL',             # Pillow image analysis (alt-text detection)
        'requests',        # Adobe API HTTP client
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],  # Exclude GUI components unless needed for macOS
    noarchive=False,
    optimize=2,             # Enable UPX compression (~40% smaller binaries)
    debug=False,            # Production builds (debug=True for development)
    
    # Build options - add to Analysis() dict if needed:
    # console='auto'          # For cross-platform (Windows .exe only)
    # noconsole               # For macOS/Linux .app/.dmg
    # bootloader_ignore_signals=True,  # Enable signal handling
    # strip=False,              # Disable code stripping for debugging
    # upx_exclude=[],           # No UPX exclusions needed
    # target_arch=None,         # Auto-detect or specify: ['x86_64', 'arm64']
)

pyz = PYZ(a.pure)  # Python-Zypper archive builder

exe = EXE(
    pyz,
    a.scripts,        # Main entry point script (main.py wrapped by PyInstaller)
    a.binaries,       # Native binaries from pip packages
    a.datas,          # Data files included in bundle
    [],                # Icon file path (optional: 'pdf-icon.ico')
    
    name='pdf-ada',  # Name of the bundled executable
    
    debug=False,              # Production builds
    bootloader_ignore_signals=True,   # Signal handling for GUI apps on macOS
    strip=False,                   # Code stripping for smaller binaries
    upx=True,                      # Enable UPX compression (smaller size)
    upx_exclude=[],                 # No exclusions
    
    console='auto',                # Auto-detect: 'auto' or 'yes'/'no'
    argv_emulation=False,          # Disable Windows console emulation for cross-platform
    target_arch=None,              # Let PyInstaller auto-detect architecture
)

# Post-build customization (optional):
# - Add icon file after build with post_build hook
# - Customize startup script to handle --server flag properly
# - Include additional data files via pyz.includef()
