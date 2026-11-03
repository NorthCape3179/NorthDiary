"""Studio lifecycle, explicit authorization, independent local conversations."""
import json

from PySide6.QtCore import QObject, QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from northdiary.services.ai_requests import prepare_request, source_fingerprint
from northdiary.services.credentials import CredentialError
from northdiary.services.deepseek import DEFAULT_MODELS, DeepSeekClient
from northdiary.services.deepseek_credentials import DeepSeekCredentialStore
from northdiary.storage.ai_repository import AIRepository
from northdiary.ui.ai_sources import RequestPreviewDialog


class StudioController(QObject):
    def __init__(self, view, credential_store=None, client_factory=DeepSeekClient):
        super().__init__(view)
        self.view = view
        self.repo = AIRepository(view.database)
        self.store = credential_store or DeepSeekCredentialStore()
        self.client = client_factory(self)
        self.settings = QSettings(str(view.database.root / 'ui.ini'), QSettings.Format.IniFormat)
        self.api_key = None
        self.key_loaded = False
        self.active = dict.fromkeys(view.tools)
        self.active_mode = None
        self.active_turn = None
        self.pending_result = None
        self.regenerating_work = None
        self.loading = False
        self.activated = False
        self.closing = False
        self.stream_buffer = []
        self.flush_timer = QTimer(self)
        self.flush_timer.setInterval(100)
        self.flush_timer.timeout.connect(self.flush_stream)
        self.client.delta.connect(self.on_delta)
        self.client.thinking.connect(self.on_thinking)
        self.client.completed.connect(self.on_complete)
        self.client.failed.connect(self.on_error)
        self.client.modelsReady.connect(self.on_models)
        selected_model = self.settings.value('deepseek/model', DEFAULT_MODELS[0])
        if selected_model not in DEFAULT_MODELS:
            view.model.addItem(selected_model, selected_model)
        view.model.setCurrentIndex(max(0, view.model.findData(selected_model)))
        view.thinking.setChecked(self.settings.value('deepseek/thinking', False, type=bool))
        view.max_tokens.setValue(self.settings.value('deepseek/max_tokens', 8192, type=int))
        view.model.currentIndexChanged.connect(self.save_options)
        view.thinking.toggled.connect(self.save_options)
        view.max_tokens.valueChanged.connect(self.save_options)
        self.refresh_lists()
        self.refresh_usage()
        self.update_controls()

    def activate(self):
        if not self.activated:
            self.repo.recover_interrupted()
            self.activated = True
            self.refresh_lists()

    def save_options(self, *_):
        self.settings.setValue('deepseek/model', self.view.model.currentData())
        self.settings.setValue('deepseek/thinking', self.view.thinking.isChecked())
        self.settings.setValue('deepseek/max_tokens', self.view.max_tokens.value())
        self.settings.sync()

    def ensure_key(self):
        if not self.key_loaded:
            self.key_loaded = True
            try:
                self.api_key = self.store.load()
                self.view.connection_status.setText('已加载本机密钥，尚未测试连接' if self.api_key else '请先配置 API Key')
            except CredentialError as error:
                self.view.connection_status.setText(str(error))
        return self.api_key

    def apply_key(self):
        try:
            key = self.view.api_key.text().strip()
            DeepSeekCredentialStore.validate(key)
            if self.view.remember_key.isChecked():
                self.store.save(key)
            else:
                self.store.delete()
            self.api_key = key
            self.key_loaded = True
            self.view.api_key.clear()
            self.view.connection_status.setText('密钥已安全保存在本机，请测试连接' if self.view.remember_key.isChecked() else '密钥仅用于本次运行，请测试连接')
        except (CredentialError, ValueError, OSError):
            self.view.connection_status.setText('密钥配置失败，请检查输入和 Windows 安全存储；也可取消本机记忆后使用。')

    def clear_key(self):
        try:
            self.store.delete()
            self.api_key = None
            self.key_loaded = True
            self.view.api_key.clear()
            self.view.connection_status.setText('已清除本机 DeepSeek 密钥')
        except OSError:
            self.view.connection_status.setText('无法清除本机密钥，请检查文件权限。')

    def test_connection(self):
        if self.client.busy:
            if self.client.kind == 'models':
                self.client.stop()
            return
        if not self.ensure_key():
            self.view.connection_status.setText('请先输入并应用 API Key')
            return
        self.view.connection_status.setText('正在连接 DeepSeek 并读取模型清单…')
        self.client.start(self.api_key)
        self.update_controls()

    def on_models(self, models):
        if self.closing:
            return
        selected = self.view.model.currentData()
        self.view.model.blockSignals(True)
        self.view.model.clear()
        for model in models:
            self.view.model.addItem(model, model)
        self.view.model.setCurrentIndex(max(0, self.view.model.findData(selected)))
        self.view.model.blockSignals(False)
        self.save_options()
        self.view.connection_status.setText(f'连接成功 · 可用模型 {len(models)} 个')
        self.update_controls()

    def page_changed(self, key):
        if key == 'settings':
            self.ensure_key()
            self.refresh_usage()
        elif key in self.active and not self.client.busy and not self.pending_result:
            row = self.repo.get(self.active[key])
            if row and tuple(json.loads(row['article_ids'])) != self.view.article_ids:
                self.active[key] = None
                self.view.reset_task_settings(key)
                self.render(key)
                self.view.tools[key]['status'].setText('文章范围已变化，已开启新对话；旧对话保留。')
                self.refresh_lists()

    def refresh_lists(self):
        for mode, tool in self.view.tools.items():
            selector = tool['conversation']
            selector.blockSignals(True)
            selector.clear()
            selector.addItem('新对话 · 无历史', None)
            for row in self.repo.conversations(mode):
                selector.addItem(row['title'], row['id'])
            selector.setCurrentIndex(max(0, selector.findData(self.active[mode])))
            selector.blockSignals(False)

    def new_conversation(self, mode):
        if self.client.busy or self.pending_result:
            return
        self.active[mode] = None
        self.view.reset_task_settings(mode)
        self.view.tools[mode]['prompt'].clear()
        self.view.tools[mode]['status'].setText('新对话不携带其他对话的历史。')
        self.refresh_lists()
        self.render(mode)
        self.update_controls()

    def load_conversation(self, mode):
        if self.loading or self.client.busy or self.pending_result:
            return
        key = self.view.tools[mode]['conversation'].currentData()
        row = self.repo.get(key)
        self.active[mode] = key if row else None
        if row:
            self.loading = True
            try:
                self.view.set_articles(json.loads(row['article_ids']))
            finally:
                self.loading = False
        self.view.tools[mode]['prompt'].clear()
        self.view.reset_task_settings(mode)
        turns = self.repo.turns(self.active[mode])
        if turns:
            self.view.restore_task_settings(mode, turns[-1]['instruction'], turns[-1]['status'] == 'complete')
        self.render(mode)
        self.refresh_lists()
        self.update_controls()

    def delete_conversation(self, mode):
        key = self.active[mode]
        if not key or self.client.busy or self.pending_result:
            return
        if QMessageBox.question(self.view, '删除对话', '删除这段对话及其用量记录？原始文章保留。',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.repo.delete(key)
        self.new_conversation(mode)
        self.refresh_usage()

    def scope_changed(self):
        if self.loading or self.client.busy or self.pending_result:
            return
        for mode in self.active:
            if self.active[mode]:
                self.active[mode] = None
                self.view.reset_task_settings(mode)
                self.render(mode)
                self.view.tools[mode]['status'].setText('文章范围已变化，已开启新对话；旧对话保留。')
        self.refresh_lists()
        self.update_controls()

    def prepare(self, mode, regenerate=False):
        articles = self.view.sources.resolve(self.view.article_ids)
        # Deleted/unconfirmed sources are removed before preparing a request.
        self.view.set_articles(a.id for a in articles)
        if mode in ('appreciation', 'analysis') and not articles:
            raise ValueError('请先选择至少一篇文章')
        if mode == 'writing' and not articles and not self.view.tools[mode]['prompt'].toPlainText().strip() and not any(self.view.tools[mode]['story_notes'].values()) and not self.repo.history(self.active[mode]):
            raise ValueError('请选择文章，或填写创作要求、故事设定')
        instruction = self.view.request_instruction(mode)
        if mode == 'chat' and not self.view.tools[mode]['prompt'].toPlainText().strip() and not regenerate:
            raise ValueError('请先写下你的问题')
        conversation = self.repo.get(self.active[mode])
        notice = ''
        if conversation and conversation['source_fingerprint'] != source_fingerprint(articles):
            notice = '原文已变化，本次将开启新对话，不携带旧版文章的历史。'
            conversation = None
        history = self.repo.history(conversation['id']) if conversation else []
        if regenerate:
            turns = self.repo.turns(self.active[mode])
            if not turns:
                raise ValueError('当前还没有可重新生成的请求')
            instruction = turns[-1]['instruction']
            if conversation and turns[-1]['status'] == 'complete':
                history = history[:-2]
        prepared = prepare_request(mode, instruction, articles, history,
                                   self.view.model.currentData(), self.view.thinking.isChecked(),
                                   self.view.max_tokens.value())
        return prepared, conversation['id'] if conversation else None, notice

    def preview(self, mode=None):
        mode = mode or self.view.current_page
        if mode not in self.view.tools:
            articles = self.view.sources.resolve(self.view.article_ids)
            dialog = RequestPreviewDialog(articles, self.view.request_instruction(), self.view)
        else:
            try:
                request, _, notice = self.prepare(mode)
            except ValueError as error:
                self.view.tools[mode]['status'].setText(str(error))
                return
            dialog = self.preview_dialog(request, False, notice)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def preview_dialog(self, request, sending, notice):
        return RequestPreviewDialog(request.articles, request.instruction, self.view,
            history=request.history, system_prompt=request.system_prompt, payload=request.payload,
            confirm_send=sending, settings_summary=f'{self.view.model.currentData()} · 输出上限 {self.view.max_tokens.value()} Token',
            extra_notice=notice)

    def send(self, mode, regenerate=False):
        if self.pending_result:
            self.retry_save()
            return
        if self.client.busy:
            return
        self.activate()
        if not self.ensure_key():
            self.view.navigate('settings')
            self.view.connection_status.setText('请先配置 API Key，再测试连接或发送。')
            return
        try:
            request, conversation_id, notice = self.prepare(mode, regenerate)
        except ValueError as error:
            self.view.tools[mode]['status'].setText(str(error))
            return
        regeneration_target = None
        if regenerate:
            turns = self.repo.turns(self.active[mode])
            if turns:
                regeneration_target = self.view.library.repo.find_by_turn(turns[-1]['id'])
            if regeneration_target:
                notice += '\n完整回复将保存为已关联作品的新版本，旧版本保留。'
        dialog = self.preview_dialog(request, True, notice)
        try:
            if dialog.exec() != dialog.DialogCode.Accepted:
                return
        finally:
            dialog.deleteLater()
        model = self.view.model.currentData()
        try:
            if conversation_id is None:
                title = self.view.tools[mode]['prompt'].toPlainText().strip() or self.view.tools[mode]['kind'].currentText()
                conversation_id = self.repo.create(mode, title, (a.id for a in request.articles), request.fingerprint)
            turn_id = self.repo.start_turn(conversation_id, request.instruction, model, (a.id for a in request.articles))
        except Exception:
            self.view.tools[mode]['status'].setText('无法保存本次请求，未发送内容；请检查数据文件夹。')
            return
        self.active[mode] = conversation_id
        self.regenerating_work = regeneration_target
        self.active_mode, self.active_turn = mode, turn_id
        self.stream_buffer.clear()
        self.render(mode)
        self.refresh_lists()
        self.view.tools[mode]['status'].setText('已确认发送，正在等待 DeepSeek 回复…')
        try:
            self.client.start(self.api_key, request.payload)
            self.flush_timer.start()
            self.update_controls()
        except (ValueError, RuntimeError):
            self.on_complete({'status': 'error', 'content': '', 'usage': None}, '请求未能启动，请检查密钥与连接配置。')

    def on_delta(self, chunk):
        if self.closing:
            return
        self.stream_buffer.append(chunk)
        if self.active_mode:
            self.view.tools[self.active_mode]['status'].setText('正在生成…')
            self.view.tools[self.active_mode]['copy'].setEnabled(True)

    def on_thinking(self):
        if self.active_mode and not self.closing:
            self.view.tools[self.active_mode]['status'].setText('DeepSeek 正在思考…')

    def flush_stream(self):
        if self.active_mode and self.stream_buffer:
            output = self.view.tools[self.active_mode]['output']
            output.append_stream(''.join(self.stream_buffer))
            self.stream_buffer.clear()

    def on_error(self, error):
        if self.closing:
            return
        if self.active_turn:
            self.on_complete(self.client.result('error'), error)
        else:
            self.view.connection_status.setText(error)
            self.update_controls()

    def on_complete(self, result, error=''):
        if self.closing:
            return
        self.flush_stream()
        self.flush_timer.stop()
        if not self.active_turn:
            self.view.connection_status.setText('连接测试已停止')
            self.update_controls()
            return
        mode, turn_id = self.active_mode, self.active_turn
        self.active_mode = self.active_turn = None
        try:
            self.repo.finish_turn(turn_id, result, error)
        except Exception:
            self.pending_result = (mode, turn_id, result, error)
            self.view.tools[mode]['status'].setText('回复暂未保存，请复制保留内容，或点击“重试保存”。')
        else:
            self.render(mode)
            if result['status'] == 'complete':
                self.view.tools[mode]['prompt'].clear()
                self.finish_work_version(mode, turn_id)
                if mode == 'writing':
                    latest = self.repo.turns(self.active[mode])[-1]
                    self.view.restore_task_settings(mode, latest['instruction'], True)
            self.refresh_usage()
        if not self.pending_result:
            self.regenerating_work = None
        self.refresh_lists()
        self.update_controls()

    def retry_save(self):
        if not self.pending_result:
            return True
        mode, turn_id, result, error = self.pending_result
        try:
            self.repo.finish_turn(turn_id, result, error)
        except Exception:
            self.view.tools[mode]['status'].setText('仍无法保存，请检查数据文件夹；当前回复保留在窗口中。')
            return False
        self.pending_result = None
        self.render(mode)
        if result['status'] == 'complete':
            self.view.tools[mode]['prompt'].clear()
            self.finish_work_version(mode, turn_id)
            if mode == 'writing':
                latest = self.repo.turns(self.active[mode])[-1]
                self.view.restore_task_settings(mode, latest['instruction'], True)
        self.refresh_usage()
        self.update_controls()
        self.regenerating_work = None
        return True

    def finish_work_version(self, mode, turn_id):
        if not self.regenerating_work:
            return
        turn = next(t for t in self.repo.turns(self.active[mode]) if t['id'] == turn_id)
        try:
            number = self.view.library.append_generation(self.regenerating_work, turn)
            self.view.tools[mode]['status'].setText(self.view.tools[mode]['status'].text() + f' · 作品已新增 v{number}')
        except Exception:
            self.view.tools[mode]['status'].setText('回复已保存在对话中，但作品新版保存失败；可点击“保存作品”重试。')

    def save_work(self, mode, edit=False):
        if self.client.busy or self.pending_result:
            return
        turn = next((t for t in reversed(self.repo.turns(self.active[mode])) if t['response'].strip()), None)
        if turn is None:
            return
        existing = self.view.library.repo.find_by_turn(turn['id'])
        if existing and not edit:
            self.view.navigate('library')
            self.view.library.show_work(existing)
            return
        from northdiary.ui.ai_work_editor import SaveWorkDialog
        category = {'appreciation': '点评', 'analysis': '分析报告', 'writing': '故事', 'chat': '创作草稿'}[mode]
        if mode == 'appreciation' and '类型：逐段批注' in turn['instruction']:
            category = '旁注'
        if mode == 'writing' and any('步骤：' + step in turn['instruction'] for step in ('故事大纲', '人物设定', '连续性整理')):
            category = '创作草稿'
        conversation = self.repo.get(self.active[mode])
        data = self.view.library.generation_data(turn, conversation['title'], category)
        dialog = SaveWorkDialog(self.view.library.repo, data, self.view, existing)
        try:
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.view.navigate('library')
                self.view.library.show_work(dialog.work_id)
        finally:
            dialog.deleteLater()

    def render(self, mode):
        tool = self.view.tools[mode]
        turns = self.repo.turns(self.active[mode])
        tool['output'].set_turns(turns, self.status_text)
        if turns:
            tool['status'].setText(self.status_text(turns[-1]))

    @staticmethod
    def status_text(turn):
        labels = {'running': '正在生成', 'complete': '已完成', 'stopped': '已停止，部分回复不加入后续上下文',
                  'error': '请求失败', 'incomplete': '达到输出上限，回复不完整；可提高输出上限后重新生成',
                  'interrupted': '上次程序退出时未完成，不加入后续上下文'}
        result = labels[turn['status']]
        if turn.get('error_text'):
            result += ' · ' + turn['error_text']
        if turn.get('prompt_tokens') is not None:
            result += f" · 输入 {turn['prompt_tokens']} / 输出 {turn['completion_tokens']} Token"
            if turn.get('cost_low_usd') is not None:
                result += f" · 预估 US${turn['cost_low_usd']:.6f}–{turn['cost_high_usd']:.6f}"
            else:
                result += ' · 该模型费用暂无参考估算'
        elif turn['status'] != 'running':
            result += ' · 服务未回报用量，费用未知'
        return result

    def copy_response(self, mode):
        if self.pending_result and self.pending_result[0] == mode:
            content = self.pending_result[2]['content']
        elif self.active_mode == mode:
            content = self.client.content
        else:
            content = next((t['response'] for t in reversed(self.repo.turns(self.active[mode])) if t['response']), '')
        if content:
            QApplication.clipboard().setText(content)

    def refresh_usage(self):
        totals = self.repo.totals()
        prompt, output = totals['prompt_tokens'] or 0, totals['completion_tokens'] or 0
        amount = (f"US${totals['cost_low_usd']:.6f}–{totals['cost_high_usd']:.6f}"
                  if totals['cost_low_usd'] is not None else '—')
        self.view.usage_label.setText(f"累计 {totals['requests']} 次请求 · 输入 {prompt} / 输出 {output} Token\n预估费用：{amount}"
                                     + (f" · {totals['unknown_usage']} 次未回报用量" if totals['unknown_usage'] else '')
                                     + (f" · {totals['unpriced_requests']} 次费用待确认" if totals['unpriced_requests'] else ''))

    def update_controls(self):
        busy = self.client.busy
        blocked = busy or self.pending_result is not None
        for mode, tool in self.view.tools.items():
            for key in ('conversation', 'new', 'kind', 'tone', 'perspective', 'length'):
                tool[key].setEnabled(not blocked)
            for key in ('focus', 'step', 'chapter', 'story_settings'):
                if key in tool:
                    tool[key].setEnabled(not blocked)
            tool['delete'].setEnabled(not blocked and bool(self.active[mode]))
            tool['prompt'].setReadOnly(blocked)
            tool['send'].setEnabled(not blocked or bool(self.pending_result and self.pending_result[0] == mode))
            tool['send'].setText('重试保存' if self.pending_result and self.pending_result[0] == mode else ('发送' if mode == 'chat' else '生成'))
            tool['stop'].setEnabled(busy and self.active_mode == mode)
            turns = self.repo.turns(self.active[mode])
            tool['regenerate'].setEnabled(not blocked and bool(turns))
            tool['copy'].setEnabled(any(t['response'] for t in turns) or self.active_mode == mode or bool(self.pending_result and self.pending_result[0] == mode))
            for key in ('save_work', 'edit_work'):
                tool[key].setEnabled(not blocked and any(t['response'].strip() for t in turns))
        for widget in (self.view.api_key, self.view.apply_key_button, self.view.clear_key_button,
                       self.view.remember_key, self.view.model, self.view.thinking, self.view.max_tokens,
                       self.view.choose_source_button, self.view.remove_source_button):
            widget.setEnabled(not blocked)
        self.view.test_button.setText('停止测试' if busy and self.client.kind == 'models' else '测试连接 / 刷新模型')
        self.view.test_button.setEnabled(not blocked or busy and self.client.kind == 'models')
        if not blocked:
            self.view.update_source_actions()

    def shutdown(self):
        if not self.view.library.can_leave():
            return False
        if not self.retry_save():
            return False
        if self.active_turn:
            try:
                self.repo.finish_turn(self.active_turn, self.client.result('stopped'))
            except Exception:
                self.view.tools[self.active_mode]['status'].setText('暂时无法保存回复，请复制内容并重试关闭。')
                return False
        self.closing = True
        self.flush_timer.stop()
        self.client.stop()
        return True
