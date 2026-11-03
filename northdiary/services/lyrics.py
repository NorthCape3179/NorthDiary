"""Opt-in Windows media observation and LRCLIB lookup; no diary access."""
import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
import json
import time

from PySide6.QtCore import QObject, QThread, Signal, QUrl, QUrlQuery
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from northdiary.services.tls import configure_tls
from northdiary.services.netease_progress import NetEaseProgressReader
from northdiary.services.lyric_data import parse_lrc, normalized
from northdiary.services.netease_lyrics import NetEaseLyricsClient



class MediaObserver(QThread):
    snapshot = Signal(object)
    unavailable = Signal(str)

    def run(self):
        try:
            from winrt.runtime import init_apartment, uninit_apartment, ApartmentType
            init_apartment(ApartmentType.MULTI_THREADED)
            try:
                asyncio.run(self.observe())
            finally:
                memory = getattr(self, 'memory_progress', None)
                if memory:
                    memory.close()
                uninit_apartment()
        except ImportError:
            self.unavailable.emit('缺少 Windows 媒体组件，请安装软件依赖后重启。')
        except Exception:
            self.unavailable.emit('暂时无法读取 Windows 媒体会话，关闭歌词后可重新开启。')

    async def observe(self):
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
        )
        manager = await asyncio.wait_for(Manager.request_async(), 5)
        self.memory_progress = NetEaseProgressReader()
        while not self.isInterruptionRequested():
            try:
                sessions = [s for s in manager.get_sessions() if any(
                    name in s.source_app_user_model_id.lower()
                    for name in ('cloudmusic', 'netease', '网易云', 'inflink'))]
                # A plugin and the native client may publish duplicate sessions.
                # Prefer the playing session that actually supplies a timeline.
                def session_rank(s):
                    t = s.get_timeline_properties()
                    return (s.get_playback_info().playback_status == Status.PLAYING,
                            t.end_time > t.start_time and t.last_updated_time.year >= 2000)
                session = max(sessions, key=session_rank) if sessions else None
                if session is None:
                    self.memory_progress.close()
                    self.snapshot.emit(None)
                else:
                    media = await asyncio.wait_for(session.try_get_media_properties_async(), 3)
                    timeline = session.get_timeline_properties()
                    info = session.get_playback_info()
                    playing = info.playback_status == Status.PLAYING
                    rate = info.playback_rate
                    rate = rate if rate is not None and rate > 0 else 1.0
                    start = timeline.start_time.total_seconds()
                    duration = max(0, timeline.end_time.total_seconds() - start)
                    position = max(0, timeline.position.total_seconds() - start)
                    known = duration > 0 and timeline.last_updated_time.year >= 2000
                    if playing and known:
                        updated = timeline.last_updated_time
                        if updated.tzinfo is None:
                            updated = updated.replace(tzinfo=timezone.utc)
                        elapsed = (datetime.now(timezone.utc) - updated).total_seconds()
                        if 0 <= elapsed < 86400:
                            position += elapsed * rate
                    sampled = time.monotonic()
                    progress_source = 'smtc' if known else ''
                    progress_detail = ''
                    if not known:
                        actual = self.memory_progress.read((media.title, media.artist, media.album_title), playing)
                        if actual:
                            position, duration, sampled = actual['position'], actual['duration'], actual['sampled']
                            known = True
                            progress_source = 'netease-memory'
                        else:
                            progress_detail = self.memory_progress.detail
                    elif self.memory_progress.candidates:
                        self.memory_progress.close()
                    self.snapshot.emit(dict(title=media.title, artist=media.artist,
                        album=media.album_title, duration=duration,
                        position=min(position, duration) if duration else position,
                        playing=playing, rate=rate, sampled=sampled,
                        position_known=known, progress_source=progress_source,
                        progress_detail=progress_detail))
            except Exception:
                self.unavailable.emit('等待网易云提供播放信息…')
            for _ in range(8):
                if self.isInterruptionRequested():
                    return
                await asyncio.sleep(.1)



def best_match(records, track):
    """Reject different recordings rather than taking the first search result."""
    candidates = []
    title, artist = normalized(track['title']), normalized(track['artist'])
    for row in records:
        if normalized(row.get('trackName', '')) != title:
            continue
        singers = normalized(row.get('artistName', ''))
        if not artist or not singers or artist != singers:
            continue
        difference = abs(float(row.get('duration') or 0) - track['duration'])
        if track['duration'] and difference > 2:
            continue
        score = (bool(row.get('syncedLyrics')), normalized(row.get('albumName', '')) == normalized(track['album']), -difference)
        candidates.append((score, row))
    return max(candidates, key=lambda pair: pair[0])[1] if candidates else None


class LyricsLookup(QObject):
    ready = Signal(object)
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        configure_tls()
        self.network = QNetworkAccessManager(self)
        self.reply = None
        self.generation = 0
        self.cache = OrderedDict()
        self.netease = NetEaseLyricsClient(self)
        self.netease.finished.connect(self.netease_finished)
        self.context = None
        self.fallback = None

    def cancel(self):
        self.generation += 1
        self.context = None
        self.netease.cancel()
        if self.reply:
            self.reply.abort()
            self.reply = None

    def fetch(self, track, force=False):
        self.cancel()
        key = (track['title'], track['artist'], track['album'], round(track['duration']))
        if not force and key in self.cache:
            self.ready.emit(self.cache[key])
            return
        self.fallback = None
        self.context = (dict(track), key, self.generation)
        self.message.emit('正在查找同步歌词与译文…')
        self.netease.fetch(track)

    def publish(self, key, result):
        self.cache[key] = result
        self.cache.move_to_end(key)
        while len(self.cache) > 48:
            self.cache.popitem(last=False)
        self.ready.emit(result)

    def netease_finished(self, result):
        if not self.context:
            return
        track, key, generation = self.context
        if generation != self.generation:
            return
        if result and (result['lines'] or result['message'].startswith('纯音乐')):
            self.publish(key, result)
        else:
            self.fallback = result
            self.message.emit('正在查询备用歌词源…')
            self.request(track, key, generation, False)

    def missing(self, key, message):
        if self.fallback:
            self.publish(key, self.fallback)
        else:
            detail = self.netease.last_error
            self.message.emit(detail + '；' + message if detail else message)

    def request(self, track, key, generation, search):
        configure_tls()
        url = QUrl('https://lrclib.net/api/search' if search else 'https://lrclib.net/api/get')
        query = QUrlQuery()
        query.addQueryItem('track_name', track['title'])
        query.addQueryItem('artist_name', track['artist'])
        if not search:
            if track['album']:
                query.addQueryItem('album_name', track['album'])
            if 1 <= track['duration'] <= 3600:
                query.addQueryItem('duration', str(round(track['duration'])))
        url.setQuery(query)
        request = QNetworkRequest(url)
        request.setRawHeader(b'User-Agent', b'NorthDiary/1.7.5 (Windows lyrics viewer)')
        request.setTransferTimeout(10000)
        reply = self.network.get(request)
        self.reply = reply

        def finished():
            try:
                if generation != self.generation:
                    return
                status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                if status == 404 and not search:
                    self.request(track, key, generation, True)
                    return
                if reply.error() != QNetworkReply.NetworkError.NoError:
                    detail = f'备用源请求失败（HTTP {status}）' if status else '备用源连接超时或网络中断'
                    self.missing(key, detail + '，可从顶部歌词菜单刷新。')
                    return
                data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                row = best_match(data, track) if search else data
                if not isinstance(row, dict):
                    self.missing(key, '未匹配到此版本的歌词。')
                    return
                if row.get('instrumental'):
                    result = {'lines': [], 'plain': [], 'message': '纯音乐 · 无歌词', 'source': 'LRCLIB', 'translations': {}}
                else:
                    lines = parse_lrc(row.get('syncedLyrics') or '')
                    plain = (row.get('plainLyrics') or '').splitlines()
                    result = {'lines': lines, 'plain': plain,
                              'message': '' if lines else '纯文本歌词 · 无时间轴 · 滚轮翻阅' if plain else '暂无歌词',
                              'source': 'LRCLIB', 'translations': {}}
                    if not lines and not search:
                        if plain:
                            self.fallback = result
                        self.request(track, key, generation, True)
                        return
                if not result['lines'] and not result['plain'] and self.fallback:
                    result = self.fallback
                self.publish(key, result)
            except (ValueError, TypeError, KeyError):
                self.missing(key, '歌词数据暂时不可用，可从顶部歌词菜单刷新。')
            finally:
                if self.reply is reply:
                    self.reply = None
                reply.deleteLater()

        reply.finished.connect(finished)
