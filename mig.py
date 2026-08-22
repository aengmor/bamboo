import os
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django
django.setup()

from texts.models import SlipText, SlipChar, Character

# 遍历所有竹简
for slip in SlipText.objects.all():
    text = slip.content  # 原始释文（如“道可道也”）
    for pos, char in enumerate(text, start=1):
        # 如果是标点符号或空格，跳过（但也可以保留，视需求而定）
        if char.strip() in ['，', '。', '？', '！', '、', '；', '：', '《', '》', '“'， '”']:
            continue
        
        # 获取或创建字
        char_obj, created = Character.objects.get_or_create(glyph=char)
        
        # 创建关联
        SlipChar.objects.create(
            slip=slip,
            character=char_obj,
            position=pos
        )
    
    print(f"已处理：{slip.slip_id}，共 {len(text)} 个字符")

print("迁移完成！")