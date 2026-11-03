"""Anonymous current-track lookup against NetEase's public web endpoints."""
import json
from PySide6.QtCore import QObject, Signal, QUrl, QUrlQuery
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from northdiary.services.lyric_data import normalized, parse_lrc, aligned_translations
from northdiary.services.tls import configure_tls


def matching_artists(credit, artists):
    remaining = normalized(credit)
    if not remaining or not artists:
        return False
    names = [normalized(a.get('name', '')) for a in artists]
    if remaining == ''.join(names):
        return True
    # Collaboration credits may use a different order or an official alias.
    for artist in sorted(artists, key=lambda a: len(a.get('name', '')), reverse=True):
        aliases = artist.get('alias') or []
        aliases = aliases if isinstance(aliases, list) else []
        choices = [normalized(v) for v in [artist.get('name', '')] + aliases if isinstance(v, str)]
        name = next((v for v in choices if v and v in remaining), None)
        if not name:
            return False
        remaining = remaining.replace(name, '', 1)
    return not remaining


def matching_songs(rows, track):
    candidates = []
    for row in rows:
        aliases = row.get('alias') or row.get('alia') or []
        aliases = aliases if isinstance(aliases, list) else []
        titles = [row.get('name', '')] + aliases
        artists = row.get('artists') or row.get('ar') or []
        if (normalized(track['title']) not in [normalized(t) for t in titles if isinstance(t, str)]
                or not matching_artists(track['artist'], artists)):
            continue
        duration = float(row.get('duration', row.get('dt', 0)) or 0) / 1000
        difference = abs(duration - track['duration'])
        if track['duration'] and (not duration or difference > 2):
            continue
        album = row.get('album', row.get('al', {})) or {}
        candidates.append(((normalized(album.get('name', '')) == normalized(track['album']), -difference), row))
    return [row for _, row in sorted(candidates, key=lambda item: item[0], reverse=True)][:2]


class NetEaseLyricsClient(QObject):
    finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        configure_tls()
        self.network = QNetworkAccessManager(self)
        self.reply = None
        self.generation = 0
        self.songs = []
        self.fallback = None
        self.last_error = ''

    def cancel(self):
        self.generation += 1
        if self.reply:
            self.reply.abort()
            self.reply = None

    def fetch(self, track):
        self.cancel()
        self.fallback = None
        self.songs = []
        self.last_error = ''
        self.search(track, False)

    def search(self, track, title_only):
        keywords = track['title'] if title_only else track['title'] + ' ' + track['artist']
        self.request('/api/search/get', dict(s=keywords, type=1, limit=50),
                     lambda data: self.searched(data, track, title_only), self.generation)

    def request(self, endpoint, args, callback, generation):
        url = QUrl('https://music.163.com' + endpoint)
        query = QUrlQuery()
        for name, value in args.items():
            query.addQueryItem(name, str(value))
        url.setQuery(query)
        req = QNetworkRequest(url)
        req.setRawHeader(b'User-Agent', b'Mozilla/5.0 NorthDiary/1.7.5')
        req.setRawHeader(b'Referer', b'https://music.163.com/')
        req.setTransferTimeout(8000)
        reply = self.network.get(req)
        self.reply = reply

        def done():
            try:
                if generation != self.generation:
                    return
                data = None
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    try:
                        data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                    except (ValueError, UnicodeError):
                        self.last_error = '网易云歌词数据格式异常'
                    if isinstance(data, dict) and data.get('code') != 200:
                        self.last_error = '网易云接口返回错误（' + str(data.get('code', '未知')) + '）'
                else:
                    status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                    self.last_error = f'网易云请求失败（HTTP {status}）' if status else '网易云连接超时或网络中断'
                try:
                    callback(data if isinstance(data, dict) and data.get('code') == 200 else None)
                except (ValueError, TypeError, KeyError, AttributeError):
                    self.last_error = '网易云歌词数据格式异常'
                    self.finished.emit(None)
            finally:
                if self.reply is reply:
                    self.reply = None
                reply.deleteLater()

        reply.finished.connect(done)

    def searched(self, data, track, title_only=False):
        rows = ((data or {}).get('result') or {}).get('songs', [])
        self.songs = matching_songs(rows, track)
        if data and not self.songs and not title_only:
            self.search(track, True)
            return
        if data and not self.songs:
            self.last_error = ('网易云候选的名称、歌手或时长与播放记录不一致' if rows
                               else '网易云未搜索到这首歌')
        self.next_song()

    def next_song(self):
        if not self.songs:
            if not self.fallback and not self.last_error:
                self.last_error = '网易云此版本暂无可用歌词'
            self.finished.emit(self.fallback)
            return
        song = self.songs.pop(0)
        self.request('/api/song/lyric', dict(id=song['id'], lv=-1, kv=-1, tv=-1),
                     self.got_lyrics, self.generation)

    def got_lyrics(self, data):
        if not data:
            self.next_song()
            return
        if data.get('nolyric'):
            self.finished.emit(dict(lines=[], plain=[], translations={}, source='网易云', message='纯音乐 · 无歌词'))
            return
        original = (data.get('lrc') or {}).get('lyric') or ''
        translated = (data.get('tlyric') or {}).get('lyric') or ''
        lines = parse_lrc(original)
        translations = aligned_translations(lines, parse_lrc(translated))
        if lines:
            self.finished.emit(dict(lines=lines, plain=[], translations=translations,
                                    source='网易云', message=''))
        else:
            if original.strip():
                self.fallback = dict(lines=[], plain=original.splitlines(), translations={},
                                     source='网易云', message='纯文本歌词 · 无时间轴 · 滚轮翻阅')
            self.next_song()
