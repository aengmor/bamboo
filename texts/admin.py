from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from .models import SlipText, Chapter, Annotation

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

# @admin.register(Comment)
# class CommentAdmin(admin.ModelAdmin):
#     list_display = ('slip', 'commenter', 'comment_type', 'reliability', 'created_at')
#     list_filter = ('comment_type', 'reliability', 'is_anonymous')
#     search_fields = ('commenter', 'content')
#     ordering = ('-created_at',)
#     readonly_fields = ('created_at', 'updated_at')

# from .models import Chapter, SlipText, Annotation

# # 已有的 SlipTextAdmin 和 ChapterAdmin 保持不变

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