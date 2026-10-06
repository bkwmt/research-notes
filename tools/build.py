#!/usr/bin/env python3
"""research-notes 建置工具。

讀 tools/manifest.yaml，從 ~/Developer 底下的原專案：
  profiles   複製既有的單檔 HTML（團隊與機構側寫）
  notes      把 markdown 筆記轉成同風格的單檔 HTML；連結全部可點（裸網址、arXiv、DOI、ACL 編號、檔名）
  documents  依 tools/documents.yaml 把有轉載授權的 PDF 複製到 papers/，並產生文獻庫頁
  slides     把 Marp 投影片轉成「公開版」HTML（移除未授權圖片與講稿註解）
  index      產生首頁：第一層研究線、第二層待查問題（分類來自 refs.md 的表格）
每個產出都記進 manifest.lock.json（來源路徑、sha256、來源修改時間、建置時間），
原專案一律不動。

用法：
  .venv/bin/python tools/build.py            # 全部
  .venv/bin/python tools/build.py notes      # 只轉筆記（仍會重產首頁）
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitelib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
MANIFEST = TOOLS / "manifest.yaml"
LOCK = ROOT / "manifest.lock.json"
STYLE = (TOOLS / "style.css").read_text(encoding="utf-8")

cfg = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
SRC_ROOT = Path(cfg["sources_root"]).expanduser()
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now().isoformat(timespec="seconds")
QUESTIONS: dict[str, str] = cfg.get("questions", {})
LINES: list[dict] = cfg.get("research_lines", [])

lock: dict[str, dict] = {}


# ---------------------------------------------------------------- 共用
def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mtime(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime).date().isoformat()


def group_label(group: str) -> str:
    """「④」→「④ 口述歷史與數位人文」；具名區塊原樣回傳。"""
    return f"{group} {QUESTIONS[group]}" if group in QUESTIONS else group


def qtags(tags: str, main: str | None = None, depth: int = 0) -> str:
    """問題編號標籤列；主要問題實心。連到首頁對應區塊。"""
    home = "../" * depth + "index.html"
    out = []
    for ch in tags or "":
        if ch in QUESTIONS:
            cls = "qtag main" if ch == main else "qtag"
            out.append(f'<a class="{cls}" href="{home}#q{sitelib.CIRCLED.index(ch) + 1}" title="{html.escape(QUESTIONS[ch])}">{ch}</a>')
    return "".join(out)


def record(out_rel: str, src: Path, kind: str, title: str, *, group: str, tags: str = "", blurb: str = "", doc: dict | None = None):
    lock[out_rel] = {
        "kind": kind,
        "title": title,
        "group": group,
        "tags": tags,
        "category": group_label(group),
        "blurb": blurb,
        "doc": doc,
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
<p class="crumb"><a href="{home}">{html.escape(cfg['site_title'])}</a> › {crumb}</p>
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


# ---------------------------------------------------------------- 文獻庫登錄與 refs.md 書目
def load_documents() -> dict[str, dict]:
    d = cfg.get("documents")
    if not d:
        return {}
    reg = yaml.safe_load((ROOT / d["registry"]).read_text(encoding="utf-8")) or {}
    allowed = set(d["allowed_licenses"])
    for name, info in reg.items():
        src = SRC_ROOT / d["src_dir"] / name
        if not src.exists():
            raise SystemExit(f"documents.yaml 登錄的檔案不存在：{src}")
        if info.get("publish") and info.get("license") not in allowed:
            raise SystemExit(f"{name} 標了 publish 但授權「{info.get('license')}」不在 allowed_licenses，拒絕建置")
        if not info.get("publish") and not info.get("source_url"):
            raise SystemExit(f"{name} 不上站卻沒有 source_url，文獻庫頁會沒有出處可連")
        info["size_mb"] = round(src.stat().st_size / 1e6, 1)
    return reg


DOCS = load_documents()


def load_refs_rows() -> dict[str, dict]:
    n = cfg["notes"]
    p = SRC_ROOT / n["src_dir"] / n.get("refs_index", "refs.md")
    return sitelib.parse_refs_tables(p.read_text(encoding="utf-8")) if p.exists() else {}


REFS = load_refs_rows()


def doc_href(name: str, depth: int) -> tuple[str, str, bool] | None:
    """回傳 (連結, 說明, 是否站內)。站內 PDF 用相對路徑；未上站的連到原始出處。"""
    info = DOCS.get(name)
    if not info:
        return None
    if info["publish"]:
        href = "../" * depth + f"{cfg['documents']['out_dir']}/{name}"
        return href, f"站內 PDF（{info['license']}，{info['size_mb']} MB）", True
    return info["source_url"], f"外部連結：著作權所限未隨站公開（{info['license']}）", False


def doc_links_for(depth: int) -> dict[str, tuple[str, str]]:
    return {name: (h[0], h[1]) for name in DOCS if (h := doc_href(name, depth))}


def doc_button(name: str, depth: int) -> str:
    h = doc_href(name, depth)
    if not h:
        return ""
    href, title, internal = h
    label = "原文 PDF" if internal else "原文（外部）"
    return f'<a class="pdfbtn{"" if internal else " ext"}" href="{html.escape(href)}" title="{html.escape(title)}">{label}</a>'


# ---------------------------------------------------------------- profiles
def build_profiles():
    for item in cfg.get("profiles", []):
        src = SRC_ROOT / item["src"]
        out = ROOT / item["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        record(item["out"], src, "profile", item["title"], group=item.get("group", "團隊與機構側寫"),
               tags=item.get("tags", ""), blurb=item.get("blurb", ""))
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


def rel_link(target_out: str, out_rel: str) -> str:
    """站內兩頁之間的相對路徑。"""
    depth = len(Path(out_rel).parts) - 1
    return "../" * depth + target_out


def rewrite_links(text: str, src: Path, src_to_out: dict[Path, str], out_rel: str) -> str:
    """筆記之間的相對連結改成站內 .html；指向文獻庫 PDF 的改成 PDF 連結或原始出處；
    指向專案其他檔案的連結改成純文字加註。"""
    depth = len(Path(out_rel).parts) - 1

    def repl(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        path_part, _, anchor = target.partition("#")
        resolved = (src.parent / path_part).resolve()
        if resolved in src_to_out:
            return f"[{label}]({rel_link(src_to_out[resolved], out_rel)}{'#' + anchor if anchor else ''})"
        if (h := doc_href(resolved.name, depth)):
            return f"[{label}]({h[0]})"
        return f"{label}<span class=\"src\">（專案內部檔案 <code>{html.escape(path_part)}</code>，未隨筆記公開）</span>"

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", repl, text)


def code_path_resolver(src: Path, src_to_out: dict[Path, str], out_rel: str):
    """`notes/_對照矩陣.md`、`refs/xxx.pdf` 這類程式碼片段：依序對筆記所在目錄、refs/ 根、專案根解析。"""
    refs_root = SRC_ROOT / cfg["notes"]["src_dir"]
    bases = [src.parent, refs_root, refs_root.parent]
    depth = len(Path(out_rel).parts) - 1

    def resolve(path: str) -> str | None:
        for b in bases:
            cand = (b / path).resolve()
            if cand in src_to_out:
                return rel_link(src_to_out[cand], out_rel)
        name = Path(path).name
        if name in DOCS and (h := doc_href(name, depth)):
            return h[0]
        return None
    return resolve


def classify_note(src: Path, rel: str, out_rel: str, text: str) -> tuple[str, str]:
    """回傳 (主要問題或區塊, 全部問題標籤)。優先序：索引頁 → 覆寫 → refs.md 表格 → 筆記自己的「對應待查問題」。"""
    n = cfg["notes"]
    if Path(out_rel).relative_to(n["out_dir"]).as_posix() in n.get("index_pages", []):
        return n.get("index_group", "索引與回顧"), ""
    row = REFS.get(src.stem + ".pdf") or REFS.get(src.stem + ".md") or {}
    tags = row.get("questions", "")
    if not tags:
        m = re.search(rf"對應待查問題\*\*[：:]([^\n]{{0,160}})", text)
        tags = "".join(re.findall(f"[{sitelib.CIRCLED}]", m.group(1))) if m else ""
    main = sitelib.primary_question(tags, override=n.get("question_overrides", {}).get(rel))
    if not main:
        print(f"  ！未分類：{rel}（refs.md 沒有這筆、筆記也沒寫對應待查問題）")
        main = "未分類"
    if main not in tags:
        tags = main + tags
    return main, tags


def build_notes():
    n = cfg["notes"]
    base = SRC_ROOT / n["src_dir"]
    items = collect_notes()
    src_to_out = {src.resolve(): out for src, out in items}
    for src, out_rel in items:
        rel = src.relative_to(base).as_posix()
        text = src.read_text(encoding="utf-8")
        title = first_h1(text, src.stem)
        group, tags = classify_note(src, rel, out_rel, text)
        depth = len(Path(out_rel).parts) - 1
        body_md = re.sub(r"^#\s+.+?\n", "", text, count=1, flags=re.M)  # H1 交給版頭
        body_md = rewrite_links(body_md, src.resolve(), src_to_out, out_rel)
        body_md = sitelib.code_paths_to_links(body_md, code_path_resolver(src.resolve(), src_to_out, out_rel))
        MD.reset()
        body = MD.convert(body_md)
        body = re.sub(r"<table>", '<div class="tablewrap"><table>', body)
        body = re.sub(r"</table>", "</table></div>", body)
        body = sitelib.linkify_html(body, doc_links=doc_links_for(depth))
        pdf_name = src.stem + ".pdf"
        doc = None
        if (h := doc_href(pdf_name, depth)):
            doc = {"name": pdf_name, "internal": h[2], "license": DOCS[pdf_name]["license"]}
        main = group if group in QUESTIONS else None
        meta = (f"來源 <code>{html.escape(str(src.relative_to(SRC_ROOT)))}</code>　"
                f"來源最後修改 {mtime(src)}　分類 {html.escape(group_label(group))}"
                + (f"　問題 {qtags(tags, main, depth)}" if tags else "")
                + (f"　{doc_button(pdf_name, depth)}" if doc else ""))
        out = ROOT / out_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(title, body, crumb=html.escape(group_label(group)), meta=meta, depth=depth), encoding="utf-8")
        record(out_rel, src, "note", title, group=group, tags=tags, doc=doc)
        print(f"[note] {out_rel}  {group}{'' if not doc else '  +PDF' if doc['internal'] else '  +外部'}")


# ---------------------------------------------------------------- documents（文獻庫）
def build_documents():
    d = cfg.get("documents")
    if not d:
        return
    src_dir = SRC_ROOT / d["src_dir"]
    out_dir = ROOT / d["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    # 先清掉不再上站的舊檔，確保 papers/ 與登錄一致
    for p in out_dir.glob("*.pdf"):
        if not DOCS.get(p.name, {}).get("publish"):
            p.unlink(); print(f"[papers] 移除 {p.name}（登錄為不上站）")
    for k in [k for k, v in lock.items() if v.get("kind") == "pdf"]:
        del lock[k]
    n_pub = 0
    for name, info in DOCS.items():
        row = REFS.get(name, {})
        title = f"{row.get('author') or name} ({row.get('year', '')}) {row.get('short', '')}".strip() if row else name
        if info["publish"]:
            shutil.copy2(src_dir / name, out_dir / name)
            record(f"{d['out_dir']}/{name}", src_dir / name, "pdf", title,
                   group=sitelib.primary_question(row.get("questions", "")) or "未分類",
                   tags=row.get("questions", ""), blurb=info["license"])
            n_pub += 1
    build_documents_page(title_rows=True)
    print(f"[papers] 上站 {n_pub}／{len(DOCS)} 份 PDF，文獻庫頁 {d['out_dir']}/index.html")


def build_documents_page(title_rows: bool = True):
    d = cfg["documents"]
    note_pages = {Path(k).stem: k for k, v in lock.items() if v.get("kind") == "note"}

    def sort_key(name: str):
        q = sitelib.primary_question(REFS.get(name, {}).get("questions", "")) or "⑩"
        return (sitelib.CIRCLED.index(q) if q in sitelib.CIRCLED else 99, name)

    rows = []
    for name in sorted(DOCS, key=sort_key):
        info, row = DOCS[name], REFS.get(name, {})
        main = sitelib.primary_question(row.get("questions", ""))
        bib = (f"<b>{html.escape(row['author'])}</b> ({html.escape(row['year'])}). {html.escape(row['short'])}"
               if row else f"<code>{html.escape(name)}</code>")
        venue = html.escape(row.get("venue", "")).replace("*", "")
        note_rel = note_pages.get(Path(name).stem)
        note_cell = f'<a href="../{note_rel}">八節筆記</a>' if note_rel else '<span class="lic">尚無筆記</span>'
        if info["publish"]:
            orig = f'<a class="pdfbtn" href="{html.escape(name)}">PDF</a> <span class="lic">{info["size_mb"]} MB</span>'
        else:
            orig = f'<a class="pdfbtn ext" href="{html.escape(info["source_url"])}">原始出處</a>'
        lic = (f'<a href="{html.escape(info["license_url"])}">{html.escape(info["license"])}</a>' if info.get("license_url")
               else html.escape(info["license"]))
        rows.append(f"<tr><td>{bib}<br><span class=\"lic\">{venue}　{html.escape(info.get('version', ''))}</span></td>"
                    f"<td>{qtags(row.get('questions', ''), main, 1)}</td><td>{note_cell}</td><td>{orig}</td>"
                    f"<td><span class=\"lic\">{lic}</span></td></tr>")
    n_pub = sum(1 for v in DOCS.values() if v["publish"])
    mb = sum(v["size_mb"] for v in DOCS.values() if v["publish"])
    body = f"""<div class="notebox"><b>這是什麼</b>：extract_ohistory 文獻庫（<code>refs/</code>）裡每一份 PDF 的清單。
有轉載授權的（CC 系列授權、CC0）直接放在站內，點「PDF」就能在瀏覽器裡閱讀；沒有轉載授權的只列書目並連到原始出處（arXiv 非專屬授權、作者網頁、HAL、LDC 等），不隨站散布。
每份的授權判定依據寫在 <code>tools/documents.yaml</code>。</div>
<p><span class="stat"><b>{len(DOCS)}</b> 份文獻</span><span class="stat"><b>{n_pub}</b> 份站內 PDF（{mb:.0f} MB）</span><span class="stat"><b>{len(DOCS) - n_pub}</b> 份只連結</span></p>
<div class="tablewrap"><table class="docs">
<thead><tr><th>文獻</th><th>問題</th><th>筆記</th><th>原文</th><th>授權</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
<h2>怎麼判定能不能放</h2>
<ul>
<li><b>arXiv</b>：每篇看 abs 頁的授權欄。CC BY／BY-SA／BY-NC／BY-NC-SA／BY-NC-ND／CC0 可轉載；「arXiv.org perpetual, non-exclusive license」只授權 arXiv 散布，第三方不得轉載，所以只連結。</li>
<li><b>ACL Anthology</b>：頁尾聲明 2016 年起的材料為 CC BY 4.0，2016 年前為 CC BY-NC-SA 3.0；LREC 系列由 ELRA 以 CC BY-NC 4.0 釋出。</li>
<li><b>期刊</b>：以 PDF 內文的授權句與 Crossref 的 license 欄為準（Poetics 兩篇 CC BY-NC-ND、MDPI 與 JOHD CC BY、Concentric CC BY-NC）。</li>
<li><b>作者網頁、HAL、LDC、GitHub 無授權檔</b>：可免費閱讀不等於可轉載，一律只連結。</li>
</ul>
"""
    out = ROOT / d["out_dir"] / "index.html"
    out.write_text(page("文獻庫：PDF 原文與原始出處", body, crumb="文獻庫", meta=f"共 {len(DOCS)} 筆　建置 {TODAY}", depth=1,
                        description="extract_ohistory 文獻庫的 PDF 清單：有轉載授權者站內閱讀，其餘連到原始出處"), encoding="utf-8")


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
        record(f"{s['out_dir']}/index.html", src_md, "slides", s["title"], group=s.get("group", "導讀投影片"), blurb=s.get("blurb", ""))
        print(f"[slides] {s['out_dir']}/index.html（保留圖片 {len(keep)} 張）")


# ---------------------------------------------------------------- index
def build_index():
    pages = {k: v for k, v in lock.items() if v.get("kind") != "pdf"}
    by_group: dict[str, list[tuple[str, dict]]] = {}
    for out_rel, info in pages.items():
        by_group.setdefault(info.get("group") or info.get("category", "其他"), []).append((out_rel, info))
    covered = {g for line in LINES for g in line["groups"]}
    leftover = [g for g in by_group if g not in covered]
    leftover += [g for g in (sitelib.primary_question(REFS.get(n, {}).get("questions", "")) or "未分類" for n in DOCS)
                 if g not in covered and g not in leftover]
    lines = LINES + ([{"id": "other", "title": "其他", "blurb": "", "groups": leftover}] if leftover else [])

    def li(out_rel: str, info: dict) -> str:
        blurb = f'<span class="b">{html.escape(info["blurb"])}</span>' if info.get("blurb") else ""
        main = info.get("group") if info.get("group") in QUESTIONS else None
        tags = qtags(info.get("tags", ""), main, 0)
        doc = info.get("doc")
        btn = doc_button(doc["name"], 0) if doc else ""
        return (f'<li><a class="t" href="{out_rel}">{html.escape(info["title"])}</a>'
                f'<span class="d">{info["source_mtime"]}</span>{tags}{btn}{blurb}</li>')

    # 只有 PDF、還沒寫筆記的文獻也掛在所屬問題底下（站內 PDF 或原始出處），讓每個問題的庫存一目了然
    note_stems = {Path(k).stem for k, v in pages.items() if v.get("kind") == "note"}
    doc_only: dict[str, list[str]] = {}
    for name in sorted(DOCS):
        if Path(name).stem in note_stems:
            continue
        g = sitelib.primary_question(REFS.get(name, {}).get("questions", "")) or "未分類"
        doc_only.setdefault(g, []).append(name)

    def li_doc(name: str) -> str:
        row = REFS.get(name, {})
        main = sitelib.primary_question(row.get("questions", ""))
        bib = (f"{html.escape(row['author'])} ({html.escape(row['year'])}). {html.escape(row['short'])}" if row else html.escape(name))
        return (f'<li><span class="t">{bib}</span><span class="d">尚無筆記</span>{qtags(row.get("questions", ""), main, 0)}'
                f'{doc_button(name, 0)}</li>')

    sections, toc = [], []
    for line in lines:
        groups = [g for g in line["groups"] if g in by_group or g in doc_only]
        if not groups:
            continue
        n_line = sum(len(by_group.get(g, [])) + len(doc_only.get(g, [])) for g in groups)
        sections.append(f'<h2 class="line" id="{html.escape(line["id"])}">{html.escape(line["title"])} <span class="tag">{n_line}</span></h2>')
        if line.get("blurb"):
            sections.append(f'<p class="line-blurb">{html.escape(line["blurb"])}</p>')
        sub = []
        for g in groups:
            gid = f"q{sitelib.CIRCLED.index(g) + 1}" if g in QUESTIONS else re.sub(r"\W+", "-", g)
            rows = sorted(by_group.get(g, []), key=lambda kv: kv[0])
            extra = doc_only.get(g, [])
            n_g = len(rows) + len(extra)
            sections.append(f'<h3 class="group" id="{gid}">{html.escape(group_label(g))} <span class="tag">{n_g}</span></h3>\n<ul class="list">\n'
                            + "\n".join([li(o, i) for o, i in rows] + [li_doc(nm) for nm in extra]) + "\n</ul>")
            sub.append(f'<li><a href="#{gid}">{html.escape(group_label(g))}</a>（{n_g}）</li>')
        toc.append(f'<li class="line-title"><a href="#{html.escape(line["id"])}">{html.escape(line["title"])}</a>（{n_line}）<ul class="sub">{"".join(sub)}</ul></li>')

    n_pub = sum(1 for v in DOCS.values() if v["publish"])
    papers_link = (f'<a href="{cfg["documents"]["out_dir"]}/index.html">文獻庫</a>：{len(DOCS)} 份 PDF 的清單，{n_pub} 份有轉載授權可直接在站內閱讀，其餘連到原始出處。'
                   if DOCS else "")
    body = f"""<div class="notebox"><b>這是什麼</b>：研究過程中寫下的文獻筆記、團隊側寫與論文導讀，從各研究專案複製快照而來；
正本仍在原專案，日期欄是來源檔的最後修改日。第一層依<b>研究線</b>分，第二層沿用各研究線自己的分類：extract_ohistory 用書目總表的九類<b>待查問題</b>（①～⑨），
每篇的主要問題是實心標籤、其餘是空心標籤。筆記採「八節模板」（貢獻、抽取流程、組織、表示法、資料集、評估、問題、對本專案的啟示），讀者設定為人文學者。
{papers_link}</div>
<div class="toc"><ul>{''.join(toc)}{f'<li class="line-title"><a href="{cfg["documents"]["out_dir"]}/index.html">文獻庫</a>（{len(DOCS)} 份，{n_pub} 份站內 PDF）</li>' if DOCS else ''}</ul></div>
{chr(10).join(sections)}
"""
    out = ROOT / "index.html"
    out.write_text(page(cfg["site_title"], body, crumb="首頁", sub=html.escape(cfg["site_subtitle"]),
                        meta=f"共 {len(pages)} 頁、{n_pub} 份站內 PDF　建置 {TODAY}", depth=0), encoding="utf-8")
    print(f"[index] index.html（{len(pages)} 頁）")


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
    steps = args or ["profiles", "notes", "documents", "slides", "index"]
    if LOCK.exists():
        lock.update(json.loads(LOCK.read_text(encoding="utf-8")))
    if "profiles" in steps: build_profiles()
    if "notes" in steps: build_notes()
    if "documents" in steps: build_documents()
    if "slides" in steps: build_slides()
    build_index()
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"lock 寫入 {LOCK.name}（{len(lock)} 筆）")
