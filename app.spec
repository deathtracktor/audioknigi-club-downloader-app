# -*- mode: python -*-

block_cipher = None

import sys

exe_suffix = '.exe' if sys.platform.startswith('win') else ''

a = Analysis(
    ['app.py'],
    pathex=[
        '.',
        os.path.join(os.pardir, 'Lib', 'site-packages'),
        os.path.join('.venv', 'Lib', 'site-packages'),
    ],
    binaries=[
        (f'geckodriver{ exe_suffix }', '.'),
        (f'ffmpeg{ exe_suffix }', '.'),
    ],
    datas=[],
    hiddenimports=['selenium'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='app',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True
)
