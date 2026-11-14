"""从 oldchinese.xlsx《古汉字字典表》导入/更新 Character。

用法：
    python loadexcel.py                # 默认 oldchinese.xlsx / 字典表
    python loadexcel.py --dry-run      # 只统计，不写库
    python loadexcel.py --file x.xlsx --sheet 字典表
"""
import argparse
import os
import sys
import time
import warnings
from contextlib import nullcontext

warnings.filterwarnings("ignore")

import pandas as pd  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bamboo.settings")
import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from texts.models import Character  # noqa: E402


def clean(value, limit=None):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text[:limit] if limit else text


def number(value, cast=float):
    text = clean(value)
    if not text:
        return None
    try:
        return cast(float(text))
    except ValueError:
        return None


def flagged(value):
    return clean(value) not in ("", "nan", "None", "NaN")


def main():
    ap = argparse.ArgumentParser(description="导入字典表")
    ap.add_argument("--file", default="oldchinese.xlsx")
    ap.add_argument("--sheet", default="字典表")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写库")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        sys.exit(f"找不到文件：{args.file}")

    frame = pd.read_excel(args.file, sheet_name=args.sheet)
    frame = frame.dropna(subset=["字"])
    total = len(frame)
    print(f"读取 {args.file} [{args.sheet}]：{total} 行")

    created = updated = skipped = 0
    started = time.time()
    scope = nullcontext() if args.dry_run else transaction.atomic()

    with scope:
        for index, (_, row) in enumerate(frame.iterrows(), start=1):
            reading = clean(row.get("字"), 10)
            if not reading:
                skipped += 1
                continue

            defaults = {
                "pronunciation": clean(row.get("音"), 10),
                "pronunciation_ascii": clean(row.get("拼音"), 100),
                "harmonic_domain": clean(row.get("諧聲域"), 20),
                "phonological_position": clean(row.get("推導音韻地位"), 30),
                "middle_chinese": clean(row.get("推導中古音"), 30),
                "mandarin": clean(row.get("推導普通話"), 30),
                "phonetic_head": clean(row.get("聲首"), 10),
                "seen_shijing_rhyme": flagged(row.get("見詩經韻")),
                "seen_zhanguo_rhyme": flagged(row.get("見戰國韻")),
                "freq_total": number(row.get("總出現次數"), int),
                "freq_pre_qin": number(row.get("先秦字頻（歸一化）"), float),
                "seen_western_zhou": number(row.get("見西周"), int),
                "freq_western_zhou": number(row.get("西周字頻（歸一化）"), float),
                "rare_source": clean(row.get("少見詞出處"), 100),
                "meaning": clean(row.get("釋義")),
                "notes": clean(row.get("注釋")),
            }

            if args.dry_run:
                continue

            obj, is_new = Character.objects.get_or_create(
                reading=reading,
                pronunciation=defaults["pronunciation"],
                defaults={**defaults, "reading": reading},
            )
            if is_new:
                created += 1
            else:
                changed = False
                for key, value in defaults.items():
                    if key == "reading" or value in ("", None):
                        continue
                    if getattr(obj, key) != value:
                        setattr(obj, key, value)
                        changed = True
                if changed:
                    obj.save(update_fields=list(defaults) + ["reading"])
                    updated += 1

            if index % 500 == 0:
                print(f"  {index}/{total}…", flush=True)

    print(
        f"完成：新增 {created}，更新 {updated}，跳过 {skipped}，"
        f"用时 {time.time() - started:.1f}s"
    )
    if args.dry_run:
        print("（dry-run，未写库）")


if __name__ == "__main__":
    main()
