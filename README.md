# research-notes

程明（Ming Cheng）的文獻筆記、團隊側寫與論文導讀投影片，以靜態網頁發布在
**https://bkwmt.github.io/research-notes/** 。與個人學術頁（bkwmt.github.io）分開維護。

## 內容

| 分類 | 內容 | 來源專案 |
|---|---|---|
| 團隊與機構側寫 | International Digital Oral History Lab（IDOHL）側寫 | extract_ohistory/refs |
| 文獻深讀筆記（八節） | 51 篇，每篇依「貢獻、抽取流程、組織、表示法、資料集、評估、問題、啟示」八節 | extract_ohistory/refs/notes |
| 索引與回顧 | 書目總表、文獻回顧、對照矩陣、卡點對照表、筆記模板 | extract_ohistory/refs |
| IDOHL 調查報告 | 團隊與歷史、三個計畫、開源程式碼、出版與相關工作 | extract_ohistory/refs/notes/idohl |
| 導讀投影片 | Crossley (2008) Pretty Connected 導讀（公開版） | SLIDES/crossley2008_punk |

## 運作方式

這裡的每一頁都是**快照**，正本留在原專案。`tools/manifest.yaml` 列來源，`tools/build.py`
負責複製或轉檔，並把每個產出的來源路徑、sha256、來源修改日寫進 `manifest.lock.json`。

```bash
python3 -m venv .venv && .venv/bin/pip install markdown pyyaml   # 第一次
.venv/bin/python tools/build.py            # 全部重建：profiles、notes、slides、index
.venv/bin/python tools/build.py --check    # 哪些頁的來源比上次建置新
.venv/bin/python tools/check.py [--links]  # 可解析、無外部資源、站內連結、用語；--links 另測外部連結
```

- **筆記**：markdown 以 Python-Markdown 轉成單檔 HTML（樣式內嵌，不引用任何外部資源）。
  筆記之間的相對連結改成站內連結；指向原專案其他檔案（WORKLOG、程式）的連結改成灰字註記。
- **投影片**：Marp markdown 以 `npx @marp-team/marp-cli` 轉檔。公開版**移除**講稿註解、
  出版社圖表（換成標頁碼的文字框）與未取得授權的照片，只保留 manifest 列出的公眾領域或 CC 授權照片，
  並補一頁圖片來源。建置時會檢查輸出不再引用任何未保留的圖片。
- **部署**：GitHub Pages 直接發布 `main` 分支根目錄（有 `.nojekyll`），不需 CI。

## 新增一頁

- 新筆記：放進原專案 `extract_ohistory/refs/notes/`，重跑 `build.py` 即自動納入；
  檔名若非 ASCII，在 manifest 的 `renames` 指定輸出檔名。
- 新側寫或投影片：在 manifest 對應區塊加一筆。

## 授權

筆記與側寫的文字採 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hant)；
建置程式（`tools/`）採 MIT。被評述的論文、投影片原文與圖片之著作權屬原作者，見 `LICENSE.md`。
