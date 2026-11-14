"""Read structured review candidates from an untrusted model response."""
import json
import re


ASSOCIATIONS = re.compile(r'^ *```memory-associations[^\S\n]*\n(.*?)^ *```[^\S\n]*$', re.M | re.S)


def report_text(response):
    return ASSOCIATIONS.sub('', response).strip()


def review_candidates(turn):
    if turn['status'] != 'complete':
        return []
    block = ASSOCIATIONS.search(turn['response'])
    if not block or len(block[1]) > 48_000:
        return []
    try:
        rows = json.loads(block[1])
        allowed = set(json.loads(turn['article_ids']))
    except (ValueError, TypeError):
        return []
    if not isinstance(rows, list):
        return []
    candidates = []
    for index, row in enumerate(rows[:12]):
        if not isinstance(row, dict):
            continue
        summary, evidence, sources = (row.get(key) for key in ('summary', 'evidence', 'sources'))
        if not isinstance(summary, str) or not summary.strip() or not isinstance(evidence, str):
            continue
        if not isinstance(sources, list) or not all(isinstance(key, str) and key in allowed for key in sources):
            continue
        sources = tuple(dict.fromkeys(sources))
        if len(sources) >= 2:
            candidates.append((index, summary.strip()[:400], evidence.strip()[:2000], sources))
    return candidates
