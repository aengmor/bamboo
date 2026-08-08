import argparse
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bamboo.settings')
import django

django.setup()

from texts.models import Chapter, SlipText, SlipChar, Character

SKIP_CHARS = set('，。？！、；：《》 …“‘”’（）【】『』〔〕〈〉﹁﹂﹃﹄︵︶︹︺︿﹀︽︾﹁﹂︿﹀︽︾')  
# 需要跳过的标点符号

def parse_import_file(path):
    """读取最简单的导入格式。

    示例：
    chapter: 曹沫之阵
    简1 | 甲乙丙丁
    简2 | 戊己庚辛
    """
    with open(path, 'r', encoding='utf-8') as fh:
        lines = [line.strip() for line in fh if line.strip()]

    chapter_title = None
    records = []

    for line in lines:
        if line.startswith('#') or line.startswith('//'):
            continue
        if line.lower().startswith('chapter:'):
            chapter_title = line.split(':', 1)[1].strip()
            continue

        if '|' in line:
            slip_id, content = line.split('|', 1)
        elif ':' in line:
            slip_id, content = line.split(':', 1)
        else:
            raise ValueError(f'这一行格式不对：{line}。请写成“简号|内容”或“简号:内容”')

        records.append((slip_id.strip(), content.strip()))

    if not chapter_title:
        raise ValueError('文件里必须先写一行：chapter: 篇名')
    if not records:
        raise ValueError('文件里没有找到任何简号和内容')

    return chapter_title, records


def import_records(chapter_title, records, reset=False):
    chapter, _ = Chapter.objects.get_or_create(title=chapter_title)

    if reset:
        SlipText.objects.filter(chapter=chapter).delete()
        print(f'🔄 已清空篇目「{chapter_title}」下的旧数据')

    created_slips = 0
    created_chars = 0

    for slip_id, content in records:
        slip, created = SlipText.objects.get_or_create(
            slip_id=slip_id,
            defaults={'chapter': chapter, 'content': content}
        )
        if not created:
            slip.chapter = chapter
            slip.content = content
            slip.save()

        if SlipChar.objects.filter(slip=slip).exists() and not reset:
            print(f'⏭️ 跳过：{slip_id}（已有字数据）')
            continue

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
    parser.add_argument('--file', default='caomo.md', help='导入文件路径，默认读取 caomo.md')
    parser.add_argument('--chapter', help='手动指定篇名；不填则从文件里读取 chapter: 行')
    parser.add_argument('--reset', action='store_true', help='重置当前篇目下的旧数据后再导入')
    args = parser.parse_args()

    file_path = args.file
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'找不到文件：{file_path}')

    chapter_title, records = parse_import_file(file_path)
    if args.chapter:
        chapter_title = args.chapter

    import_records(chapter_title, records, reset=args.reset)


if __name__ == '__main__':
    main()
