import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import json
import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QDialog

from northdiary.services.ai_requests import estimate_cost, prepare_request, source_fingerprint
from northdiary.services.credentials import WindowsDPAPI
from northdiary.services.deepseek import DeepSeekClient
from northdiary.services.deepseek_credentials import DeepSeekCredentialStore
from northdiary.storage.ai_repository import AIRepository
from northdiary.storage.database import Database, SCHEMA_VERSION
from northdiary.storage.repository import ArticleRepository
from northdiary.ui.ai_sources import ArticleSelectionDialog, RequestPreviewDialog, SourceArticle
from northdiary.ui.ai_studio import AIStudio


APP = QApplication.instance() or QApplication([])
APP.setStyle('Fusion')


def wait_until(predicate, seconds=4):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(15)
    if not predicate():
        raise AssertionError('Timed out waiting for asynchronous result')


class MemoryStore:
    def __init__(self):
        self.key = None
    def load(self):
        return self.key
    def save(self, key):
        self.key = key
    def delete(self):
        self.key = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.server.calls.append(('GET', self.path, None))
        content = json.dumps({'data': [{'id': 'deepseek-flash'}, {'id': 'deepseek-v4-pro'}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.calls.append(('POST', self.path, request))
        mode = self.server.mode
        if isinstance(mode, int):
            self.send_response(mode)
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"untrusted provider error must not be echoed"}}')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        packets = [
            {'choices': [{'delta': {'reasoning_content': 'test reasoning'}, 'finish_reason': None}]},
            {'model': 'deepseek-flash', 'choices': [{'delta': {'content': '你好，'}, 'finish_reason': None}]},
            {'choices': [{'delta': {'content': '这是回复。'}, 'finish_reason': None}]},
            {'choices': [{'delta': {}, 'finish_reason': 'length' if mode == 'length' else 'stop'}],
             'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'prompt_cache_hit_tokens': 30}},
        ]
        try:
            self.wfile.write(b': heartbeat\r\n\r\n')
            for i, packet in enumerate(packets):
                event = ('data: ' + json.dumps(packet, ensure_ascii=False) + '\r\n\r\n').encode('utf-8')
                # Deliberately split UTF-8 characters, CRLFs and SSE boundaries.
                for offset in range(0, len(event), 3):
                    self.wfile.write(event[offset:offset + 3])
                    self.wfile.flush()
                if mode == 'slow' and i == 1:
                    self.server.resume.wait(3)
                if mode == 'broken' and i == 1:
                    return
            self.wfile.write(b'data: [DONE]\r\n\r\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.server.calls = []
        self.server.mode = 'stream'
        self.server.resume = threading.Event()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f'http://127.0.0.1:{self.server.server_port}'
        self.client = DeepSeekClient(base_url=self.base_url)

    def tearDown(self):
        self.client.stop()
        self.server.resume.set()
        self.server.shutdown()
        self.server.server_close()
        APP.processEvents()
        self.client.deleteLater()

    def test_streaming_utf8_usage_and_models_over_actual_http(self):
        models = QSignalSpy(self.client.modelsReady)
        self.client.start('test-only-placeholder')
        wait_until(lambda: models.count() == 1)
        self.assertEqual(models.at(0)[0], ['deepseek-flash', 'deepseek-v4-pro'])
        chunks, complete, errors = QSignalSpy(self.client.delta), QSignalSpy(self.client.completed), QSignalSpy(self.client.failed)
        self.client.start('test-only-placeholder', b'{"stream":true}')
        wait_until(lambda: complete.count() or errors.count())
        self.assertEqual(errors.count(), 0)
        self.assertEqual(chunks.count(), 2)
        result = complete.at(0)[0]
        self.assertEqual(result['content'], '你好，这是回复。')
        self.assertEqual(result['usage']['prompt_cache_hit_tokens'], 30)
        self.assertEqual(result['status'], 'complete')

    def test_stop_preserves_partial_content_without_waiting_for_server(self):
        self.server.mode = 'slow'
        complete = QSignalSpy(self.client.completed)
        self.client.start('test-only-placeholder', b'{}')
        wait_until(lambda: self.client.content == '你好，')
        before = time.monotonic()
        self.client.stop()
        wait_until(lambda: complete.count() == 1)
        self.assertLess(time.monotonic() - before, 1)
        self.assertEqual(complete.at(0)[0]['status'], 'stopped')
        self.assertEqual(complete.at(0)[0]['content'], '你好，')

    def test_broken_stream_is_error_and_length_is_incomplete(self):
        self.server.mode = 'broken'
        errors, complete = QSignalSpy(self.client.failed), QSignalSpy(self.client.completed)
        self.client.start('test-only-placeholder', b'{}')
        wait_until(lambda: errors.count() == 1)
        self.assertEqual(self.client.content, '你好，')
        self.assertEqual(complete.count(), 0)
        self.server.mode = 'length'
        self.client.start('test-only-placeholder', b'{}')
        wait_until(lambda: complete.count() == 1)
        self.assertEqual(complete.at(0)[0]['status'], 'incomplete')

    def test_status_errors_do_not_echo_server_body(self):
        for status, text in [(401, 'API Key'), (402, '余额'), (429, '频繁')]:
            self.server.mode = status
            errors = QSignalSpy(self.client.failed)
            self.client.start('test-only-placeholder', b'{}')
            wait_until(lambda: errors.count() == 1)
            self.assertIn(text, errors.at(0)[0])
            self.assertNotIn('untrusted', errors.at(0)[0])

    def test_ui_confirmation_exact_payload_persistent_history_and_scope_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp))
            repo = ArticleRepository(db)
            first, secret = repo.create(), repo.create()
            repo.save(first.id, '已选文章', '2026-11-02', '<p>授权内容</p>', '授权内容', [], [])
            repo.save(secret.id, '未选文章', '2026-11-02', '<p>隐藏内容</p>', '隐藏内容', [], [])
            store = MemoryStore()
            view = AIStudio(db, credential_store=store,
                            client_factory=lambda parent: DeepSeekClient(parent, self.base_url))
            view.show()
            view.navigate('chat')
            view.set_articles([first.id])
            view.api_key.setText('test-only-placeholder')
            view.runtime.apply_key()
            self.assertEqual(view.api_key.text(), '')
            view.tools['chat']['prompt'].setPlainText('谈谈这篇文章')
            with patch.object(RequestPreviewDialog, 'exec', return_value=QDialog.DialogCode.Rejected):
                view.runtime.send('chat')
            self.assertEqual(self.server.calls, [])
            self.assertEqual(view.runtime.repo.conversations('chat'), [])
            payloads = []

            def confirm(dialog):
                dialog.list.setCurrentRow(dialog.list.count() - 1)
                payloads.append(json.loads(dialog.body.toPlainText()))
                return QDialog.DialogCode.Accepted

            with patch.object(RequestPreviewDialog, 'exec', confirm):
                view.runtime.send('chat')
                wait_until(lambda: not view.runtime.client.busy)
                APP.processEvents()
                conv = view.runtime.active['chat']
                self.assertEqual(view.runtime.repo.turns(conv)[0]['status'], 'complete')
                view.tools['chat']['prompt'].setPlainText('再说说细节')
                view.runtime.send('chat')
                wait_until(lambda: not view.runtime.client.busy)
                self.assertEqual(len(view.runtime.repo.history(conv)), 4)
                view.runtime.send('chat', True)
                wait_until(lambda: not view.runtime.client.busy)
                self.assertEqual(len(view.runtime.repo.turns(conv)), 3)
                self.assertEqual(len(view.runtime.repo.history(conv)), 6)
            requests = [call[2] for call in self.server.calls if call[0] == 'POST']
            self.assertEqual(requests, payloads)
            self.assertNotIn('隐藏内容', json.dumps(requests, ensure_ascii=False))
            self.assertEqual([m['role'] for m in requests[1]['messages']], ['system', 'user', 'user', 'assistant', 'user'])
            repo.save(first.id, '已选文章', '2026-11-02', '<p>修改后的原文</p>', '修改后的原文', [], [])
            view.tools['chat']['prompt'].setPlainText('再看一次')
            fresh, cid, notice = view.runtime.prepare('chat')
            self.assertIsNone(cid)
            self.assertFalse(fresh.history)
            self.assertIn('原文已变化', notice)
            view.set_articles([secret.id])
            self.assertIsNone(view.runtime.active['chat'])
            view.tools['chat']['prompt'].setPlainText('新的素材')
            prepared, cid, _ = view.runtime.prepare('chat')
            self.assertFalse(prepared.history)
            self.assertNotIn('授权内容', prepared.payload.decode())
            view.runtime.shutdown()
            view.close()
            db.close()
            reopened = Database(Path(temp))
            self.assertEqual(len(AIRepository(reopened).history(conv)), 6)
            reopened.close()
            view.deleteLater()

    def test_shutdown_mid_stream_persists_partial_before_database_closes(self):
        self.server.mode = 'slow'
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp))
            store = MemoryStore()
            store.key = 'test-only-placeholder'
            view = AIStudio(db, credential_store=store,
                            client_factory=lambda parent: DeepSeekClient(parent, self.base_url))
            view.navigate('chat')
            view.tools['chat']['prompt'].setPlainText('测试关闭')
            with patch.object(RequestPreviewDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                view.runtime.send('chat')
            wait_until(lambda: view.runtime.client.content == '你好，')
            self.assertTrue(view.runtime.shutdown())
            turn = view.runtime.repo.turns(view.runtime.active['chat'])[-1]
            self.assertEqual(turn['status'], 'stopped')
            self.assertEqual(turn['response'], '你好，')
            db.close()
            APP.processEvents()
            view.close()
            view.deleteLater()

    def test_response_save_failure_preserves_text_and_retry_does_not_resend(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp))
            store = MemoryStore()
            store.key = 'test-only-placeholder'
            view = AIStudio(db, credential_store=store,
                            client_factory=lambda parent: DeepSeekClient(parent, self.base_url))
            view.navigate('chat')
            view.tools['chat']['prompt'].setPlainText('保存失败测试')
            with patch.object(RequestPreviewDialog, 'exec', return_value=QDialog.DialogCode.Accepted), \
                 patch.object(view.runtime.repo, 'finish_turn', side_effect=OSError('test disk failure')):
                view.runtime.send('chat')
                wait_until(lambda: not view.runtime.client.busy)
                self.assertIsNotNone(view.runtime.pending_result)
                self.assertIn('你好，这是回复。', view.tools['chat']['output'].toPlainText())
                self.assertFalse(view.runtime.shutdown())
                cid = view.runtime.active['chat']
                view.runtime.new_conversation('chat')
                self.assertEqual(view.runtime.active['chat'], cid)
            view.runtime.send('chat')  # Retry persistence only.
            self.assertIsNone(view.runtime.pending_result)
            self.assertEqual(len(self.server.calls), 1)
            self.assertEqual(view.runtime.repo.turns(cid)[0]['status'], 'complete')
            view.runtime.shutdown()
            view.close()
            db.close()
            view.deleteLater()

    def test_request_start_failure_does_not_reuse_an_old_reply_or_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp))
            store = MemoryStore()
            store.key = 'test-only-placeholder'
            view = AIStudio(db, credential_store=store,
                            client_factory=lambda parent: DeepSeekClient(parent, self.base_url))
            view.runtime.client.content = '之前的回复'
            view.runtime.client.usage = {'prompt_tokens': 9, 'completion_tokens': 9}
            view.navigate('chat')
            view.tools['chat']['prompt'].setPlainText('新问题')
            with patch.object(RequestPreviewDialog, 'exec', return_value=QDialog.DialogCode.Accepted), \
                 patch.object(view.runtime.client, 'start', side_effect=ValueError('invalid test key')):
                view.runtime.send('chat')
            turn = view.runtime.repo.turns(view.runtime.active['chat'])[-1]
            self.assertEqual(turn['response'], '')
            self.assertIsNone(turn['prompt_tokens'])
            self.assertEqual(turn['status'], 'error')
            self.assertEqual(view.runtime.repo.totals()['unpriced_requests'], 1)
            view.runtime.shutdown()
            view.close()
            db.close()
            view.deleteLater()


class PersistenceTests(unittest.TestCase):
    def test_migration_v7_snapshots_database_and_preserves_original_article(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = Database(root)
            repo = ArticleRepository(db)
            article = repo.create()
            with db.connection:
                db.connection.execute('DROP TABLE ai_work_versions')
                db.connection.execute('DROP TABLE ai_works')
                db.connection.execute('DROP TABLE ai_turns')
                db.connection.execute('DROP TABLE ai_conversations')
                db.connection.execute('PRAGMA user_version=7')
            db.close()
            migrated = Database(root)
            self.assertEqual(ArticleRepository(migrated).get(article.id).title, article.title)
            self.assertEqual(migrated.connection.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
            backups = list((root / 'backups').glob('before-v8-*'))
            self.assertEqual(len(backups), 1)
            with closing(sqlite3.connect(backups[0])) as before:
                self.assertEqual(before.execute('PRAGMA user_version').fetchone()[0], 7)
            migrated.close()

    def test_only_completed_turns_become_history_and_crash_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp))
            repo = AIRepository(db)
            cid = repo.create('chat', '独立对话', [], source_fingerprint([]))
            first = repo.start_turn(cid, '问题', 'deepseek-flash', [])
            repo.finish_turn(first, {'status': 'complete', 'content': '完整回答',
                                     'usage': {'prompt_tokens': 10, 'completion_tokens': 3}})
            partial = repo.start_turn(cid, '中断的问题', 'deepseek-flash', [])
            repo.finish_turn(partial, {'status': 'stopped', 'content': '未完回答'})
            running = repo.start_turn(cid, '退出时的问题', 'deepseek-flash', [])
            repo.recover_interrupted()
            self.assertEqual(len(repo.history(cid)), 2)
            self.assertEqual(repo.turns(cid)[-1]['status'], 'interrupted')
            other = repo.create('analysis', '另一个对话', [], source_fingerprint([]))
            self.assertEqual(repo.history(other), [])
            self.assertEqual(repo.totals()['unknown_usage'], 2)
            db.close()

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI test')
    @unittest.skipIf(os.environ.get('NORTHDIARY_TEST_SANDBOX') == '1', 'DPAPI verified separately outside restricted test sandbox')
    def test_real_windows_encrypted_key_roundtrip_and_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            store = DeepSeekCredentialStore(Path(temp), WindowsDPAPI())
            placeholder = 'test-only-placeholder-key'
            store.save(placeholder)
            self.assertNotIn(placeholder.encode(), store.path.read_bytes())
            self.assertEqual(store.load(), placeholder)
            store.delete()
            self.assertIsNone(store.load())

    def test_price_range_usage_validation_and_unknown_model(self):
        low, high = estimate_cost('deepseek-flash', {'prompt_tokens': 1000000, 'completion_tokens': 1000000, 'prompt_cache_hit_tokens': 0})
        self.assertAlmostEqual(low, 0.75)
        self.assertAlmostEqual(high, 1.5)
        self.assertEqual(estimate_cost('unknown-future-model', {'prompt_tokens': 1, 'completion_tokens': 2}), (None, None))
        self.assertEqual(estimate_cost('deepseek-flash', None), (None, None))

    def test_select_all_follows_current_category_tag_search_and_keeps_previous_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(Path(temp))
            repo = ArticleRepository(db)
            ids = []
            for title, category, tag in [('甲一', '分类甲', '标签一'), ('甲二', '分类甲', '标签二'), ('乙一', '分类乙', '标签一')]:
                article = repo.create()
                repo.save(article.id, title, '2026-11-02', '', '', [category], [tag])
                ids.append(article.id)
            dialog = ArticleSelectionDialog(db)
            dialog.category.setCurrentIndex(dialog.category.findData('分类甲'))
            dialog.select_visible()
            self.assertEqual(set(dialog.selected), set(ids[:2]))
            dialog.category.setCurrentIndex(0)
            dialog.tag.setCurrentIndex(dialog.tag.findData('标签一'))
            dialog.search.setText('乙')
            dialog.select_visible()
            self.assertEqual(set(dialog.selected), set(ids))
            dialog.clear_selection()
            dialog.select_visible()
            self.assertEqual(set(dialog.selected), {ids[2]})
            dialog.search.setText('不存在')
            self.assertFalse(dialog.select_all.isEnabled())
            dialog.close()
            dialog.deleteLater()
            db.close()


if __name__ == '__main__':
    unittest.main()
