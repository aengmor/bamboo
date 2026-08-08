import os
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django
django.setup()

from texts.models import Chapter, SlipText, SlipChar, Character

# 读取 Markdown 文件
with open('caomo.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 按简号分隔（你已有的逻辑）
pattern = r'[₀₁₂₃₄₅₆₇₈₉]+[ᴀʙᴄ]?'
parts = re.split(r'(' + pattern + r')', content)

# 获取或创建篇目（如“曹沫之阵”）
chapter, _ = Chapter.objects.get_or_create(title="曹沫之阵")

sub_map = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')

i = 0
while i < len(parts):
    if re.match(pattern, parts[i]):
        raw_id = parts[i]
        num_part = raw_id.translate(sub_map)
        slip_id = f"曹沫之阵·简{num_part}"
        i += 1
        if i < len(parts):
            content_text = parts[i].strip()
            if content_text:
                # 1. 创建或获取竹简记录
                slip, _ = SlipText.objects.get_or_create(
                    slip_id=slip_id,
                    defaults={'chapter': chapter}
                )
                # 如果该简已有内容，先清空再重建（或跳过）
                # 这里我们假设只执行一次，如果想重新导入可以清空
                # 简单起见，如果已有记录则跳过
                if SlipChar.objects.filter(slip=slip).exists():
                    print(f"⏭️ 跳过：{slip_id}（已有数据）")
                else:
                    # 2. 逐字拆解
                    for pos, char in enumerate(content_text, start=1):
                        # 跳过标点符号（可配置）
                        if char in '，。？！、；：《》':
                            continue
                        # 3. 创建或获取字
                        char_obj, _ = Character.objects.get_or_create(glyph=char)
                        # 4. 创建关联
                        SlipChar.objects.create(
                            slip=slip,
                            character=char_obj,
                            position=pos
                        )
                    print(f"✅ 已导入：{slip_id}，共 {SlipChar.objects.filter(slip=slip).count()} 个字")
    i += 1

print("导入完成！")