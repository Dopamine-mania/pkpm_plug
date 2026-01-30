import os
import sys
import traceback
from pathlib import Path


def _message_box(title: str, text: str) -> None:
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
            return
        except Exception:
            pass
    try:
        print(f"{title}\n{text}")
    except Exception:
        pass


def _write_log(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    app_dir = Path(__file__).resolve().parent
    try:
        os.chdir(app_dir)
    except Exception:
        pass

    temp_dir = Path(os.environ.get("TEMP") or os.environ.get("TMP") or str(app_dir))
    log_path = temp_dir / "pkpm_composite_beam_ui.log"

    try:
        import PyQt5  # noqa: F401
    except Exception as e:
        msg = (
            "无法启动 UI：缺少 PyQt5 依赖。\n\n"
            "请先运行：安装依赖.bat\n\n"
            f"Python: {sys.executable}\n"
            f"日志: {log_path}\n"
        )
        _write_log(log_path, msg + "\n\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)))
        _message_box("PKPM-CAE Composite Beam Tool", msg)
        return 1

    try:
        # NOTE: use normal import so PyInstaller can detect and bundle UI module.
        # Do NOT use runpy.run_path here; it is fragile under PyInstaller onefile extraction.
        import ui_main_pro

        ui_main_pro.main()
        return 0
    except SystemExit as e:
        code = int(getattr(e, "code", 0) or 0)
        return code
    except Exception as e:
        msg = (
            "UI 运行异常，已生成日志。\n\n"
            f"Python: {sys.executable}\n"
            f"程序目录: {app_dir}\n"
            f"日志: {log_path}\n\n"
            "请把日志内容发回以便定位修复。"
        )
        _write_log(log_path, msg + "\n\n" + "".join(traceback.format_exception(type(e), e, e.__traceback__)))
        _message_box("PKPM-CAE Composite Beam Tool", msg)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
