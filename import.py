import argparse
import os
from unittest import skip

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django

django.setup()

from texts.models import Chapter, SlipText, SlipChar, Character

SKIP_CHARS = set('，。？！、；：《》 …“‘”’（）【】『』〔〕〈〉﹁﹂﹃﹄︵︶︹︺︿﹀︽︾﹁﹂︿﹀︽︾')  
# 需要跳过的标点符号

def parse_import_file(path):
    """读取最简单的导入格式"""
    with open(path, 'r', encoding='utf-8') as fh:
        lines = [line.strip() for line in fh if line.strip()]

    chapter_title = None
    records = []

    for line in lines:
        if line.lower().startswith('###'):
            chapter_title = line.split(' ', 1)[1].strip()
            continue
        if line.startswith('//'):
            continue

        if '|' in line:
            slip_id, content = line.split('|', 1)
        elif '.' in line:
            slip_id, content = line.split('.', 1)
        elif ':' in line:
            slip_id, content = line.split(':', 1)
        elif '：' in line:
            slip_id, content = line.split('：', 1)
        else:
            raise ValueError(f'这一行格式不对：{line}。请写成“简号|内容”或“简号:内容”')

        if slip_id[0].isdigit():
            slip_id = chapter_title + slip_id
        
        records.append((chapter_title.strip(), slip_id.strip(), content.strip()))

    if not chapter_title:
        raise ValueError('文件里必须先写一行：chapter: 篇名')
    if not records:
        raise ValueError('文件里没有找到任何简号和内容')

    return records


def import_records(records):
    created_slips = 0
    created_chars = 0
    order = 1

    for chapter_title, slip_id, content in records:
        chapter, _ = Chapter.objects.get_or_create(title=chapter_title)

        slip, created = SlipText.objects.get_or_create(
            slip_id=slip_id,
            defaults={'chapter': chapter, 'content': content, 'order': order}
        )
        if not created:
            slip.chapter = chapter
            slip.content = content
            slip.save()

        if SlipChar.objects.filter(slip=slip).exists():
            print(f'⏭️ 跳过：{slip_id}（已有字数据）')
            continue

        order = order + 1
        SlipChar.objects.filter(slip=slip).delete()

        position = 1
        for char in content:
            if char in SKIP_CHARS or char == ' ':
                continue
            char_obj, _ = Character.objects.get_or_create(glyph=char)
            SlipChar.objects.create(slip=slip, character=char_obj, position=position)
            position += 1
            created_chars += 1

        created_slips += 1
        print(f'✅ 已导入：{slip_id}，共 {position - 1} 个字')

    print(f'导入完成：篇目「{chapter_title}」共新增 {created_slips} 简，{created_chars} 个字')


def main():
    parser = argparse.ArgumentParser(description='把简单文本文件导入到竹简数据库')
    parser.add_argument('--file', default='document.md', help='导入文件路径，默认读取 document.md')
    args = parser.parse_args()

    file_path = args.file
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'找不到文件：{file_path}')

    records = parse_import_file(file_path)

    import_records(records)


if __name__ == '__main__':
    main()
