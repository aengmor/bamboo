"""批量整理子居「清华简某篇解析」PDF：抽【宽式释文】、按【N】简号切分，出草稿。

用法：python batch_qinghua.py [--limit N]
输出：drafts/qinghua/<辑>_<篇>.md，以及 drafts/qinghua/_report.md
"""
import argparse
import collections
import difflib
import os
import re

import pymupdf
import zhconv

SRC = r"D:\program\web\bamboo\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\qinghua"
PUNCT = "，。、；：？！“”‘’《》（）〔〕［］…—·「」『』〈〉 \t\n"
NUM = "〇一二三四五六七八九十"
TITLE_RE = re.compile(r"清华简([一二三四五六七八九十]+)[《〈]([^》〉]+)[》〉](?:第([一二三四五六七八九十]+)章)?解析")
PART_RE = re.compile(r"[（(]([一二三四五六七八九十]+)[）)]\s*$")


def cn2int(s):
    table = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (table.get(a, 1) if a else 1) * 10 + (table.get(b, 0) if b else 0)
    return table.get(s, 0)


def reading(s):
    s = re.sub(r"〔[^〕]*〕", "", s)
    s = s.replace("〓", "")
    out, i = [], 0
    while i < len(s):
        if s[i] == "（":
            j = s.find("）", i)
            if j < 0:
                out.append(s[i + 1:])
                break
            out.append(s[i + 1:j].replace("，", ""))
            i = j + 1
            continue
        out.append(s[i])
        i += 1
    return "".join(out)


def sc(s):
    return zhconv.convert(s, "zh-cn")


def plain(s):
    return "".join(ch for ch in s if ch not in PUNCT)


def read_pdf(path):
    doc = pymupdf.open(path)
    text = "".join(p.get_text() for p in doc).replace("\n", "")
    wides, pos = [], 0
    for m in re.finditer(r"【[^】]*宽式释文】", text):
        a = m.end()
        b = text.find("【", a)
        if b < 0:
            b = len(text)
        wides.append(text[a:b])
        pos = b
    wide = "".join(re.sub(r"\s+", "", w) for w in wides)
    analysis = text[pos:] if pos else ""
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"【([%s]{1,3}[上下]?)】" % NUM, analysis)]
    return wide, analysis, marks


def cut(wide, analysis, marks):
    """Return list of (label, text) using left-context-first anchors."""
    wn = plain(sc(wide))
    wmap = [i for i, ch in enumerate(wide) if ch not in PUNCT]
    cuts, prev, notes = [], 0, []
    for pos, num in marks:
        cand = []
        left = plain(sc(reading(analysis[max(0, pos - 26):pos])))[-12:]
        if len(left) >= 4:
            sub = wn[prev:]
            blk = difflib.SequenceMatcher(None, left, sub, autojunk=False).find_longest_match(0, len(left), 0, len(sub))
            if blk.size >= 5:
                cand.append(prev + blk.b + blk.size)
        tail = analysis[pos + len(num) + 2: pos + len(num) + 2 + 26]
        for stop in ("整理者注", "《", "第", "页"):
            k = tail.find(stop)
            if k > 0:
                tail = tail[:k]
        right = plain(sc(reading(tail)))[:10]
        if len(right) >= 4:
            sub = wn[prev:]
            blk = difflib.SequenceMatcher(None, right, sub, autojunk=False).find_longest_match(0, len(right), 0, len(sub))
            if blk.size >= 5:
                cand.append(prev + blk.b)
        cut_at = None
        for c in cand:
            if c > prev:
                cut_at = c
                break
        if cut_at is None:
            notes.append(f"{num}: 边界未定位")
            continue
        prev = cut_at
        cuts.append((num, cut_at))
    bounds, labels = [0], []
    for num, c in cuts:
        if c > bounds[-1]:
            bounds.append(c)
            labels.append(num)
    bounds.append(len(wide))
    slips = [(labels[i], wide[bounds[i]:bounds[i + 1]].strip("。，、；： ")) for i in range(len(labels))]
    return slips, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

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

    os.makedirs(OUT, exist_ok=True)
    report = ["# 清华简批量整理报告", "", f"共 {len(groups)} 篇", ""]
    report.append("| 篇 | 辑 | 文件数 | 宽式字 | 简数 | 最短/最长 | 提示 |")
    report.append("|---|---|---|---|---|---|---|")
    done = 0
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (cn2int(kv[0][0]), kv[0][1])):
        files.sort()
        wide, analysis = "", ""
        for _, p in files:
            w, a, _ = read_pdf(p)
            wide += w
            analysis += a
        _, _, marks = read_pdf(files[0][1])
        full_marks = []
        pos = 0
        for _, p in files:
            w, a, ms = read_pdf(p)
            full_marks += [(m[0] + pos, m[1]) for m in ms]
            pos += len(a)
        slips, notes = cut(wide, analysis, full_marks) if wide else ([], ["无宽式释文"])
        lens = [len(s[1]) for s in slips]
        tip = "；".join(notes[:3])
        if lens:
            short = [s[0] for s in slips if len(s[1]) < 30]
            long_ = [s[0] for s in slips if len(s[1]) > 95]
            if short:
                tip += f"；偏短:{','.join(short)}"
            if long_:
                tip += f"；偏长:{','.join(long_)}"
        report.append(f"| {pian} | {juan} | {len(files)} | {len(wide)} | {len(slips)} | "
                      f"{(min(lens) if lens else 0)}/{max(lens) if lens else 0} | {tip} |")
        if slips:
            lines = ["## 清华简", f"### {pian}"]
            for k, (lab, body) in enumerate(slips, 1):
                lines.append(f"{k}:{body}")
            safe = re.sub(r"[\\/:*?\"<>|]", "_", f"{juan}_{pian}")
            open(os.path.join(OUT, safe + ".md"), "w", encoding="utf-8", newline="").write(
                "\r\n".join(lines) + "\r\n")
        done += 1
        if args.limit and done >= args.limit:
            break
    open(os.path.join(OUT, "_report.md"), "w", encoding="utf-8", newline="").write(
        "\r\n".join(report) + "\r\n")
    print(f"done {done} texts")


if __name__ == "__main__":
    main()


