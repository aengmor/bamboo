from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import SlipText, Chapter
from .forms import AnnotationForm

def slip_list(request):
    query = request.GET.get('q', '').strip()
    chapters = Chapter.objects.all().order_by('title')
    chapter_id = request.GET.get('chapter', '').strip()
    queryset = SlipText.objects.select_related('chapter').all()

    if query:
        queryset = queryset.filter(
            Q(content__icontains=query) | Q(slip_id__icontains=query)
        )
    
    if chapter_id and chapter_id.isdigit():
        queryset = queryset.filter(chapter_id=int(chapter_id))
    
    chapter_data = []
    chapter_ids_in_queryset = queryset.values_list('chapter_id', flat=True).distinct()
    for ch in chapters:
        if ch.id not in chapter_ids_in_queryset:
            continue
        slips_in_chapter = queryset.filter(chapter=ch)
        if slips_in_chapter.exists():
            try:
                slips_sorted = slips_in_chapter.order_by('order', 'slip_id')
            except:
                slips_sorted = slips_in_chapter.order_by('slip_id')
            chapter_data.append({
                'chapter': ch,
                'slips': slips_sorted,
            })
    
    context = {
        'chapter_data': chapter_data,
        'query': query,
        'chapters': chapters,
        'selected_chapter_id': int(chapter_id) if chapter_id.isdigit() else None,
        'query_count': queryset.count(),
    }

    return render(request, 'texts/slip_list.html', context)

def slip_detail(request, pk):
    slip = get_object_or_404(SlipText.objects.select_related('chapter'), pk=pk)
    
    if request.method == 'POST':
        form = AnnotationForm(request.POST)
        if form.is_valid():
            annotation = form.save(commit=False)
            annotation.slip = slip
            annotation.is_approved = False  # 默认待审核
            annotation.confidence = 1        # 初始可靠度
            annotation.likes = 0
            annotation.save()
            messages.success(request, '✅ 您的集释已提交，等待审核后显示。')
            return redirect('slip_detail', pk=slip.pk)
        else:
            messages.error(request, '❌ 提交失败，请检查表单内容。')
    else:
        form = AnnotationForm()
    
    # 获取该简下已审核的集释
    annotations = slip.annotations.filter(is_approved=True).order_by('-created_at')
    
    context = {
        'slip': slip,
        'form': form,
        'annotations': annotations,
    }
    return render(request, 'texts/slip_detail.html', context)

