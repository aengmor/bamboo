# migrate_data.py
import os
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django
django.setup()

from texts.models import SlipText, Chapter

# 1. 确保篇目存在（如果不存在则创建）
chapter_name = "曹沫之阵"
chapter, created = Chapter.objects.get_or_create(title=chapter_name)

# 2. 遍历所有旧的 SlipText 记录
for old in SlipText.objects.all():
    old.chapter = chapter
   
    old.save()
    print(f"已迁移：{old.slip_id} → {chapter.title}")

print("数据迁移完成！")