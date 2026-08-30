# Web Game UI Contract：PvPvE Escape 瀏覽器版

本文件是前端畫面、輸入和部署邊界的契約，不是後端 API 契約。網站為單機、單一路由、記憶體內狀態的瀏覽器遊戲，所有互動都在使用者瀏覽器完成。

## 畫面階段

| 階段 | 必須顯示 | 使用者操作 | 下一階段 |
|---|---|---|---|
| `loading`（App 啟動閘門） | loading 標題、資料準備提示與非空白的進度視覺 | 不接受遊戲快捷鍵；不得建立或更新比賽 | 資源完成或轉為 fallback 後進入 `intro` |
| `intro` | 遊戲標題、簡短玩法、控制說明、開始按鈕 | Enter 或按鈕 | `character-select` |
| `character-select` | 六種角色、三種戰術、目前選擇、開始提示 | 滑鼠或 `1`–`6` 選角色、`Q`/`W`/`E` 選戰術、Enter | `playing` |
| `playing` | 原版 1280×720 Canvas 世界、頭頂私人／公開資訊、右下玩家列表、死亡倒數與必要鍵盤提示 | 鍵盤／滑鼠 | `result` 或重新開始 |
| `result` | 原版勝者／無人勝利文字與重新開始／離開提示 | Enter／可聚焦提示文字或 Esc | Enter 到 `character-select`；Esc 到 `intro` |

`loading` 是 App 層的短暫啟動閘門，不是 `ScreenPhase` 或 `MatchPhase`；在必要地圖／角色資源完成所有載入嘗試前，不能顯示 `intro`、`character-select` 或 `playing`，也不能建立 `MatchState`。載入、建置或資源錯誤不得停留在空白畫面；單一資源失敗時完成 fallback 後仍須進入可玩的流程，若核心初始化失敗則提供可讀的錯誤訊息和重新載入／重新開始操作。

## 鍵盤與滑鼠輸入

| 輸入 | 行為 |
|---|---|
| `W` / `A` / `S` / `D` | 玩家上下左右移動 |
| 滑鼠位置 | 瞄準；由 Canvas 邊界座標轉成邏輯座標，再轉成世界座標 |
| 滑鼠左鍵 | 主要武器射擊／維持射擊 |
| 滑鼠右鍵 | 使用大招（依角色規則消耗 100 點能量） |
| `Space` | 使用目前戰術技能 |
| `Tab` | 切換目前玩家的自動瞄準 |
| `R` | 清除目前比賽並回到角色／戰術選擇；不作為手動換彈 |
| `Esc` | playing／result 回到 `intro`；不攔截瀏覽器關閉或返回行為 |
| `F1` | 切換開發者模式 |
| `1`–`5` | 開發者模式下選取對應的假玩家 |
| `M` | 開發者模式下將選取的假玩家放入中央撤離區 |
| `N` | 開發者模式下將選取的假玩家返回出生點 |
| `Enter` | 啟動、確認選擇、從結果頁回到角色選擇再玩一次；intro 也可用 `Space` 進入選角 |

輸入管理器必須在 `window.blur`、`document.visibilitychange` 進入 hidden、Canvas 失去焦點時清除所有持續按鍵與滑鼠按壓；恢復焦點後不得自動重播先前卡住的輸入，原先按住的動作鍵必須先收到真正的放開事件才可再次施放。playing 中的 WASD／滑鼠／Space／Tab／F1／M/N 快捷鍵只在 Canvas 已取得焦點且不是文字輸入欄位時生效；intro、選角與 result 的畫面流程鍵則由外層畫面處理。

## HUD 與資訊隱私

- 人類玩家 HUD 必須在原版 Canvas 頭頂資訊顯示自己的生命、能量、彈藥、配件就緒圓點與強化；Canvas／固定座標 overlay 右上顯示比賽倒數與開啟後的撤離進度，不得加入數值冷卻卡片取代原版畫面。
- 公開區域可以顯示其他玩家／敵人的名稱、位置、生命條或結果等規格允許的資訊；本功能沒有固定隊伍。
- 其他玩家的完整私有數值、冷卻和撤離進度不可被正常 HUD 顯示；`Tab` 只改變人類玩家的 auto-aim，不開啟私有資料面板。
- HUD 不得覆蓋必要的瞄準或撤離提示；在窄視窗中只等比例縮放原版 surface，而非加入不同的 web-only 排版。

## 畫布、縮放與可及性

- 遊戲使用 1280×720 的邏輯畫布，維持 16:9 顯示比例；實際 Canvas 尺寸隨容器縮放。
- 至少驗證 1024×576、1280×720 及更寬的桌面瀏覽器視窗；不支援觸控與手機排版作為本功能範圍。
- 所有滑鼠座標必須使用實際 Canvas bounding rect 和邏輯比例換算，不能直接把 client 座標當世界座標。
- intro、選角和結果頁的按鈕及選項使用原生可聚焦 DOM 元素；焦點順序、文字名稱、選中狀態和錯誤訊息要能被鍵盤與螢幕閱讀器理解。
- Canvas 外層提供 `tabIndex`、可見 focus 樣式和一段簡短的鍵盤操作說明；Canvas 本身只承載即時畫面，不是唯一的文字資訊來源。
- Canvas／DOM 的可見內容以 `rendering.py` 的固定邏輯座標與文案為準；可及性文字可隱藏提供，但不可產生額外可見資訊層。

## 資源與錯誤 fallback

- 角色與地圖 PNG 從網站自身 `/assets/` 路徑載入；不可依賴父專案目錄、Python 程式或本機服務。
- 首次開啟與重新整理先由 App loading gate 預載地圖 manifest 與可玩角色動畫；所有必要資源完成或轉為 fallback 後才進入 `intro`，`CharacterSelect` 與 `PlayingScreen` 共用同一份已完成的資源快取。
- 資源 manifest 的路徑錯誤、檔案遺失或解碼失敗時，使用幾何圖形、角色色彩和文字標籤替代該資產，並將警告寫入 developer mode／非侵入式狀態訊息。
- 資源載入失敗不得清除已建立的規則狀態；只有不可初始化遊戲核心時才切換到明確的錯誤畫面。
- 瀏覽器重新整理、回到 intro 或按「再玩一次」會清除舊的記憶體狀態並建立新的 seed，不保存帳號或比賽資料。

## Sites 部署契約

- 網站標題為 `PvPvE Escape — Browser Edition`，預定私人 production slug 為 `pvpve-escape-web`。
- production 必須由 Sites 的 owner-only/private access policy 保護；Sites 的權限層負責拒絕未授權訪客，且不需要啟動父專案的 Python／Pygame 或任何本機 server。
- 建置輸出必須能以 Sites／Cloudflare Workers 相容的靜態前端方式提供；沒有 API、資料庫、D1、R2 或 WebSocket 依賴。
- Sites project id 儲存在 `pvpve_escape_web/.openai/hosting.json`，不在核心遊戲模組讀取或使用。
- 發布前需用本機 preview 完成至少一次可玩的有意義流程，再分別以已授權擁有者與未授權瀏覽器 session 在私人 production URL 驗證存取與代表性情境。
