"""给已提取的释文文本分自然段：版面缩进优先，失败则按句读分段。"""
import os
import re

import pymupdf

SRC = r"D:\program\web\bamboo_archive\datasource\qinghua"
TXT = r"D:\program\web\bamboo\drafts\qinghua_full"
OUT = r"D:\program\web\bamboo\drafts\清华简_段落.md"
NUM = "〇一二三四五六七八九十"
TITLE_RE = re.compile(
    r"清华简(?:(?P<juan>[%s]+))?[《〈](?P<pian>[^》〉]+)[》〉](?P<rest>[^/]*)解析" % NUM)


def cn2int(s):
    t = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
         "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (t.get(a, 1) if a else 1) * 10 + (t.get(b, 0) if b else 0)
    return t.get(s, 0) if s in t else 99


def layout(path):
    doc = pymupdf.open(path)
    seq, pids = [], []
    pid = 0
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b["lines"]:
                txt = "".join(s["text"] for s in l["spans"])
                if l["bbox"][0] > 100:
                    pid += 1
                for ch in txt:
                    if ch.isspace():
                        continue
                    seq.append(ch)
                    pids.append(pid)
    return "".join(seq), pids


def try_layout(text, path):
    seq, pids = layout(path)
    i = seq.find(text[:40])
    if i < 0:
        return None
    j = i + len(text)
    if j > len(seq):
        return None
    if sum(1 for a, b in zip(seq[i:j], text) if a != b) > max(2, len(text) * 0.01):
        return None
    paras, cur = [], ""
    for k in range(i, j):
        if k > i and pids[k] != pids[k - 1]:
            if cur:
                paras.append(cur)
            cur = ""
        cur += seq[k]
    if cur:
        paras.append(cur)
    return paras


def sentence_split(text, size=40):
    paras, buf, i = [], "", 0
    while i < len(text):
        ch = text[i]
        buf += ch
        if ch in "。！？" and len(buf) >= size:
            if i + 1 < len(text) and text[i + 1] in "”』」":
                buf += text[i + 1]
                i += 1
            paras.append(buf)
            buf = ""
        i += 1
    if buf.strip():
        paras.append(buf)
    return paras


def main():
    groups = {}
    for name in os.listdir(SRC):
        if not name.lower().endswith(".pdf"):
            continue
        m = TITLE_RE.search(name)
        if not m:
            continue
        groups.setdefault(((m.group("juan") or "无辑"), m.group("pian").strip()), []).append(
            os.path.join(SRC, name))
    out = ["## 清华简", ""]
    stats = []
    total = 0
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (cn2int(kv[0][0]), kv[0][1])):
        fn = os.path.join(TXT, f"{juan}_{pian}.txt")
        if not os.path.exists(fn):
            continue
        text = open(fn, encoding="utf-8").read().strip()
        if not text:
            continue
        files.sort()
        paras = None
        for p in files:
            paras = try_layout(text, p)
            if paras:
                break
        how = "版面"
        if not paras:
            paras = sentence_split(text)
            how = "句读"
        total += len(text)
        stats.append((pian, how, len(paras)))
        out.append(f"### {pian}")
        for para in paras:
            out.append(para)
            out.append("")
    open(OUT, "w", encoding="utf-8", newline="").write("\n".join(out))
    print("total:", total, "texts:", len(stats))
    print("句读 fallback:", [s[0] for s in stats if s[1] == "句读"])


if __name__ == "__main__":
    main()
