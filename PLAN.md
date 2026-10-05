# 計畫：research-notes（2026-10-06 核准後執行）

## Context

使用者要把 `~/Developer` 底下與 HTML 有關的產出分類放上 GitHub，但不掛在個人學術頁（bkwmt.github.io）下。
盤點 621 個 HTML 後，使用者把範圍縮到**參考與筆記類**：IDOHL 團隊側寫、`extract_ohistory/refs` 的
markdown 文獻筆記（轉 HTML）、Crossley 2008 導讀投影片（公開版）。一個總 repo、開 GitHub Pages、
複製快照不動原專案、repo 名 `research-notes`。

## 做法

1. **repo 骨架**：`tools/manifest.yaml`（來源清單）、`tools/build.py`（複製／轉檔／首頁／lock）、
   `tools/check.py`（驗證）、`tools/style.css`（內嵌樣式）、`.nojekyll`、`.gitignore`、README、LICENSE、WORKLOG。
2. **三類來源**：
   - profiles：單檔 HTML 直接複製。
   - notes：Python-Markdown 轉檔；筆記間連結改站內、專案內部檔案連結改灰字註記；非 ASCII 檔名在 manifest 指定輸出名。
   - slides：從 Marp md 重新產生公開版（刪講稿註解、刪未授權圖、論文圖表換文字框、補圖片來源頁），建置時檢查殘留。
3. **部署**：`gh repo create bkwmt/research-notes --public`，推 main，`gh api` 開 Pages（legacy，main，/）。
4. **登記**：`Developer/CLAUDE.md` 補一行；`extract_ohistory/WORKLOG.md` 記來源筆記的用語修正。

## 驗證

- `tools/check.py`：66 頁可解析、零外部資源、站內連結全部存在、用語零命中（兩頁例外有註明）。
- `curl -sI https://bkwmt.github.io/research-notes/` 回 200；首頁、一篇筆記、投影片各開一次。
- `tools/build.py --check` 對剛建好的 lock 回報 0 頁過期。

## 不做的事

- 不碰 bkwmt.github.io repo；不放任何研究報告、網絡圖、PASMA 或 NTU-Bonn 產出。
- 不替投影片下載 Commons 替代照片（`img/照片來源.md` 有三張建議，日後要補再加進 manifest 的 keep_images）。
