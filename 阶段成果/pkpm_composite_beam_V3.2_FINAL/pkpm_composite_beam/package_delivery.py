import argparse
import os
from datetime import datetime
from pathlib import Path
import zipfile


def _iter_files(base_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(base_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base_dir)
        if "__pycache__" in rel.parts:
            continue
        if path.suffix.lower() == ".pyc":
            continue
        if path.name in {"ui_error.log", "ui_bat.log", "diag.log", "build_exe.log"}:
            continue
        paths.append(path)
    return paths


def _zip_write(zip_path: Path, files: list[Path], arc_prefix: str, base_dir: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            rel = path.relative_to(base_dir)
            z.write(path, arcname=str(Path(arc_prefix) / rel))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["exe", "src"], default="exe")
    args = ap.parse_args()

    base_dir = Path(__file__).resolve().parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    if args.mode == "exe":
        exe = base_dir / "dist" / "PKPM叠合梁工具.exe"
        if not exe.exists():
            raise SystemExit("EXE not found: dist/PKPM叠合梁工具.exe (please run build_exe.py first)")

        allow = {
            exe,
            base_dir / "运行_UI界面.bat",
            base_dir / "运行_UI界面_调试.bat",
            base_dir / "一键诊断.bat",
            base_dir / "上手指南.txt",
            base_dir / "示例参数_客户验收_多直径.xlsx",
            base_dir / "示例参数_T梁_洞口_多直径.xlsx",
        }
        files = [p for p in allow if p.exists()]
        zip_path = base_dir / f"PKPM叠合梁工具_客户交付包_{stamp}.zip"
        _zip_write(zip_path, files, arc_prefix="PKPM叠合梁工具", base_dir=base_dir)
        print(f"[OK] Wrote: {zip_path}")
        return 0

    # src support pack: full folder (excluding caches/logs/build outputs)
    files = _iter_files(base_dir)
    zip_path = base_dir / f"PKPM叠合梁工具_源码支持包_{stamp}.zip"
    _zip_write(zip_path, files, arc_prefix="pkpm_composite_beam", base_dir=base_dir)
    print(f"[OK] Wrote: {zip_path}")
    return 0


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    raise SystemExit(main())
