from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def update_qs(context, **kwargs):
    """更新当前查询字符串，保留现有参数并添加/覆盖新参数"""
    request = context['request']
    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = str(value)
    return '?' + urlencode(params) if params else ''