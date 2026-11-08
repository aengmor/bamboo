"""批量整理子居「清华简某篇解析」PDF：按【N】简号切分【宽式释文】。

改进点（相对旧版）：
* 宽式标题兼容「【第X章宽式释文】」；解析标题兼容「【释文解析2】」等；
* 补字标记 〖…〗 保留；
* 切点用「窗口内模糊匹配」：左文脉优先、右文脉兜底、仍失败则按平均简长推定并标记；
* 多章/多部分文件按顺序合并，简号沿用原文标记。

输出：drafts/qinghua/<辑>_<篇>.md 与 _report.md
"""
import collections
import difflib
import os
import re

import pymupdf
import zhconv

SRC = r"D:\program\web\bamboo\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\qinghua"
PUNCT = "，。、；：？！“”‘’《》（）〔〕［］…—·「」『』〈〉〖〗 \t\n"
NUM = "〇一二三四五六七八九十"
HEAD_RE = re.compile(r"【([^】]{2,16})】")
MARK_RE = re.compile(r"【([%s]{1,3}[上下]?)】" % NUM)
TITLE_RE = re.compile(r"清华简([一二三四五六七八九十]+)[《〈]([^》〉]+)[》〉](?:第([一二三四五六七八九十]+)章)?解析")
PART_RE = re.compile(r"[（(]([一二三四五六七八九十]+)[）)]\s*$")


def cn2int(s):
    t = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
         "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (t.get(a, 1) if a else 1) * 10 + (t.get(b, 0) if b else 0)
    return t.get(s, 0)


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


def units_of(path):
    """Return [(wide, analysis)] in document order."""
    doc = pymupdf.open(path)
    text = "".join(p.get_text() for p in doc).replace("\n", "")
    heads = [(m.start(), m.end(), m.group(1)) for m in HEAD_RE.finditer(text)]
    units = []
    cur_wide, cur_an = None, None
    for k, (s, e, name) in enumerate(heads):
        nxt = heads[k + 1][0] if k + 1 < len(heads) else len(text)
        seg = text[e:nxt]
        if "宽式释文" in name:
            cur_wide = seg
        elif "释文解析" in name or "釋文" in name:
            cur_an = seg
        if cur_wide is not None and cur_an is not None:
            units.append((cur_wide, cur_an))
            cur_wide, cur_an = None, None
    if cur_wide is not None:
        units.append((cur_wide, ""))
    return units


def cut(wide, analysis):
    wide = re.sub(r"\s+", "", wide)
    wn, wmap = [], []
    for i, ch in enumerate(wide):
        if ch in PUNCT:
            continue
        wn.append(ch)
        wmap.append(i)
    wn = plain(sc("".join(wn)))
    marks = [(m.start(), m.group(1)) for m in MARK_RE.finditer(analysis)]
    if not wn or not marks:
        return [], len(marks)
    avg = max(20, len(wn) / len(marks))
    bounds, labels, prev, missed = [0], [], 0, []
    for pos, num in marks:
        left = plain(sc(reading(analysis[max(0, pos - 30):pos])))[-12:]
        right = plain(sc(reading(analysis[pos + len(num) + 2: pos + len(num) + 30])))[:12]
        best = None
        for mode in ("L", "R"):
            probe = left if mode == "L" else right
            if len(probe) < 4:
                continue
            lo, hi = prev, min(len(wn), int(prev + 2.2 * avg))
            sub = wn[lo:hi]
            blk = difflib.SequenceMatcher(None, probe, sub, autojunk=False).find_longest_match(
                0, len(probe), 0, len(sub))
            if blk.size >= 5:
                cand = lo + blk.b + (blk.size if mode == "L" else 0)
                if cand > prev and (best is None or blk.size > best[0]):
                    best = (blk.size, cand)
        if best:
            cut_at = best[1]
        else:
            cut_at = int(prev + avg)
            missed.append(num)
        cut_at = min(cut_at, len(wn))
        if cut_at <= prev:
            cut_at = min(prev + 1, len(wn))
        prev = cut_at
        bounds.append(cut_at)
        labels.append(num)
    bounds.append(len(wn))
    slips = []
    for i, lab in enumerate(labels):
        a = wmap[bounds[i]] if bounds[i] < len(wmap) else len(wide)
        b = wmap[bounds[i + 1]] if bounds[i + 1] < len(wmap) else len(wide)
        slips.append((lab, wide[a:b].strip("，。 ；")))
    return slips, len(missed)


def main():
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
    report = ["# 清华简批量整理报告", "", f"共 {len(groups)} 篇", "",
              "| 篇 | 辑 | 文件 | 宽式字 | 简数 | 最短/最长 | 提示 |", "|---|---|---|---|---|---|---|"]
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (cn2int(kv[0][0]), kv[0][1])):
        files.sort()
        slips, wl, missed = [], 0, 0
        for _, p in files:
            for wide, an in units_of(p):
                wl += len(re.sub(r"\s+", "", wide))
                s, m = cut(wide, an)
                slips += s
                missed += m
        lens = [len(s[1]) for s in slips]
        short = [s[0] for s in slips if len(s[1]) < 30]
        long_ = [s[0] for s in slips if len(s[1]) > 95]
        tip = []
        if missed:
            tip.append(f"{missed}个标记未定位")
        if short:
            tip.append("偏短:" + ",".join(short[:8]))
        if long_:
            tip.append("偏长:" + ",".join(long_[:8]))
        report.append(f"| {pian} | {juan} | {len(files)} | {wl} | {len(slips)} | "
                      f"{(min(lens) if lens else 0)}/{max(lens) if lens else 0} | {'；'.join(tip)} |")
        if slips:
            lines = ["## 清华简", f"### {pian}"] + [f"{k}:{b}" for k, (_, b) in enumerate(slips, 1)]
            safe = re.sub(r"[\\/:*?\"<>|]", "_", f"{juan}_{pian}")
            open(os.path.join(OUT, safe + ".md"), "w", encoding="utf-8", newline="").write(
                "\r\n".join(lines) + "\r\n")
    open(os.path.join(OUT, "_report.md"), "w", encoding="utf-8", newline="").write(
        "\r\n".join(report) + "\r\n")
    print("texts:", len(groups))


if __name__ == "__main__":
    main()
