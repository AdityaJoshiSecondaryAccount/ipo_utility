import sys
import os

manage_bin = 'dist/manage.exe' if (sys.platform == 'win32' or os.path.exists('dist/manage.exe')) else 'dist/manage'
binaries = [(manage_bin, '.')]
if os.path.exists('wkhtmltoimage.exe'):
    binaries.append(('wkhtmltoimage.exe', '.'))
elif os.path.exists('wkhtmltoimage'):
    binaries.append(('wkhtmltoimage', '.'))

a = Analysis(
    ['Setup.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('pemfile', 'pemfile'),
        ('db.sqlite3', '.'),
        ('sys_usb.json', '.'),
        ('pem_files.json', '.'),
        ('.env', '.'),
        ('home/migrations', 'home/migrations'),
    ],
    hiddenimports=[
        'webview',
        'sqlcipher3',
        'pysqlcipher3',
        'psutil',
        'PIL',
        'bs4',
        'requests',
        'xlsxwriter',
        'openpyxl',
        'lxml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='IPOUtility',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
