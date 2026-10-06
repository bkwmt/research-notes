# research-notes

程明（Ming Cheng）的文獻筆記、團隊側寫、論文導讀投影片與文獻庫，以靜態網頁發布在
**https://bkwmt.github.io/research-notes/** 。與個人學術頁（bkwmt.github.io）分開維護。

## 內容與分類

首頁第一層依**研究線**分，第二層沿用各研究線自己的分類。

| 研究線 | 區塊 | 內容 | 來源專案 |
|---|---|---|---|
| 口述歷史的 LLM 知識抽取 | 索引與回顧 | 書目總表、文獻回顧、對照矩陣、卡點對照表、筆記模板 | extract_ohistory/refs |
| 〃 | 待查問題 ①～⑨ | 54 篇八節深讀筆記、IDOHL 團隊側寫與四份調查報告，各掛在 `refs.md` 給它的主要問題底下；其餘問題編號當標籤 | extract_ohistory/refs |
| 音樂社會網絡分析（SNA） | 導讀投影片 | Crossley (2008) Pretty Connected 導讀（公開版） | SLIDES/crossley2008_punk |
| （跨線） | 文獻庫 `papers/` | `refs/` 全部 59 份 PDF 的清單；38 份有轉載授權者放在站內可直接閱讀，21 份只列書目並連到原始出處 | extract_ohistory/refs |

九類待查問題是 extract_ohistory 書目總表（`refs.md`）原本的分類：①LLM 抽取與知識圖譜建構現況
②agentic 建構 ③Agent Skills 與 harness 的出處 ④口述歷史與數位人文 ⑤無 gold standard 的評估
⑥來歷標記、極性與時間記法 ⑦零標注三元組抽取的參照點 ⑧本體學習與 schema 歸納 ⑨跨來源實體對齊。
每篇文獻的編號由 `build.py` 解析 `refs.md` 的表格取得，`refs.md` 沒列的在 manifest 的 `question_overrides` 指定。

## 運作方式

這裡的每一頁都是**快照**，正本留在原專案。`tools/manifest.yaml` 列來源，`tools/build.py`
負責複製或轉檔，並把每個產出的來源路徑、sha256、來源修改日寫進 `manifest.lock.json`。

```bash
python3 -m venv .venv && .venv/bin/pip install markdown pyyaml   # 第一次
.venv/bin/python tools/build.py            # 全部重建：profiles、notes、documents、slides、index
.venv/bin/python tools/build.py notes      # 只轉筆記（仍重產首頁）
.venv/bin/python tools/build.py --check    # 哪些頁的來源比上次建置新
.venv/bin/python tools/check.py [--links]  # 可解析、無外部資源、站內連結、用語、文獻庫登錄；--links 另測外部連結
.venv/bin/python -m unittest discover -s tools/tests   # sitelib 的單元測試
```

- **筆記**：markdown 以 Python-Markdown 轉成單檔 HTML（樣式內嵌，不引用任何外部資源）。
  筆記之間的相對連結改成站內連結；`路徑.md`／`路徑.pdf` 這類程式碼片段若指向站內頁或文獻庫也改成連結；
  指向原專案其他檔案（WORKLOG、程式）的連結改成灰字註記。
  轉出的 HTML 再經 `tools/sitelib.py` 連結化：裸網址、`arXiv:ID`、DOI、ACL Anthology 編號、
  白名單網域（aclanthology.org、anthropic.com、github.com 等）與文獻檔名都變成可點的連結，`<a>`、`<code>`、`<pre>` 內不動。
- **文獻庫**：`tools/documents.yaml` 逐檔登錄授權（`license`）、判定依據（`evidence`）、原始出處（`source_url`）與是否上站（`publish`）。
  `build.py` 只複製 `publish: true` 且授權在 manifest `allowed_licenses`（CC 系列與 CC0）內的檔案到 `papers/`，
  其餘在文獻庫頁只列書目並連到原始出處；`check.py` 另核對 `papers/` 裡沒有未登錄的檔。
  每篇筆記版頭與首頁列表都有「原文 PDF」（站內）或「原文（外部）」按鈕。
- **投影片**：Marp markdown 以 `npx @marp-team/marp-cli` 轉檔。公開版**移除**講稿註解、
  出版社圖表（換成標頁碼的文字框）與未取得授權的照片，只保留 manifest 列出的公眾領域或 CC 授權照片，
  並補一頁圖片來源。建置時會檢查輸出不再引用任何未保留的圖片。
- **部署**：GitHub Pages 直接發布 `main` 分支根目錄（有 `.nojekyll`），不需 CI。

## 新增一頁

- 新筆記：放進原專案 `extract_ohistory/refs/notes/`，並在 `refs.md` 的表格加一列（問題編號從那裡來），重跑 `build.py` 即自動納入；
  檔名若非 ASCII，在 manifest 的 `renames` 指定輸出檔名。
- 新 PDF：在 `tools/documents.yaml` 加一筆，先查授權（arXiv abs 頁的授權欄、ACL Anthology 頁尾聲明、PDF 內文授權句、Crossref 的 license 欄），
  能轉載才標 `publish: true`；不能轉載的填 `source_url` 即可。
- 新側寫或投影片：在 manifest 對應區塊加一筆並指定 `group`。
- 新研究線：在 manifest `research_lines` 加一條，列出它的區塊。

## 授權

筆記與側寫的文字採 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hant)；
建置程式（`tools/`）採 MIT。文獻庫裡每份 PDF 各依其自身授權轉載（CC BY、CC BY-SA、CC BY-NC、CC BY-NC-SA、CC BY-NC-ND、CC0），
授權與出處列在文獻庫頁與 `tools/documents.yaml`。被評述的論文、投影片原文與圖片之著作權屬原作者，見 `LICENSE.md`。
