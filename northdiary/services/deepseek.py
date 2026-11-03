"""DeepSeek-only asynchronous HTTPS and SSE. No diary or credential persistence here."""
import json

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from northdiary.services.tls import configure_tls


DEFAULT_MODELS = ('deepseek-flash', 'deepseek-v4-pro')
ERRORS = {
    400: '请求内容或上下文长度不被接受，请减少文章、缩短输入或新建对话。',
    401: 'API Key 无效或已失效，请在 API 设置中重新配置。',
    402: 'DeepSeek API 余额不足，请到开放平台检查余额。',
    403: '当前 API Key 没有访问权限。',
    404: '模型或接口不存在，请测试连接并重新选择模型。',
    413: '请求内容过大，请减少文章或新建对话。',
    422: '模型不支持当前参数，请检查模型和输出长度。',
    429: '请求过于频繁，请稍后手动重试。',
    500: 'DeepSeek 服务暂时出错，请稍后手动重试。',
    503: 'DeepSeek 服务繁忙，请稍后手动重试。',
}


class DeepSeekClient(QObject):
    delta = Signal(str)
    thinking = Signal()
    completed = Signal(dict)
    failed = Signal(str)
    modelsReady = Signal(list)

    def __init__(self, parent=None, base_url='https://api.deepseek.com'):
        super().__init__(parent)
        configure_tls()
        # base_url is injectable for a local protocol test; the UI never exposes it.
        self.base_url = base_url.rstrip('/')
        self.manager = QNetworkAccessManager(self)
        self.reply = None
        self.reset()

    @property
    def busy(self):
        return self.reply is not None

    def reset(self):
        self.buffer = b''
        self.body = b''
        self.content = ''
        self.usage = None
        self.model = ''
        self.finish_reason = None
        self.done = False
        self.cancelled = False
        self.protocol_error = ''
        self.received = 0
        self.kind = ''

    def start(self, api_key, payload=None):
        if self.busy:
            raise RuntimeError('已有请求正在进行')
        if not isinstance(api_key, str) or not api_key or len(api_key) > 512 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in api_key):
            raise ValueError('请先配置有效的 API Key')
        self.reset()
        self.kind = 'chat' if payload is not None else 'models'
        request = QNetworkRequest(QUrl(self.base_url + ('/chat/completions' if payload is not None else '/models')))
        request.setRawHeader(b'Authorization', ('Bearer ' + api_key).encode('ascii'))
        request.setRawHeader(b'Content-Type', b'application/json')
        request.setRawHeader(b'Accept', b'text/event-stream' if payload is not None else b'application/json')
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        request.setTransferTimeout(90_000)
        self.reply = self.manager.post(request, payload) if payload is not None else self.manager.get(request)
        self.reply.readyRead.connect(self.read)
        self.reply.finished.connect(self.finish)

    def stop(self):
        if self.reply is not None:
            self.cancelled = True
            self.reply.abort()

    def read(self):
        if self.reply is None or not self.reply.isOpen():
            return
        data = bytes(self.reply.readAll())
        self.received += len(data)
        if self.cancelled:
            return
        if self.received > 8 * 1024 * 1024:
            self.protocol_error = '响应超过本客户端的安全处理上限，请缩短输出。'
            self.reply.abort()
            return
        status = self.reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
        if self.kind == 'models' or status != 200:
            self.body += data
            return
        self.buffer += data
        # Normalize CRLF without corrupting a CR split across TCP chunks.
        self.buffer = self.buffer.replace(b'\r\n', b'\n')
        while b'\n\n' in self.buffer:
            event, self.buffer = self.buffer.split(b'\n\n', 1)
            lines = [line[5:].lstrip(b' ') for line in event.split(b'\n') if line.startswith(b'data:')]
            if not lines:
                continue  # Heartbeats and comments do not contain data.
            raw = b'\n'.join(lines)
            if raw == b'[DONE]':
                self.done = True
                continue
            try:
                packet = json.loads(raw.decode('utf-8'))
                if not isinstance(packet, dict) or 'error' in packet:
                    raise ValueError()
                if packet.get('usage') is not None:
                    self.usage = packet['usage']
                self.model = packet.get('model') or self.model
                for choice in packet.get('choices', []):
                    delta = choice.get('delta') or {}
                    chunk = delta.get('content') or ''
                    if not isinstance(chunk, str):
                        raise ValueError()
                    if chunk:
                        self.content += chunk
                        self.delta.emit(chunk)
                    if delta.get('reasoning_content'):
                        self.thinking.emit()
                    if choice.get('finish_reason'):
                        self.finish_reason = choice['finish_reason']
            except (ValueError, TypeError, AttributeError, UnicodeError):
                self.protocol_error = '收到无法解析的流式响应，已保留当前内容，请手动重试。'
                self.reply.abort()
                break

    def finish(self):
        reply = self.reply
        if reply is None:
            return
        self.read()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
        network_error = reply.error() != QNetworkReply.NetworkError.NoError
        self.reply = None
        reply.deleteLater()
        if self.cancelled:
            self.completed.emit(self.result('stopped'))
        elif self.protocol_error:
            self.failed.emit(self.protocol_error)
        elif status != 200:
            self.failed.emit(ERRORS.get(status, '连接失败，请检查网络、系统代理与证书后重试。' if not status else f'DeepSeek 请求失败（HTTP {status}），请稍后重试。'))
        elif network_error:
            self.failed.emit('网络中断或请求超时，已保留当前内容，请手动重试。')
        elif self.kind == 'models':
            try:
                rows = json.loads(self.body.decode('utf-8'))['data']
                models = list(dict.fromkeys(r['id'] for r in rows if isinstance(r.get('id'), str) and r['id']))
                if not models:
                    raise ValueError()
                self.modelsReady.emit(models)
            except (ValueError, KeyError, TypeError, AttributeError, UnicodeError):
                self.failed.emit('连接成功，但模型清单无法解析，请稍后重试。')
        elif not self.done or not self.finish_reason:
            self.failed.emit('响应提前结束，已保留当前内容；本次不会作为完整回复加入后续上下文。')
        elif self.finish_reason not in ('stop', 'length'):
            self.failed.emit('模型未正常完成回复（' + self.finish_reason + '），已保留当前内容。')
        else:
            self.completed.emit(self.result('complete' if self.finish_reason == 'stop' and self.content.strip() else 'incomplete'))

    def result(self, status):
        return {'status': status, 'content': self.content, 'usage': self.usage,
                'model': self.model, 'finish_reason': self.finish_reason}
