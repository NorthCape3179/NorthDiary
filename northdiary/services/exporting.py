from pathlib import Path
from typing import Protocol
from northdiary.models import ExportSelection


class Exporter(Protocol):
    """EPUB/PDF adapters consume the same ordered selection."""
    def export(self, selection: ExportSelection, destination: Path) -> Path: ...


def validate_selection(repository, selection: ExportSelection):
    if not selection.article_ids:
        raise ValueError('请至少选择一篇文章')
    if len(set(selection.article_ids)) != len(selection.article_ids):
        raise ValueError('导出列表中不能重复添加同一篇文章')
    articles = [repository.get(key) for key in selection.article_ids]
    if any(article.deleted_at for article in articles):
        raise ValueError('不能导出回收站中的文章')
    return articles

