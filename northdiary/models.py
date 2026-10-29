from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    diary_date: str
    body_html: str
    body_text: str
    created_at: str
    updated_at: str
    deleted_at: str | None = None
    pinned: int = 0
    sort_order: int = 0


@dataclass(frozen=True)
class ExportSelection:
    """Ordered IDs are independent of categories; exporters resolve fresh content."""
    article_ids: tuple[str, ...]
    title: str
    author: str = ''
