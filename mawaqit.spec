# -*- mode: python -*-
block_cipher = None

a = Analysis([
    'mawaqit.py',
],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

dist = BUNDLE(binaries=[], name='mawaqit',)

# Optionally, you can customize the build process below.

# pyz = PYZ(a.pure, a.zipped, cipher=block_cipher)
# exe = EXE(pyz,
#           a.scripts,
#           [],
#           name='mawaqit',
#           debug=False,
#           bootloader_ignore_signals=False,
#           strip=False,
#           upx=True,
#           console=True )

# coll = COLLECT(exe,
#                a.binaries,
#                a.zipfiles,
#                a.datas,
#                strip=False,
#                upx=True,
#                upx_exclude=[],
#                name='mawaqit')
