"""按 PDF 版面缩进还原「宽式释文/释文」的自然段，输出 drafts/清华简_段落.md"""
import collections
import os
import re

import pymupdf

SRC = r"D:\program\web\bamboo_archive\datasource\qinghua"
OUT = r"D:\program\web\bamboo\drafts\清华简_段落.md"
NUM = "〇一二三四五六七八九十"
TITLE_RE = re.compile(
    r"清华简(?:(?P<juan>[%s]+))?[《〈](?P<pian>[^》〉]+)[》〉](?P<rest>[^/]*)解析" % NUM)
START_RE = re.compile(r"宽式释文|《[^》]{1,8}》释文|释文[：:]")
STOP_RE = re.compile(r"释文解析|釋文解析")
HEADER_SIZE = 10.0
BODY_INDENT = 100.0


def cn2int(s):
    t = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
         "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (t.get(a, 1) if a else 1) * 10 + (t.get(b, 0) if b else 0)
    return t.get(s, 0) if s in t else 99


def paragraphs_of(path):
    doc = pymupdf.open(path)
    lines = []
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b["lines"]:
                txt = "".join(s["text"] for s in l["spans"]).strip()
                if not txt:
                    continue
                size = max(s["size"] for s in l["spans"])
                if size < HEADER_SIZE:
                    continue
                lines.append((l["bbox"][0], txt))
    paras, cur = [], None
    inside = False
    for x0, txt in lines:
        if START_RE.search(txt) and len(txt) < 40:
            inside = True
            cur = None
            continue
        if STOP_RE.search(txt):
            if cur:
                paras.append(cur)
            inside = False
            cur = None
            continue
        if not inside:
            continue
        if x0 > BODY_INDENT:
            if cur:
                paras.append(cur)
            cur = txt
        else:
            cur = (cur or "") + txt
    if cur:
        paras.append(cur)
    return [re.sub(r"\s+", "", p) for p in paras if p.strip()]


def main():
    groups = collections.defaultdict(list)
    for name in os.listdir(SRC):
        if not name.lower().endswith(".pdf"):
            continue
        m = TITLE_RE.search(name)
        if not m:
            continue
        juan = m.group("juan") or ""
        pian = m.group("pian").strip()
        rest = m.group("rest").strip()
        groups[(juan, pian)].append((rest, os.path.join(SRC, name)))
    out = ["## 清华简", ""]
    total = 0
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (cn2int(kv[0][0]), kv[0][1])):
        files.sort()
        paras = []
        for _, p in files:
            paras += paragraphs_of(p)
        text = "".join(paras)
        total += len(text)
        out.append(f"### {pian}")
        for para in paras:
            out.append(para)
            out.append("")
        print(f"{pian}: {len(paras)} 段 {len(text)} 字")
    open(OUT, "w", encoding="utf-8", newline="").write("\n".join(out))
    print("total:", total)


if __name__ == "__main__":
    main()
