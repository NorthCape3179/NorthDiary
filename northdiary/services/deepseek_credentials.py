"""Device-local key, outside diary data, backups and GitHub article packages."""
import json
import os
import tempfile
from pathlib import Path

from northdiary.services.credentials import CredentialError, WindowsDPAPI


class DeepSeekCredentialStore:
    def __init__(self, root=None, protector=None):
        self.root = Path(root) if root is not None else Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'NorthDiary' / 'device-secrets'
        self.path = self.root / 'deepseek.credentials'
        self.protector = protector

    def crypt(self):
        return self.protector or WindowsDPAPI()

    def load(self):
        if not self.path.exists():
            return None
        try:
            if self.path.stat().st_size > 64 * 1024:
                raise ValueError()
            key = json.loads(self.crypt().decrypt(self.path.read_bytes()))['api_key']
            self.validate(key)
            return key
        except (ValueError, KeyError, TypeError, OSError):
            raise CredentialError('无法读取本机 DeepSeek 密钥，请重新配置。') from None

    @staticmethod
    def validate(key):
        if not isinstance(key, str) or not key or len(key) > 512 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in key):
            raise ValueError('API Key 不能为空，且不能包含空格、换行或非英文字符。')

    def save(self, key):
        self.validate(key)
        content = self.crypt().encrypt(json.dumps({'api_key': key}).encode('utf-8'))
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.root, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def delete(self):
        self.path.unlink(missing_ok=True)
