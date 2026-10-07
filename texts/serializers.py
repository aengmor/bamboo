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
    SlipText,
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
    class Meta:
        model = Character
        fields = [
            'id',
            'glyph',
            'initial',
            'rhyme',
            'pronunciation',
            'pronunciation_ascii',
            'glyph_image',
            'ids',
            'meaning',
            'notes',
        ]


class GlyphSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Glyph
        fields = ['id', 'image', 'position', 'source', 'notes']


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
        model = SlipText
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
        glyph_map = self.context.get('glyph_map', {})
        glyph = glyph_map.get(obj.position)
        return GlyphSummarySerializer(glyph, context=self.context).data if glyph else None


class SlipDetailSerializer(SlipSummarySerializer):
    characters = serializers.SerializerMethodField()

    class Meta(SlipSummarySerializer.Meta):
        fields = SlipSummarySerializer.Meta.fields + ['characters']

    def get_characters(self, obj):
        glyph_map = {glyph.position: glyph for glyph in getattr(obj, 'api_glyphs', [])}
        context = {**self.context, 'glyph_map': glyph_map}
        return SlipCharacterSerializer(
            getattr(obj, 'api_slipchars', []), many=True, context=context
        ).data


class CharacterDetailSerializer(CharacterSummarySerializer):
    occurrence_count = serializers.IntegerField(read_only=True)

    class Meta(CharacterSummarySerializer.Meta):
        fields = CharacterSummarySerializer.Meta.fields + ['occurrence_count']


class GlyphDetailSerializer(serializers.ModelSerializer):
    character = CharacterSummarySerializer(read_only=True)
    slip = SlipSummarySerializer(read_only=True)
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

    def get_context_before(self, obj):
        context = self._surrounding_characters(obj)
        return context[0]

    def get_context_after(self, obj):
        context = self._surrounding_characters(obj)
        return context[1]

    @staticmethod
    def _surrounding_characters(obj):
        characters = getattr(obj.slip, 'api_slipchars', [])
        index = next(
            (i for i, slip_char in enumerate(characters) if slip_char.position == obj.position),
            -1,
        )
        if index < 0:
            return '', ''
        before = ''.join(item.character.glyph for item in characters[max(0, index - 10):index])
        after = ''.join(item.character.glyph for item in characters[index + 1:index + 11])
        return before, after