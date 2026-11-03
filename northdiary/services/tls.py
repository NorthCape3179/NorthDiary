"""Prefer native Windows TLS before Qt can probe conflicting OpenSSL DLLs."""
import sys

from northdiary.bootstrap import configure_runtime
configure_runtime()

from PySide6.QtNetwork import QSslSocket


_configured = False


def configure_tls():
    global _configured
    if _configured:
        return
    if sys.platform == 'win32' and not QSslSocket.setActiveBackend('schannel'):
        raise RuntimeError('无法启用 Windows 系统 TLS 连接，请重新启动 NorthDiary。')
    _configured = True
