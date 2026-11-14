"""修复历史数据：把指向"空读音字头"的字位，改挂到字典表中有读音的同名字头。

原因：早期 import.py 用 get_or_create(reading=char, pronunciation='') 建字头，
与字典表中已有读音的字头并存，导致释文页取不到注音。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bamboo.settings")
import django  # noqa: E402

django.setup()

from texts.models import Character, SlipChar  # noqa: E402


def main():
    rich = {}
    for char in Character.objects.exclude(pronunciation="").order_by("-freq_total", "id"):
        rich.setdefault(char.reading, char)

    empties = list(Character.objects.filter(pronunciation=""))
    moved = deleted = 0
    for empty in empties:
        target = rich.get(empty.reading)
        if target is None:
            continue
        moved += SlipChar.objects.filter(character=empty).update(character=target)
        if not SlipChar.objects.filter(character=empty).exists():
            empty.delete()
            deleted += 1

    total = SlipChar.objects.count()
    with_pron = SlipChar.objects.exclude(character__pronunciation="").count()
    print(f"重挂字位 {moved} 条，删除空字头 {deleted} 个")
    print(f"字位总数 {total}，其中有注音 {with_pron}")


if __name__ == "__main__":
    main()
