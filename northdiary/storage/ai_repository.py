"""Conversations and request usage are separate from original articles and AI works."""
import json
from uuid import uuid4

from northdiary.services.ai_requests import estimate_cost, token_usage
from northdiary.storage.repository import now


class AIRepository:
    def __init__(self, database):
        self.db = database.connection

    def conversations(self, mode):
        return [dict(row) for row in self.db.execute(
            'SELECT * FROM ai_conversations WHERE mode=? ORDER BY updated_at DESC,id', (mode,))]

    def get(self, conversation_id):
        row = self.db.execute('SELECT * FROM ai_conversations WHERE id=?', (conversation_id,)).fetchone()
        return dict(row) if row else None

    def create(self, mode, title, article_ids, fingerprint):
        key, stamp = str(uuid4()), now()
        with self.db:
            self.db.execute('INSERT INTO ai_conversations VALUES (?,?,?,?,?,?,?)',
                            (key, mode, title.strip()[:40] or '新对话', json.dumps(list(article_ids)), fingerprint, stamp, stamp))
        return key

    def turns(self, conversation_id):
        if not conversation_id:
            return []
        return [dict(row) for row in self.db.execute(
            'SELECT * FROM ai_turns WHERE conversation_id=? ORDER BY created_at,id', (conversation_id,))]

    def history(self, conversation_id):
        messages = []
        for turn in self.turns(conversation_id):
            if turn['status'] == 'complete':
                messages.extend([{'role': 'user', 'content': turn['instruction']},
                                 {'role': 'assistant', 'content': turn['response']}])
        return messages

    def start_turn(self, conversation_id, instruction, model, article_ids):
        key, stamp = str(uuid4()), now()
        with self.db:
            self.db.execute('''INSERT INTO ai_turns
                (id,conversation_id,instruction,model,status,article_ids,created_at,updated_at)
                VALUES (?,?,?,?,'running',?,?,?)''',
                            (key, conversation_id, instruction, model, json.dumps(list(article_ids)), stamp, stamp))
            self.db.execute('UPDATE ai_conversations SET updated_at=? WHERE id=?', (stamp, conversation_id))
        return key

    def finish_turn(self, turn_id, result, error=''):
        row = self.db.execute('SELECT model FROM ai_turns WHERE id=?', (turn_id,)).fetchone()
        if row is None:
            raise KeyError('对话请求不存在')
        usage = token_usage(result.get('usage')) or {}
        low, high = estimate_cost(row['model'], result.get('usage'))
        stamp = now()
        with self.db:
            self.db.execute('''UPDATE ai_turns SET response=?,response_model=?,status=?,updated_at=?,
                prompt_tokens=?,completion_tokens=?,cache_hit_tokens=?,cost_low_usd=?,cost_high_usd=?,
                error_text=?,finish_reason=? WHERE id=?''',
                (result.get('content', ''), result.get('model', ''), result['status'], stamp,
                 usage.get('prompt_tokens'), usage.get('completion_tokens'), usage.get('cache_hit_tokens'),
                 low, high, error, result.get('finish_reason'), turn_id))

    def delete(self, conversation_id):
        with self.db:
            self.db.execute('DELETE FROM ai_conversations WHERE id=?', (conversation_id,))

    def recover_interrupted(self):
        # Called once when first opening the studio, never at construction in tests.
        with self.db:
            self.db.execute("UPDATE ai_turns SET status='interrupted' WHERE status='running'")

    def totals(self):
        return dict(self.db.execute('''SELECT COUNT(*) AS requests, SUM(prompt_tokens) AS prompt_tokens,
            SUM(completion_tokens) AS completion_tokens, SUM(cost_low_usd) AS cost_low_usd,
            SUM(cost_high_usd) AS cost_high_usd,
            SUM(CASE WHEN prompt_tokens IS NULL THEN 1 ELSE 0 END) AS unknown_usage
            ,SUM(CASE WHEN cost_low_usd IS NULL THEN 1 ELSE 0 END) AS unpriced_requests
            FROM ai_turns''').fetchone())
