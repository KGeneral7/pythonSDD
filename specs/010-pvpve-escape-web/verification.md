# Verification：PvPvE Escape 瀏覽器版

## 驗證範圍

- 驗證日期：2026-08-30（Asia/Taipei）。
- 驗證目標：獨立的 `pvpve_escape_web/` Sites app；既有 `pvpve_escape/` Python/Pygame 版本未修改。
- 本機環境：Windows PowerShell、Node.js `v24.16.0`、npm `11.13.0`、桌面瀏覽器。

## 自動驗證

| 檢查 | 結果 |
| --- | --- |
| `npm run typecheck` | 通過 |
| `npm run test` | 通過；16 個 test files、133 個 tests |
| `npm run lint` | 通過 |
| `npm run build` | 通過；Vinext production build 產生 `dist/server/index.js` |
| 靜態資源 | 通過；角色／地圖 149 個 PNG、`public/og.png`、`public/favicon.svg` 存在 |

測試覆蓋包含：地形 24 個 deterministic 案例、怪物 24 個、撤離 26 個，以及角色攻擊、資源、輸入、HUD 隱私、auto-aim、生命週期、結果頁、resize、鏡頭移動後游標瞄準刷新、資源 fallback、初始 loading gate、Canvas focus 邊界與 Canvas 外 pointerup 釋放回歸案例。

本次回歸修正另涵蓋：Space 放開時清除 `tacticalHeld`、tactical cooldown 開始後隱藏配件瞄準預覽，以及依原版 alpha>=64 可見外框正規化 breacher 素材；sniper 保留原版 source-canvas 行為。另修正選角頁 `.role-glyph span` 誤套造成的像素角色旋轉、縮小與菱形邊線，並保留原版卡片選取框。

本次回歸修正另涵蓋：保留游標的 client 座標，於每一幀依目前 canvas rect 與 camera 重新計算 `mouseWorldPosition`，因此滑鼠停住時角色移動或鏡頭移動，視線線仍會持續對準游標。

本次回歸修正另涵蓋：App 先預載地圖與可玩角色動畫並顯示 loading 頁；載入完成或資源 fallback 完成前不顯示導覽、不接受啟動快捷鍵、不建立或更新 `MatchState`，完成後由選角與對局共用資源快取。

本次本地 code review 修正：視窗層級 keydown 只有在 Canvas 為 `document.activeElement` 時才轉成遊戲輸入；進入對局時自動聚焦 Canvas；滑鼠在 Canvas 外放開或收到 pointercancel 時會清除持續輸入，避免普攻／大招卡住。新增回歸測試後共 133 個測試通過。

## 本機 preview 人工 smoke

- URL：`http://localhost:3210/`。
- HTTP 頁面檢查：status `200`；title 為 `PvPvE Escape — Browser Edition`；頁面包含遊戲入口。
- 已完成代表性流程：intro → Enter → 選角；依序抽查六種角色與三種 tactical module 的選中狀態；Deploy 建立 6-player match；playing HUD 顯示玩家生命、彈藥、能量、強化、倒數與撤離狀態；按 `R` 回到乾淨的 loadout selection。
- Canvas 採固定 1280×720 logical resolution、16:9 contain 與 client-to-logical-to-world 座標轉換；resize、DPI、背景分頁 dt cap 與 asset fallback 另由自動測試覆蓋。

本版 loading gate 的新增瀏覽器視覺／互動 smoke 仍列在 T060、T063；目前僅以 `app-flow`、`assets` 自動測試與程式碼檢查確認「載入完成前不顯示入口、不接受開始、不建立／更新比賽」，未把它誤記為已完成的 owner production 流程。

人工測試前提：使用者已確認 loading gate／原版 parity 版本的人工測試完成且沒有問題；本次 code review 新增的輸入邊界修正已由自動化回歸、本地 build 與 Sites version 7 production deployment 驗證。

## 成功標準對照

| 標準 | 證據／結果 |
| --- | --- |
| SC-001 | 自動測試確認 loading 期間不建立比賽且完成後才釋出 intro；本機 intro／選角 smoke 通過；private production version 7 已部署。loading 頁的新增瀏覽器 smoke 仍待 T060／T063。 |
| SC-002 | 六個角色與三個 tactical module 的選取狀態可用；固定建立 6 名玩家的測試通過。 |
| SC-003 | 六種角色 attack/passive/ultimate、彈藥、能量與 tactical 行為由 combat tests 覆蓋。 |
| SC-004 | deterministic geometry、玩家／怪物／投射物、牆體／草叢／視線／鏡頭案例通過。 |
| SC-005 | deterministic ammo、regen、energy、upgrade、death/reset、respawn 與 cooldown 案例通過。 |
| SC-006 | deterministic extraction 案例 26 個，涵蓋並行、離區／死亡歸零、tie-break、優先序與 timeout。 |
| SC-007 | 16:9、resize、DPI、滑鼠座標、鏡頭移動後游標刷新與 Canvas focus 輸入邊界自動測試通過；本機代表性流程可操作。 |
| SC-008 | frame sampler 已實作並由 developer overlay 保留不可見的可及性狀態；本次未在固定硬體上完成連續 60 秒／平均 55 FPS 的正式量測，需由 owner 在目標桌面補測。 |
| SC-009 | manifest promise cache、單一 PNG 失敗、幾何／文字 fallback 與不改寫 match state 測試通過。 |
| SC-010 | restart、reload 新局、死亡清除與 result flow 測試通過；本機按 `R` 已回到乾淨選角。 |
| SC-011 | Sites version 7 deployment 成功；Sites 回應確認 `active`、owner-only policy 與 production URL。未授權 in-app Browser session 顯示「需要登入」且未取得遊戲內容；本次 code review 修正已納入 production，owner interactive production smoke 因目前瀏覽器沒有 owner 登入 session，未使用 token bypass，仍待 owner 登入後補測。 |
| SC-014 | `app-flow` 與 `assets` 自動測試確認 loading gate 未完成時維持無 `MatchState`、不接受開始操作且不推進遊戲；資源成功或 fallback 完成後才進入既有流程。 |

## 已知限制

- 這是單機 deterministic simulation：一名人類玩家加五名 dummy，不提供真正線上多人、帳號、戰績或跨頁保存。
- 本次只以已授權的本機 preview 完成既有互動 smoke；version 7 production deployment 與未授權阻擋已由 Sites／in-app Browser 狀態確認，本地 code review 修正已納入 production，production owner 的完整鍵鼠流程與 60 秒 frame sampler 仍需在已登入的 owner 瀏覽器補測。

## 本地 code review 摘要

- review 範圍涵蓋核心規則／固定 update 順序、Canvas `dt` cap 與 frame sampler、輸入 focus／blur、Canvas 外 pointerup／pointercancel、asset fallback、public/private HUD view、結果頁停止更新與 restart/reset 邊界。
- 發現並修正一項輸入生命週期問題：視窗按鍵原先未確認 Canvas focus，且 Canvas 外 mouseup 可能遺失；現在已限制鍵盤焦點、進入對局自動聚焦 Canvas，並加入 pointerup／pointercancel 清理。相對應的型別、133 個自動測試、lint、build 與 `git diff --check` 均已重跑通過。
- 這些本地 review 修正已建立 Sites version 7 saved version 並完成 production deployment；Sites source commit、封存 archive 與 saved version provenance 一致。
- 父專案 SDD 與發布紀錄已推送至功能分支，並建立 [PR #18](https://github.com/KGeneral7/pythonSDD/pull/18)；最終 PR head 為 `b3fe7ba34c8acca62431d098ebc51588263291c8`，已 squash merge 為 `e25ad21a138f81920b0dd6f75f26bfcce0aa8c0d`，並發布 `v0.8.0`。
- 未提交或覆蓋父專案的 Python/Pygame 資料；`day3/` 與 `sample.png` 等原有未追蹤使用者檔案仍保留在工作區。
- review 結論不把未登入的 production owner 流程或跨硬體 60 秒效能量測誤記為已完成；兩者已列為補測限制。
