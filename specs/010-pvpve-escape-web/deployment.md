# Deployment：PvPvE Escape 瀏覽器版

## Sites 專案

- 顯示名稱：`PvPvE Escape — Browser Edition`
- slug：`pvpve-escape-web`
- Sites project id：`appgprj_6a92ecc344a8819193bf75d3538a6642`
- `.openai/hosting.json` 已保存上述 project id；未新增 D1、R2 或 runtime secret。
- source branch：`main`
- 上一版 version 6 source commit：`6fecda427cdcf41f5d0e22a65195fe4fe1950d63`
- 目前部署 version 7 source commit：`22764ca5ec22ae9d9d4bee864181e0335d66be32`

## 存取政策

- access mode：`custom`
- current user role：`owner`
- allowed owner account：1
- workspace groups：0
- tenant groups：0
- external visitors：0
- 結論：符合 Sites owner-only/private deployment 條件；本功能未公開分享、未新增自訂網域。

## 已儲存版本與部署

- Sites version：`7`（目前 production）
- saved version id：`appgprj_6a92ecc344a8819193bf75d3538a6642~appgver_32e05061355481919bae856307594fab`
- packaged archive：由 Sites hosting `scripts/package-site.sh` 產生；archive size `49,203,200` bytes，content hash `sha256:a4e9a48835f618f88745b138c4004cb94396e224fa556fb16075e87598e4de98`。
- deployment id：`appgdep_6a93d185b56c8191bfba1b4835ede853`
- deployment status：`succeeded`
- deployment time：`2026-08-30T06:45:42.619335+00:00`（台北時間 `2026-08-30 14:45:42`）
- production URL：[https://pvpve-escape-web.innovation-s-3626.chatgpt.site](https://pvpve-escape-web.innovation-s-3626.chatgpt.site)

## 發布後狀態

Sites 回報 current live URL 與 version 7 一致，站點狀態為 `active`。未授權瀏覽器 session 只能看到 ChatGPT 登入提示，不能取得遊戲內容；owner interactive smoke 的補測紀錄見 [`verification.md`](./verification.md)。

本次修正內容：配件瞄準預覽在 Space 放開或 tactical cooldown 開始後消失；breacher 以原版 alpha 可見外框裁切，避免選角與對局角色因透明邊界而偏小；sniper source-canvas 行為保持不變；選角頁像素角色不再被 CSS 誤旋轉、縮小或加上菱形邊線；每一幀以目前游標 client 座標重新換算 `mouseWorldPosition`，視線線不再依賴 `pointermove` 才更新。

本版新增：首次開啟或重新整理先顯示 loading 頁，預載地圖與可玩角色動畫；資源完成或轉為 fallback 前不顯示導覽、不接受開始快捷鍵、不建立或更新比賽，完成後才進入既有 intro／選角流程，且選角與對局共用資源快取。

本次本地 code review 修正已納入 version 7：限制只有 Canvas 取得焦點時才接受遊戲鍵盤、進入對局時自動聚焦 Canvas，並處理 Canvas 外 pointerup／pointercancel，避免持續攻擊狀態卡住。

## 本地 code review 摘要

- 逐一檢查網站的核心規則、Canvas 更新迴圈、輸入 focus/blur、Canvas 外 pointerup／pointercancel、資源 loader、public/private view 與結果頁生命週期；發現並修正 Canvas focus 與滑鼠 release 的輸入生命週期問題。
- 網頁程式只引用 `pvpve_escape_web/` 自身的 `src/` 與 `/assets/`；未引用父專案 Python、Pygame、桌面地圖編輯器、本機服務或外部 runtime secret。
- version 7 的 Sites source、build archive、saved version commit provenance 一致；本地 review 修正已以 `typecheck`、133 個 tests、lint、build 與 `git diff --check` 驗證，並完成 version 7 production deployment。
- review 保留兩項已知限制：production owner interactive smoke 需要已登入的 owner browser session；SC-008 以其他硬體／瀏覽器的長時間效能仍應由 owner 補測。未為了清除限制而宣稱未執行的結果。

## 父專案 PR 狀態

- Sites source 已獨立推送並完成 version 7 production deployment；父專案的 `010-pvpve-escape-web` 文件變更已推送，並建立 [PR #18](https://github.com/KGeneral7/pythonSDD/pull/18)。
- PR #18 最終 head commit 為 `b3fe7ba34c8acca62431d098ebc51588263291c8`，已於 `2026-08-30T07:20:16Z` squash merge 至 `main`，合併 commit 為 `e25ad21a138f81920b0dd6f75f26bfcce0aa8c0d`。
- 父專案已建立 [v0.8.0 Release](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.8.0)；功能分支的遠端／本地清理刻意延後，因工作區仍有 `day3/`、`sample.png` 與 Sites nested repository 等未追蹤使用者內容，待可安全使用隔離工作樹時再處理。
- 使用者已確認人工測試完成且沒有問題；本地 code review、Sites 發布與父專案文件提交均保留既有 Python/Pygame 與未追蹤使用者檔案。

## 回滾

目前已保存 version 1 至 version 7，production 指向 version 7。後續版本應沿用相同 project id，先推送對應 source commit、用成功 build 封存，再以 Sites saved version 進行部署；不得直接部署未儲存版本。
