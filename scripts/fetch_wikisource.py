"""从维基文库抓取清华简各篇释文（action=raw），清洗后存为 txt。"""
import os
import re
import subprocess
import urllib.parse

OUT = r"D:\program\web\bamboo\drafts\qinghua_full"
RAW = r"C:\Users\Lenovo\AppData\Local\Temp\ws_raw"
BASE = "https://zh.wikisource.org/w/index.php?title=%s&action=raw"
PREFIX = "清華大學藏戰國竹簡/"

TITLES = [
    "尹誥", "金縢", "皇門", "祭公",
    "良臣", "祝辭", "赤鵠之集湯之屋",
    "命訓", "湯處於湯丘", "湯在啻門", "殷高宗問於三壽",
    "子犯子餘", "禱辭", "病方",
    "成后", "兩中",
    "胥馬", "凡馬之疾", "馴馬", "馭術", "馭馬之道",
]


def fetch(title):
    page = PREFIX + title
    url = BASE % urllib.parse.quote(page)
    dst = os.path.join(RAW, title + ".wiki")
    r = subprocess.run(["curl", "-sL", "-m", "60", "-A", "Mozilla/5.0",
                        "-o", dst, "-w", "%{http_code}", url],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    code = (r.stdout or "").strip()
    size = os.path.getsize(dst) if os.path.exists(dst) else 0
    return code, size, dst


def clean(raw):
    s = re.sub(r"\{\{\*\|[^}]*\}\}", "", raw)      # 简文注
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)            # 其它模板
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<onlyinclude>|</onlyinclude>", "", s)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)  # [[a|b]] -> b
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''''|'''|''", "", s)
    s = s.replace("　", " ")
    paras = []
    for block in re.split(r"\n\s*\n", s):
        block = block.strip()
        if not block:
            continue
        if block.startswith("{{header") or block.startswith("|"):
            continue
        text = re.sub(r"\s+", "", block)
        text = text.strip("　 ")
        if len(text) < 4:
            continue
        paras.append(text)
    return paras


def main():
    os.makedirs(RAW, exist_ok=True)
    log = []
    for t in TITLES:
        code, size, dst = fetch(t)
        paras = []
        if code == "200" and size > 60:
            raw = open(dst, encoding="utf-8", errors="ignore").read()
            paras = clean(raw)
        text = "".join(paras)
        ok = len(text) >= 60
        if ok:
            open(os.path.join(OUT, f"维基_{t}.txt"), "w", encoding="utf-8", newline="").write(text + "\n")
        log.append((t, code, size, len(text)))
        print(f"{t}: {code} {size}B -> {len(text)}字 {'OK' if ok else 'FAIL'}")
    return log


if __name__ == "__main__":
    main()
