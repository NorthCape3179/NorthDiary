"""Manual private-repository package transfer, without a server or git client."""
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

from northdiary.services.native_format import (
    FORMAT, FORMAT_VERSION, MANIFEST_PATH, MAX_MANIFEST, MAX_MEMBER, MAX_TOTAL,
)

MAX_PACKAGE = 20 * 1024 * 1024
MARKER_PATH = 'northdiary-data.json'
MARKER = {'format': 'NorthDiaryData', 'version': 1}
PACKAGE_PATTERN = re.compile(r'[0-9]{8}T[0-9]{12}Z-[0-9a-f]{32}\.epub')


class GitHubError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a private token to a redirected host.
        raise GitHubError('GitHub 返回了意外跳转，已停止请求')


class GitHubHTTP:
    def __init__(self, opener=None):
        self.opener = opener or build_opener(NoRedirect())

    def request(self, method, url, *, token='', data=None, form=False, raw=False, limit=2 * 1024 * 1024):
        if not (url.startswith('https://api.github.com/') or url in (
                'https://github.com/login/device/code', 'https://github.com/login/oauth/access_token')):
            raise GitHubError('不允许的 GitHub 请求地址')
        headers = {'Accept': 'application/vnd.github.raw+json' if raw else 'application/json',
                   'User-Agent': 'NorthDiary', 'X-GitHub-Api-Version': '2022-11-28'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        body = None
        if data is not None:
            body = urlencode(data).encode() if form else json.dumps(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                payload = response.read(limit + 1)
                if len(payload) > limit:
                    raise GitHubError('GitHub 响应超过大小限制')
                return payload if raw else json.loads(payload)
        except HTTPError as error:
            messages = {401: 'GitHub 登录已失效，请重新连接',
                        403: 'GitHub 拒绝访问：请检查仓库权限或稍后重试',
                        404: 'GitHub 仓库或文件不存在，或当前账号无权访问',
                        409: '远端记录发生冲突，请刷新后重试',
                        422: 'GitHub 未接受此操作，请检查名称或刷新仓库记录',
                        429: 'GitHub 请求过于频繁，请稍后重试'}
            raise GitHubError(messages.get(error.code, f'GitHub 请求失败（HTTP {error.code}）'), error.code) from None
        except (URLError, TimeoutError, OSError):
            # Request/response bodies and credentials must not enter diagnostics.
            raise GitHubError('无法连接 GitHub。请检查网络；若正在上传，请先刷新远端记录确认结果再重试') from None
        except (ValueError, UnicodeError):
            raise GitHubError('GitHub 返回了无法识别的响应') from None


@dataclass(frozen=True)
class DeviceChallenge:
    user_code: str
    device_code: str = field(repr=False)
    verification_uri: str
    interval: int
    expires_in: int


class DeviceLogin:
    def __init__(self, client_id, http=None):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', client_id):
            raise GitHubError('请先填写有效的 GitHub 应用 Client ID')
        self.client_id = client_id
        self.http = http or GitHubHTTP()

    def start(self):
        result = self.http.request('POST', 'https://github.com/login/device/code', form=True,
                                   data={'client_id': self.client_id, 'scope': 'repo'})
        try:
            if result.get('error'):
                raise GitHubError('GitHub 应用尚未启用设备授权，或 Client ID 无效')
            uri = result['verification_uri']
            if uri != 'https://github.com/login/device':
                raise GitHubError('GitHub 返回了非预期的登录页面')
            interval, expires = int(result.get('interval', 5)), int(result['expires_in'])
            code, device = result['user_code'], result['device_code']
            if not (5 <= interval <= 60 and 1 <= expires <= 1800
                    and isinstance(code, str) and re.fullmatch(r'[A-Z0-9-]{4,32}', code)
                    and isinstance(device, str) and 0 < len(device) <= 1024):
                raise ValueError()
            return DeviceChallenge(code, device, uri, interval, expires)
        except (KeyError, TypeError, ValueError):
            raise GitHubError('GitHub 设备授权响应无效') from None

    def poll(self, challenge):
        result = self.http.request('POST', 'https://github.com/login/oauth/access_token', form=True,
                                   data={'client_id': self.client_id, 'device_code': challenge.device_code,
                                         'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'})
        state = result.get('error')
        if state in ('authorization_pending', 'slow_down'):
            return state, None
        if state:
            messages = {'expired_token': '登录验证码已过期，请重新开始',
                        'access_denied': '你已取消 GitHub 授权',
                        'incorrect_client_credentials': 'GitHub 应用 Client ID 无效'}
            raise GitHubError(messages.get(state, 'GitHub 授权未完成，请重新开始'))
        token = result.get('access_token')
        if not isinstance(token, str) or not token or result.get('token_type', '').lower() != 'bearer':
            raise GitHubError('GitHub 未返回有效的访问凭据')
        scopes = [scope.strip() for scope in result.get('scope', '').split(',')]
        if 'repo' not in scopes:
            raise GitHubError('此次授权缺少私有数据仓库读写权限')
        return 'connected', token


def repository_name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}', value):
        raise GitHubError('仓库请填写为 账号/仓库名')
    owner, name = value.split('/')
    if name in ('.', '..') or name.lower() == 'northdiary':
        raise GitHubError('请使用独立的数据仓库，例如 NorthDiary-Data；不能选择 NorthDiary 源码仓库')
    return owner, name


def git_blob_sha(content):
    return hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()


def validate_package(content):
    if not content or len(content) > MAX_PACKAGE:
        raise GitHubError('文章包必须小于等于 20 MiB，请减少文章或图片后分批上传')
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if (len(members) > 5000 or sum(item.file_size for item in members) > MAX_TOTAL
                    or any(item.file_size > MAX_MEMBER for item in members)
                    or archive.getinfo(MANIFEST_PATH).file_size > MAX_MANIFEST
                    or archive.getinfo('mimetype').file_size != len(b'application/epub+zip')):
                raise ValueError()
            manifest = json.loads(archive.read(MANIFEST_PATH))
            if (not isinstance(manifest, dict) or archive.read('mimetype') != b'application/epub+zip' or manifest.get('format') != FORMAT
                    or type(manifest.get('version')) is not int or manifest['version'] not in (1, 2, FORMAT_VERSION)):
                raise ValueError()
    except (BadZipFile, KeyError, ValueError, TypeError, UnicodeError, RecursionError):
        raise GitHubError('仅允许传输 NorthDiary 新版原生 EPUB 文章包') from None


@dataclass(frozen=True)
class RemotePackage:
    name: str
    path: str
    sha: str
    size: int
    commit: str


class GitHubPackages:
    def __init__(self, token, http=None):
        self._token = token
        self.http = http or GitHubHTTP()

    def _api(self, method, path, **kwargs):
        return self.http.request(method, 'https://api.github.com' + path, token=self._token, **kwargs)

    def user(self):
        result = self._api('GET', '/user')
        login = result.get('login')
        if not isinstance(login, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,39}', login):
            raise GitHubError('GitHub 账号信息无效')
        return login

    def _repo(self, repository):
        repository_name(repository)
        result = self._api('GET', '/repos/' + repository)
        if result.get('private') is not True:
            raise GitHubError('日记只能上传到私有数据仓库，请先将仓库设为 Private')
        branch = result.get('default_branch')
        if not isinstance(branch, str) or not branch or len(branch) > 255:
            raise GitHubError('仓库默认分支无效')
        return result

    def _contents(self, repository, path, ref=None, **kwargs):
        url = '/repos/' + repository + '/contents/' + quote(path, safe='/')
        if ref is not None:
            url += '?' + urlencode({'ref': ref})
        return self._api('GET', url, **kwargs)

    def check_repository(self, repository):
        metadata = self._repo(repository)
        marker = self._contents(repository, MARKER_PATH, metadata['default_branch'], raw=True, limit=4096)
        try:
            value = json.loads(marker)
        except (ValueError, UnicodeError):
            raise GitHubError('仓库的 NorthDiary 数据标识已损坏') from None
        if value != MARKER or type(value.get('version')) is not int:
            raise GitHubError('此仓库不是受支持的 NorthDiary 数据仓库')
        return metadata

    def initialize_repository(self, repository):
        """Explicit UI action: mark an empty private repo, never a source repo."""
        metadata = self._repo(repository)
        try:
            return self.check_repository(repository)
        except GitHubError as error:
            if error.status != 404:
                raise
        try:
            entries = self._contents(repository, '')
        except GitHubError as error:
            if error.status != 404:
                raise
            entries = []
        if entries != []:
            raise GitHubError('这个仓库已有其他文件，不能初始化；请选择空的私有数据仓库')
        self._api('PUT', '/repos/' + repository + '/contents/' + MARKER_PATH,
                  data={'message': 'Initialize NorthDiary data repository',
                        'content': base64.b64encode(json.dumps(MARKER).encode()).decode()})
        return self.check_repository(repository)

    def create_repository(self, name):
        login = self.user()
        repository_name(login + '/' + name)
        result = self._api('POST', '/user/repos',
                           data={'name': name, 'private': True, 'auto_init': False,
                                 'description': 'Private NorthDiary article packages'})
        full_name = result.get('full_name')
        if full_name != login + '/' + name or result.get('private') is not True:
            raise GitHubError('GitHub 未返回预期的私有仓库，请到网页检查创建结果')
        self.initialize_repository(full_name)
        return full_name

    def list_packages(self, repository):
        metadata = self.check_repository(repository)
        branch = quote(metadata['default_branch'], safe='')
        head = self._api('GET', '/repos/' + repository + '/branches/' + branch)['commit']['sha']
        if not re.fullmatch(r'[0-9a-f]{40}', head):
            raise GitHubError('GitHub 分支版本无效')
        try:
            rows = self._contents(repository, 'packs', head)
        except GitHubError as error:
            if error.status == 404:
                return []
            raise
        if not isinstance(rows, list) or len(rows) >= 1000:
            raise GitHubError('远端文章包列表无效或过多，请使用新的数据仓库归档')
        packages = []
        for row in rows:
            if row.get('type') != 'file' or not PACKAGE_PATTERN.fullmatch(row.get('name', '')):
                continue
            name, sha, size = row['name'], row.get('sha'), row.get('size')
            if (row.get('path') != 'packs/' + name or not isinstance(sha, str)
                    or not re.fullmatch(r'[0-9a-f]{40}', sha)
                    or type(size) is not int or not 0 < size <= MAX_PACKAGE):
                raise GitHubError('远端文章包信息无效或超过 20 MiB')
            packages.append(RemotePackage(name, 'packs/' + name, sha, size, head))
        return sorted(packages, key=lambda item: item.name, reverse=True)

    def upload(self, repository, content):
        validate_package(content)
        metadata = self.check_repository(repository)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        name = stamp + '-' + uuid4().hex + '.epub'
        result = self._api('PUT', '/repos/' + repository + '/contents/packs/' + name,
                           data={'message': 'Upload NorthDiary article package',
                                 'branch': metadata['default_branch'],
                                 'content': base64.b64encode(content).decode()})
        if result.get('content', {}).get('sha') != git_blob_sha(content):
            raise GitHubError('上传响应未能核对，请刷新远端记录确认结果后再重试')
        return name

    def download(self, repository, package):
        self.check_repository(repository)
        if (not isinstance(package, RemotePackage) or not PACKAGE_PATTERN.fullmatch(package.name)
                or package.path != 'packs/' + package.name
                or not re.fullmatch(r'[0-9a-f]{40}', package.commit)
                or not re.fullmatch(r'[0-9a-f]{40}', package.sha)
                or not 0 < package.size <= MAX_PACKAGE):
            raise GitHubError('请先刷新并选择有效的远端文章包')
        content = self._contents(repository, package.path, package.commit, raw=True, limit=MAX_PACKAGE)
        if len(content) != package.size or git_blob_sha(content) != package.sha:
            raise GitHubError('下载校验失败，未写入本机文章')
        validate_package(content)
        return content
