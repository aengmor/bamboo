"""
URL configuration for bamboo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from texts import views
from django.conf.urls.static import static
from django.conf import settings
from texts.api_views import (
    ChapterViewSet,
    CharacterViewSet,
    CollectionViewSet,
    GlyphViewSet,
    HomeSummaryView,
    SlipTextViewSet,
    csrf_token,
)
from texts.spa import spa_app

router = DefaultRouter()
router.register(r'slips', SlipTextViewSet, basename='slip')
router.register(r'chapters', ChapterViewSet, basename='chapter-api')
router.register(r'collections', CollectionViewSet, basename='collection-api')
router.register(r'characters', CharacterViewSet, basename='character-api')
router.register(r'glyphs', GlyphViewSet, basename='glyph-api')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', spa_app, name='home'),
    path('all/', spa_app, name='slip_list'),
    path('slip/<int:pk>/', spa_app, name='slip_detail'),
    path('character/<int:pk>/', spa_app, name='character_detail'),
    path('chapters/', spa_app, name='chapter_list'),
    path('glyph/<int:pk>/', spa_app, name='glyph_detail'),
    path('collections/', spa_app, name='collection_list'),
    path('collection/<int:pk>/', spa_app, name='collection_detail'),
    path('search/', spa_app, name='search'),
    path('dictionary/', spa_app, name='dictionary'),
    path('random/', views.random_slip, name='random_slip'),
    path('api/csrf/', csrf_token, name='api-csrf'),
    path('api/home/', HomeSummaryView.as_view(), name='api-home'),
    path('api/', include(router.urls)),    # 所有 API 都在 /api/ 下
    re_path(r'^(?!(?:admin|api|media|static)(?:/|$)).*$', spa_app),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)