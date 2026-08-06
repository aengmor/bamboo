from django import forms
from .models import Annotation

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