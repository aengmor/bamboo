from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import SlipText, Chapter, Character, SlipChar, Annotation
from .forms import AnnotationForm

def home(request):
    """首页"""
    # 统计信息
    total_chapters = Chapter.objects.count()
    total_slips = SlipText.objects.count()
    total_chars = Character.objects.count()
    total_annotations = Annotation.objects.filter(is_approved=True).count()
    
    # 最近更新的竹简（取最近添加的5条）
    recent_slips = SlipText.objects.order_by('-id')[:5]
    
    # 随机展示一条集释（如果有的话）
    random_annotation = Annotation.objects.filter(is_approved=True).order_by('?').first()
    
    context = {
        'total_chapters': total_chapters,
        'total_slips': total_slips,
        'total_chars': total_chars,
        'total_annotations': total_annotations,
        'recent_slips': recent_slips,
        'random_annotation': random_annotation,
    }
    return render(request, 'texts/home.html', context)

def slip_list(request):
    query = request.GET.get('q', '').strip()
    chapters = Chapter.objects.all().order_by('title')
    chapter_id = request.GET.get('chapter', '').strip()

    selected_chapter = None
    if chapter_id and chapter_id.isdigit():
        selected_chapter = Chapter.objects.filter(id=int(chapter_id)).first()

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
        'selected_chapter': selected_chapter,  
        'query_count': queryset.count(),
    }

    return render(request, 'texts/slip_list.html', context)

def slip_detail(request, pk):
    slip = get_object_or_404(SlipText.objects.select_related('chapter'), pk=pk)

    # 获取该简上的所有字，按位置排序
    chars = slip.slipchars.all().select_related('character').order_by('position')

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
        'chars': chars,
        'form': form,
        'annotations': annotations,
    }
    return render(request, 'texts/slip_detail.html', context)

def character_detail(request, pk):
    char = get_object_or_404(Character, pk=pk)
    
    # 获取该字出现的所有位置（按篇目排序）
    occurrences = SlipChar.objects.filter(character=char).select_related('slip__chapter').order_by('slip__chapter__title', 'slip__slip_id', 'position')
    
    # 按篇目分组
    chapter_dict = {}
    total_count = 0
    for sc in occurrences:
        total_count += 1
        chapter_title = sc.slip.chapter.title if sc.slip.chapter else "未分类"
        if chapter_title not in chapter_dict:
            chapter_dict[chapter_title] = []
        
        # 获取上下文片段（前后各3个字）
        # 获取该简的所有字，按位置排序
        chars_in_slip = SlipChar.objects.filter(slip=sc.slip).select_related('character').order_by('position')
        char_list = list(chars_in_slip)
        # 找到当前字在列表中的索引
        idx = -1
        for i, c in enumerate(char_list):
            if c.pk == sc.pk:
                idx = i
                break
        context_before = ''
        context_after = ''
        if idx != -1:
            # 取前3个字（如果存在）
            before = char_list[max(0, idx-10):idx]
            context_before = ''.join([c.character.glyph for c in before])
            # 取后3个字（如果存在）
            after = char_list[idx+1:min(len(char_list), idx+11)]
            context_after = ''.join([c.character.glyph for c in after])
        # 组装上下文片段：前3个字 + [该字] + 后3个字
        context_str = f"{context_before}【{char.glyph}】{context_after}"
        
        # 将上下文片段和位置信息存入该 occurrence 对象（临时属性）
        sc.context = context_str
        sc.before = context_before
        sc.after = context_after
        
        chapter_dict[chapter_title].append(sc)
    
    # 统计出现次数（按篇目分）
    chapter_stats = {}
    for ch_title, sc_list in chapter_dict.items():
        chapter_stats[ch_title] = len(sc_list)
    
    context = {
        'char': char,
        'occurrences': occurrences,
        'chapter_dict': chapter_dict,
        'total_count': total_count,
        'chapter_stats': chapter_stats,
    }
    return render(request, 'texts/character_detail.html', context)

def chapter_list(request):
    chapters = Chapter.objects.all().order_by('title')
    return render(request, 'texts/chapter_list.html', {'chapters': chapters})