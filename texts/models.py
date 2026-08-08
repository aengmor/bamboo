from django.db import models

class Chapter(models.Model):
    """篇目模型（如《曹沫之阵》、《民之父母》）"""
    title = models.CharField(max_length=100, unique=True, verbose_name="篇名")
    description = models.TextField(blank=True, verbose_name="篇目说明")
    slip_order = models.JSONField(
        default=list,
        blank=True,
        verbose_name="简序",
        help_text="按顺序存储该篇所有简，如 ['41', '1', '37A', '2']"
    )

    # def get_ordered_slips(self):
    #     """按 slip_order 返回该篇下的所有 SlipText 对象"""
    #     if not self.slip_order:
    #         return self.sliptext_set.all()  # fallback：无顺序时按默认
    #     # 构建一个字典以便快速查找：slip_number → SlipText 对象
    #     slip_dict = {obj.slip_number: obj for obj in self.sliptext_set.all()}
    #     ordered = []
    #     for num in self.slip_order:
    #         if num in slip_dict:
    #             ordered.append(slip_dict[num])
    #     # 补充：slip_order 里没有但实际存在的（防止数据不一致）
    #     for obj in self.sliptext_set.all():
    #         if obj.slip_number not in self.slip_order:
    #             ordered.append(obj)
    #     return ordered

    def __str__(self):
        return self.title


class SlipText(models.Model):
    """竹简释文模型"""
    slip_id = models.CharField(max_length=50, verbose_name="简号")
    content = models.TextField(verbose_name="释文")
    chapter = models.ForeignKey('Chapter', on_delete=models.SET_NULL, related_name='slip_texts', null=True, verbose_name="篇目")
    order = models.PositiveIntegerField(default=0, verbose_name="简序")
    source = models.CharField(max_length=200, blank=True, verbose_name="出处")
    parallel_text = models.CharField(max_length=200, blank=True, verbose_name="对读")
    image = models.ImageField(upload_to='slips/', blank=True, null=True, verbose_name="图版")

    def __str__(self):
        return self.slip_id

    class Meta:
        ordering = ['order'] 

class Glyph(models.Model):
    """字形"""
    character = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='glyphs',
        verbose_name="所属字"
    )
    # 关联到哪支简（用于精确定位该字形出现的上下文）
    slip = models.ForeignKey(
        'SlipText',
        on_delete=models.CASCADE,
        related_name='glyphs',
        verbose_name="所在竹简"
    )
    # 字形图片
    image = models.ImageField(
        upload_to='glyphs/%Y/%m/',
        verbose_name="字形图片"
    )
    # 可选：该字在竹简上的位置（便于快速定位）
    position = models.PositiveIntegerField(
        default=0,
        verbose_name="在简上的位置"
    )
    # 图片来源说明
    source = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="图片来源"
    )
    # 备注
    notes = models.TextField(
        blank=True,
        verbose_name="备注"
    )

    class Meta:
        ordering = ['slip', 'position']
        # 确保同一字在同一简上不会重复添加同一位置
        unique_together = ['character', 'slip', 'position']
        verbose_name = "字形"
        verbose_name_plural = "字形"

    def __str__(self):
        return f"{self.character.glyph} · {self.slip.slip_id} · 位置{self.position}"

class Annotation(models.Model):
    """ 集释模型：学者对竹简释文的评论、意见、证据等 """
    # 定义集释类型（下拉选择框）
    TYPE_CHOICES = [
        ('lishi', '隶定意见'),
        ('shiyi', '释义意见'),
        ('yinyun', '音韵证据'),
        ('cixian', '古文献辞例'),
        ('bianlian', '编联意见'),
        ('zonghe', '综合意见'),
        ('qita', '其他'),
    ]
    
    # 关联到哪支简
    slip = models.ForeignKey('SlipText', on_delete=models.CASCADE, related_name='annotations', verbose_name="所属竹简")
    
    # 集释类型（学者可标记自己的意见属于哪一类）
    annotation_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="集释类型")
    
    # 标题（可选，用于概括）
    title = models.CharField(max_length=200, blank=True, verbose_name="标题")
    
    # 集释正文（核心内容）
    content = models.TextField(verbose_name="集释内容")
    
    # 证据引用（学者列出的文献证据）
    evidence = models.TextField(blank=True, verbose_name="证据引用", help_text="所引用的音韵、古文字、辞例等证据")
    
    # 评论人（暂时用字符串，以后可改为外键 User）
    author = models.CharField(max_length=100, verbose_name="评论人")
    
    # 是否已审核（管理员确认后，可标记为“已审核”）
    is_approved = models.BooleanField(default=False, verbose_name="已审核")
    
    # 可靠度（1-5星，可由管理员或社区投票决定）
    confidence = models.IntegerField(default=0, verbose_name="可靠度", help_text="1-5，数值越高越可靠")
    
    # 发布时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")
    
    # 点赞数（预留字段，未来实现）
    likes = models.IntegerField(default=0, verbose_name="点赞数")
    
    class Meta:
        ordering = ['-created_at']  # 最新评论在前
        verbose_name = "集释"
        verbose_name_plural = "集释"
    
    def __str__(self):
        return f"{self.slip.slip_id} · {self.author} · {self.get_annotation_type_display()}"
    
    def content_preview(self):
        """后台列表预览用"""
        return self.content[:30] + '...' if len(self.content) > 30 else self.content
    content_preview.short_description = '集释预览'

class Character(models.Model):
    """独立存储每个字的信息"""
    glyph = models.CharField(max_length=10, unique=True, verbose_name="释读")
    
    # 上古音信息
    initial = models.CharField(max_length=20, blank=True, verbose_name="声母")
    rhyme = models.CharField(max_length=20, blank=True, verbose_name="韵部")
    pronunciation = models.CharField(max_length=10, blank=True, verbose_name="读音")
    
    # 字形信息（图片或动态组字编码）
    glyph_image = models.ImageField(upload_to='glyphs/', blank=True, null=True, verbose_name="字形图片")
    ligature_code = models.CharField(max_length=100, blank=True, verbose_name="构字式")
    
    # 基本释义
    meaning = models.TextField(blank=True, verbose_name="释义")
    
    # 备注
    notes = models.TextField(blank=True, verbose_name="备注")
    
    def __str__(self):
        return self.glyph

    def get_phonetic(self):
        parts = [part for part in (self.initial, self.rhyme, self.pronunciation) if part]
        return ' '.join(parts) if parts else ''

class SlipChar(models.Model):
    """竹简上的字——关联竹简和字，并记录位置"""
    slip = models.ForeignKey('SlipText', on_delete=models.CASCADE, related_name='slipchars', verbose_name="竹简")
    character = models.ForeignKey(Character, on_delete=models.CASCADE, verbose_name="字")
    position = models.IntegerField(default=0, verbose_name="位置")  # 第几个字
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.slip.slip_id} · {self.position} · {self.character.glyph}"