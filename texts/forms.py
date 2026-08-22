from django import forms
from .models import Annotation, Chapter, ChapterComment, Collection, CollectionComment, GlyphAnnotation

class AnnotationForm(forms.ModelForm):
    class Meta:
        model = Annotation
        fields = ['annotation_type', 'author', 'title', 'content', 'evidence']
        labels = {
            'annotation_type': '集释类型',
            'author': '您的姓名',
            'title': '标题（可选）',
            'content': '集释内容',
            'evidence': '证据引用（可选）',
        }
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': '请在此输入您的集释见解...'}),
            'evidence': forms.Textarea(attrs={'rows': 3, 'placeholder': '引用音韵、古文字、辞例等证据...'}),
            'author': forms.TextInput(attrs={'placeholder': '姓名或笔名'}),
            'title': forms.TextInput(attrs={'placeholder': '给您的意见起个标题（可选）'}),
        }

class GlyphAnnotationForm(forms.ModelForm):
    class Meta:
        model = GlyphAnnotation
        fields = ['annotation_type', 'author', 'title', 'reading', 'content', 'evidence']
        labels = {
            'annotation_type': '集释类型',
            'author': '您的姓名',
            'title': '标题（可选）',
            'reading': '释读为何字',
            'content': '内容',
            'evidence': '证据引用（可选）',
        }
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': '请在此输入您的见解...'}),
            'evidence': forms.Textarea(attrs={'rows': 3, 'placeholder': '引用音韵、古文字、辞例等证据...'}),
            'author': forms.TextInput(attrs={'placeholder': '姓名或笔名'}),
            'title': forms.TextInput(attrs={'placeholder': '标题（可选）'}),
            'reading': forms.TextInput(attrs={'placeholder': '例如：读为"道"'}),
        }

class ChapterCommentForm(forms.ModelForm):
    class Meta:
        model = ChapterComment
        fields = ['author', 'content']
        widgets = {
            'author': forms.TextInput(attrs={'placeholder': '您的姓名或笔名', 'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': '请在此输入您的篇章评述...', 'class': 'form-control'}),
        }
        labels = {
            'author': '评论人',
            'content': '评论内容',
        }

class CollectionCommentForm(forms.ModelForm):
    class Meta:
        model = CollectionComment
        fields = ['author', 'content']
        widgets = {
            'author': forms.TextInput(attrs={'placeholder': '您的姓名或笔名'}),
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': '请在此输入您的评论...'}),
        }
        labels = {
            'author': '评论人',
            'content': '评论内容',
        }

class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='关键词',
        widget=forms.TextInput(attrs={'placeholder': '输入关键词...', 'class': 'form-control'})
    )
    chapter = forms.ModelChoiceField(
        queryset=Chapter.objects.all(),
        required=False,
        label='篇目',
        empty_label='全部篇目'
    )
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all(),
        required=False,
        label='批次',
        empty_label='全部批次'
    )
    search_in = forms.ChoiceField(
        choices=[
            ('content', '释文内容'),
            ('slip_id', '竹简编号'),
            ('character', '具体字符'),
            ('all', '全部'),
        ],
        required=False,
        initial='all',
        label='搜索范围'
    )