# AGENTS.md

## 專案:BOOKD 成約引擎 — 形象網站
靜態行銷頁面:「Workflow AI over Data」全自動獲客服務。前檔賣「已約好會議」結果,資料庫串接在後台。語言:繁體中文。

## 檔案
- `index.html` — 單頁結構(Hero / 對比 / 五段管線 / 試跑 widget / 定價 / FAQ)
- `styles.css` — 工業調度台美學:ink black、safety orange、cream paper、lime accent
- `script.js` — 終端機流程模擬、ticker、滾動動畫、計數器、試跑 widget

## 本機預覽
`python3 -m http.server 12000`

## 字型守則
mono stack 用 `"JetBrains Mono", "Noto Sans TC", monospace` — 少了中文 fallback 會出現缺字方塊(tofu)。
