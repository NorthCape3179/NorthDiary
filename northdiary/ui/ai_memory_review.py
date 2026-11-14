"""Local review of proposed links in a saved memory report."""
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QTextEdit, QVBoxLayout

from northdiary.ui.ai_sources import inherit_theme


class MemoryReviewDialog(QDialog):
    def __init__(self, candidates, decisions, titles, parent=None):
        super().__init__(parent)
        self.candidates = candidates
        self.decisions = dict(decisions)
        self.titles = titles
        self.source_id = None
        self.setWindowTitle('核对关联 · AI 记忆引擎')
        self.resize(680, 510)
        layout = QVBoxLayout(self)
        hint = QLabel('判断保存在这份回忆报告里。打开原文前，请先保存当前判断。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.items = QListWidget()
        for _, summary, _, _ in candidates:
            self.items.addItem(summary)
        layout.addWidget(self.items, 1)
        self.evidence = QTextEdit()
        self.evidence.setReadOnly(True)
        layout.addWidget(self.evidence, 1)
        sources = QHBoxLayout()
        self.sources = QComboBox()
        sources.addWidget(self.sources, 1)
        open_source = QPushButton('打开原文')
        open_source.clicked.connect(self.open_source)
        sources.addWidget(open_source)
        layout.addLayout(sources)
        actions = QHBoxLayout()
        self.decision = QComboBox()
        for label, value in [('暂不确认', 'pending'), ('确认关联', 'confirmed'), ('否认关联', 'rejected')]:
            self.decision.addItem(label, value)
        self.decision.currentIndexChanged.connect(self.change_decision)
        actions.addWidget(self.decision)
        actions.addStretch()
        cancel = QPushButton('取消')
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        save = QPushButton('保存判断')
        save.clicked.connect(self.accept)
        actions.addWidget(save)
        layout.addLayout(actions)
        self.items.currentRowChanged.connect(self.show_candidate)
        self.items.setCurrentRow(0)
        inherit_theme(self, parent)

    def show_candidate(self, row):
        if row < 0:
            return
        index, summary, evidence, sources = self.candidates[row]
        self.evidence.setPlainText(summary + '\n\n' + evidence)
        self.sources.clear()
        for key in sources:
            self.sources.addItem(self.titles.get(key, '原文已不可用'), key)
        self.decision.blockSignals(True)
        self.decision.setCurrentIndex(self.decision.findData(self.decisions.get(index, 'pending')))
        self.decision.blockSignals(False)

    def change_decision(self):
        row = self.items.currentRow()
        if row >= 0:
            self.decisions[self.candidates[row][0]] = self.decision.currentData()

    def open_source(self):
        self.source_id = self.sources.currentData()
        if self.source_id:
            self.accept()
