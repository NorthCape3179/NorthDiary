"""An optional embedded scene; journal storage and music lookup stay native."""
import json
import math
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog


class _Host(QObject):
    message = Signal(str)

    def __init__(self, scene):
        super().__init__(scene)
        self.scene = scene

    @Slot()
    def ready(self):
        self.scene.ready = True
        self.scene.startup_timer.stop()
        self.scene.error.hide()
        self.scene.retry.hide()
        self.scene.send_state()

    @Slot(bool)
    def setLyricsEnabled(self, enabled):
        if self.scene.active:
            self.scene.lyricsToggled.emit(enabled)


class AutumnScene(QWidget):
    lyricsToggled = Signal(bool)

    def __init__(self, board, lyrics_button, parent=None):
        super().__init__(parent)
        self.board, self.lyrics_button = board, lyrics_button
        self.active = self.ready = False
        self.view = self.assets = self.profile = None
        self.setMinimumSize(0, 0)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.error = QLabel('正在准备秋日湖畔…')
        self.error.setWordWrap(True)
        self.layout.addWidget(self.error)
        self.retry = QPushButton('重新加载场景')
        self.retry.clicked.connect(self.reload)
        self.retry.hide()
        self.layout.addWidget(self.retry)
        self.host = _Host(self)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.send_state)
        self.startup_timer = QTimer(self)
        self.startup_timer.setSingleShot(True)
        self.startup_timer.setInterval(30000)
        self.startup_timer.timeout.connect(lambda: self.show_error('场景加载较慢或显卡不支持 WebGL，可点击重新加载。'))

    def initialize(self):
        # Lazy loading keeps the journal usable if WebEngine is unavailable.
        from PySide6.QtWebEngineCore import (
            QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
            QWebEngineUrlRequestInterceptor,
        )
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebChannel import QWebChannel
        from northdiary.services.scene_assets import SceneAssets

        assets_root = Path(__file__).resolve().parent.parent / 'assets'
        self.assets = SceneAssets(assets_root / 'autumn-scene', assets_root / 'lyrics-fonts')
        origin = QUrl(self.assets.url)

        class LocalOnly(QWebEngineUrlRequestInterceptor):
            def interceptRequest(self, info):
                url = info.requestUrl()
                local = (url.scheme() == 'http' and url.host() == '127.0.0.1'
                         and url.port() == origin.port() and url.path().startswith(origin.path()))
                internal = url.scheme() in ('blob', 'data') or url.toString() == 'qrc:///qtwebchannel/qwebchannel.js'
                info.block(not (local or internal))

        class LocalPage(QWebEnginePage):
            def acceptNavigationRequest(self, url, kind, main_frame):
                return (url.scheme() == 'http' and url.host() == origin.host()
                        and url.port() == origin.port() and url.path().startswith(origin.path()))

        self.profile = QWebEngineProfile(self)  # Off-the-record; no persistent browser account.
        self.interceptor = LocalOnly(self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile.downloadRequested.connect(self.download)
        self.view = QWebEngineView(self)
        self.page = LocalPage(self.profile, self.view)
        self.view.setPage(self.page)
        self.page.setBackgroundColor(QColor('#182522'))
        settings = self.page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject('northDiaryHost', self.host)
        self.page.setWebChannel(self.channel)
        self.view.loadFinished.connect(self.loaded)
        self.page.loadingChanged.connect(self.loading_changed)
        self.page.renderProcessTerminated.connect(lambda *_: self.show_error('场景渲染已中断，可重新加载；日记内容仍保留。'))
        self.layout.addWidget(self.view, 1)
        self.view.setUrl(origin)

    def set_active(self, enabled):
        self.active = enabled
        if enabled:
            try:
                if self.view is None:
                    self.initialize()
                self.timer.start()
            except Exception as error:
                self.show_error('秋日湖畔暂时无法打开：' + str(error))
        else:
            self.timer.stop()
        self.send_state()

    def click_control(self, name):
        if self.active and self.ready:
            button_id = json.dumps(name)
            self.page.runJavaScript(f'document.getElementById({button_id})?.click()')

    def loaded(self, ok):
        if not ok:
            self.show_error('秋日湖畔页面加载失败，请重新加载。')
        elif not self.ready:
            self.startup_timer.start()

    def loading_changed(self, info):
        if info.errorCode():
            self.show_error('秋日湖畔页面加载失败：' + info.errorString())

    def show_error(self, message):
        if self.ready and self.startup_timer.isActive():
            return
        self.error.setText(message)
        self.error.show()
        self.retry.show()

    def reload(self):
        if self.view is not None:
            self.ready = False
            self.error.setText('正在重新加载秋日湖畔…')
            self.retry.hide()
            self.view.reload()
        else:
            self.set_active(True)

    def send_state(self):
        if not self.ready:
            return
        self.startup_timer.stop()
        enabled = self.active and self.lyrics_button.isChecked()
        b = self.board
        track = b.track if enabled else None
        playback = None
        if enabled:
            duration = max(0., float((track or {}).get('duration') or 0))
            position = b.position() if track else 0
            position = max(0., position + b.offset.value() / 1000)
            lines = [{'timeMs': round(max(0, stamp) * 1000), 'text': text[:500],
                      'translation': b.translations.get(stamp, '')[:500]}
                     for stamp, text in b.lines[:500] if math.isfinite(stamp) and stamp >= 0]
            duration = max(duration, position, (lines[-1]['timeMs'] / 1000 if lines else 0))
            playback = {
                'title': str((track or {}).get('title') or '网易云音乐')[:200],
                'artist': str((track or {}).get('artist') or '')[:200],
                'durationMs': min(86400000, round(duration * 1000)),
                'positionMs': min(86400000, round(position * 1000)),
                'playing': bool(track and track.get('playing')),
                'positionKnown': bool(track and track.get('position_known', True)),
                'status': ((track.get('progress_detail') or '等待网易云提供准确播放进度')
                           if track and not track.get('position_known', True) else b.message or '等待歌词')[:500],
                'lines': lines,
                'font': b.font_choice.currentData() or 'fusion-pixel',
                'fontSize': b.font_size.value(),
            }
        self.host.message.emit(json.dumps({'type': 'hostState', 'active': self.active,
                                          'lyricsEnabled': enabled, 'playback': playback}, ensure_ascii=False))

    def download(self, item):
        # Only the scene's explicit parameter-export action can create a download.
        if item.suggestedFileName() != 'autumn_day.scene.json' or not item.url().scheme() == 'blob':
            item.cancel()
            return
        path, _ = QFileDialog.getSaveFileName(self, '导出秋日湖畔参数', 'autumn_day.scene.json', 'JSON (*.json)')
        if not path:
            item.cancel()
            return
        target = Path(path)
        item.setDownloadDirectory(str(target.parent))
        item.setDownloadFileName(target.name)
        item.accept()

    def shutdown(self):
        self.active = False
        self.timer.stop()
        self.startup_timer.stop()
        self.send_state()
        if self.view:
            self.view.stop()
            # Destroy the page before its off-the-record profile.
            self.view.setPage(None)
            self.page.deleteLater()
            self.view.deleteLater()
            self.view = None
        if self.assets:
            self.assets.close()
            self.assets = None
