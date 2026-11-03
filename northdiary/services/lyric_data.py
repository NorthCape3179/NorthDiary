"""Shared LRC data handling for lyrics sources."""
from bisect import bisect_left
import re
import unicodedata


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value).casefold() if c.isalnum())


def parse_lrc(value):
    offset = re.search(r'\[offset:([+-]?\d+)\]', value, re.I)
    shift = int(offset[1]) / 1000 if offset else 0
    lines = {}
    for row in value.splitlines():
        stamps = re.findall(r'\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]', row)
        body = re.sub(r'\[[^\]]*\]', '', row).strip()
        for minute, second, fraction in stamps:
            at = int(minute) * 60 + int(second) + float('0.' + (fraction or '0')) - shift
            parts = lines.setdefault(at, [])
            if body and body not in parts:
                parts.append(body)
    return [(at, ' / '.join(parts)) for at, parts in sorted(lines.items())]


def aligned_translations(original, translated):
    """Align only nearby timestamps, never infer translations by row number."""
    stamps = [at for at, _ in original]
    mapping = {}
    for at, body in translated:
        if not body or not stamps:
            continue
        i = bisect_left(stamps, at)
        choices = [j for j in (i - 1, i) if 0 <= j < len(stamps)]
        index = min(choices, key=lambda j: abs(stamps[j] - at))
        if abs(stamps[index] - at) <= .5 and body != original[index][1]:
            key = stamps[index]
            mapping[key] = (mapping[key] + ' / ' + body) if key in mapping else body
    return mapping
