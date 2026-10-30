"""Windows per-user DPAPI storage. No plaintext or cross-platform fallback."""
import ctypes
import json
import os
from pathlib import Path
import tempfile


class CredentialError(Exception):
    pass


class WindowsDPAPI:
    def __init__(self):
        if os.name != 'nt':
            raise CredentialError('当前系统不支持 Windows 安全存储，可使用仅本次连接')

    def _crypt(self, content, decrypt=False):
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

        source_buffer = (ctypes.c_ubyte * len(content)).from_buffer_copy(content)
        source = Blob(len(content), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        output = Blob()
        crypt = ctypes.WinDLL('crypt32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        function.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
            raise CredentialError('Windows 安全存储不可用，请使用仅本次连接或重新登录')
        try:
            return ctypes.string_at(output.data, output.size)
        finally:
            kernel.LocalFree(ctypes.cast(output.data, ctypes.c_void_p))

    def encrypt(self, content):
        return self._crypt(content)

    def decrypt(self, content):
        return self._crypt(content, decrypt=True)


class GitHubCredentialStore:
    def __init__(self, root, protector=None):
        self.path = Path(root) / 'github.credentials'
        self.protector = protector

    def _protector(self):
        return self.protector or WindowsDPAPI()

    def load(self):
        if not self.path.exists():
            return None
        try:
            if self.path.stat().st_size > 64 * 1024:
                raise ValueError()
            result = json.loads(self._protector().decrypt(self.path.read_bytes()))
            if not isinstance(result, dict) or not isinstance(result.get('token'), str) or not result['token']:
                raise ValueError()
            return result
        except (OSError, ValueError, TypeError):
            raise CredentialError('无法读取已保存的 GitHub 登录，请重新连接') from None

    def save(self, token, login):
        encrypted = self._protector().encrypt(json.dumps({'token': token, 'login': login}).encode())
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(encrypted)
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def delete(self):
        self.path.unlink(missing_ok=True)
