# research-notes 工作紀錄

> 這個 repo 是「參考與筆記類」HTML 的對外發布點（GitHub Pages），與個人學術頁 bkwmt.github.io 分開。
> 正本都在原專案；這裡只放快照與建置工具。每頁的來源在 `manifest.lock.json`。

## 現況

- 網址：https://bkwmt.github.io/research-notes/ （GitHub Pages，`main` 根目錄，無 CI）
- 內容：65 頁（團隊側寫 1、文獻筆記 63＝八節深讀 54＋索引與回顧 5＋IDOHL 調查報告 4、導讀投影片 1）＋文獻庫頁；
  文獻庫 59 份 PDF 中 38 份上站（約 82 MB）、21 份只連結原始出處
- 分類：首頁第一層研究線（口述歷史的 LLM 知識抽取／音樂社會網絡分析），第二層沿用 `refs.md` 的九類待查問題 ①～⑨；
  每篇的主要問題取 `refs.md` 表格「問題」欄第一個編號，`refs.md` 沒列的在 manifest `question_overrides` 指定
- 工具：`tools/build.py`（建置）、`tools/sitelib.py`（連結化與 refs.md 解析的純函式，`tools/tests/` 有 16 個單元測試）、
  `tools/check.py`（驗證，含文獻庫登錄守門）、`tools/manifest.yaml`（來源清單與分類）、`tools/documents.yaml`（PDF 授權登錄）
- 刻意不放的：研究報告（週會報告、網絡圖、時間軸：含口述逐字句與時間碼）、PASMA 衍生圖（私人收藏）、
  NTU-Bonn 任何產出（問卷明文不公開）、行政文書、`amateur/document.html`（整本書的 OCR 全文）、
  `refs/notes/語料言據標記盤點_2026-08-22.md` 與 `講述者標記盤點_2026-09-04.txt`（語料衍生）、
  沒有轉載授權的 21 份 PDF（只連結）。完整盤點見 2026-10-06 日誌。

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

### 2026-10-06（一）　第二輪：依研究方向分類、連結全部可點、文獻庫上站

**起因**：使用者看過第一版後提三點：（1）要依原本的研究方向分類，不是依「側寫／筆記／投影片」的檔案類型；
（2）超連結目前只是純文字；（3）下載好的文件希望直接上傳，在網站上就能閱讀，但要注意合法性。

**分類**：「原本的研究方向」取 `refs.md` 書目總表自己的九類待查問題 ①～⑨，而不是另發明一套。`build.py` 解析
`refs.md` 的 markdown 表格，每篇文獻的主要問題是「問題」欄第一個編號、其餘編號當標籤；方法學基礎文獻那張表沒有
「問題」欄，從區塊內文「對應問題編號 **⑥**」取預設；portelli／mbakwe／vansina（口述史觀）與 IDOHL 四份報告在
manifest `question_overrides` 指定 ④。首頁第一層是研究線（manifest `research_lines`），目前兩條：extract_ohistory
與 SNA（只有 Crossley 投影片），日後 hirata、JP_music_network 等線的筆記可各加一條。沒有筆記只有 PDF 的 7 篇
（⑧ 五篇本體學習、⑨ 兩篇實體對齊）也掛在所屬問題底下標「尚無筆記」，否則 ⑨ 在首頁會消失。

**連結**：原因是 Python-Markdown 不會自動把裸網址變連結，而來源筆記裡有 1,001 個裸網址（IDOHL 四份報告佔大半）
與 125 個 DOI／arXiv 純文字識別碼。新寫 `tools/sitelib.py`：在轉好的 HTML 上只處理文字節點（`<a>`、`<code>`、`<pre>`
內不動），把裸網址、`arXiv:ID`、DOI、ACL Anthology 編號（`2024.lrec-main.35`、`ACL P07-1131`）、白名單網域
（aclanthology.org、anthropic.com、github.com…）與文獻檔名變成連結；另在 markdown 層把 `notes/_對照矩陣.md`、
`refs/xxx.pdf` 這類程式碼片段解析成站內連結。全形標點（；。）、）緊貼網址的情況用字元類排除，結尾的 ASCII 標點留在
連結外。`refs.html` 的 `<a>` 從 1 個變 118 個，IDOHL 01 報告從 1 個變 241 個；`check.py` 的站內連結與用語檢查仍零問題。

**文獻庫**：`refs/` 有 59 份 PDF（130 MB）。逐篇查轉載授權：26 篇 arXiv 用程式讀 abs 頁的授權欄（16 篇 CC 系列或 CC0，
10 篇只有 arXiv 非專屬散布授權）；15 篇 ACL 會議論文看 PDF 頁尾並對照 Anthology 頁尾聲明（2016 起 CC BY 4.0、
2016 前 CC BY-NC-SA 3.0、LREC 系列 ELRA CC BY-NC 4.0）；期刊查 Crossref 的 license 欄與 PDF 內文授權句
（Poetics 兩篇 CC BY-NC-ND、MDPI 與 JOHD CC BY、Concentric CC BY-NC、IJL 期刊層級 CC BY-NC-ND、
Portelli 波蘭譯本 CC BY-SA）；HAL 用 API 查 `licence_s`（只是作者存放授權）、MeDoraH 簡報的 GitHub 儲存庫
`license: null`。結果 **38 份上站（82 MB）、21 份只連結**：arXiv 非專屬授權的 10 篇、作者網頁／HAL／LDC／中研院網站
可免費下載但未附轉載授權的 11 篇。判定逐筆寫在 `tools/documents.yaml` 的 `evidence`；`build.py` 拒絕建置
「標了 publish 但授權不在 allowed_licenses」的檔，`check.py` 核對 `papers/` 沒有未登錄的 PDF。
最弱的一筆是 Aikhenvald 2007（只有期刊層級聲明，PDF 內未標示），已在登錄裡註明，使用者可改成只連結。
Vansina 1985 與 LOC EDTF 本來就沒有 PDF。閱讀方式：PDF 用瀏覽器原生檢視器開，筆記版頭、首頁列表、文獻庫頁
都有「原文 PDF」或「原文（外部）」按鈕；不另做閱讀器。

**驗證**：`tools/tests/` 16 個單元測試通過；`check.py` 67 頁零問題（外部連結 456 個不重複，未逐一測可達）；
Playwright 開首頁與一篇筆記看版面；`build.py --check` 對新 lock 回報 0 頁過期。
