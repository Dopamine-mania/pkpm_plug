import os
import sys
from pathlib import Path


def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> int:
    if not sys.platform.startswith("win"):
        _die("build_exe.py must be run on Windows.")

    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    os.environ.setdefault("PYTHONPATH", "")

    app_dir = Path(__file__).resolve().parent
    os.chdir(app_dir)

    try:
        import PyQt5  # noqa: F401
    except Exception as e:
        _die(f"PyQt5 not available in this Python: {sys.executable}\n{e}")

    try:
        import PyInstaller.__main__  # noqa: F401
    except Exception as e:
        _die(f"PyInstaller not available in this Python: {sys.executable}\n{e}")

    # Avoid pulling huge optional deps (and avoid broken numpy/pandas env)
    args = [
        "--noconsole",
        "--onefile",
        "--clean",
        "--name",
        "PKPM叠合梁工具",
        "--add-data",
        "示例参数_客户验收_多直径.xlsx;.",
        "--add-data",
        "示例参数_T梁_洞口_多直径.xlsx;.",
        "--add-data",
        "上手指南.txt;.",
        "--exclude-module",
        "pandas",
        "--exclude-module",
        "numpy",
        "--exclude-module",
        "openpyxl",
        "launch_ui.py",
    ]

    import PyInstaller.__main__

    print("[INFO] Running PyInstaller:")
    print(" ".join(args))
    PyInstaller.__main__.run(args)

    exe = app_dir / "dist" / "PKPM叠合梁工具.exe"
    if exe.exists():
        print(f"[SUCCESS] Built: {exe}")
        return 0
    _die("Build finished but EXE not found under dist/.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

