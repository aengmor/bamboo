"""用 PDF 版面缩进给已提取的释文文本分自然段。"""
import os
import re

import pymupdf

SRC = r"D:\program\web\bamboo\datasource\qinghua"
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


def layout_map(path):
    """Return (sequence, paragraph ids per char)."""
    doc = pymupdf.open(path)
    seq, pids = [], []
    pid = 0
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b["lines"]:
                txt = "".join(s["text"] for s in l["spans"])
                x0 = l["bbox"][0]
                if x0 > 100:
                    pid += 1
                for ch in txt:
                    if ch.isspace():
                        continue
                    seq.append(ch)
                    pids.append(pid)
    return "".join(seq), pids


def split_by_layout(text, path):
    seq, pids = layout_map(path)
    i = seq.find(text[:60])
    if i < 0:
        return None
    j = i + len(text)
    if j > len(seq):
        return None
    # 校验：把 seq[i:j] 与 text 比对一致率
    same = sum(1 for a, b in zip(seq[i:j], text) if a == b)
    if same / max(1, len(text)) < 0.9:
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


def main():
    groups = {}
    for name in os.listdir(SRC):
        if not name.lower().endswith(".pdf"):
            continue
        m = TITLE_RE.search(name)
        if not m:
            continue
        juan = m.group("juan") or "无辑"
        pian = m.group("pian").strip()
        groups.setdefault((juan, pian), []).append(os.path.join(SRC, name))
    out = ["## 清华简", ""]
    total = 0
    fallback = []
    for (juan, pian), files in sorted(groups.items(), key=lambda kv: (cn2int(kv[0][0]), kv[0][1])):
        fn = os.path.join(TXT, f"{juan}_{pian}.txt")
        if not os.path.exists(fn):
            continue
        text = open(fn, encoding="utf-8").read().strip()
        if not text:
            continue
        files.sort()
        paras = []
        cursor = 0
        for p in files:
            seq, pids = layout_map(p)
            head = text[cursor:cursor + 30]
            if not head:
                break
            pos = seq.find(head)
            if pos < 0:
                continue
            L = 0
            while cursor + L < len(text) and pos + L < len(seq) and text[cursor + L] == seq[pos + L]:
                L += 1
            if L < 20:
                continue
            chunk = text[cursor:cursor + L]
            cp, cur2, last = [], "", pids[pos]
            for k in range(pos, pos + L):
                if k > pos and pids[k] != pids[k - 1]:
                    if cur2:
                        cp.append(cur2)
                    cur2 = ""
                cur2 += seq[k]
            if cur2:
                cp.append(cur2)
            # 用原文字符还原标点（seq 已含全部字符）
            paras += cp
            cursor += L
        if cursor < len(text):
            paras.append(text[cursor:])
        joined = "".join(paras)
        if abs(len(joined) - len(text)) > 2 or joined[:20] != text[:20]:
            # 版面切分不可靠，退回按句读分段
            paras, buf = [], ""
            i = 0
            while i < len(text):
                ch = text[i]
                buf += ch
                if ch in "。！？" and len(buf) >= 40:
                    if i + 1 < len(text) and text[i + 1] in "”』」":
                        buf += text[i + 1]
                        i += 1
                    paras.append(buf)
                    buf = ""
                i += 1
            if buf.strip():
                paras.append(buf)
        if not paras:
            fallback.append(pian)
            paras = [text]
        total += len(text)
        out.append(f"### {pian}")
        for para in paras:
            out.append(para)
            out.append("")
    open(OUT, "w", encoding="utf-8", newline="").write("\n".join(out))
    print("total chars:", total)
    print("fallback (整篇一段):", fallback)


if __name__ == "__main__":
    main()
