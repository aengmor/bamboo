"""全量提取子居「清华简某篇解析」中的【宽式释文】，按篇保存为纯文本。

不做简号切分：每篇一个 txt，章节顺序拼接，保留 〖补字〗。
"""
import collections
import os
import re

import pymupdf

SRC = r"D:\program\web\bamboo\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\qinghua_full"
TITLE_RE = re.compile(r"清华简([一二三四五六七八九十]+)[《〈]([^》〉]+)[》〉](?:第([一二三四五六七八九十]+)章)?解析")
PART_RE = re.compile(r"[（(]([一二三四五六七八九十]+)[）)]\s*$")
HEAD_RE = re.compile(r"【[^】]*宽式释文】|【[^】]*宽式释文|(?<!【)第[一二三四五六七八九十]+章宽式释文")


def cn2int(s):
    t = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
         "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (t.get(a, 1) if a else 1) * 10 + (t.get(b, 0) if b else 0)
    return t.get(s, 0)


def wide_of(path):
    doc = pymupdf.open(path)
    text = "".join(p.get_text() for p in doc).replace("\n", "")
    heads = [(m.start(), m.end(), m.group(1)) for m in
             re.finditer(r"【([^】]{0,12}(?:宽式释文|释文解析|釋文|释文)[^】]{0,3})】", text)]
    parts = []
    for k, (hs, he, name) in enumerate(heads):
        if "宽式释文" not in name:
            continue
        stop = len(text)
        for hs2, he2, name2 in heads[k + 1:]:
            if hs2 > he:
                stop = hs2
                break
        parts.append(text[he:stop])
    return "".join(re.sub(r"\s+", "", p) for p in parts)


def main():
    os.makedirs(OUT, exist_ok=True)
    groups = collections.defaultdict(list)
    for name in os.listdir(SRC):
        if not name.lower().endswith(".pdf"):
            continue
        m = TITLE_RE.search(name)
        if not m:
            continue
        juan, pian = m.group(1), m.group(2).strip()
        if m.group(3):
            part = cn2int(m.group(3))
        else:
            pm = PART_RE.search(os.path.splitext(name)[0])
            part = cn2int(pm.group(1)) if pm else 0
        groups[(juan, pian)].append((part, os.path.join(SRC, name)))

    rows = []
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (cn2int(kv[0][0]), kv[0][1])):
        files.sort()
        text = "".join(wide_of(p) for _, p in files)
        safe = re.sub(r"[\\/:*?\"<>|]", "_", f"{juan}_{pian}")
        open(os.path.join(OUT, safe + ".txt"), "w", encoding="utf-8", newline="").write(text + "\n")
        rows.append((juan, pian, len(files), len(text)))
    lines = ["# 清华简宽式释文提取报告", "", "| 辑 | 篇 | 文件数 | 字数 |", "|---|---|---|---|"]
    for juan, pian, n, ln in rows:
        lines.append(f"| {juan} | {pian} | {n} | {ln} |")
    open(os.path.join(OUT, "_report.md"), "w", encoding="utf-8", newline="").write("\r\n".join(lines) + "\r\n")
    print("texts:", len(rows), "total chars:", sum(r[3] for r in rows))
    for r in rows:
        if r[3] < 200:
            print("SHORT:", r)


if __name__ == "__main__":
    main()
