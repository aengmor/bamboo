"""从子居清华简各篇解析 PDF 中提取「宽式释文」文本（按行识别小节标题）。"""
import collections
import os
import re

import pymupdf

SRC = r"D:\program\web\bamboo\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\qinghua_full"
NUM = "〇一二三四五六七八九十"
TITLE_RE = re.compile(
    r"清华简(?:(?P<juan>[%s]+))?[《〈](?P<pian>[^》〉]+)[》〉](?P<rest>[^/]*)解析" % NUM)
HEAD_LINE_RE = re.compile(
    r"^【?第?[0-9%s]*章?(?:宽式释文|释文解析|釋文解析|釋文|释文|注释|集释|註釋)[0-9]*】?$" % NUM)
SEG_ORDER = {"首段": 1, "中段": 2, "末段": 3, "上篇": 1, "中篇": 2, "下篇": 3,
             "上": 1, "中": 2, "下": 3}


def cn2int(s):
    t = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
         "六": 6, "七": 7, "八": 8, "九": 9}
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (t.get(a, 1) if a else 1) * 10 + (t.get(b, 0) if b else 0)
    return t.get(s, 0)


def wide_of(path):
    doc = pymupdf.open(path)
    whole = "".join(p.get_text() for p in doc)
    text = re.sub(r"\s+", "", whole)
    starts = [m.start() for m in re.finditer("宽式释文", text)]
    if not starts:
        return ""
    out = []
    for st in starts:
        a = st + len("宽式释文")
        if a < len(text) and text[a] == "】":
            a += 1
        stops = []
        for tok in ("释文解析", "寬式釋文", "宽式释文"):
            x = text.find(tok, a)
            if x > a:
                stops.append(x)
        b = min(stops) if stops else len(text)
        out.append(text[a:b])
    return "".join(out)


def part_key(rest):
    rest = re.sub(r"（.*?）", "", rest).strip()
    if not rest:
        return (0, 0)
    if rest in SEG_ORDER:
        return (0, SEG_ORDER[rest])
    m = re.match(r"^([0-9%s]+)(?:[～~\-—、]([0-9%s]+))?章?$" % (NUM, NUM), rest)
    if m:
        return (1, cn2int(m.group(1)))
    return (2, 0)


def main():
    os.makedirs(OUT, exist_ok=True)
    groups = collections.defaultdict(list)
    skipped = []
    for name in os.listdir(SRC):
        if not name.lower().endswith(".pdf"):
            continue
        m = TITLE_RE.search(name)
        if not m:
            skipped.append(name)
            continue
        juan = m.group("juan") or ""
        pian = m.group("pian").strip()
        groups[(juan, pian)].append((part_key(m.group("rest").strip()), os.path.join(SRC, name)))
    rows = []
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        files.sort()
        text = "".join(wide_of(p) for _, p in files)
        safe = re.sub(r"[\\/:*?\"<>|]", "_", f"{juan or '无辑'}_{pian}")
        open(os.path.join(OUT, safe + ".txt"), "w", encoding="utf-8", newline="").write(text + "\n")
        rows.append((juan, pian, len(files), len(text)))
    lines = ["# 清华简宽式释文提取报告", "", "| 辑 | 篇 | 文件数 | 字数 |", "|---|---|---|---|"]
    for juan, pian, n, ln in rows:
        lines.append(f"| {juan or '—'} | {pian} | {n} | {ln} |")
    lines += ["", "## 未匹配文件", ""] + [f"- {s}" for s in sorted(skipped)]
    open(os.path.join(OUT, "_report.md"), "w", encoding="utf-8", newline="").write("\r\n".join(lines) + "\r\n")
    print("texts:", len(rows), "chars:", sum(r[3] for r in rows), "skipped:", len(skipped))
    for r in rows:
        if r[3] < 150:
            print("SHORT:", r)


if __name__ == "__main__":
    main()
