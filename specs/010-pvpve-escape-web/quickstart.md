# Quickstart：PvPvE Escape 瀏覽器版

## 前置條件

- Windows PowerShell。
- Node.js 與 npm；規劃時確認版本為 Node `v24.16.0`、npm `11.13.0`。
- 可使用鍵盤與滑鼠的桌面瀏覽器。
- 網頁版本身不需要安裝 Python 或 Pygame；父專案的 Python 測試仍依既有流程執行。

## 安裝與本機開發

從 repository 根目錄執行：

```powershell
Set-Location .\pvpve_escape_web
npm install
npm run dev
```

開啟 Vinext dev server 顯示的本機 URL。預期先看到 loading 頁；地圖與角色資料尚未完成載入前，不顯示導覽／選角、不接受 Enter／Space 等開始操作，也不建立或更新比賽。所有載入嘗試完成（失敗資源已切換為 fallback）後，才看到與原版 `rendering.draw_intro()` 相同的 1280×720 比例導覽；按 Enter／Space 或導覽文字入口後可以進入選角畫面。

## 自動驗證

```powershell
Set-Location .\pvpve_escape_web
npm run typecheck
npm run test
npm run build
```

預期結果：型別檢查、核心規則、玩家／怪物生命週期、瞄準、撤離、輸入與原版 parity fixture 測試通過；production build 成功，且輸出不需要父專案 Python、Pygame 或執行中的本機服務。

## 代表性人工情境

1. **載入、啟動與選擇**：重新整理或首次開啟時先確認顯示 loading 頁；在資料準備完成前按 Enter／Space 不會進入導覽、選角或建立比賽。載入完成後才從網頁導覽以 Enter／Space 進入選角，使用滑鼠或 `1`–`6` 選角色、`Q`/`W`/`E` 選戰術，確認六個角色和三個戰術都能選取，開始後建立 1 名人類加 5 名不自主移動／攻擊的 dummy。
2. **移動與視窗**：進入 playing 後確認 Canvas 已取得焦點，再使用 WASD、滑鼠、左鍵普攻、右鍵大招、Space 戰術；用 `Tab` 切換 auto-aim、`R` 重新開始，調整 1024×576、1280×720 及更寬視窗，確認畫面比例、相機和滑鼠瞄準一致；在 Canvas 外放開滑鼠、切出瀏覽器或取消指標後，確認按鍵與攻擊不會卡住。
3. **角色與戰鬥**：依序抽查六種角色的數值、武器、彈藥自動恢復、能量、升級和三種戰術，確認攻擊與效果可用，且只在原版授權的動作中破壞薄牆。
4. **PvE 與地形**：確認四個營地各有 chaser、shooter、brute，怪物能導航／攻擊；障礙、薄牆／草叢互動、投射物、生命回復和死亡規則可觀察，並核對 18 個原始矩形與 150 個正規化地形格。
5. **撤離與開發者模式**：等待或用 F1 debug 輔助確認 210 秒後撤離開放、10 秒進度與 240 秒上限；檢查 1–5 選取假玩家、M 放入中央撤離區、N 返回出生點及結果頁，並在 playing 開始後以 frame sampler 連續記錄 60 秒，確認 `frameCount / elapsedSeconds` 平均至少 55 FPS。
6. **資源 fallback**：以開發環境中的失效資源路徑驗證，單一 PNG 失敗時出現色彩／文字幾何替代，不發生整頁白屏。
7. **原版畫面 parity**：在 `1280×720` 邏輯座標檢查導覽三欄、選角三欄角色卡／戰術列、對局右上倒數／右下 roster、F1 文字與結果面板；確認沒有額外 web-only header、footer、Toast、HUD 卡片或撤離圓環。

## 發布前驗證

1. `npm run typecheck`、`npm run test` 和 `npm run build` 成功。
2. 本機 preview 完成至少一個從 intro 到結果頁或重新開始的流程。
3. 建立 Sites 專案並將實際 project id 寫入 `.openai/hosting.json`。
4. 以 slug `pvpve-escape-web` 建立私人 production，設定 Sites owner-only/private access policy；記錄實際部署版本和 URL。
5. 以已授權擁有者與未授權瀏覽器 session 分別驗證 production URL：前者可重跑啟動、輸入、resize、資源、撤離和結果，後者不得取得網站內容；確認未引用父專案路徑或本機服務。
