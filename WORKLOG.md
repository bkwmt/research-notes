# research-notes 工作紀錄

> 這個 repo 是「參考與筆記類」HTML 的對外發布點（GitHub Pages），與個人學術頁 bkwmt.github.io 分開。
> 正本都在原專案；這裡只放快照與建置工具。每頁的來源在 `manifest.lock.json`。

## 現況

- 網址：https://bkwmt.github.io/research-notes/ （GitHub Pages，`main` 根目錄，無 CI）
- 內容：團隊側寫 1、文獻深讀筆記 51、索引與回顧 5、IDOHL 調查報告 4、導讀投影片 1（共 62 頁＋首頁）
- 工具：`tools/build.py`（建置）、`tools/check.py`（驗證）、`tools/manifest.yaml`（來源清單）
- 刻意不放的：研究報告（週會報告、網絡圖、時間軸：含口述逐字句與時間碼）、PASMA 衍生圖（私人收藏）、
  NTU-Bonn 任何產出（問卷明文不公開）、行政文書、`amateur/document.html`（整本書的 OCR 全文）、
  `refs/notes/語料言據標記盤點_2026-08-22.md` 與 `講述者標記盤點_2026-09-04.txt`（語料衍生）。
  完整盤點見下方 2026-10-06 日誌。

## 日誌

### 2026-10-06（一）　建站：盤點 621 個 HTML，只收參考與筆記類

**起因**：使用者要把 Developer 底下與 HTML 有關的東西分類放上 GitHub，但不掛在個人網頁下。
三個 Explore agent 盤點：Developer 下 621 個 .html（排除 node_modules／venv／dist 後，15 個專案；
其中 531 個是 Jazzification 獨奏頁與 html-showcase UMAP 圖的批次頁面）、13 個會產 HTML 的專案的
git 與 Pages 狀態、以及明文保密規則 19 條。使用者裁決：**只放參考、筆記類**；一個總 repo 分資料夾；
開 Pages；複製快照不動原專案；repo 名 `research-notes`；納入 refs/notes 的 markdown 筆記（轉 HTML）
與 Crossley 2008 導讀投影片。

**關鍵限制與處理**：
- 私有 repo 的 HTML 在 GitHub 上不會渲染；私有 repo 開 Pages 要 GitHub Pro，而且網站本身仍是任何人可開。
  所以只放可公開的東西，整個 repo 公開。
- 投影片的 17 張圖只有 3 張是公眾領域或 CC 授權（`img/照片來源.md`），3 張論文圖表屬出版社。
  公開版由 `build.py` 從原 md 重新產生：刪講稿註解、刪未授權照片、論文圖表換成標頁碼的文字框、
  補一頁圖片來源；建置時檢查輸出不再引用任何未保留的圖。
- 筆記來源檔裡五篇用了「主語／賓語」（2026-09-06 之前寫的），依全域用語規則改成「主詞／受詞」；
  IDOHL 03 報告的「代碼」改「編號」。這是改原專案的來源檔，extract_ohistory 的 WORKLOG 有記。
- 用語檢查對 `template.html`（規則本文列出禁用詞當例子）與 `refs.html`（引用中國大陸期刊的簡體刊名）
  不報錯，其餘 64 頁零命中。

**工具**：Python-Markdown 3.11（tables、fenced_code、sane_lists、toc）；Marp CLI 4.5.1 經 npx；
樣式沿用 extract_ohistory 的霧藍紙色盤，全部內嵌、零外部資源。
