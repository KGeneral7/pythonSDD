# 研究紀錄：PvPvE Escape 瀏覽器版

**功能分支**：`010-pvpve-escape-web`
**日期**：2026-08-29

## 研究目的

本功能要把既有 `pvpve_escape/` Python/Pygame 桌面遊戲提供成可在桌面瀏覽器直接遊玩的私人網站。研究重點是：如何在不改動既有桌面版的前提下，重現目前的角色、戰鬥、怪物、地形、撤離與開發者模式，並符合 Sites 的部署邊界。

## 決策摘要

### 1. 採用獨立的瀏覽器產品目錄

**決策**：新增 `pvpve_escape_web/`，以單一網頁入口承載瀏覽器版；既有 `pvpve_escape/` 與 001–009 的文件、程式和發行紀錄保持不變。

**理由**：瀏覽器版需要不同的執行環境、建置工具和資源入口。分離目錄可以讓 Python/Pygame 桌面版繼續維持可回歸的基準，也避免把 Sites 的建置產物混入原有遊戲模組。

**淘汰方案**：直接把既有 Python 專案改造成網站，會同時改變已發布桌面版的啟動方式、依賴和測試邊界，風險高且不符合本功能「新增網頁版」的範圍。

### 2. 使用 TypeScript／React／Vite 的瀏覽器原生實作

**決策**：使用 Sites starter 建立 React + TypeScript + Vite 網頁；遊戲畫面以 Canvas 繪製，React/DOM 負責畫面階段、說明文字、選擇控制項與可及性語意。

**理由**：這個組合能直接使用瀏覽器的輸入、動畫迴圈、Canvas 和靜態資源，也符合 Sites 的前端部署模型。遊戲核心可放在不依賴 React 的 TypeScript 模組，便於單元測試。

**淘汰方案**：

- Pyodide/WASM 雖可能重用 Python，但會增加載入重量、Pygame 顯示層整合和輸入轉接的不確定性，不適合第一個可玩的網站版本。
- 以 iframe 或遠端桌面嵌入 Pygame 會保留伺服器／桌面執行環境依賴，無法形成獨立的靜態 Sites 網站。

### 3. 以既有 Python 原始碼作為行為基準，而非逐檔翻譯

**決策**：先從 `models.py`、`config.py`、`rules.py`、`characters.py`、`monsters.py`、`terrain.py`、`navigation.py`、`aiming.py`、`auto_aim.py`、`world.py` 與 `rendering.py` 擷取公開行為、數值、狀態轉換、固定文案和邏輯座標，再在 `pvpve_escape_web/src/game/` 與 `src/components/` 以瀏覽器友善的型別和模組重建 1:1 parity。

**理由**：Pygame 的事件迴圈、surface、sprite 和鍵盤事件不能直接搬到瀏覽器；但規則、數值、資料表、狀態流程、固定 UI 文案與繪製層級是可驗證的產品行為。瀏覽器端不逐行複製平台 API，但以 parity fixture 和固定邏輯座標逐項核對可見與可玩的結果。

**淘汰方案**：把桌面渲染器逐行改寫成 Canvas 會把平台細節、DOM 互動和遊戲規則混在一起，難以測試和維護。

### 4. 使用 requestAnimationFrame 搭配固定更新上限

**決策**：主迴圈以 `requestAnimationFrame` 驅動，時間以 `performance.now()` 計算；每幀傳入的 `deltaTime` 上限為 0.05 秒，依固定順序執行輸入取樣、玩家、怪物、投射物、效果、撤離、動畫和結果判定。

**理由**：瀏覽器 tab 暫停、切換視窗或低幀率時可能產生很大的時間差。限制步長可避免一次更新讓角色穿越障礙或跳過撤離／傷害事件；固定順序也讓規則測試可重現。

**淘汰方案**：完全依賴每幀實際時間、不限制步長，會讓背景分頁恢復時的狀態跳躍，且不同裝置的結果更難比較。

### 5. Canvas 與 DOM 分工

**決策**：遊戲世界、角色、怪物、投射物、地形、特效、玩家頭頂資訊和瞄準提示在 Canvas 上繪製；intro、角色／戰術選擇、結果頁，以及 playing 的固定右上文字／右下 roster 與鍵盤可及性語意使用 DOM overlay，但只占原版固定座標，不新增可見現代化 HUD。

**理由**：Canvas 適合目前的 2D 即時畫面，DOM 適合文字選擇、焦點管理、螢幕閱讀器和瀏覽器語意。兩者分工可保持遊戲更新核心不依賴 React。

### 6. 資源由網站自帶並提供可理解的 fallback

**決策**：將父專案 `pvpve_escape/assets/` 的 PNG 資源複製到 `pvpve_escape_web/public/assets/`，建立角色／地圖資源 manifest 與載入快取；單一圖片載入失敗時顯示帶角色色彩和文字標籤的幾何 fallback，不讓整場遊戲白屏。

**理由**：Sites 需要可由靜態 URL 取得的檔案，網站不能依賴父目錄或本機 Python 程式。fallback 能把檔案遺失轉為可辨識的畫面狀態，並讓規則與互動仍可測試。

### 7. 輸入採用顯式 InputState，並在失焦時清空按鍵

**決策**：DOM 事件只更新語意化 `InputState`；遊戲核心只讀取該狀態。滑鼠座標在 Canvas 邊界內轉成邏輯 1280×720 座標，再轉成世界座標。左鍵是普攻、右鍵是大招、Space 是戰術、`Tab` 切換 auto-aim、`R` 回到選角重開、playing／result 的 `Esc` 回到 intro；`blur`、`visibilitychange` 和 Canvas 失去焦點時清除持續按鍵與滑鼠按壓。

**理由**：避免 React state 直接驅動每幀規則，也避免使用者切出瀏覽器後 WASD、Space 或滑鼠按鍵卡住。保留既有 controller 的語意（包含 Tab auto-aim、R restart 和右鍵 ultimate），邏輯座標固定後縮放與寬螢幕只影響相機和繪製尺寸。

### 8. 測試採單元測試、建置檢查與情境式人工驗證

**決策**：以 Vitest 覆蓋純遊戲核心的數值和狀態轉換，使用 `npm run build` 檢查 Sites 靜態建置，使用本機 preview 與私人 production URL 驗證畫面、輸入、資源和 resize。

**理由**：本功能沒有後端 API 或多人網路同步；主要風險在規則等價、瀏覽器輸入、Canvas 尺寸、資源路徑和部署後路由。這些風險由單元、建置和瀏覽器情境測試共同涵蓋。

**淘汰方案**：第一版不引入大型 E2E 框架；其安裝和維護成本高於目前單一路由遊戲的收益，且 Canvas 內的像素／動畫判斷仍需要人工觀察。

### 9. 不建立後端、帳號、持久化或外部遊戲服務

**決策**：遊戲狀態全部存在瀏覽器記憶體中；不使用資料庫、D1、R2、API route、遊戲帳號、排行榜、WebSocket 或外部遊戲服務。網站存取權由 Sites 的 owner-only/private access policy 負責，並以擁有者／未授權 session 驗證；Sites 的 hosting project id 只記在部署設定，不進入遊戲核心。

**理由**：規格只要求私人可存取的單機瀏覽器體驗。把授權交給 Sites 而不是在遊戲中重建帳號系統，可保持靜態前端、降低安全與部署複雜度，也不會誤把目前的 1 人加 5 dummy 模式擴張成線上 PvP。

### 10. 私人 Sites 發布設定

**決策**：Sites 專案使用 slug `pvpve-escape-web`、標題 `PvPvE Escape — Browser Edition`，以 production/private 方式發布；首次有意義的本機預覽確認後再產生 `public/og.png` 與頁面 metadata。`pvpve_escape_web/.openai/hosting.json` 只保存 Sites 要求的 project id 與支援的 hosting capabilities；實際 slug、URL、版本和 private access policy 記錄在部署文件。

**理由**：先確認可玩的初版，能避免把空白 starter 或失敗資源路徑公開成正式版本；Sites 的 owner-only/private access policy 符合使用者要求的發佈範圍，並讓未授權 session 在部署後可被驗證拒絕。

## 舊版行為對照

| Python/Pygame 基準 | 瀏覽器版對應 | 驗證方式 |
|---|---|---|
| `world.py` 的比賽狀態與 update 順序 | `src/game/world.ts` 的 `MatchState` 與 `updateMatch` | Vitest + 60 秒人工遊玩 |
| `models.py` 的角色、怪物、地形資料 | `src/game/types.ts`、definitions 與設定表 | 型別檢查、數值測試 |
| `models.py`、`controllers.py` 的 enum 與輸入事件 | `src/game/types.ts`、`src/game/input.ts` 的 `InputState` | WASD、滑鼠左／右鍵、Space、Tab、R、1–6、Q/W/E、失焦測試 |
| `rendering.py` 的世界、玩家頭頂資訊與瞄準 | Canvas renderer | 1280×720、縮放、固定繪製順序與效果回歸測試 |
| `rendering.py` 的固定倒數、roster、developer 與 result | React/DOM overlay + result shell | 固定邏輯座標、文案、隱私與 parity checklist |
| `assets/` PNG | `public/assets/` manifest/cache | build、資源 200、fallback 測試 |
| Python `map_editor.py` | 不納入瀏覽器版 | 規格範圍檢查 |

Python `CharacterId` 的 canonical 對照是 `BREACHER`／破陣者、`SNIPER`／狙擊者、`GUARDIAN`／守衛者、`HUNTER`／追獵者、`CONTROLLER`／控場者、`SIPHONER`／吸能者；`TacticalId` 是 `DASH`／短距離衝刺、`SHIELD`／短時間護盾、`CONTROL`／範圍控場。網頁版不得改用無法對照的泛稱 ID。

## 研究結論

規格中與平台、功能邊界、資源來源、測試方式及私人部署有關的選擇，均已在本研究中定案；實作前不再保留未決的設計項目。
