from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from .models import SlipText, Chapter, Comment

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

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('slip', 'commenter', 'comment_type', 'reliability', 'created_at')
    list_filter = ('comment_type', 'reliability', 'is_anonymous')
    search_fields = ('commenter', 'content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')