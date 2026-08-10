import random

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q, Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from urllib.parse import urlencode
from .models import SlipText, Chapter, Character, SlipChar, Annotation, ChapterComment, Glyph
from .forms import AnnotationForm, ChapterCommentForm, GlyphAnnotationForm

# 这是应用的视图文件，负责把数据库中的数据读取出来，传给前端模板显示。
# 所有函数都返回一个 render(request, template, context) 用于渲染页面。

def home(request):
    """首页"""
    # 统计信息
    total_chapters = Chapter.objects.count()
    total_slips = SlipText.objects.count()
    total_chars = Character.objects.count()
    total_annotations = Annotation.objects.filter(is_approved=True).count()
    
    # 最近更新的竹简（取最近添加的5条），预取篇目避免模板中 N+1 查询
    recent_slips = SlipText.objects.select_related('chapter').order_by('-id')[:5]
    
    # 随机展示一条已审批的集释，避免使用 inefficient order_by('?')
    approved_annotations = Annotation.objects.filter(is_approved=True)
    random_annotation = None
    annotation_count = approved_annotations.count()
    if annotation_count:
        random_index = random.randrange(annotation_count)
        random_annotation = approved_annotations[random_index]
    
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
    """竹简释文列表页，支持搜索、按篇章过滤和分页。"""
    query = request.GET.get('q', '').strip()
    chapter_id = request.GET.get('chapter', '').strip()
    page = request.GET.get('page', 1)

    other_get = {k: v for k, v in request.GET.items() if k != 'page' and v != ''}
    get_params = urlencode(other_get)

    selected_chapter = None
    approved_comments_qs = None
    if chapter_id.isdigit():
        approved_comments_qs = ChapterComment.objects.filter(is_approved=True).order_by('-created_at')
        selected_chapter = Chapter.objects.filter(id=int(chapter_id)).prefetch_related(
            Prefetch('comments', queryset=approved_comments_qs, to_attr='approved_comments')
        ).first()

    if request.method == 'POST':
        form = ChapterCommentForm(request.POST)
        if form.is_valid():
            target_chapter_id = request.POST.get('chapter_id', '').strip()
            target_chapter = Chapter.objects.filter(id=int(target_chapter_id)).first() if target_chapter_id.isdigit() else None
            if target_chapter:
                comment = form.save(commit=False)
                comment.chapter = target_chapter
                comment.is_approved = False
                comment.save()
                messages.success(request, '✅ 您的评论已提交，等待审核后显示。')
                return redirect(f"{request.path}{'?' + get_params if get_params else ''}")
            messages.error(request, '❌ 未找到目标篇章，提交失败。')
        else:
            messages.error(request, '❌ 提交失败，请检查表单内容。')
    else:
        form = ChapterCommentForm()

    slips_queryset = SlipText.objects.select_related('chapter')
    if query:
        slips_queryset = slips_queryset.filter(
            Q(content__icontains=query) | Q(slip_id__icontains=query)
        )
    if selected_chapter:
        slips_queryset = slips_queryset.filter(chapter=selected_chapter)

    query_count = slips_queryset.count()
    selected_chapter_comments = getattr(selected_chapter, 'approved_comments', []) if selected_chapter else []

    paginated_slips = None
    paginator = None
    page_obj = None
    chapter_data = []

    if query or selected_chapter:
        page_qs = slips_queryset.order_by('order', 'slip_id')
        paginator = Paginator(page_qs, 20)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        paginated_slips = page_obj.object_list
        chapters = Chapter.objects.order_by('title')
    else:
        chapters_qs = Chapter.objects.order_by('title').prefetch_related(
            Prefetch('slip_texts', queryset=slips_queryset.order_by('order', 'slip_id'), to_attr='filtered_slips'),
        )
        paginator = Paginator(chapters_qs, 10)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        chapters = page_obj.object_list
        chapter_data = [
            {
                'chapter': ch,
                'slips': ch.filtered_slips,
            }
            for ch in chapters
            if getattr(ch, 'filtered_slips', [])
        ]

    context = {
        'chapter_data': chapter_data,
        'paginated_slips': paginated_slips,
        'paginator': paginator,
        'page_obj': page_obj,
        'get_params': get_params,
        'query': query,
        'chapters': Chapter.objects.order_by('title'),
        'selected_chapter_id': int(chapter_id) if chapter_id.isdigit() else None,
        'selected_chapter': selected_chapter,
        'selected_chapter_comments': selected_chapter_comments,
        'query_count': query_count,
        'form': form,
    }

    return render(request, 'texts/slip_list.html', context)

def slip_detail(request, pk):
    slip = get_object_or_404(SlipText.objects.select_related('chapter'), pk=pk)

    # 获取该简上的所有字，按位置排序；批量加载当前简的字形图片以避免 N+1 查询
    chars = slip.slipchars.select_related('character').order_by('position')
    glyphs = Glyph.objects.filter(slip=slip)
    glyph_map = {glyph.position: glyph for glyph in glyphs}
    for sc in chars:
        sc.glyph_obj = glyph_map.get(sc.position)

    form = AnnotationForm()
    chapter_comment_form = ChapterCommentForm()
    chapter_comments = []

    if request.method == 'POST':
        if request.POST.get('form_type') == 'chapter_comment':
            chapter_comment_form = ChapterCommentForm(request.POST)
            if chapter_comment_form.is_valid():
                if slip.chapter:
                    comment = chapter_comment_form.save(commit=False)
                    comment.chapter = slip.chapter
                    comment.is_approved = False
                    comment.save()
                    messages.success(request, '✅ 您的评论已提交，等待审核后显示。')
                    return redirect('slip_detail', pk=slip.pk)
                messages.error(request, '❌ 当前竹简未关联篇章，无法提交篇章评论。')
            else:
                messages.error(request, '❌ 提交失败，请检查表单内容。')
        else:
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

    if slip.chapter:
        chapter_comments = slip.chapter.comments.filter(is_approved=True).order_by('-created_at')

    # 获取该简下已审核的集释，并分页显示，避免注释过多时页面过长
    annotations_qs = slip.annotations.filter(is_approved=True).order_by('-created_at')
    annotation_page = request.GET.get('anno_page', 1)
    annotation_paginator = Paginator(annotations_qs, 8)
    try:
        annotation_obj = annotation_paginator.page(annotation_page)
    except PageNotAnInteger:
        annotation_obj = annotation_paginator.page(1)
    except EmptyPage:
        annotation_obj = annotation_paginator.page(annotation_paginator.num_pages)
    
    context = {
        'slip': slip,
        'chars': chars,
        'form': form,
        'chapter_comment_form': chapter_comment_form,
        'chapter_comments': chapter_comments,
        'annotations': annotation_obj.object_list,
        'annotation_paginator': annotation_paginator,
        'annotation_page_obj': annotation_obj,
    }
    return render(request, 'texts/slip_detail.html', context)

def character_detail(request, pk):
    char = get_object_or_404(Character, pk=pk)
    
    # 获取该字出现的所有位置（按篇目分组），并预取当前简的所有字，避免 N+1 查询
    occurrences_qs = SlipChar.objects.filter(character=char).select_related('slip__chapter').prefetch_related(
        Prefetch(
            'slip__slipchars',
            queryset=SlipChar.objects.select_related('character').order_by('position'),
            to_attr='slip_chars'
        )
    ).order_by('slip__chapter__title', 'slip__slip_id', 'position')

    # 为每个 SlipChar 预加载对应的字形图片（如果存在）
    for sc in occurrences_qs:
        # 查询该字在该简该位置的字形图片
        sc.glyph_obj = char.glyphs.filter(slip=sc.slip, position=sc.position).first()

    # 分页处理出现位置，避免单页过长
    page = request.GET.get('page', 1)
    occurrence_paginator = Paginator(occurrences_qs, 20)
    try:
        occurrence_page = occurrence_paginator.page(page)
    except PageNotAnInteger:
        occurrence_page = occurrence_paginator.page(1)
    except EmptyPage:
        occurrence_page = occurrence_paginator.page(occurrence_paginator.num_pages)

    occurrences = list(occurrence_page.object_list)
    
    chapter_dict = {}
    # total_count 直接使用 queryset.count()，避免重复计算
    total_count = occurrences_qs.count()

    # 生成一个包含全部出现位置的快速跳转列表，方便用户在分页之外直接选择任一位置
    picker_groups = []
    last_chapter = None
    for row in occurrences_qs.values('slip__chapter__title', 'slip__slip_id', 'slip__pk', 'position'):
        chapter_title = row['slip__chapter__title'] or "未分类"
        if chapter_title != last_chapter:
            picker_groups.append({'chapter_title': chapter_title, 'items': []})
            last_chapter = chapter_title
        picker_groups[-1]['items'].append(row)

    for sc in occurrences:
        chapter_title = sc.slip.chapter.title if sc.slip.chapter else "未分类"
        if chapter_title not in chapter_dict:
            chapter_dict[chapter_title] = []
        
        char_list = getattr(sc.slip, 'slip_chars', [])
        idx = next((i for i, c in enumerate(char_list) if c.pk == sc.pk), -1)

        context_before = ''
        context_after = ''
        if idx != -1:
            before = char_list[max(0, idx-10):idx]
            context_before = ''.join([c.character.glyph for c in before])
            after = char_list[idx+1:min(len(char_list), idx+11)]
            context_after = ''.join([c.character.glyph for c in after])
        
        context_str = f"{context_before}【{char.glyph}】{context_after}"
        sc.context = context_str
        sc.before = context_before
        sc.after = context_after
        
        chapter_dict[chapter_title].append(sc)
    
    chapter_stats = {ch_title: len(sc_list) for ch_title, sc_list in chapter_dict.items()}
    
    context = {
        'char': char,
        'occurrences': occurrences,
        'chapter_dict': chapter_dict,
        'picker_groups': picker_groups,
        'total_count': total_count,
        'chapter_stats': chapter_stats,
        'occurrence_paginator': occurrence_paginator,
        'occurrence_page_obj': occurrence_page,
    }
    return render(request, 'texts/character_detail.html', context)


def chapter_list(request):
    """篇章目录页，带分页"""
    page = request.GET.get('page', 1)
    chapters_qs = Chapter.objects.annotate(slips_count=Count('slip_texts')).order_by('title')
    paginator = Paginator(chapters_qs, 20)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'chapters': page_obj.object_list,
        'paginator': paginator,
        'page_obj': page_obj,
    }
    return render(request, 'texts/chapter_list.html', context)

def glyph_detail(request, pk):
    glyph = get_object_or_404(Glyph.objects.select_related('character', 'slip__chapter'), pk=pk)
    
    if request.method == 'POST':
        form = GlyphAnnotationForm(request.POST)
        if form.is_valid():
            annotation = form.save(commit=False)
            annotation.glyph = glyph
            annotation.is_approved = False  # 默认待审核
            annotation.save()
            messages.success(request, '✅ 您的讨论已提交，等待审核后显示。')
            return redirect('glyph_detail', pk=glyph.pk)
        else:
            messages.error(request, '❌ 提交失败，请检查表单内容。')
    else:
        form = GlyphAnnotationForm()
    
    annotations = glyph.annotations.filter(is_approved=True).order_by('-created_at')
    
    context = {
        'glyph': glyph,
        'annotations': annotations,
        'form': form,
    }
    return render(request, 'texts/glyph_detail.html', context)