import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from zipfile import ZipFile

from northdiary.services.github_sync import (
    GitHubHTTP, GitHubError, GitHubPackages, DeviceLogin, DeviceChallenge,
    RemotePackage, MARKER, MAX_PACKAGE, MANIFEST_PATH, git_blob_sha, NoRedirect,
)
from northdiary.services.credentials import GitHubCredentialStore, CredentialError, WindowsDPAPI

REPO = 'tester/NorthDiary-Data'
COMMIT = 'a' * 40
NAME = '20261030T050000000000Z-' + 'b' * 32 + '.epub'


def package():
    stream = io.BytesIO()
    with ZipFile(stream, 'w') as archive:
        archive.writestr('mimetype', b'application/epub+zip')
        archive.writestr(MANIFEST_PATH, json.dumps({'format': 'NorthDiary-EPUB', 'version': 1, 'articles': []}))
    return stream.getvalue()


class FakeHTTP:
    def __init__(self):
        self.calls = []
        self.private = True
        self.marker = True
        self.root = []
        self.rows = []
        self.content = package()
        self.fail_put = False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if method == 'PUT':
            if self.fail_put:
                raise GitHubError('远端冲突', 409)
            if url.endswith('northdiary-data.json'):
                self.marker = True
                return {}
            content = base64.b64decode(kwargs['data']['content'])
            return {'content': {'sha': git_blob_sha(content)}}
        if method == 'POST' and url.endswith('/user/repos'):
            return {'full_name': REPO, 'private': True}
        if url.endswith('/user'):
            return {'login': 'tester'}
        if '/branches/' in url:
            return {'commit': {'sha': COMMIT}}
        if '/contents/northdiary-data.json' in url:
            if not self.marker:
                raise GitHubError('missing', 404)
            return json.dumps(MARKER).encode()
        if '/contents/packs/' in url:
            return self.content
        if '/contents/packs?' in url:
            return self.rows
        if url.endswith('/contents/'):
            return self.root
        return {'private': self.private, 'default_branch': 'main'}


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.http = FakeHTTP()
        self.client = GitHubPackages('test-only-token', self.http)

    def test_upload_is_private_append_only_and_never_sends_sha_overwrite(self):
        content = package()
        first = self.client.upload(REPO, content)
        second = self.client.upload(REPO, content)
        self.assertNotEqual(first, second)
        writes = [call for call in self.http.calls if call[0] == 'PUT']
        self.assertEqual(len(writes), 2)
        self.assertNotIn('sha', writes[0][2]['data'])
        self.assertEqual(base64.b64decode(writes[0][2]['data']['content']), content)
        self.assertTrue(all(call[2]['token'] == 'test-only-token' for call in self.http.calls))

    def test_public_and_source_repositories_rejected_before_any_write(self):
        self.http.private = False
        with self.assertRaisesRegex(GitHubError, '私有'):
            self.client.upload(REPO, package())
        with self.assertRaisesRegex(GitHubError, '源码仓库'):
            self.client.upload('tester/NorthDiary', package())
        self.assertFalse(any(call[0] == 'PUT' for call in self.http.calls))

    def test_initialize_only_empty_private_repo_and_reuses_valid_marker(self):
        self.http.marker = False
        self.http.root = [{'name': 'source.py'}]
        with self.assertRaisesRegex(GitHubError, '已有其他文件'):
            self.client.initialize_repository(REPO)
        self.assertFalse(any(call[0] == 'PUT' for call in self.http.calls))
        self.http.root = []
        self.client.initialize_repository(REPO)
        writes = [call for call in self.http.calls if call[0] == 'PUT']
        self.assertEqual(json.loads(base64.b64decode(writes[0][2]['data']['content'])), MARKER)
        self.client.initialize_repository(REPO)
        self.assertEqual(len([call for call in self.http.calls if call[0] == 'PUT']), 1)

    def test_create_is_private_and_validates_name(self):
        self.assertEqual(self.client.create_repository('NorthDiary-Data'), REPO)
        created = next(call for call in self.http.calls if call[0] == 'POST')
        self.assertTrue(created[2]['data']['private'])
        for name in ('../escape', 'https://evil.test/x', 'NorthDiary'):
            with self.assertRaises(GitHubError):
                self.client.create_repository(name)

    def test_listing_pins_commit_and_download_checks_git_blob_sha(self):
        content = self.http.content
        self.http.rows = [{'name': NAME, 'path': 'packs/' + NAME, 'type': 'file',
                           'sha': git_blob_sha(content), 'size': len(content)}]
        row = self.client.list_packages(REPO)[0]
        self.assertEqual(row.commit, COMMIT)
        self.assertEqual(self.client.download(REPO, row), content)
        raw = next(call for call in self.http.calls if '/contents/packs/' in call[1])
        self.assertIn('ref=' + COMMIT, raw[1])
        self.assertTrue(raw[2]['raw'])
        self.assertNotIn('download_url', raw[1])
        self.http.content = b'tampered'
        with self.assertRaisesRegex(GitHubError, '校验失败'):
            self.client.download(REPO, row)

    def test_bad_package_oversize_and_unexpected_remote_paths_rejected(self):
        with self.assertRaises(GitHubError):
            self.client.upload(REPO, b'not an epub')
        with patch('northdiary.services.github_sync.MAX_PACKAGE', 10), self.assertRaises(GitHubError):
            self.client.upload(REPO, package())
        bad = RemotePackage(NAME, '../escape', 'b' * 40, 100, COMMIT)
        with self.assertRaises(GitHubError):
            self.client.download(REPO, bad)
        self.http.rows = [{'name': NAME, 'path': '../escape', 'type': 'file', 'sha': 'b' * 40, 'size': 100}]
        with self.assertRaises(GitHubError):
            self.client.list_packages(REPO)

    def test_upload_conflict_is_not_retried_or_overwritten(self):
        self.http.fail_put = True
        with self.assertRaises(GitHubError):
            self.client.upload(REPO, package())
        self.assertEqual(len([call for call in self.http.calls if call[0] == 'PUT']), 1)


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.responses = []
        self.calls = []
        outer = self

        class HTTP:
            def request(self, *args, **kwargs):
                outer.calls.append((args, kwargs))
                return outer.responses.pop(0)

        self.auth = DeviceLogin('test-client-id', HTTP())
        self.challenge = DeviceChallenge('ABCD-EFGH', 'test-device', 'https://github.com/login/device', 5, 900)

    def test_device_flow_no_secret_and_pending_slowdown_success(self):
        self.responses = [{'user_code': 'ABCD-EFGH', 'device_code': 'test-device',
                           'verification_uri': 'https://github.com/login/device', 'interval': 5, 'expires_in': 900},
                          {'error': 'authorization_pending'}, {'error': 'slow_down'},
                          {'access_token': 'test-token', 'token_type': 'bearer', 'scope': 'gist, repo'}]
        challenge = self.auth.start()
        self.assertEqual(self.auth.poll(challenge), ('authorization_pending', None))
        self.assertEqual(self.auth.poll(challenge), ('slow_down', None))
        self.assertEqual(self.auth.poll(challenge), ('connected', 'test-token'))
        self.assertTrue(all('client_secret' not in call[1]['data'] for call in self.calls))
        self.assertNotIn('test-device', repr(challenge))

    def test_error_codes_and_foreign_login_url_rejected(self):
        for state in ('expired_token', 'access_denied', 'incorrect_client_credentials'):
            self.responses = [{'error': state}]
            with self.assertRaises(GitHubError):
                self.auth.poll(self.challenge)
        self.responses = [{'user_code': 'ABCD-EFGH', 'device_code': 'test-device',
                           'verification_uri': 'https://evil.test/login', 'interval': 5, 'expires_in': 900}]
        with self.assertRaises(GitHubError):
            self.auth.start()

    def test_missing_private_scope_or_empty_client_id_rejected(self):
        with self.assertRaises(GitHubError):
            DeviceLogin('')
        self.responses = [{'access_token': 'test-token', 'token_type': 'bearer', 'scope': 'read:user'}]
        with self.assertRaises(GitHubError):
            self.auth.poll(self.challenge)


class HTTPTests(unittest.TestCase):
    def test_transport_fixed_hosts_no_redirects_and_response_limit(self):
        class Response(io.BytesIO):
            pass

        class Opener:
            def open(self, request, timeout):
                self.request, self.timeout = request, timeout
                return Response(b'{"login":"tester"}')

        opener = Opener()
        http = GitHubHTTP(opener)
        self.assertEqual(http.request('GET', 'https://api.github.com/user', token='test-token')['login'], 'tester')
        self.assertEqual(opener.request.get_header('Authorization'), 'Bearer test-token')
        self.assertEqual(opener.timeout, 30)
        with self.assertRaises(GitHubError):
            http.request('GET', 'https://evil.test/', token='test-token')
        with self.assertRaises(GitHubError):
            http.request('GET', 'https://api.github.com/user', limit=1)
        with self.assertRaises(GitHubError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.test/')

    def test_network_errors_never_echo_response_or_credentials(self):
        class Opener:
            def open(self, request, timeout):
                raise HTTPError(request.full_url, 401, 'test-sensitive-body', {}, io.BytesIO(b'test-token'))

        with self.assertRaises(GitHubError) as error:
            GitHubHTTP(Opener()).request('GET', 'https://api.github.com/user', token='test-token')
        self.assertEqual(error.exception.status, 401)
        self.assertNotIn('test-token', str(error.exception))
        self.assertNotIn('test-sensitive-body', str(error.exception))


class CredentialTests(unittest.TestCase):
    def test_encrypted_storage_and_delete_with_injected_protector(self):
        class Protector:
            def encrypt(self, value):
                return b'encrypted:' + bytes(byte ^ 0x55 for byte in value)

            def decrypt(self, value):
                return bytes(byte ^ 0x55 for byte in value.removeprefix(b'encrypted:'))

        with tempfile.TemporaryDirectory() as directory:
            store = GitHubCredentialStore(Path(directory), Protector())
            self.assertIsNone(store.load())
            store.save('test-token', 'tester')
            self.assertNotIn(b'test-token', store.path.read_bytes())
            self.assertEqual(store.load()['token'], 'test-token')
            store.delete()
            self.assertIsNone(store.load())

    def test_secure_storage_failure_never_writes_plaintext_or_damages_previous(self):
        class Protector:
            def encrypt(self, value):
                raise CredentialError('不可用')

        with tempfile.TemporaryDirectory() as directory:
            store = GitHubCredentialStore(Path(directory), Protector())
            store.path.write_bytes(b'previous-encrypted-value')
            with self.assertRaises(CredentialError):
                store.save('test-token', 'tester')
            self.assertEqual(store.path.read_bytes(), b'previous-encrypted-value')
        with patch('northdiary.services.credentials.os.name', 'posix'), self.assertRaises(CredentialError):
            WindowsDPAPI()
