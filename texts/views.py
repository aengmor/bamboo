from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import SlipText, Chapter

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
    # 获取该简的所有评论，按创建时间排序（最新的在前）
    comments = slip.comments.all().order_by('-created_at')
    return render(request, 'texts/slip_detail.html', {
        'slip': slip,
        'comments': comments,
    })

