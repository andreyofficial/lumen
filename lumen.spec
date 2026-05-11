# PyInstaller spec for Lumen — produces a standalone executable.
# Run via:  pyinstaller lumen.spec --noconfirm
#
# By default this builds a one-folder app at dist/lumen/.
# Set LUMEN_ONEFILE=1 in the environment to produce a single binary at dist/lumen.
import os
import sys
from pathlib import Path

# When PyInstaller loads a spec it doesn't define __file__. Use the cwd, which
# build.sh sets to the project root.
SPECPATH = os.environ.get("LUMEN_SPECPATH", os.getcwd())
ROOT = Path(SPECPATH).resolve()

ONEFILE = os.environ.get("LUMEN_ONEFILE") == "1"
DEBUG = os.environ.get("LUMEN_DEBUG") == "1"

# Pick a platform-appropriate icon. PyInstaller refuses an SVG on Windows
# (needs .ico) and macOS (needs .icns), so resolve to the right asset and
# fall back to None when the expected file is missing — the build still
# succeeds, just without a custom icon.
if sys.platform == "win32":
    _ico = ROOT / "lumen.ico"
    ICON_PATH = str(_ico) if _ico.is_file() else None
elif sys.platform == "darwin":
    _icns = ROOT / "lumen.icns"
    ICON_PATH = str(_icns) if _icns.is_file() else None
else:
    _svg = ROOT / "assets" / "lumen.svg"
    ICON_PATH = str(_svg) if _svg.is_file() else None

block_cipher = None

datas = [
    (str(ROOT / "assets" / "lumen.svg"), "assets"),
]
# Bundle every pre-rendered hicolor PNG so the running app can install
# them into the user's icon cache on first launch, and the taskbar /
# tray show a crisp pixmap at any size.
_icons_root = ROOT / "assets" / "icons"
if _icons_root.is_dir():
    for size_dir in sorted(_icons_root.iterdir()):
        png = size_dir / "lumen.png"
        if png.is_file():
            datas.append((str(png), f"assets/icons/{size_dir.name}"))

hiddenimports = [
    "PyQt6.QtSvg",
    "PyQt6.QtSvgWidgets",
    "PyQt6.QtPrintSupport",
    "PyQt6.QtNetwork",
]

# Trim Qt modules / plugins we definitely don't use to keep the binary small.
excludes = [
    "PyQt6.Qt3DCore",
    "PyQt6.Qt3DAnimation",
    "PyQt6.Qt3DExtras",
    "PyQt6.Qt3DInput",
    "PyQt6.Qt3DLogic",
    "PyQt6.Qt3DRender",
    "PyQt6.QtBluetooth",
    "PyQt6.QtCharts",
    "PyQt6.QtDataVisualization",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtNfc",
    "PyQt6.QtPositioning",
    "PyQt6.QtQuick",
    "PyQt6.QtQuick3D",
    "PyQt6.QtQuickWidgets",
    "PyQt6.QtQml",
    "PyQt6.QtRemoteObjects",
    "PyQt6.QtSensors",
    "PyQt6.QtSerialBus",
    "PyQt6.QtSerialPort",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtWebChannel",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineQuick",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebSockets",
    "PyQt6.QtWebView",
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
    "test",
]


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="lumen",
        debug=DEBUG,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_PATH,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="lumen",
        debug=DEBUG,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_PATH,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="lumen",
    )
