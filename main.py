"""Desktop entry point, with a local diagnostic log for startup failures."""
import os
import sys
import tempfile
import traceback
from pathlib import Path


if __name__ == '__main__':
    try:
        from northdiary.app import main
        raise SystemExit(main())
    except Exception:
        detail = traceback.format_exc()
        log = None
        for root in [Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'NorthDiary' / 'logs',
                     Path(tempfile.gettempdir()) / 'NorthDiary-logs']:
            try:
                root.mkdir(parents=True, exist_ok=True)
                log = root / 'startup-error.log'
                log.write_text(detail, encoding='utf-8')
                break
            except OSError:
                continue
        if sys.platform == 'win32':
            import ctypes
            text = '程序启动未完成。\n' + ('错误详情已保存到：\n' + str(log) if log else '请联系开发者检查运行环境。')
            ctypes.windll.user32.MessageBoxW(None, text, 'NorthDiary · 启动失败', 0x10)
        elif sys.stderr:
            sys.stderr.write(detail)
        raise SystemExit(1)
