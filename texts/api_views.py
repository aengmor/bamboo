import random

import zhconv
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import (
    Annotation,
    Chapter,
    ChapterComment,
    Character,
    Collection,
    CollectionComment,
    Glyph,
    GlyphAnnotation,
    SlipChar,
    SlipText,
)
from .serializers import (
    AnnotationReadSerializer,
    AnnotationSubmissionSerializer,
    ChapterCommentSerializer,
    ChapterSummarySerializer,
    ChapterWithSlipsSerializer,
    CharacterDetailSerializer,
    CharacterSummarySerializer,
    CollectionCommentSerializer,
    CollectionSummarySerializer,
    GlyphAnnotationReadSerializer,
    GlyphAnnotationSubmissionSerializer,
    GlyphDetailSerializer,
    GlyphSummarySerializer,
    SlipDetailSerializer,
    SlipSummarySerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200


@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


class HomeSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        recent_slips = SlipText.objects.select_related('chapter').order_by('-id')[:5]
        return Response({
            'total_chapters': Chapter.objects.count(),
            'total_slips': SlipText.objects.count(),
            'total_characters': Character.objects.count(),
            'total_annotations': Annotation.objects.filter(is_approved=True).count(),
            'recent_slips': SlipSummarySerializer(recent_slips, many=True, context={'request': request}).data,
        })


class PublicReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    throttle_scope = 'submission'
    submission_actions = frozenset()

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_throttles(self):
        if self.action in self.submission_actions and self.request.method == 'POST':
            return [ScopedRateThrottle()]
        return []


class SlipTextViewSet(PublicReadOnlyViewSet):
    queryset = SlipText.objects.all()
    serializer_class = SlipSummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['chapter', 'slip_id']
    submission_actions = frozenset({'annotations'})

    def get_queryset(self):
        queryset = SlipText.objects.select_related('chapter', 'chapter__collection')
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'slipchars',
                    queryset=SlipChar.objects.select_related('character').order_by('position'),
                    to_attr='api_slipchars',
                ),
                Prefetch('glyphs', queryset=Glyph.objects.select_related('character'), to_attr='api_glyphs'),
            )
        chapter_id = self.request.query_params.get('chapter')
        if chapter_id and chapter_id.isdigit():
            queryset = queryset.filter(chapter_id=int(chapter_id))
        collection_id = self.request.query_params.get('collection')
        if collection_id and collection_id.isdigit():
            queryset = queryset.filter(chapter__collection_id=int(collection_id))
        return queryset.order_by('chapter__title', 'order', 'slip_id', 'pk')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SlipDetailSerializer
        return SlipSummarySerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '').strip()
        search_in = request.query_params.get('search_in', 'all')
        queryset = self.get_queryset()
        if query:
            if search_in == 'content':
                queryset = queryset.filter(content__icontains=query)
            elif search_in == 'slip_id':
                queryset = queryset.filter(slip_id__icontains=query)
            elif search_in == 'character':
                queryset = queryset.filter(slipchars__character__glyph__icontains=query).distinct()
            else:
                queryset = queryset.filter(
                    Q(content__icontains=query)
                    | Q(slip_id__icontains=query)
                    | Q(chapter__title__icontains=query)
                )
        page = self.paginate_queryset(queryset)
        serializer = SlipSummarySerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def annotations(self, request, pk=None):
        slip = self.get_object()
        if request.method == 'POST':
            serializer = AnnotationSubmissionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(slip=slip, is_approved=False, confidence=1, likes=0)
            return Response(
                {'detail': '投稿已提交，审核通过后显示。'},
                status=status.HTTP_201_CREATED,
            )

        annotations = slip.annotations.filter(is_approved=True).order_by('-created_at')
        page = self.paginate_queryset(annotations)
        data = AnnotationReadSerializer(page, many=True, context={'request': request}).data
        return self.get_paginated_response(data)

    @action(detail=False, methods=['get'])
    def random(self, request):
        slip_count = SlipText.objects.count()
        if not slip_count:
            return Response({'detail': '暂无竹简数据。'}, status=status.HTTP_404_NOT_FOUND)
        slip_id = SlipText.objects.order_by('pk').values_list('pk', flat=True)[random.randrange(slip_count)]
        return Response({'id': slip_id, 'url': f'/slip/{slip_id}/'})


class ChapterViewSet(PublicReadOnlyViewSet):
    queryset = Chapter.objects.all()

    def get_queryset(self):
        queryset = Chapter.objects.select_related('collection').annotate(
            slips_count=Count('slip_texts', distinct=True)
        )
        if self.action == 'list' and self.request.query_params.get('include_slips') == '1':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'slip_texts',
                    queryset=SlipText.objects.select_related('chapter', 'chapter__collection').order_by(
                        'order', 'slip_id', 'pk'
                    ),
                    to_attr='api_slips',
                )
            )
        collection_id = self.request.query_params.get('collection')
        if collection_id and collection_id.isdigit():
            queryset = queryset.filter(collection_id=int(collection_id))
        return queryset.order_by('title', 'pk')

    submission_actions = frozenset({'comments'})

    def get_serializer_class(self):
        if self.action == 'list' and self.request.query_params.get('include_slips') == '1':
            return ChapterWithSlipsSerializer
        return ChapterSummarySerializer

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        chapter = self.get_object()
        if request.method == 'POST':
            serializer = PublicCommentSubmissionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            ChapterComment.objects.create(
                chapter=chapter,
                author=serializer.validated_data['author'],
                content=serializer.validated_data['content'],
                is_approved=False,
            )
            return Response({'detail': '评论已提交，审核通过后显示。'}, status=status.HTTP_201_CREATED)

        comments = chapter.comments.filter(is_approved=True).order_by('-created_at')
        page = self.paginate_queryset(comments)
        data = ChapterCommentSerializer(page, many=True, context={'request': request}).data
        return self.get_paginated_response(data)


class CollectionViewSet(PublicReadOnlyViewSet):
    queryset = Collection.objects.all()

    def get_queryset(self):
        queryset = Collection.objects.annotate(chapter_count=Count('chapters', distinct=True))
        return queryset.order_by('order', 'name', 'pk')

    submission_actions = frozenset({'comments'})

    def get_serializer_class(self):
        return CollectionSummarySerializer

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        collection = self.get_object()
        if request.method == 'POST':
            serializer = PublicCommentSubmissionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            CollectionComment.objects.create(
                collection=collection,
                author=serializer.validated_data['author'],
                content=serializer.validated_data['content'],
                is_approved=False,
            )
            return Response({'detail': '评论已提交，审核通过后显示。'}, status=status.HTTP_201_CREATED)

        comments = collection.comments.filter(is_approved=True).order_by('-created_at')
        page = self.paginate_queryset(comments)
        data = CollectionCommentSerializer(page, many=True, context={'request': request}).data
        return self.get_paginated_response(data)


class CharacterViewSet(PublicReadOnlyViewSet):
    queryset = Character.objects.all()
    serializer_class = CharacterSummarySerializer

    def get_queryset(self):
        queryset = Character.objects.annotate(occurrence_count=Count('slipchar', distinct=True))
        query = self.request.query_params.get('q', '').strip()
        search_type = self.request.query_params.get('search_type', 'glyph')
        if not query:
            return queryset.order_by('glyph', 'pronunciation', 'pk')
        if search_type == 'meaning':
            queryset = queryset.filter(meaning__icontains=query)
        elif search_type == 'pronunciation':
            queryset = queryset.filter(
                Q(pronunciation_ascii__iexact=query) | Q(pronunciation__iexact=query)
            )
        else:
            try:
                query = zhconv.convert(query, 'zh-hant')
            except (LookupError, ValueError):
                pass
            queryset = queryset.filter(
                Q(glyph__icontains=query)
                | Q(pronunciation_ascii__icontains=query)
                | Q(pronunciation__icontains=query)
            )
        return queryset.order_by('glyph', 'pronunciation', 'pk')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CharacterDetailSerializer
        return CharacterSummarySerializer

    @action(detail=True, methods=['get'])
    def picker(self, request, pk=None):
        character = self.get_object()
        rows = SlipChar.objects.filter(character=character).values(
            'slip_id', 'slip__slip_id', 'slip__chapter__title', 'position'
        ).order_by('slip__chapter__title', 'slip__slip_id', 'position')
        return Response(list(rows))

    @action(detail=True, methods=['get'])
    def occurrences(self, request, pk=None):
        character = self.get_object()
        queryset = SlipChar.objects.filter(character=character).select_related(
            'character', 'slip', 'slip__chapter', 'slip__chapter__collection'
        ).prefetch_related(
            Prefetch(
                'slip__slipchars',
                queryset=SlipChar.objects.select_related('character').order_by('position'),
                to_attr='api_slipchars',
            ),
            Prefetch(
                'slip__glyphs',
                queryset=Glyph.objects.select_related('character'),
                to_attr='api_glyphs',
            ),
        ).order_by('slip__chapter__title', 'slip__slip_id', 'position')
        page = self.paginate_queryset(queryset)
        results = []
        for occurrence in page:
            chars = getattr(occurrence.slip, 'api_slipchars', [])
            index = next((i for i, item in enumerate(chars) if item.pk == occurrence.pk), -1)
            if index < 0:
                before = after = ''
            else:
                before = ''.join(item.character.glyph for item in chars[max(0, index - 10):index])
                after = ''.join(item.character.glyph for item in chars[index + 1:index + 11])
            glyph = next(
                (item for item in getattr(occurrence.slip, 'api_glyphs', [])
                 if item.position == occurrence.position),
                None,
            )
            results.append({
                'id': occurrence.pk,
                'position': occurrence.position,
                'status': occurrence.status,
                'context_before': before,
                'context_after': after,
                'slip': {
                    'id': occurrence.slip.pk,
                    'slip_id': occurrence.slip.slip_id,
                    'chapter': {
                        'id': occurrence.slip.chapter_id,
                        'title': occurrence.slip.chapter.title if occurrence.slip.chapter else None,
                    },
                },
                'character': CharacterSummarySerializer(occurrence.character, context={'request': request}).data,
                'glyph': GlyphSummarySerializer(glyph, context={'request': request}).data if glyph else None,
            })
        return self.get_paginated_response(results)


class GlyphViewSet(PublicReadOnlyViewSet):
    queryset = Glyph.objects.all()
    serializer_class = GlyphDetailSerializer

    def get_queryset(self):
        queryset = Glyph.objects.select_related(
            'character', 'slip', 'slip__chapter', 'slip__chapter__collection'
        ).prefetch_related(
            Prefetch(
                'slip__slipchars',
                queryset=SlipChar.objects.select_related('character').order_by('position'),
                to_attr='api_slipchars',
            ),
        )
        return queryset

    submission_actions = frozenset({'annotations'})

    @action(detail=True, methods=['get', 'post'])
    def annotations(self, request, pk=None):
        glyph = self.get_object()
        if request.method == 'POST':
            serializer = GlyphAnnotationSubmissionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(glyph=glyph, is_approved=False)
            return Response({'detail': '投稿已提交，审核通过后显示。'}, status=status.HTTP_201_CREATED)

        annotations = glyph.annotations.filter(is_approved=True).order_by('-created_at')
        page = self.paginate_queryset(annotations)
        data = GlyphAnnotationReadSerializer(page, many=True, context={'request': request}).data
        return self.get_paginated_response(data)


class PublicCommentSubmissionSerializer(serializers.Serializer):
    author = serializers.CharField(max_length=100)
    content = serializers.CharField()