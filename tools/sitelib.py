"""research-notes 建置用的純函式（無檔案存取，方便測試）：

  linkify_html          把 HTML 文字節點裡的裸網址、arXiv 編號、DOI、ACL Anthology 編號、
                        白名單網域與文獻檔名變成 <a>；<a>、<code>、<pre> 內不動。
  parse_refs_tables     解析 refs.md 的 markdown 表格，取出每份文獻的書目欄位與問題編號。
  primary_question      依「覆寫 → 第一個編號 → 區塊預設」決定主要問題。
  code_paths_to_links   把 markdown 裡 `路徑.md`／`路徑.pdf` 這類程式碼片段改成站內連結。
"""
from __future__ import annotations

import re
from typing import Callable

CIRCLED = "①②③④⑤⑥⑦⑧⑨"

# 純文字裡沒寫 https:// 也直接連結的網域（尾端比對，含子網域）
LINK_HOSTS = ("aclanthology.org", "anthropic.com", "arxiv.org", "doi.org", "github.com",
              "huggingface.co", "readthedocs.io", "idohl.org", "ucl.ac.uk", "ldc.upenn.edu")

# 網址允許的字元：排除空白、角括號、引號與中文全形標點（全形標點常緊貼在網址後面）
_U = r"[^\s<>\"'（）「」『』，。；、！？]"
_HOSTS = "|".join(re.escape(h) for h in LINK_HOSTS)
_TOKEN = re.compile(
    r"(?P<url>https?://" + _U + r"+)"
    r"|(?P<host>(?<![\w/.@-])(?:[\w-]+\.)*(?:" + _HOSTS + r")/" + _U + r"+)"
    r"|(?P<arxiv>arXiv:\s?(?P<arxiv_id>\d{4}\.\d{4,5}(?:v\d+)?))"
    r"|(?P<doi>(?<![\w/.])10\.\d{4,9}/" + _U + r"+)"
    r"|(?P<acl>(?<![\w/.-])(?P<acl_id>20\d\d\.[a-z][a-z0-9]*-[a-z0-9]+\.\d+)(?![\w.-]))"
    r"|(?P<acl_old>(?<=ACL )(?P<acl_old_id>[A-Z]\d{2}-\d{4})(?![\w-]))"
    r"|(?P<pdf>(?<![\w/.-])[a-z][a-z0-9_-]*\.pdf(?![\w.-]))"
)
_TRAIL = ".,;:!?)]"
_SKIP_TAGS = {"a", "code", "pre", "script", "style"}
_TAG_SPLIT = re.compile(r"(<[^>]+>)")


def _anchor(href: str, text: str, cls: str = "", title: str = "") -> str:
    attrs = f' href="{href}"'
    if cls:
        attrs += f' class="{cls}"'
    if title:
        attrs += f' title="{title}"'
    return f"<a{attrs}>{text}</a>"


def _linkify_text(text: str, doc_links: dict[str, tuple[str, str]] | None) -> str:
    # m.lastgroup 會回報最內層的具名群組（例如 arxiv_id），所以用外層群組名逐一判斷
    def repl(m: re.Match) -> str:
        for kind in ("url", "host", "arxiv", "doi", "acl", "acl_old", "pdf"):
            if m.group(kind) is not None:
                return _repl_kind(kind, m, doc_links)
        return m.group(0)

    return _TOKEN.sub(repl, text)


def _repl_kind(kind: str, m: re.Match, doc_links) -> str:
    if kind in ("url", "host", "doi"):
        body = m.group(kind)
        tail = ""
        while body and body[-1] in _TRAIL:
            tail = body[-1] + tail
            body = body[:-1]
        if kind == "url":
            return _anchor(body, body) + tail
        if kind == "host":
            return _anchor("https://" + body, body) + tail
        return _anchor("https://doi.org/" + body, body) + tail
    if kind == "arxiv":
        return _anchor("https://arxiv.org/abs/" + m.group("arxiv_id"), m.group(0))
    if kind == "acl":
        return _anchor(f"https://aclanthology.org/{m.group('acl_id')}/", m.group("acl_id"))
    if kind == "acl_old":
        return _anchor(f"https://aclanthology.org/{m.group('acl_old_id')}/", m.group("acl_old_id"))
    name = m.group(0)
    if doc_links and name in doc_links:
        href, title = doc_links[name]
        return _anchor(href, name, cls="doc", title=title)
    return name


def linkify_html(html_text: str, *, doc_links: dict[str, tuple[str, str]] | None = None) -> str:
    """只處理文字節點；進入 <a>/<code>/<pre>/<script>/<style> 後直到對應關閉標籤為止都不動。"""
    out: list[str] = []
    depth = 0
    for part in _TAG_SPLIT.split(html_text):
        if not part:
            continue
        if part.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)", part)
            if m and m.group(2).lower() in _SKIP_TAGS:
                depth = max(0, depth - 1) if m.group(1) else depth + 1
            out.append(part)
        elif depth == 0:
            out.append(_linkify_text(part, doc_links))
        else:
            out.append(part)
    return "".join(out)


# ---------------------------------------------------------------- refs.md
_FILENAME = re.compile(r"^[a-z0-9_-]+\.(pdf|md)$")


def parse_refs_tables(md_text: str) -> dict[str, dict]:
    """回傳 {檔名: {section, author, year, short, venue, review, id, questions, topic}}。
    表格沒有「問題」欄時，問題編號取該區塊的預設：標題裡的圈號，或內文「對應問題編號 **⑥」。"""
    rows: dict[str, dict] = {}
    section, section_default, header = "", "", []
    for line in md_text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            m = re.search(f"[{CIRCLED}]", section)
            section_default = m.group(0) if m else ""
            header = []
            continue
        if not line.startswith("|"):
            if not section_default:
                m = re.search(rf"對應問題編號\s*\**\s*([{CIRCLED}])", line)
                if m:
                    section_default = m.group(1)
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].startswith("檔名"):
            header = cells
            continue
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        if not _FILENAME.match(cells[0]):
            continue
        get = lambda name: next((cells[i] for i, h in enumerate(header) if name in h and i < len(cells)), "")
        questions = "".join(re.findall(f"[{CIRCLED}]", get("問題"))) or section_default
        rows[cells[0]] = {
            "section": section,
            "author": get("作者"), "year": get("年"), "short": get("標題"), "venue": get("場域"),
            "review": get("同儕審查"),
            "id": next((cells[i] for i, h in enumerate(header) if any(k in h for k in ("DOI", "ID", "Anthology")) and i < len(cells)), ""),
            "questions": questions,
            "topic": get("主題"),
        }
    return rows


def primary_question(questions: str, *, override: str | None = None, default: str | None = None) -> str | None:
    if override:
        return override
    for ch in questions or "":
        if ch in CIRCLED:
            return ch
    return default


# ---------------------------------------------------------------- code spans → links
_CODE_PATH = re.compile(r"(?<!\[)`([^`\n]+\.(?:md|pdf|txt|html))`(?!\])")


def code_paths_to_links(md: str, resolver: Callable[[str], str | None]) -> str:
    """`路徑` 若能由 resolver 解析成站內連結，改寫為 [`路徑`](連結)；解析不到的原樣保留。"""
    def repl(m: re.Match) -> str:
        link = resolver(m.group(1))
        return f"[`{m.group(1)}`]({link})" if link else m.group(0)
    return _CODE_PATH.sub(repl, md)
