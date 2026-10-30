import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import test_ui
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from northdiary.models import ExportSelection
from northdiary.services.epub import EpubExporter
from northdiary.services.github_sync import DeviceChallenge, GitHubError, RemotePackage, git_blob_sha
from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository
from northdiary.services.attachments import AttachmentService
from northdiary.ui.export_dialog import ExportDialog
from northdiary.ui.github_dialog import GitHubDialog

NAME = '20261030T050000000000Z-' + 'b' * 32 + '.epub'


class MemoryStore:
    def load(self):
        return None

    def delete(self):
        self.deleted = True


class FakeClient:
    def __init__(self):
        self.thread_ids = []
        self.uploaded = []
        self.content = b''

    def note(self):
        self.thread_ids.append(threading.get_ident())

    def user(self):
        self.note()
        return 'tester'

    def check_repository(self, repository):
        self.note()
        return {'private': True}

    def initialize_repository(self, repository):
        self.note()
        return {'private': True}

    def list_packages(self, repository):
        self.note()
        if not self.content:
            return []
        return [RemotePackage(NAME, 'packs/' + NAME, git_blob_sha(self.content), len(self.content), 'a' * 40)]

    def upload(self, repository, content):
        self.note()
        self.uploaded.append(content)
        return NAME

    def download(self, repository, package):
        self.note()
        return self.content


class GitHubWindowTests(unittest.TestCase):
    def setUp(self):
        test_ui.WindowTests.setUp(self)
        self.client = FakeClient()
        self.dialog = GitHubDialog(self.window, client_factory=lambda token: self.client, credential_store=MemoryStore())
        self.dialog.show()
        test_ui.APP.processEvents()

    def tearDown(self):
        self.wait_idle()
        self.dialog.reject()
        test_ui.WindowTests.tearDown(self)

    def wait_idle(self):
        deadline = time.monotonic() + 3
        while self.dialog.worker is not None and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertIsNone(self.dialog.worker, '后台任务未在测试时限内结束')

    def connect(self):
        self.dialog.token_input.setText('test-only-token')
        self.dialog.connect_token()
        self.wait_idle()
        self.dialog.use_repository()
        self.wait_idle()

    def remote_book(self):
        db = Database(self.root / 'remote')
        try:
            repo = ArticleRepository(db)
            key = repo.create().id
            repo.save(key, '远端文章', '2026-未知-未知', '<p>远端正文</p>', '远端正文', ['回忆'], ['测试'])
            path = self.root / 'remote.epub'
            EpubExporter(repo, AttachmentService(db)).export(ExportSelection((key,), '远端文集'), path)
            self.client.content = path.read_bytes()
        finally:
            db.close()

    def test_connect_and_repo_ready_network_work_is_off_ui_thread(self):
        self.connect()
        self.assertEqual(self.dialog.login, 'tester')
        self.assertEqual(self.dialog.repository, 'tester/NorthDiary-Data')
        self.assertTrue(self.dialog.upload_button.isEnabled())
        self.assertEqual(self.dialog.token_input.text(), '')
        self.assertEqual(self.window.ui_settings.value('github/repository'), 'tester/NorthDiary-Data')
        self.assertIsNone(self.window.ui_settings.value('github/token'))
        self.assertTrue(self.client.thread_ids)
        self.assertTrue(all(key != threading.get_ident() for key in self.client.thread_ids))

    def test_upload_saves_pending_edits_and_transfers_native_epub(self):
        self.connect()
        self.window.new_article()
        key = self.window.current_id
        self.window.title.setText('未保存的标题')
        self.window.editor.setPlainText('未保存的正文')
        dialog = ExportDialog(self.window.repository.list())
        with patch('northdiary.ui.github_dialog.ExportDialog', return_value=dialog), \
             patch.object(dialog, 'exec', return_value=dialog.DialogCode.Accepted), \
             patch('northdiary.ui.github_dialog.QMessageBox.information'):
            self.dialog.upload()
            self.wait_idle()
        self.assertEqual(self.window.repository.get(key).body_text, '未保存的正文')
        self.assertEqual(len(self.client.uploaded), 1)
        self.assertGreater(len(self.client.uploaded[0]), 100)
        self.assertFalse((Path(self.dialog.temp.name) / 'upload.epub').exists())

    def test_download_previews_import_and_repeated_download_skips(self):
        self.remote_book()
        self.connect()
        self.dialog.packages.setCurrentItem(self.dialog.packages.topLevelItem(0))
        with patch('northdiary.ui.github_dialog.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            self.dialog.download()
            self.wait_idle()
        articles = self.window.repository.list()
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, '远端文章')
        self.assertFalse((Path(self.dialog.temp.name) / 'download.epub').exists())
        self.dialog.packages.setCurrentItem(self.dialog.packages.topLevelItem(0))
        with patch('northdiary.ui.github_dialog.QMessageBox.question') as question:
            self.dialog.download()
            self.wait_idle()
            question.assert_not_called()
        self.assertEqual(len(self.window.repository.list()), 1)
        self.assertIn('跳过 1 篇', self.dialog.status.text())

    def test_download_cancel_keeps_local_data_and_cleans_temporary_file(self):
        self.remote_book()
        self.connect()
        self.dialog.packages.setCurrentItem(self.dialog.packages.topLevelItem(0))
        with patch('northdiary.ui.github_dialog.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
            self.dialog.download()
            self.wait_idle()
        self.assertEqual(self.window.repository.list(), [])
        self.assertFalse((Path(self.dialog.temp.name) / 'download.epub').exists())

    def test_save_failure_prevents_export_and_upload(self):
        self.connect()
        self.window.new_article()
        self.window.editor.setPlainText('不能丢失')
        with patch.object(self.window.repository, 'save', side_effect=OSError('不可写')), \
             patch.object(self.window, 'fail'), \
             patch('northdiary.ui.github_dialog.ExportDialog') as dialog:
            self.dialog.upload()
            dialog.assert_not_called()
        self.assertTrue(self.window.dirty)
        self.assertEqual(self.client.uploaded, [])

    def test_browser_auth_slowdown_expiry_and_cancel(self):
        class Auth:
            def start(self):
                return DeviceChallenge('ABCD-EFGH', 'test-device', 'https://github.com/login/device', 5, 900)

            def poll(self, challenge):
                return 'slow_down', None

        self.dialog.login_factory = lambda client_id: Auth()
        self.dialog.client_id.setText('test-app')
        with patch('northdiary.ui.github_dialog.QDesktopServices.openUrl', return_value=True) as browser:
            self.dialog.start_login()
            self.wait_idle()
            browser.assert_called_once()
        self.assertEqual(self.dialog.code.text(), 'ABCD-EFGH')
        self.assertFalse(self.dialog.upload_button.isEnabled())
        self.dialog.poll_timer.stop()
        self.dialog.poll_login()
        self.wait_idle()
        self.assertEqual(self.dialog.auth_interval, 10)
        self.dialog.poll_timer.stop()
        self.dialog.auth_deadline = time.monotonic() - 1
        self.dialog.poll_login()
        self.assertIsNone(self.dialog.auth)
        self.assertIn('过期', self.dialog.status.text())
        self.assertFalse(self.dialog.poll_timer.isActive())

    def test_cancel_pending_browser_request_does_not_open_browser_or_store_result(self):
        release = threading.Event()

        class Auth:
            def start(self):
                release.wait(2)
                return DeviceChallenge('ABCD-EFGH', 'test-device', 'https://github.com/login/device', 5, 900)

        self.dialog.login_factory = lambda client_id: Auth()
        with patch('northdiary.ui.github_dialog.QDesktopServices.openUrl') as browser:
            self.dialog.start_login()
            self.dialog.cancel_login()
            release.set()
            self.wait_idle()
            browser.assert_not_called()
        self.assertFalse(self.dialog.poll_timer.isActive())
        self.assertIsNone(self.dialog.client)

    def test_network_failure_and_disconnect_keep_articles(self):
        self.connect()
        self.window.new_article()
        key = self.window.current_id
        self.window.editor.setPlainText('本地文章')
        self.window.save()
        self.client.list_packages = lambda repository: (_ for _ in ()).throw(GitHubError('网络断开'))
        self.dialog.refresh()
        self.wait_idle()
        self.assertIn('网络断开', self.dialog.status.text())
        self.assertEqual(self.window.repository.get(key).body_text, '本地文章')
        self.dialog.disconnect()
        self.assertIsNone(self.dialog.client)
        self.assertEqual(self.window.repository.get(key).body_text, '本地文章')

    def test_active_network_job_blocks_close_until_worker_finishes(self):
        release = threading.Event()
        self.dialog.run_job('测试中', lambda: release.wait(2), lambda value: None)
        self.dialog.reject()
        self.assertIsNotNone(self.dialog.worker)
        self.assertIn('尚未结束', self.dialog.status.text())
        release.set()
        self.wait_idle()
