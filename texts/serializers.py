import bleach
import markdown
from rest_framework import serializers

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
    Slip,
)


class CollectionSummarySerializer(serializers.ModelSerializer):
    chapter_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'order', 'chapter_count']


class ChapterSummarySerializer(serializers.ModelSerializer):
    collection = CollectionSummarySerializer(read_only=True)
    slips_count = serializers.IntegerField(read_only=True)
    description_html = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'title', 'description', 'description_html', 'slip_order', 'collection', 'slips_count']

    def get_description_html(self, obj):
        html = markdown.markdown(obj.description)
        allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS) | {
            'blockquote', 'br', 'h1', 'h2', 'h3', 'h4', 'hr', 'li', 'ol', 'p', 'pre', 'ul',
        }
        return bleach.clean(
            html,
            tags=allowed_tags,
            attributes={'a': ['href', 'title']},
            protocols={'http', 'https', 'mailto'},
            strip=True,
        )


class ChapterCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterComment
        fields = ['id', 'author', 'content', 'created_at']


class CollectionCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionComment
        fields = ['id', 'author', 'content', 'created_at']


class CharacterSummarySerializer(serializers.ModelSerializer):
    # 前端沿用旧字段名 glyph 表示字头，这里与 reading 对齐
    glyph = serializers.CharField(source='reading', read_only=True)

    class Meta:
        model = Character
        fields = [
            'id',
            'reading',
            'glyph',
            'initial',
            'rhyme',
            'pronunciation',
            'pronunciation_ascii',
            'harmonic_domain',
            'phonological_position',
            'middle_chinese',
            'mandarin',
            'phonetic_head',
            'seen_shijing_rhyme',
            'seen_zhanguo_rhyme',
            'freq_total',
            'freq_pre_qin',
            'seen_western_zhou',
            'freq_western_zhou',
            'rare_source',
            'glyph_image',
            'ids',
            'meaning',
            'notes',
        ]


class GlyphSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Glyph
        fields = ['id', 'image', 'source', 'notes']


class AnnotationReadSerializer(serializers.ModelSerializer):
    annotation_type_label = serializers.CharField(source='get_annotation_type_display', read_only=True)

    class Meta:
        model = Annotation
        fields = [
            'id',
            'annotation_type',
            'annotation_type_label',
            'title',
            'content',
            'evidence',
            'author',
            'confidence',
            'created_at',
        ]


class AnnotationSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['annotation_type', 'title', 'content', 'evidence', 'author']


class GlyphAnnotationReadSerializer(serializers.ModelSerializer):
    annotation_type_label = serializers.CharField(source='get_annotation_type_display', read_only=True)

    class Meta:
        model = GlyphAnnotation
        fields = [
            'id',
            'annotation_type',
            'annotation_type_label',
            'title',
            'reading',
            'content',
            'evidence',
            'author',
            'confidence',
            'created_at',
        ]


class GlyphAnnotationSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlyphAnnotation
        fields = ['annotation_type', 'title', 'reading', 'content', 'evidence', 'author']


class SlipSummarySerializer(serializers.ModelSerializer):
    chapter = ChapterSummarySerializer(read_only=True)

    class Meta:
        model = Slip
        fields = ['id', 'slip_id', 'content', 'chapter', 'order', 'source', 'parallel_text', 'image']


class ChapterWithSlipsSerializer(ChapterSummarySerializer):
    slips = serializers.SerializerMethodField()

    class Meta(ChapterSummarySerializer.Meta):
        fields = ChapterSummarySerializer.Meta.fields + ['slips']

    def get_slips(self, obj):
        slips = getattr(obj, 'api_slips', [])
        return SlipSummarySerializer(slips, many=True, context=self.context).data


class SlipCharacterSerializer(serializers.ModelSerializer):
    character = CharacterSummarySerializer(read_only=True)
    glyph = serializers.SerializerMethodField()

    class Meta:
        model = SlipChar
        fields = ['id', 'position', 'status', 'character', 'glyph']

    def get_glyph(self, obj):
        if not obj.glyph_id:
            return None
        try:
            glyph = obj.glyph
        except Glyph.DoesNotExist:
            return None
        return GlyphSummarySerializer(glyph, context=self.context).data


class SlipDetailSerializer(SlipSummarySerializer):
    characters = serializers.SerializerMethodField()

    class Meta(SlipSummarySerializer.Meta):
        fields = SlipSummarySerializer.Meta.fields + ['characters']

    def get_characters(self, obj):
        slipchars = getattr(obj, 'api_slipchars', None)
        if slipchars is None:
            slipchars = obj.slipchars.select_related('character', 'glyph').order_by('position')
        return SlipCharacterSerializer(slipchars, many=True, context=self.context).data


class CharacterDetailSerializer(CharacterSummarySerializer):
    occurrence_count = serializers.IntegerField(read_only=True)

    class Meta(CharacterSummarySerializer.Meta):
        fields = CharacterSummarySerializer.Meta.fields + ['occurrence_count']


class GlyphDetailSerializer(serializers.ModelSerializer):
    character = serializers.SerializerMethodField()
    slip = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    context_before = serializers.SerializerMethodField()
    context_after = serializers.SerializerMethodField()

    class Meta:
        model = Glyph
        fields = [
            'id',
            'character',
            'slip',
            'image',
            'position',
            'source',
            'notes',
            'context_before',
            'context_after',
        ]

    def _occurrence(self, obj):
        cached = getattr(obj, '_first_occurrence', None)
        if cached is None:
            cached = (
                obj.slipchar_set.select_related('character', 'slip', 'slip__chapter')
                .order_by('pk')
                .first()
            )
            obj._first_occurrence = cached
        return cached

    def get_character(self, obj):
        occurrence = self._occurrence(obj)
        if not occurrence:
            return None
        return CharacterSummarySerializer(occurrence.character, context=self.context).data

    def get_slip(self, obj):
        occurrence = self._occurrence(obj)
        if not occurrence:
            return None
        return SlipSummarySerializer(occurrence.slip, context=self.context).data

    def get_position(self, obj):
        occurrence = self._occurrence(obj)
        return occurrence.position if occurrence else None

    def get_context_before(self, obj):
        return self._surrounding_characters(obj)[0]

    def get_context_after(self, obj):
        return self._surrounding_characters(obj)[1]

    def _surrounding_characters(self, obj):
        occurrence = self._occurrence(obj)
        if not occurrence:
            return '', ''
        characters = list(
            occurrence.slip.slipchars.select_related('character').order_by('position')
        )
        index = next((i for i, item in enumerate(characters) if item.pk == occurrence.pk), -1)
        if index < 0:
            return '', ''
        before = ''.join(item.character.reading for item in characters[max(0, index - 10):index])
        after = ''.join(item.character.reading for item in characters[index + 1:index + 11])
        return before, after