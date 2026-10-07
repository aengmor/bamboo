from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def spa_app(request, *args, **kwargs):
    index_path = Path(settings.BASE_DIR) / 'texts' / 'static' / 'texts' / 'vue' / 'index.html'
    try:
        html = index_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return HttpResponse(
            'Vue assets are missing. Build the frontend before serving public pages.',
            status=503,
        )
    return HttpResponse(html, content_type='text/html; charset=utf-8')