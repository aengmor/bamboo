"""全量提取子居「清华简某篇解析/韵读」中的宽式释文（含无辑号、分章、分段题名）。"""
import collections
import os
import re

import pymupdf

SRC = r"D:\program\web\bamboo\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\qinghua_full"
NUM = "〇一二三四五六七八九十"

# 篇名 + 可选 辑号、可选 分章/分段
TITLE_RE = re.compile(
    r"清华简(?:(?P<juan>[%s]+))?[《〈](?P<pian>[^》〉]+)[》〉]"
    r"(?P<rest>[^/]*)解析" % NUM
)
REST_RE = None
SEG_ORDER = {"首段": 1, "中段": 2, "末段": 3, "上篇": 1, "中篇": 2, "下篇": 3,
             "上": 1, "中": 2, "下": 3}
HEAD_RE = re.compile(r"【[^】]{0,14}(?:宽式释文|释文解析|釋文解析|釋文|释文)[^】]{0,3}】")
PLAIN_HEAD_RE = re.compile(r"(?<![【》〉])第?[0-9%s]*章?宽式释文(?!】)" % NUM)


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


def headings(text):
    hs = []
    for m in HEAD_RE.finditer(text):
        hs.append((m.start(), m.end(), m.group(0)))
    for m in PLAIN_HEAD_RE.finditer(text):
        hs.append((m.start(), m.end(), m.group(0)))
    hs.sort()
    return hs


def wide_of(path):
    doc = pymupdf.open(path)
    text = "".join(p.get_text() for p in doc).replace("\n", "")
    hs = headings(text)
    parts = []
    for k, (s, e, name) in enumerate(hs):
        if "宽式释文" not in name:
            continue
        stop = hs[k + 1][0] if k + 1 < len(hs) else len(text)
        parts.append(text[e:stop])
    return "".join(re.sub(r"\s+", "", p) for p in parts)


def part_key(rest):
    rest = re.sub(r"[（(].*?[）)]", "", rest).strip()
    if not rest:
        return (0, 0, 0)
    seg = SEG_ORDER.get(rest)
    if seg:
        return (0, seg, 0)
    m = re.match(r"^(?P<a>[0-9%s]+)(?:[～~\-—、](?P<b>[0-9%s]+))?章?$" % (NUM, NUM), rest)
    if m:
        return (1, cn2int(m.group("a")), cn2int(m.group("b") or m.group("a")))
    return (2, 0, 0)


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
        rest = m.group("rest").strip()
        groups[(juan, pian)].append((part_key(rest), os.path.join(SRC, name), name))
    rows = []
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        files.sort()
        text = "".join(wide_of(p) for _, p, _ in files)
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
