#!/usr/bin/env python3
"""驗證站內所有 HTML：可解析、無外部資源、站內連結存在、無簡體字與中國大陸詞彙。
用法：.venv/bin/python tools/check.py [--links]   加 --links 時另外逐一測外部連結可達。"""
from __future__ import annotations

import concurrent.futures as cf
import html.parser
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = [p for p in ROOT.rglob("*.html") if ".venv" not in p.parts and "node_modules" not in p.parts]
BAD_WORDS = ["信息", "視頻", "數據庫", "軟件", "代碼", "賓語", "主語", "質量", "用戶", "默認", "服務器", "接口", "內存", "硬盤", "計算機", "互聯網"]
SIMP = set("这个说时间来发经对会学国问题们为开关还从进过与义书见两点听没让头长种动实际")
# 用語檢查的例外：模板本文把禁用詞當例子列出；refs 引用中國大陸期刊時保留簡體刊名
SKIP_WORD_CHECK = {"notes/template.html", "notes/refs.html"}


class P(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.n = 0
    def handle_starttag(self, t, a):
        self.n += 1


problems = 0
ext_urls: set[str] = set()
for p in sorted(PAGES):
    s = p.read_text(encoding="utf-8")
    rel = p.relative_to(ROOT)
    P().feed(s)
    ext = re.findall(r'<(?:script|link|img|iframe)[^>]+(?:src|href)="(https?://[^"]+)"', s)
    if ext:
        problems += 1; print(f"[外部資源] {rel}: {ext[:3]}")
    # 專有名詞與跨詞邊界的誤判先剝掉（例如「承接口述」「計算機學院」）
    s_chk = s
    for phrase in ("承接口述", "計算機學院", "計算機學報", "計算機學會"):
        s_chk = s_chk.replace(phrase, "")
    hits = [w for w in BAD_WORDS if w in s_chk]
    simp = sorted({c for c in s_chk if c in SIMP})
    if str(rel) in SKIP_WORD_CHECK:
        hits, simp = [], []
    if hits or simp:
        problems += 1; print(f"[用語] {rel}: 詞彙 {hits} 簡體 {''.join(simp)}")
    for href in re.findall(r'href="([^"#]+)(?:#[^"]*)?"', s):
        if href.startswith(("http://", "https://", "mailto:")):
            ext_urls.add(href.replace("&amp;", "&")); continue
        target = (p.parent / href).resolve()
        if not target.exists():
            problems += 1; print(f"[站內連結失效] {rel} → {href}")
print(f"檢查 {len(PAGES)} 頁，問題 {problems} 項，外部連結 {len(ext_urls)} 個不重複")

if "--links" in sys.argv:
    socket.setdefaulttimeout(12)
    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) link-check/1.0"}

    def chk(u):
        for m in ("HEAD", "GET"):
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method=m)); return u, r.status
            except urllib.error.HTTPError as e:
                if m == "GET": return u, e.code
            except Exception as e:
                if m == "GET": return u, f"ERR {type(e).__name__}"
        return u, "?"
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(chk, sorted(ext_urls)))
    bad = [(u, s) for u, s in res if not (isinstance(s, int) and s < 400)]
    print(f"外部連結可達 {len(res) - len(bad)}／{len(res)}")
    for u, s in bad:
        print(f"   {s}\t{u}")
sys.exit(1 if problems else 0)
