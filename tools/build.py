#!/usr/bin/env python3
"""research-notes 建置工具。

讀 tools/manifest.yaml，從 ~/Developer 底下的原專案：
  profiles  複製既有的單檔 HTML（團隊與機構側寫）
  notes     把 markdown 筆記轉成同風格的單檔 HTML
  slides    把 Marp 投影片轉成「公開版」HTML（移除未授權圖片與講稿註解）
  index     產生首頁
每個產出都記進 manifest.lock.json（來源路徑、sha256、來源修改時間、建置時間），
原專案一律不動。

用法：
  .venv/bin/python tools/build.py            # 全部
  .venv/bin/python tools/build.py notes      # 只轉筆記
  .venv/bin/python tools/build.py --check    # 只比對來源是否比 lock 新，不寫檔
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
MANIFEST = TOOLS / "manifest.yaml"
LOCK = ROOT / "manifest.lock.json"
STYLE = (TOOLS / "style.css").read_text(encoding="utf-8")

cfg = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
SRC_ROOT = Path(cfg["sources_root"]).expanduser()
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now().isoformat(timespec="seconds")

lock: dict[str, dict] = {}


# ---------------------------------------------------------------- 共用
def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mtime(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime).date().isoformat()


def record(out_rel: str, src: Path, kind: str, title: str, category: str, blurb: str = ""):
    lock[out_rel] = {
        "kind": kind,
        "title": title,
        "category": category,
        "blurb": blurb,
        "source": str(src.relative_to(SRC_ROOT)),
        "source_sha256": sha256(src),
        "source_mtime": mtime(src),
        "built_at": NOW,
    }


def page(title: str, body: str, *, crumb: str, sub: str = "", meta: str = "", depth: int = 1, description: str = "") -> str:
    """把內文包成單檔 HTML。depth 決定回首頁的相對路徑。"""
    home = "../" * depth + "index.html"
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description or sub or title)}">
<style>
{STYLE}
</style>
</head>
<body>
<header class="hero"><div class="wrap">
<p class="crumb"><a href="{home}">{html.escape(cfg['site_title'])}</a> › {html.escape(crumb)}</p>
<h1>{html.escape(title)}</h1>
{f'<p class="sub">{sub}</p>' if sub else ''}
{f'<p class="meta">{meta}</p>' if meta else ''}
</div></header>
<main class="wrap">
{body}
<footer><p>{html.escape(cfg['license_notice'])}　建置 {TODAY}。</p></footer>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- profiles
def build_profiles():
    for item in cfg.get("profiles", []):
        src = SRC_ROOT / item["src"]
        out = ROOT / item["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        record(item["out"], src, "profile", item["title"], "團隊與機構側寫", item.get("blurb", ""))
        print(f"[profile] {item['out']}")


# ---------------------------------------------------------------- notes
MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"], output_format="html5")


def first_h1(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    return re.sub(r"[*`]", "", m.group(1)) if m else fallback


def collect_notes() -> list[tuple[Path, str]]:
    """回傳 [(來源絕對路徑, 輸出相對路徑 notes/…)]。"""
    n = cfg["notes"]
    base = SRC_ROOT / n["src_dir"]
    excluded = {e["path"] for e in n.get("exclude", [])}
    items: list[tuple[Path, str]] = []
    for rel, out in n["renames"].items():
        items.append((base / rel, f"{n['out_dir']}/{out}"))
    renamed = set(n["renames"])
    for p in sorted(base.glob(n["eight_section_glob"])):
        rel = str(p.relative_to(base))
        if rel in renamed or rel in excluded or p.name.startswith("_"):
            continue
        items.append((p, f"{n['out_dir']}/{p.stem}.html"))
    return items


def rewrite_links(text: str, src: Path, src_to_out: dict[Path, str], out_rel: str) -> str:
    """筆記之間的相對連結改成站內 .html；指向專案其他檔案的連結改成純文字加註。"""
    out_dir = Path(out_rel).parent

    def repl(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        path_part, _, anchor = target.partition("#")
        resolved = (src.parent / path_part).resolve()
        if resolved in src_to_out:
            rel_target = Path(src_to_out[resolved]).relative_to(out_dir) if Path(src_to_out[resolved]).is_relative_to(out_dir) else Path("../" * len(out_dir.parts)) / src_to_out[resolved]
            # 同一層以上的路徑用相對寫法
            rel_str = str(rel_target).replace("\\", "/")
            return f"[{label}]({rel_str}{'#' + anchor if anchor else ''})"
        return f"{label}<span class=\"src\">（專案內部檔案 <code>{html.escape(path_part)}</code>，未隨筆記公開）</span>"

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", repl, text)


def build_notes():
    n = cfg["notes"]
    items = collect_notes()
    src_to_out = {src.resolve(): out for src, out in items}
    cat_of: dict[str, str] = {}
    for cat, files in n.get("categories", {}).items():
        for f in files:
            cat_of[f"{n['out_dir']}/{f}"] = cat
    for src, out_rel in items:
        text = src.read_text(encoding="utf-8")
        title = first_h1(text, src.stem)
        body_md = re.sub(r"^#\s+.+?\n", "", text, count=1, flags=re.M)  # H1 交給版頭
        body_md = rewrite_links(body_md, src.resolve(), src_to_out, out_rel)
        MD.reset()
        body = MD.convert(body_md)
        body = re.sub(r"<table>", '<div class="tablewrap"><table>', body)
        body = re.sub(r"</table>", "</table></div>", body)
        category = cat_of.get(out_rel, "文獻深讀筆記（八節）")
        depth = len(Path(out_rel).parts) - 1
        meta = (f"來源 <code>{html.escape(str(src.relative_to(SRC_ROOT)))}</code>　"
                f"來源最後修改 {mtime(src)}　分類 {html.escape(category)}")
        out = ROOT / out_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(title, body, crumb=category, meta=meta, depth=depth), encoding="utf-8")
        record(out_rel, src, "note", title, category)
        print(f"[note] {out_rel}")


# ---------------------------------------------------------------- slides
def build_slides():
    for s in cfg.get("slides", []):
        src_md = SRC_ROOT / s["src_md"]
        img_dir = SRC_ROOT / s["src_img_dir"]
        out_dir = ROOT / s["out_dir"]
        (out_dir / "img").mkdir(parents=True, exist_ok=True)
        text = src_md.read_text(encoding="utf-8")

        # 1) 講稿註解不進公開版（保留 Marp 指令註解，例如 <!-- _class: lead -->）
        if s.get("strip_note_comments"):
            text = re.sub(r"<!--\s*講稿[\s\S]*?-->\s*", "", text)

        # 2) 圖片：保留清單內的照片；論文圖表換成文字框；其餘背景照片整行刪除
        keep = s.get("keep_images", {})
        placeholders = s.get("figure_placeholders", {})

        def img_repl(m: re.Match) -> str:
            attrs, fname = m.group(1), Path(m.group(2)).name
            if fname in keep:
                return m.group(0)
            if fname in placeholders:
                return f"> **{placeholders[fname]}**"
            return ""  # 未授權照片：刪除整個圖片標記

        text = re.sub(r"!\[([^\]]*)\]\((?:\./)?img/([^)]+)\)", img_repl, text)

        # 3) 補一頁圖片來源
        credits = "\n".join(f"- `{k}`：{v}" for k, v in keep.items())
        text = text.rstrip() + f"""

---

# Image credits（公開版）

公開版只保留公眾領域或 CC 授權的照片；論文圖表（Figure 1–3）與其餘照片因著作權未附上，原始投影片僅供實驗室內部教學。

{credits}

論文：Crossley, N. (2008). Pretty Connected: The Social Network of the Early UK Punk Movement. *Theory, Culture & Society*, 25(6), 89–116. https://doi.org/10.1177/0263276408095546
"""
        tmp_md = out_dir / "_public.md"
        tmp_md.write_text(text, encoding="utf-8")
        for fname in keep:
            shutil.copy2(img_dir / fname, out_dir / "img" / fname)
        cmd = ["npx", "-y", "@marp-team/marp-cli@latest", str(tmp_md), "-o", str(out_dir / "index.html")]
        subprocess.run(cmd, check=True, cwd=out_dir, capture_output=True)
        tmp_md.unlink()
        # 殘留檢查：公開版不得引用任何未保留的 img/
        built = (out_dir / "index.html").read_text(encoding="utf-8")
        refs = set(re.findall(r"img/([^\"'&)]+)", built))
        bad = refs - set(keep)
        if bad:
            raise SystemExit(f"公開版投影片仍引用未授權圖片：{sorted(bad)}")
        record(f"{s['out_dir']}/index.html", src_md, "slides", s["title"], "導讀投影片", s.get("blurb", ""))
        print(f"[slides] {s['out_dir']}/index.html（保留圖片 {len(keep)} 張）")


# ---------------------------------------------------------------- index
def build_index():
    groups: dict[str, list[tuple[str, dict]]] = {}
    for out_rel, info in lock.items():
        groups.setdefault(info["category"], []).append((out_rel, info))
    order = ["團隊與機構側寫", "導讀投影片", "索引與回顧", "IDOHL 調查報告（2026-10-05）", "文獻深讀筆記（八節）"]
    sections = []
    for cat in order + [c for c in groups if c not in order]:
        if cat not in groups:
            continue
        rows = sorted(groups[cat], key=lambda kv: kv[0])
        lis = []
        for out_rel, info in rows:
            blurb = f'<span class="b">{html.escape(info["blurb"])}</span>' if info.get("blurb") else ""
            lis.append(f'<li><a class="t" href="{out_rel}">{html.escape(info["title"])}</a>'
                       f'<span class="d">{info["source_mtime"]}</span>{blurb}</li>')
        sections.append(f'<h2 id="{html.escape(cat)}">{html.escape(cat)} <span class="tag">{len(rows)}</span></h2>\n<ul class="list">\n' + "\n".join(lis) + "\n</ul>")
    toc = "".join(f'<li><a href="#{html.escape(c)}">{html.escape(c)}</a>（{len(groups[c])}）</li>' for c in order + [c for c in groups if c not in order] if c in groups)
    body = f"""<div class="notebox"><b>這是什麼</b>：研究過程中寫下的文獻筆記、團隊側寫與論文導讀，從各研究專案複製快照而來；
正本仍在原專案，日期欄是來源檔的最後修改日。筆記採「八節模板」（貢獻、抽取流程、組織、表示法、資料集、評估、問題、對本專案的啟示），
讀者設定為人文學者。每篇都標明來源檔路徑；寫作時的專案內部檔案連結改成灰字註記、不對外連。</div>
<div class="toc"><ul>{toc}</ul></div>
{''.join(sections)}
"""
    out = ROOT / "index.html"
    out.write_text(page(cfg["site_title"], body, crumb="首頁", sub=html.escape(cfg["site_subtitle"]),
                        meta=f"共 {len(lock)} 頁　建置 {TODAY}", depth=0), encoding="utf-8")
    print(f"[index] index.html（{len(lock)} 頁）")


# ---------------------------------------------------------------- check
def check_stale() -> int:
    if not LOCK.exists():
        print("尚無 manifest.lock.json"); return 1
    old = json.loads(LOCK.read_text(encoding="utf-8"))
    stale = []
    for out_rel, info in old.items():
        src = SRC_ROOT / info["source"]
        if not src.exists():
            stale.append((out_rel, "來源不存在"))
        elif sha256(src) != info["source_sha256"]:
            stale.append((out_rel, f"來源已更新（{mtime(src)}）"))
    for o, why in stale:
        print(f"  過期  {o}  ←  {why}")
    print(f"檢查 {len(old)} 頁，{len(stale)} 頁過期")
    return 1 if stale else 0


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check_stale())
    steps = args or ["profiles", "notes", "slides", "index"]
    if LOCK.exists():
        lock.update(json.loads(LOCK.read_text(encoding="utf-8")))
    if "profiles" in steps: build_profiles()
    if "notes" in steps: build_notes()
    if "slides" in steps: build_slides()
    if "index" in steps or steps != args: build_index()
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"lock 寫入 {LOCK.name}（{len(lock)} 筆）")
