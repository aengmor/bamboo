"""越公其事 第4-11章：按宽式释文顺序切简（锚点失败时按比例均分）。"""
import os
import re

import difflib
import pymupdf
import zhconv

SRC = r"D:\program\web\bamboo\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\越公其事.md"
PUNCT = "，。、；：？！“”‘’《》（）〔〕［］…—·「」『』〈〉〖〗 \t\n"
NUM = "〇一二三四五六七八九十"


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


def chapter(path, ch):
    d = pymupdf.open(path)
    t = "".join(p.get_text() for p in d).replace("\n", "")
    tag = f"【第{ch}章宽式释文】"
    i = t.find(tag)
    j = t.find("【", i + len(tag))
    wide = re.sub(r"\s+", "", t[i + len(tag): j])
    seg = t[j:]
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"【([%s]{1,3}[上下]?)】" % NUM, seg)]
    return wide, seg, marks


def cut(wide, seg, marks):
    wn, wmap = [], []
    for i, c in enumerate(wide):
        if c in PUNCT:
            continue
        wn.append(c)
        wmap.append(i)
    wn = plain(sc("".join(wn)))
    bounds, prev, missed = [0], 0, 0
    for k, (pos, num) in enumerate(marks):
        left = plain(sc(reading(seg[max(0, pos - 30):pos])))[-10:]
        right = plain(sc(reading(seg[pos + len(num) + 2: pos + len(num) + 30])))[:10]
        best = None
        for probe, side in ((left, "L"), (right, "R")):
            if len(probe) < 4:
                continue
            sub = wn[prev:]
            blk = difflib.SequenceMatcher(None, probe, sub, autojunk=False).find_longest_match(
                0, len(probe), 0, len(sub))
            if blk.size >= 6:
                cand = prev + blk.b + (blk.size if side == "L" else 0)
                if cand > prev:
                    best = cand
                    break
        if best is None:
            remain_marks = len(marks) - k
            best = prev + max(1, (len(wn) - prev) // max(1, remain_marks))
            missed += 1
        bounds.append(min(best, len(wn)))
        prev = bounds[-1]
    bounds.append(len(wn))
    out = []
    for i in range(len(marks)):
        a = wmap[bounds[i]] if bounds[i] < len(wmap) else len(wide)
        b = wmap[bounds[i + 1]] if bounds[i + 1] < len(wmap) else len(wide)
        out.append(wide[a:b].strip("，。 "))
    return out, missed


def main():
    cur = open(OUT, encoding="utf-8").read().rstrip("\r\n").splitlines()
    nxt = 27
    report = []
    for ch in ["四", "五", "六", "七", "八", "九", "十"]:
        # 十 covers 第十、第十一章
        f = os.path.join(SRC, f"子居：清华简七《越公其事》第{ch}章解析.pdf")
        if not os.path.exists(f):
            print("missing", f)
            continue
        wide, seg, marks = chapter(f, ch)
        slips, missed = cut(wide, seg, marks)
        report.append(f"第{ch}章: {len(slips)} 简, 未定位 {missed}, 字数 {[len(s) for s in slips]}")
        for s in slips:
            cur.append(f"{nxt}:{s}")
            nxt += 1
    open(OUT, "w", encoding="utf-8", newline="").write("\r\n".join(cur) + "\r\n")
    print("\n".join(report))
    print("total slips:", nxt - 1)


if __name__ == "__main__":
    main()
