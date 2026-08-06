import os
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django
django.setup()

from texts.models import SlipText

def parse_markdown_file(filepath):
    """读取 Markdown 文件，按段落切分，返回列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按简号标记切分成段落（忽略空段落）
    paragraphs = [p.strip() for p in re.split(r'([₀₁₂₃₄₅₆₇₈₉]+[ᴀʙᴄ]?)', content) if p.strip()]
    print(f"parse_markdown_file: 📄 读取文件：{filepath}，{paragraphs}")
   
    return paragraphs

def extract_slip_id(text):
    """从段落中提取简号，如 '₄₁' → '曹沫之阵·简41'"""
    # 匹配所有类似 ₄₁、₃₇ʙ、₅₁ʙ 的简号标记
    pattern = r'[₀₁₂₃₄₅₆₇₈₉]+[ᴀʙᴄ]?'
    matches = re.findall(pattern, text)
    print(f"🔍 匹配到简号标记：{matches}")
    if matches:
        # 取第一个匹配作为简号
        raw_id = matches[0]
        # 转换下标数字为普通数字
        sub_map = str.maketrans('₀₁₂₃₄₅₆₇₈₉ᴀʙᴄ', '0123456789ABC')
        num_part = raw_id.translate(sub_map).strip()
        print(f"extract_slip_id: ✅ 提取简号：{num_part}")
        return f"曹沫之阵{num_part}"
    return None

def clean_content(text):
    """移除段落中的简号标记，保留纯释文"""
    pattern = r'[₀₁₂₃₄₅₆₇₈₉]+[ᴀʙᴄ]?'
    cleaned = re.sub(pattern, '', text)
    # 清理多余的空白和标点
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def import_data():
    filepath = 'caomo.md'
    paragraphs = parse_markdown_file(filepath)
    print(f"import_data: 📊 开始导入数据，共 {len(paragraphs)} 个段落")
    success_count = 0
    skip_count = 0
    
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        # 跳过标题行或过短的段落（可能是注释）
        #if para.startswith('###'): #or len(para) < 10:
        #    continue
        
        print(f"\n📄 处理段落：{para}")
        slip_id = paragraphs[i+1] if i < len(paragraphs) - 1 else None  # 简号在后一段落
        slip_id = extract_slip_id(slip_id) if slip_id else None
        if not slip_id:
            # 如果没有简号，跳过或做特殊处理（这里选择跳过）
            print(f"⚠️ 跳过（无简号）：{para}")
            i += 1
            continue
            
        content = clean_content(para)
        if not content:
            i += 1
            continue
            
        obj, created = SlipText.objects.get_or_create(
            slip_id=slip_id,
            defaults={"content": content}
        )
        if created:
            print(f"✅ 已导入：{slip_id}")
            success_count += 1
        else:
            print(f"⏭️ 跳过（已存在）：{slip_id}")
            skip_count += 1
    
        i += 2  # 每次处理两段：释文 + 简号
    print(f"\n📊 导入完成：成功 {success_count} 条，跳过 {skip_count} 条")

if __name__ == "__main__":
    import_data()