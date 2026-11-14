"""Portable typography only: no URLs, Qt internals or arbitrary CSS."""
import re


_FAMILY_NAME = r'''(?:'[^'\\\x00-\x1f;{}<>]+'|"[^"\\\x00-\x1f;{}<>]+"|[\w .+&@!-]+)'''
FAMILY = re.compile(_FAMILY_NAME + r'(?:\s*,\s*' + _FAMILY_NAME + r')*')
LENGTH = re.compile(r'(-?(?:\d+(?:\.\d+)?|\.\d+))(pt|px|em|rem|%)?')


def safe_typography(node):
    values = {}
    for item in node.get('style', '').split(';'):
        if ':' in item:
            key, value = item.split(':', 1)
            values[key.strip().lower()] = value.strip()
    if node.get('align', '').lower() in ('left', 'center', 'right', 'justify'):
        values.setdefault('text-align', node.get('align').lower())
    result = {}
    for key, value in values.items():
        lower = value.lower()
        if key == 'font-family' and len(value) <= 512 and FAMILY.fullmatch(value):
            result[key] = value
        elif key == 'font-weight' and (lower in ('normal', 'bold') or re.fullmatch('[1-9]00', lower)):
            result[key] = lower
        elif key == 'font-style' and lower in ('normal', 'italic', 'oblique'):
            result[key] = lower
        elif key == 'text-align' and lower in ('left', 'center', 'right', 'justify'):
            result[key] = lower
        elif key == 'text-decoration' and lower.split() and set(lower.split()) <= {'none', 'underline', 'line-through', 'overline'}:
            result[key] = lower
        elif key in ('font-size', 'text-indent', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right', 'line-height'):
            match = LENGTH.fullmatch(lower)
            if not match:
                continue
            number, unit = float(match[1]), match[2]
            if key == 'font-size':
                valid = unit is not None and 0 < number <= (1000 if unit == '%' else 512 if unit in ('px', 'pt') else 32)
            elif key == 'line-height':
                valid = 0 < number <= (1000 if unit else 10)
            else:
                valid = abs(number) <= 10000 and (unit is not None or number == 0)
            if valid:
                result[key] = lower
    return result


def style_string(values):
    return '; '.join(f'{key}: {value}' for key, value in values.items())
