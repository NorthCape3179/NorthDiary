import os
from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QThread, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QTabWidget, QWidget, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QInputDialog,
)

from northdiary.services.credentials import GitHubCredentialStore, CredentialError
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.services.github_sync import (
    GitHubPackages, DeviceLogin, GitHubError, MAX_PACKAGE,
)
from northdiary.ui.export_dialog import ExportDialog


class NetworkJob(QThread):
    """Only HTTP work runs here; the SQLite connection stays on the UI thread."""
    def __init__(self, action, parent):
        super().__init__(parent)
        self.action = action
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.action()
        except (GitHubError, CredentialError) as error:
            self.error = error
        except Exception:
            self.error = GitHubError('操作未完成，请检查网络和配置后重试')


class GitHubDialog(QDialog):
    def __init__(self, main_window, client_factory=GitHubPackages,
                 login_factory=DeviceLogin, credential_store=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.client_factory = client_factory
        self.login_factory = login_factory
        self.store = credential_store or GitHubCredentialStore(main_window.database.root)
        self.client = None
        self.worker = None
        self.callback = None
        self.job_generation = None
        self.login = ''
        self.repository = ''
        self.challenge = None
        self.auth = None
        self.auth_generation = 0
        self.auth_deadline = 0
        self.auth_interval = 5
        self.temp = tempfile.TemporaryDirectory(prefix='northdiary-github-')
        self.setWindowTitle('GitHub 文章上传与下载')
        self.resize(720, 690)
        self.poll_timer = QTimer(self)
        self.poll_timer.setSingleShot(True)
        self.poll_timer.timeout.connect(self.poll_login)
        self.build_ui()
        self.restore_login()

    def button(self, text, action):
        button = QPushButton(text)
        button.clicked.connect(action)
        return button

    def build_ui(self):
        layout = QVBoxLayout(self)
        intro = QLabel('选择独立的私有数据仓库。上传保留新的文章包，下载后预览导入，不覆盖现有文章。')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.tabs = QTabWidget()
        browser = QWidget()
        column = QVBoxLayout(browser)
        column.addWidget(QLabel('GitHub 应用 Client ID（首次需在 GitHub 登记并启用设备授权）'))
        self.client_id = QLineEdit(self.main_window.ui_settings.value('github/client_id', ''))
        self.client_id.setPlaceholderText('Client ID 是应用编号，不是密码或 Client Secret')
        column.addWidget(self.client_id)
        row = QHBoxLayout()
        self.browser_button = self.button('在浏览器中登录 GitHub', self.start_login)
        row.addWidget(self.browser_button)
        settings = self.button('打开应用登记页面', lambda: QDesktopServices.openUrl(
            QUrl('https://github.com/settings/developers')))
        row.addWidget(settings)
        column.addLayout(row)
        self.tabs.addTab(browser, '浏览器登录')
        token_page = QWidget()
        column = QVBoxLayout(token_page)
        hint = QLabel('也可使用只授权数据仓库的细粒度令牌，授予 Contents 读写权限。令牌不会写入源码或普通设置文件。')
        hint.setWordWrap(True)
        column.addWidget(hint)
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText('粘贴 Personal access token')
        column.addWidget(self.token_input)
        self.token_button = self.button('使用令牌连接', self.connect_token)
        column.addWidget(self.token_button)
        self.tabs.addTab(token_page, '专用令牌')
        layout.addWidget(self.tabs)
        permissions = QLabel('浏览器设备授权使用 repo 权限，可访问账号授权范围内的私有仓库；如需仅授权一个数据仓库，请使用专用令牌。')
        permissions.setWordWrap(True)
        layout.addWidget(permissions)
        self.remember = QCheckBox('记住登录（Windows 当前用户加密存储）')
        self.remember.setChecked(os.name == 'nt')
        self.remember.setEnabled(os.name == 'nt')
        layout.addWidget(self.remember)
        self.code_row = QWidget()
        row = QHBoxLayout(self.code_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel('在 GitHub 网页输入验证码：'))
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        row.addWidget(self.code)
        row.addWidget(self.button('复制', lambda: QApplication.clipboard().setText(self.code.text())))
        self.cancel_auth = self.button('取消登录', self.cancel_login)
        row.addWidget(self.cancel_auth)
        layout.addWidget(self.code_row)
        self.code_row.hide()
        self.account = QLabel('尚未连接')
        self.account.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.account)
        row = QHBoxLayout()
        self.repo_input = QLineEdit(self.main_window.ui_settings.value('github/repository', ''))
        self.repo_input.setPlaceholderText('账号/NorthDiary-Data')
        row.addWidget(self.repo_input)
        self.repo_button = self.button('连接 / 初始化空仓库', self.use_repository)
        row.addWidget(self.repo_button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.create_button = self.button('新建私有数据仓库', self.create_repository)
        row.addWidget(self.create_button)
        self.disconnect_button = self.button('断开并清除本机登录', self.disconnect)
        row.addWidget(self.disconnect_button)
        row.addStretch()
        layout.addLayout(row)
        self.packages = QTreeWidget()
        self.packages.setHeaderLabels(['上传时间（UTC）', '大小', '文件编号'])
        self.packages.setRootIsDecorated(False)
        self.packages.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.packages, 1)
        row = QHBoxLayout()
        self.upload_button = self.button('选择文章并上传', self.upload)
        self.refresh_button = self.button('刷新远端记录', self.refresh)
        self.download_button = self.button('下载并导入所选记录', self.download)
        for button in (self.upload_button, self.refresh_button, self.download_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel('每个文章包最多 20 MiB，可分批选择文章。GitHub 传输不包含未在正文引用的独立附件。')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        close = self.button('关闭', self.reject)
        layout.addWidget(close)
        self.update_buttons()

    def update_buttons(self):
        busy = self.worker is not None
        authenticating = self.auth is not None
        idle = not busy and not authenticating
        connected = self.client is not None
        ready = connected and bool(self.repository)
        self.browser_button.setEnabled(not busy and not authenticating)
        self.token_button.setEnabled(not busy and not authenticating)
        self.tabs.setEnabled(not busy and not authenticating)
        self.repo_input.setEnabled(idle and connected)
        self.remember.setEnabled(not busy and not authenticating and os.name == 'nt')
        self.repo_button.setEnabled(idle and connected)
        self.create_button.setEnabled(idle and connected)
        self.disconnect_button.setEnabled(idle and connected)
        self.upload_button.setEnabled(idle and ready)
        self.refresh_button.setEnabled(idle and ready)
        self.download_button.setEnabled(idle and ready and self.packages.currentItem() is not None)
        self.packages.setEnabled(not busy)

    def run_job(self, message, action, callback, auth_generation=None):
        if self.worker is not None:
            return
        self.status.setText(message)
        self.callback = callback
        self.job_generation = auth_generation
        self.worker = NetworkJob(action, self)
        self.worker.finished.connect(self.finish_job)
        self.update_buttons()
        self.worker.start()

    def finish_job(self):
        worker, callback = self.worker, self.callback
        obsolete = self.job_generation is not None and self.job_generation != self.auth_generation
        self.worker, self.callback = None, None
        self.update_buttons()
        if obsolete:
            pass
        elif worker.error:
            self.cancel_login()
            if getattr(worker.error, 'status', None) == 401:
                self.disconnect()
            self.status.setText(str(worker.error))
        else:
            try:
                callback(worker.result)
            except (GitHubError, CredentialError, OSError, ValueError) as error:
                self.status.setText(str(error))
            except Exception:
                self.status.setText('操作未完成，请检查配置后重试')
        worker.action = None
        worker.result = None
        worker.deleteLater()
        self.update_buttons()

    def restore_login(self):
        try:
            saved = self.store.load()
        except CredentialError as error:
            self.status.setText(str(error))
            return
        if saved:
            self.verify_token(saved['token'])

    def connect_token(self):
        token = self.token_input.text().strip()
        if not token or len(token) > 10000:
            self.status.setText('请填写有效的专用访问令牌')
            return
        self.verify_token(token)

    def verify_token(self, token):
        self.client = None
        self.repository = ''
        self.packages.clear()
        client = self.client_factory(token)
        self.run_job('正在验证 GitHub 账号…', lambda: (client, client.user(), token), self.connected)

    def connected(self, result):
        client, login, token = result
        self.client, self.login = client, login
        self.token_input.clear()
        self.account.setText('已连接：' + login)
        try:
            if self.remember.isChecked():
                self.store.save(token, login)
            else:
                self.store.delete()
            notice = '已连接。请选择或新建独立的私有数据仓库。'
        except (CredentialError, OSError):
            notice = '已连接，但未能安全保存登录；本次会话可用，关闭后需重新连接。'
        self.status.setText(notice)
        if not self.repo_input.text().strip():
            self.repo_input.setText(login + '/NorthDiary-Data')
        else:
            repository = self.repo_input.text().strip()
            self.run_job('正在检查已选仓库…', lambda: (repository, client.check_repository(repository)),
                         self.repository_connected)

    def start_login(self):
        try:
            self.auth = self.login_factory(self.client_id.text().strip())
        except GitHubError as error:
            self.status.setText(str(error))
            return
        self.main_window.ui_settings.setValue('github/client_id', self.client_id.text().strip())
        generation = self.auth_generation
        self.run_job('正在获取 GitHub 登录验证码…', self.auth.start,
                     lambda challenge: self.show_challenge(challenge), auth_generation=generation)

    def show_challenge(self, challenge):
        self.challenge = challenge
        self.auth_interval = challenge.interval
        self.auth_deadline = time.monotonic() + challenge.expires_in
        self.code.setText(challenge.user_code)
        self.code_row.show()
        self.status.setText('请在 GitHub 官方页面登录、输入验证码并确认授权。')
        if not QDesktopServices.openUrl(QUrl(challenge.verification_uri)):
            self.status.setText('请手动打开 https://github.com/login/device，输入上方验证码并授权。')
        self.poll_timer.start(self.auth_interval * 1000)

    def poll_login(self):
        if not self.auth:
            return
        if time.monotonic() >= self.auth_deadline:
            self.cancel_login()
            self.status.setText('登录验证码已过期，请重新开始')
            return
        generation = self.auth_generation
        auth, challenge = self.auth, self.challenge
        self.run_job('正在等待 GitHub 授权…', lambda: auth.poll(challenge),
                     self.polled, auth_generation=generation)

    def polled(self, result):
        state, token = result
        if state == 'connected':
            self.cancel_login()
            self.verify_token(token)
            return
        if state == 'slow_down':
            self.auth_interval += 5
        self.status.setText('等待你在 GitHub 网页确认授权…')
        self.poll_timer.start(self.auth_interval * 1000)

    def cancel_login(self):
        if self.auth:
            self.status.setText('已取消登录。')
        self.auth_generation += 1
        self.auth = self.challenge = None
        self.poll_timer.stop()
        self.code.clear()
        self.code_row.hide()
        self.update_buttons()

    def disconnect(self):
        if self.worker:
            return
        self.cancel_login()
        self.client = None
        self.login = self.repository = ''
        self.packages.clear()
        self.token_input.clear()
        try:
            self.store.delete()
            self.status.setText('已断开并清除本机保存的登录。')
        except OSError:
            self.status.setText('已断开，但无法清除本机加密凭据，请检查数据目录权限。')
        self.account.setText('尚未连接')
        self.update_buttons()

    def use_repository(self):
        repository, client = self.repo_input.text().strip(), self.client
        self.repository = ''
        self.packages.clear()
        self.run_job('正在检查或初始化私有数据仓库…',
                     lambda: (repository, client.initialize_repository(repository)), self.repository_connected)

    def create_repository(self):
        name, accepted = QInputDialog.getText(self, '新建私有数据仓库', '仓库名称', text='NorthDiary-Data')
        if accepted:
            client = self.client
            self.run_job('正在创建私有数据仓库…', lambda: client.create_repository(name.strip()),
                         lambda repository: self.repository_connected((repository, None)))

    def repository_connected(self, result):
        repository, _ = result
        self.repository = repository
        self.repo_input.setText(repository)
        self.main_window.ui_settings.setValue('github/repository', repository)
        self.refresh()

    def refresh(self):
        repository, client = self.repository, self.client
        self.packages.clear()
        self.run_job('正在读取远端文章包…', lambda: client.list_packages(repository), self.show_packages)

    def show_packages(self, packages):
        for package in packages:
            stamp = package.name.split('-')[0]
            from datetime import datetime
            display = datetime.strptime(stamp, '%Y%m%dT%H%M%S%fZ').strftime('%Y-%m-%d %H:%M:%S')
            item = QTreeWidgetItem([display, f'{package.size / 1024 / 1024:.2f} MiB', package.name])
            item.setData(0, Qt.ItemDataRole.UserRole, package)
            self.packages.addTopLevelItem(item)
        self.packages.resizeColumnToContents(0)
        self.packages.resizeColumnToContents(1)
        self.status.setText(f'已读取 {len(packages)} 份文章包。上传会新增记录，下载前请选择一份。')

    def upload(self):
        if not self.main_window.save(True):
            return
        dialog = ExportDialog(self.main_window.repository.list(), self)
        dialog.setWindowTitle('选择要上传到 GitHub 的文章')
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        path = Path(self.temp.name) / 'upload.epub'
        try:
            EpubExporter(self.main_window.repository, self.main_window.attachments).export(dialog.selection(), path)
            if path.stat().st_size > MAX_PACKAGE:
                raise GitHubError('文章包超过 20 MiB，请减少文章或图片后分批上传')
            content = path.read_bytes()
        except Exception as error:
            self.status.setText(str(error))
            return
        finally:
            path.unlink(missing_ok=True)
        repository, client = self.repository, self.client
        self.run_job('正在上传文章包…', lambda: client.upload(repository, content), self.uploaded)

    def uploaded(self, name):
        QMessageBox.information(self, '上传完成', '所选文章与正文图片已上传到私有数据仓库。')
        self.refresh()

    def download(self):
        item = self.packages.currentItem()
        if not item:
            return
        package = item.data(0, Qt.ItemDataRole.UserRole)
        repository, client = self.repository, self.client
        self.run_job('正在下载并校验文章包…', lambda: client.download(repository, package), self.downloaded)

    def downloaded(self, content):
        path = Path(self.temp.name) / 'download.epub'
        try:
            path.write_bytes(content)
            importer = EpubImporter(self.main_window.repository, self.main_window.attachments)
            preview = importer.prepare(path)
            if preview.new_count + preview.conflict_count:
                message = (f'新增 {preview.new_count} 篇，冲突副本 {preview.conflict_count} 篇，'
                           f'跳过 {preview.skipped_count} 篇。\n确认导入？现有文章不会被覆盖。')
                if QMessageBox.question(self, '下载完成，预览导入', message,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    self.status.setText('已取消导入，本机文章未改动。')
                    return
            result = importer.apply(preview)
            self.main_window.refresh_categories()
            self.main_window.refresh_people()
            self.main_window.refresh_list()
            if result.article_ids and not self.main_window.current_id:
                self.main_window.load_article(result.article_ids[0])
                self.main_window.refresh_list()
            self.status.setText(f'下载导入完成：新增 {result.imported} 篇，跳过 {result.skipped} 篇。可在文章总览中查看。')
        finally:
            path.unlink(missing_ok=True)

    def reject(self):
        if self.worker is not None:
            self.status.setText('当前网络操作尚未结束，请稍候再关闭。')
            return
        self.cancel_login()
        self.client = None
        self.temp.cleanup()
        super().reject()
