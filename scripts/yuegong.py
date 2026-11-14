"""重建《越公其事》草稿：按宽式释文顺序切简，兼容【第X章宽式释文】与无括号标题。"""
import os
import re

import difflib
import pymupdf
import zhconv

SRC = r"D:\program\web\bamboo_archive\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\越公其事.md"
PUNCT = "，。、；：？！“”‘’《》（）〔〕［］…—·「」『』〈〉〖〗 \t\n"
NUM = "〇一二三四五六七八九十"
FILES = [
    ("一", "子居：清华简七《越公其事》第一章解析.pdf"),
    ("二", "子居：清华简七《越公其事》第二章解析.pdf"),
    ("三", "子居：清华简七《越公其事》第三章解析.pdf"),
    ("四", "子居：清华简七《越公其事》第四章解析.pdf"),
    ("五", "子居：清华简七《越公其事》第五章解析.pdf"),
    ("六", "子居：清华简七《越公其事》第六章解析.pdf"),
    ("七", "子居：清华简七《越公其事》第七、第八章解析.pdf"),
    ("八", "子居：清华简七《越公其事》第七、第八章解析.pdf"),
    ("九", "子居：清华简七《越公其事》第九章解析.pdf"),
    ("十", "子居：清华简七《越公其事》第十、十一章解析.pdf"),
    ("十一", "子居：清华简七《越公其事》第十、十一章解析.pdf"),
]


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


def extract(path, ch):
    d = pymupdf.open(path)
    t = "".join(p.get_text() for p in d).replace("\n", "")
    tag = f"第{ch}章宽式释文"
    i = t.find(tag)
    if i < 0:
        return "", ""
    if t[i - 1] == "【":
        i -= 1
        start = i + len("【") + len(tag) + 1
    else:
        start = i + len(tag)
    nxt = t.find("【", start)
    wide = re.sub(r"\s+", "", t[start: nxt if nxt > start else len(t)])
    atag = f"第{ch}章释文解析"
    a = t.find(atag)
    if a < 0:
        return wide, ""
    b = len(t)
    for other in NUM:
        o = t.find(f"第{other}章释文解析", a + len(atag))
        if o > a:
            b = min(b, o)
            break
    return wide, t[a:b]


def cut(wide, seg):
    wn, wmap = [], []
    for i, c in enumerate(wide):
        if c in PUNCT:
            continue
        wn.append(c)
        wmap.append(i)
    wn = plain(sc("".join(wn)))
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"【([%s]{1,3}[上下]?)】" % NUM, seg)]
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
            best = prev + max(1, (len(wn) - prev) // max(1, len(marks) - k))
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
    slips = []
    report = []
    for ch, fname in FILES:
        path = os.path.join(SRC, fname)
        wide, seg = extract(path, ch)
        if not wide:
            report.append(f"第{ch}章: 宽式未找到")
            continue
        body, missed = cut(wide, seg)
        report.append(f"第{ch}章: {len(body)} 简, 未定位 {missed}, 字数 {[len(x) for x in body]}")
        slips += body
    lines = ["## 清华简", "### 越公其事"] + [f"{i}:{s}" for i, s in enumerate(slips, 1)]
    open(OUT, "w", encoding="utf-8", newline="").write("\r\n".join(lines) + "\r\n")
    print("\n".join(report))
    print("total:", len(slips), "chars:", sum(len(s) for s in slips))


if __name__ == "__main__":
    main()
