from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from django.utils.html import format_html
from .models import Character, SlipChar, SlipText, Chapter, Annotation, Glyph

@admin.register(SlipText)
class SlipTextAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('order', 'chapter', 'slip_id', 'content_preview')
    list_filter = ('chapter',)
    sortable_by = ('order', 'slip_id')
    #ordering = ('order',)
    
    def content_preview(self, obj):
        return obj.content[:15] + '......' + obj.content[-15:] if len(obj.content) > 30 else obj.content
    content_preview.short_description = '释文预览'

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description')
    search_fields = ('title',)
    fields = ('title', 'description', 'slip_order')

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('glyph', 'initial', 'rhyme', 'pronunciation', 'ligature_code')  # 显示哪些字段
    search_fields = ('glyph',)  # 按字形搜索
    list_editable = ('initial', 'rhyme', 'pronunciation')  # 允许在列表页直接编辑音韵信息
    fieldsets = (
        ('基本信息', {
            'fields': ('glyph', 'ligature_code')
        }),
        ('上古音信息', {
            'fields': ('initial', 'rhyme', 'pronunciation')
        }),
        ('释义与备注', {
            'fields': ('meaning', 'notes')
        })
    )

@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('slip', 'author', 'annotation_type', 'confidence', 'is_approved', 'created_at')
    list_filter = ('annotation_type', 'is_approved', 'slip')
    search_fields = ('author', 'content', 'evidence')
    list_editable = ('is_approved', 'confidence')  # 可直接在列表页修改
    readonly_fields = ('created_at',)  # 发布时间不可编辑
    
    fieldsets = (
        ('基本信息', {
            'fields': ('slip', 'annotation_type', 'title', 'author')
        }),
        ('集释内容', {
            'fields': ('content', 'evidence')
        }),
        ('审核与评价', {
            'fields': ('is_approved', 'confidence', 'likes')
        }),
        ('系统信息', {
            'fields': ('created_at',)
        }),
    )

@admin.register(SlipChar)
class SlipCharAdmin(admin.ModelAdmin):
    list_display = ('slip', 'character', 'position')
    list_filter = ('slip',)
    search_fields = ('slip__slip_id', 'character__glyph')

@admin.register(Glyph)
class GlyphAdmin(admin.ModelAdmin):
    list_display = ('character', 'slip', 'position', 'image_preview')
    list_filter = ('character', 'slip')
    search_fields = ('character__glyph', 'slip__slip_id')
    list_editable = ('position',)

    class Media:
        css = {
            'all': ('texts/css/admin.css',)
        }

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img class="glyph-image-preview" src="{}" />',
                obj.image.url
            )
        return "无图片"
    image_preview.short_description = "预览"