import os
import pandas as pd
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django
django.setup()

from texts.models import Character

# 1. 读取 Excel 文件
file_path = 'oldchinese.xlsx'  # 放在项目根目录
df = pd.read_excel(file_path, sheet_name="字典表")

# 2. 去除空行
df = df.dropna(subset=['字'])

# 3. 统计
total = len(df)
created = 0
updated = 0

for idx, row in df.iterrows():
    glyph = str(row['字']).strip()
    if not glyph:
        continue
    
    # 准备数据
    data = {
        'glyph': glyph,
        'pronunciation': str(row['音']) if pd.notna(row['音']) else '',
        'meaning': str(row['釋義']) if pd.notna(row['釋義']) else '',
        'notes': str(row['注釋']) if pd.notna(row['注釋']) else '',
    }
    
    # 如果字段不存在，用 get_or_create
    obj, created_flag = Character.objects.get_or_create(
        glyph=glyph,
        defaults=data
    )
    if created_flag:
        created += 1
    else:
        # 如果已存在，更新字段
        for key, value in data.items():
            if value and key != 'glyph':
                setattr(obj, key, value)
        obj.save()
        updated += 1

print(f"导入完成：新增 {created} 条，更新 {updated} 条")