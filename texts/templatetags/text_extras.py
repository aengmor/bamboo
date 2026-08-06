from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def highlight(value, arg):
    """在文本中高亮显示关键词"""
    if not arg:
        return value
    # 转义正则特殊字符，并忽略大小写
    pattern = re.compile(re.escape(arg), re.IGNORECASE)
    # 用 <mark> 标签包裹匹配到的关键词
    highlighted = pattern.sub(lambda m: f'<mark>{m.group(0)}</mark>', value)
    return mark_safe(highlighted)