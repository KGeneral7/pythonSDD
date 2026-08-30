---
description: "PvPvE Escape 瀏覽器版的可執行任務清單"
---

# 任務：PvPvE Escape 瀏覽器版

**輸入**：`specs/010-pvpve-escape-web/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md`、`contracts/` 與 `quickstart.md`

**前置條件**：先完成規格、研究、資料模型、UI 契約與實作計畫；既有 `pvpve_escape/` Python/Pygame 版本只作為行為基準，不在本任務中改寫。

**測試策略**：功能規格提供獨立測試情境與成功標準，因此每個 User Story 都包含先行的 Vitest 任務；另外以本機 preview、build 和私人 Sites URL 執行人工情境。

**路徑慣例**：本功能是獨立 web app，所有網頁程式、測試和建置設定位於 `pvpve_escape_web/`；SDD 文件位於 `specs/010-pvpve-escape-web/`。

## 任務格式

每個實作任務都使用 `- [ ] [TaskID] [P?] [Story?] 描述與檔案路徑` 格式：`[P]` 表示可在沒有未完成依賴時平行執行，`[US#]` 對應功能規格中的 User Story。

## Phase 1：Setup（共用基礎設施）

**目的**：建立獨立的 Sites／React／TypeScript／Vite 專案邊界，不影響父專案。

- [X] T001 建立 `pvpve_escape_web/package.json`，加入 React、Vinext、Vite、TypeScript、Sites、shadcn/ui、`lucide-react`、Vitest 依賴與 `dev`、`build`、`preview`、`test`、`typecheck` scripts
- [X] T002 [P] 建立 `pvpve_escape_web/tsconfig.json`、`pvpve_escape_web/vite.config.ts`、`pvpve_escape_web/vitest.config.ts` 與 `pvpve_escape_web/next.config.ts`，設定 Vinext 單一路由、TypeScript 編譯、Vitest 與 Sites Vite plugin
- [X] T003 [P] 建立 `pvpve_escape_web/app/layout.tsx`、`pvpve_escape_web/app/page.tsx`、`pvpve_escape_web/src/app/App.tsx` 與 `pvpve_escape_web/src/app/styles.css`，提供可掛載的 React shell、全域樣式與非空白初始畫面

## Phase 2：Foundational（所有 User Story 的阻塞前置）

**目的**：完成可被所有故事共用的核心資料、規則、座標、輸入和比賽更新邊界；本階段未完成前不開始故事整合。

- [X] T004 定義 `pvpve_escape_web/src/game/types.ts` 的 `ScreenPhase`、四值 `MatchPhase`、`alive/dead` 玩家狀態、canonical 角色／戰術／怪物 enum、幾何型別、`GameState`、`MatchState`、玩家／怪物／投射物／地形／輸入／相機、`FrameSamplerState`、`AimGuide` 與 public/private view 型別
- [X] T005 定義 `pvpve_escape_web/src/game/config.ts` 的 2400×1400 世界、1280×720 邏輯畫布、6 名玩家、12 隻怪物、4 個營地、中央 `(1200,700)`／半徑 140 撤離區、150 個地形格、240 秒比賽、210 秒撤離開放、10 秒撤離、5 秒生命回復延遲、每秒 10% 最大生命回復、5 秒玩家重生、6 秒怪物重生、0.20 秒 auto-aim lookback、0.05 秒 dt 上限、3% 強化倍率與所有數值邊界常數
- [X] T006 [P] 實作 `pvpve_escape_web/src/game/vector.ts` 與 `pvpve_escape_web/src/game/geometry.ts` 的向量、矩形／圓形碰撞、世界邊界裁切、邏輯座標與世界座標轉換
- [X] T007 [P] 建立 `pvpve_escape_web/tests/test-utils.ts` 與 `pvpve_escape_web/tests/model-boundaries.test.ts`，提供 deterministic seed、固定時間和狀態邊界測試工具，先鎖定玩家、怪物、營地與數值不變量
- [X] T008 實作 `pvpve_escape_web/src/game/rules.ts` 的 clamp、傷害／護盾／減傷、五秒離戰生命回復、能量、自動逐發補彈、冷卻、最後有效傷害歸屬、每層 3% 強化、死亡清除與時間工具
- [X] T009 [P] 實作 `pvpve_escape_web/src/game/characters.ts` 的 canonical 六角色與三種戰術定義，包含六種普攻形態、被動、大招、彈匣 2–4 發、0.2–0.8 秒自動補彈間隔、能量成本與 12 秒冷卻
- [X] T010 [P] 實作 `pvpve_escape_web/src/game/terrain.ts` 的世界邊界、厚牆、可破壞薄牆、Bush、中央撤離區與四個怪物生成區資料；只保留 Python 基準已定義的牆體／草叢互動
- [X] T011 [P] 實作 `pvpve_escape_web/src/game/monsters.ts` 的 chaser、shooter、brute 定義，以及四個營地各一組三隻怪物的初始狀態 factory
- [X] T012 實作 `pvpve_escape_web/src/game/navigation.ts` 的障礙感知路徑、被阻擋時繞行、營地遊蕩點與追擊／保持攻擊距離所需的導航查詢
- [X] T013 [P] 實作 `pvpve_escape_web/src/game/aiming.ts` 與 `pvpve_escape_web/src/game/autoAim.ts` 的角度、射線、攻擊範圍、投射物初速、0.20 秒 lookback 位置選擇與施放後不追蹤規則
- [X] T014 實作 `pvpve_escape_web/src/game/input.ts` 的 `InputState`、WASD／滑鼠左鍵普攻／右鍵大招／Space 戰術／Tab auto-aim／R restart／Esc／F1／1–5／M／N／Enter／選角 1–6 與 Q/W/E 事件轉接、pressed 一次性消費與 blur／visibilitychange 清除
- [X] T015 [P] 建立 `pvpve_escape_web/tests/rules.test.ts` 與 `pvpve_escape_web/tests/world.test.ts`，覆蓋規則數值、初始集合、固定 update 順序、世界邊界和重新建立新 seed 的預期行為
- [X] T016 實作 `pvpve_escape_web/src/game/world.ts` 的 `createMatch`、`updateMatch`、公共／私人 view 查詢、四值 match phase、固定更新順序、最後傷害玩家／`winnerId`、玩家／怪物／投射物集合和 deterministic seed 協調器
- [X] T017 執行 `npm run typecheck` 與 `npm run test`（腳本位於 `pvpve_escape_web/package.json`），修正 Phase 2 的型別、匯入和核心基準測試，確認不依賴 React、DOM、Python 或 Pygame

**檢查點**：核心可在沒有 Canvas 或 React 的測試環境建立 6 名玩家、12 隻怪物與 4 個營地，並依固定順序更新。

## Phase 3：User Story 1 - 從私有網址進入並開始比賽（優先級：P1）🎯 MVP

**目標**：測試者能從網站導覽進入選角，選擇六種角色／三種戰術中的項目，開始一局 1 名人類加 5 名固定 dummy 的比賽。

**獨立測試**：在本機 preview 開啟 intro，使用滑鼠與鍵盤走過導覽和選角；分別抽查六種角色與三種戰術，開始後確認玩家集合為 6 筆，重新整理後沒有沿用上一局狀態。

### User Story 1 測試（先行）

- [X] T018 [P] [US1] 在 `pvpve_escape_web/tests/app-flow.test.ts` 撰寫 intro、Enter／Space、角色 1–6、戰術 Q/W/E、Enter 確認、六名玩家建立、選擇套用、R 回選角與重新整理新狀態的測試

### User Story 1 實作

- [X] T019 [P] [US1] 實作 `pvpve_escape_web/src/app/gameSession.ts` 的畫面階段 reducer、選角／戰術 session、開始比賽、重新開始和舊 match 清除
- [X] T020 [P] [US1] 實作 `pvpve_escape_web/src/components/IntroScreen.tsx`，顯示標題、勝利目標、玩法、主要控制和開始按鈕／Enter 操作
- [X] T021 [P] [US1] 實作 `pvpve_escape_web/src/components/CharacterSelect.tsx`，由角色／戰術 definitions 產生六種角色、三種戰術、選中狀態、說明與開始提示
- [X] T022 [US1] 在 `pvpve_escape_web/src/app/App.tsx` 串接 `gameSession`、`IntroScreen` 和 `CharacterSelect`，確認選擇有效後呼叫 `createMatch` 並切換到 playing shell
- [X] T023 [US1] 在 `pvpve_escape_web/src/game/world.ts` 完成玩家 0 套用人類選擇、玩家 1–5 使用其餘不同角色／有效戰術，以及六筆初始玩家狀態的驗證

**檢查點**：此故事可獨立由 intro 走到一局已建立的比賽；按重新整理或重新開始後生命、能量、強化、彈藥、地形與撤離資料均為新狀態。

## Phase 4：User Story 2 - 在瀏覽器中探索地圖並進行完整戰鬥（優先級：P1）

**目標**：玩家能在 Canvas 中用鍵盤／滑鼠移動、瞄準、普攻、使用大招和三種戰術，並體驗六種角色的不同攻擊與成長。

**獨立測試**：用 deterministic match 或 playing harness 直接載入每種角色，執行移動、左鍵普攻、右鍵大招、Space 戰術、蓄力／持續攻擊、彈藥消耗與能量累積，確認角色差異和失焦清除。

### User Story 2 測試（先行）

- [X] T024 [P] [US2] 在 `pvpve_escape_web/tests/combat.test.ts` 撰寫六種角色攻擊形態、被動、大招、左鍵普攻／右鍵大招、彈藥自動恢復、能量、最後有效傷害歸屬、每層 3% 強化、傷害和持續／蓄力攻擊結束測試
- [X] T025 [P] [US2] 在 `pvpve_escape_web/tests/input.test.ts` 撰寫 WASD、滑鼠座標、左鍵普攻、右鍵大招、Space 戰術、R 重新開始、Tab auto-aim、Esc、失焦清除和最大 dt 測試

### User Story 2 實作

- [X] T026 [US2] 在 `pvpve_escape_web/src/game/world.ts` 與 `pvpve_escape_web/src/game/rules.ts` 完成玩家移動、世界邊界、武器 cooldown、自動補彈、左鍵普攻／右鍵大招／Space 戰術觸發、能量累積與傷害事件套用
- [X] T027 [P] [US2] 實作 `pvpve_escape_web/src/game/renderer.ts` 的邏輯 1280×720 Canvas、相機跟隨、世界／玩家／投射物／攻擊效果的幾何繪製、基本命中回饋與 60 秒 frame sampler 狀態
- [X] T028 [US2] 實作 `pvpve_escape_web/src/components/GameCanvas.tsx` 的 `requestAnimationFrame`、`performance.now()`、0.05 秒 dt cap、input snapshot、`updateMatch` 呼叫與每幀 render
- [X] T029 [US2] 實作 `pvpve_escape_web/src/components/PlayingScreen.tsx`，掛載 GameCanvas、遊戲焦點容器、鍵盤提示、死亡／更新狀態提示和回到 App 的 playing 介面
- [X] T030 [US2] 在 `pvpve_escape_web/src/app/App.tsx` 將 playing phase 接到 `PlayingScreen`，確保進入遊戲後不再渲染空白 shell，且可以安全離開更新迴圈
- [X] T031 [US2] 在 `pvpve_escape_web/src/game/characters.ts` 與 `pvpve_escape_web/src/game/world.ts` 完成破陣者、狙擊者、守衛者、追獵者、控場者、吸能者的六組差異化攻擊、被動和大招效果

**檢查點**：至少可從 US1 進入 playing，使用 WASD／滑鼠／Space 完成一段戰鬥；六種角色的攻擊形狀、彈藥、能量與冷卻可由測試和畫面辨識。

## Phase 5：User Story 3 - 讀懂敵人、地形與自身戰鬥狀態（優先級：P1）

**目標**：玩家能辨認三種怪物、理解地形互動、使用 auto-aim 預覽，並在不洩漏他人私有資源的情況下讀取自己的 HUD。

**獨立測試**：從固定 seed 的比賽觀察四個營地的三種怪物，移動穿越／攻擊厚牆、薄牆和草叢，切換 debug 檢視，讓人類玩家受傷、補彈、回復、死亡和重生，核對世界與 HUD。

### User Story 3 測試（先行）

- [X] T032 [P] [US3] 在 `pvpve_escape_web/tests/monsters.test.ts` 撰寫至少 20 個 deterministic 案例，覆蓋四營地、三種怪物、追擊／保持距離、繞行、投射物、最後傷害玩家和原地六秒重生
- [X] T033 [P] [US3] 在 `pvpve_escape_web/tests/terrain.test.ts` 撰寫至少 20 個 deterministic 案例，覆蓋厚牆阻擋、薄牆／草叢單格破壞、草叢可見資訊、邊界、視線和地形重置
- [X] T034 [P] [US3] 在 `pvpve_escape_web/tests/hud.test.ts`、`pvpve_escape_web/tests/aiming.test.ts` 與 `pvpve_escape_web/tests/health.test.ts` 撰寫 public/private HUD 隱私、三種怪物辨識、0.20 秒 lookback、施放後不追蹤、瞄準預覽、五秒離戰生命回復與死亡狀態測試

### User Story 3 實作

- [X] T035 [US3] 在 `pvpve_escape_web/src/game/monsters.ts`、`pvpve_escape_web/src/game/navigation.ts` 與 `pvpve_escape_web/src/game/world.ts` 完成三種怪物 AI、四個營地行為、攻擊距離、繞行、死亡與六秒重生
- [X] T036 [US3] 在 `pvpve_escape_web/src/game/terrain.ts`、`pvpve_escape_web/src/game/geometry.ts` 與 `pvpve_escape_web/src/game/world.ts` 完成厚牆、薄牆／草叢單格破壞、草叢可見性和碰撞解析；角色技能的 slow／root 維持在角色規則
- [X] T037 [US3] 在 `pvpve_escape_web/src/game/aiming.ts`、`pvpve_escape_web/src/game/autoAim.ts` 與 `pvpve_escape_web/src/game/renderer.ts` 完成瞄準線、範圍、飛行路徑、回看位置、命中回饋與投射物固定路徑
- [X] T038 [US3] 在 `pvpve_escape_web/src/game/world.ts`、`pvpve_escape_web/src/components/Hud.tsx` 與 `pvpve_escape_web/src/game/renderer.ts` 完成自己的完整 HUD、其他玩家 public view、生命／彈藥／能量／強化／狀態同步與隱私邊界
- [X] T039 [US3] 在 `pvpve_escape_web/src/game/world.ts`、`pvpve_escape_web/src/components/DeveloperOverlay.tsx` 與 `pvpve_escape_web/src/game/renderer.ts` 完成 F1 開關、1–5 選取假玩家、M 放入中央撤離區、N 返回出生點、原版 developer overlay 與不可見 frame sampler 狀態，並隔離正常 HUD
- [X] T040 [US3] 在 `pvpve_escape_web/src/components/PlayingScreen.tsx` 串接怪物、地形、HUD、developer overlay、生命回復、死亡／重生和資源狀態提示，完成故事的瀏覽器畫面整合

**檢查點**：玩家可在同一局辨認所有怪物／地形／狀態；自己的私有數值完整，其他玩家不顯示完整資源，debug 功能不改寫一般撤離規則。

## Phase 6：User Story 4 - 在中央撤離區爭取勝利（優先級：P1）

**目標**：玩家能在最後 30 秒進入中央撤離區，獨立累積 10 秒進度並依固定規則得到唯一勝負結果。

**獨立測試**：以固定時間或 developer mode 將一名／多名玩家放入撤離區，驗證單人進度、同區並行、個別離場／死亡歸零、同幀固定順序裁決、撤離優先於時間到及無人勝利。

### User Story 4 測試（先行）

- [X] T041 [P] [US4] 在 `pvpve_escape_web/tests/extraction.test.ts` 撰寫至少 20 個 deterministic 案例，覆蓋 210 秒開放、10 秒進度、個別進度、離區／死亡清除、同區並行、同幀 tie-break、撤離優先與 240 秒上限
- [X] T042 [P] [US4] 在 `pvpve_escape_web/tests/result-flow.test.ts` 撰寫人類勝利、無人勝利、結果頁停止上一局 update、Enter／再玩一次回選角、Esc 回 intro 與重新開始流程測試

### User Story 4 實作

- [X] T043 [US4] 在 `pvpve_escape_web/src/game/rules.ts` 與 `pvpve_escape_web/src/game/world.ts` 完成剩餘 30 秒啟用撤離、每名玩家獨立 10 秒進度、離區／死亡歸零、撤離優先、固定 playerId tie-break 與 `winnerId`
- [X] T044 [US4] 在 `pvpve_escape_web/src/game/world.ts` 與 `pvpve_escape_web/src/game/rules.ts` 完成死亡清除強化／能量／持續效果／撤離進度、五秒安全重生和重生後可重新遊玩
- [X] T045 [US4] 在 `pvpve_escape_web/src/game/input.ts` 與 `pvpve_escape_web/src/game/world.ts` 實作 developer mode 的 M（放入中央撤離區）與 N（返回出生點）測試控制，且不繞過正式撤離規則
- [X] T046 [US4] 在 `pvpve_escape_web/src/components/ResultScreen.tsx`、`pvpve_escape_web/src/app/gameSession.ts` 與 `pvpve_escape_web/src/components/PlayingScreen.tsx` 實作勝利／無人勝利結果、停止 animation loop、摘要、再玩一次回選角和 Esc 回 intro
- [X] T047 [US4] 在 `pvpve_escape_web/src/app/App.tsx` 串接 victory／no-winner match phase、唯一勝者訊息、時間到訊息與 `ResultScreen`，確保上一局不會在結果頁繼續更新

**檢查點**：可用不等待四分鐘的 deterministic 測試重現所有撤離邊界；人工從 playing 到結果頁後，重新開始會建立乾淨的新局。

## Phase 7：User Story 5 - 在不同桌面瀏覽器尺寸中穩定使用（優先級：P2）

**目標**：網站在 1024×576、1280×720 與更寬桌面視窗維持 16:9、可讀 HUD、正確滑鼠座標和資源失敗 fallback。

**獨立測試**：以本機 preview 和 production-like build 在三種 viewport 完成導覽、選角、移動、攻擊與結果；令單一 PNG 失效、切換背景分頁和失去焦點，確認仍可玩且不會出現時間跳躍或白屏。

### User Story 5 測試（先行）

- [X] T048 [P] [US5] 在 `pvpve_escape_web/tests/resize-input.test.ts` 撰寫 Canvas bounding rect、邏輯／世界座標、高 DPI、1024×576／1280×720 比例、背景分頁 dt cap、R restart 和 focus loss 測試
- [X] T049 [P] [US5] 在 `pvpve_escape_web/tests/assets.test.ts` 撰寫 manifest 路徑、載入快取、單一 PNG 失敗幾何 fallback、資源錯誤不清除規則狀態和重新開始測試

### User Story 5 實作

- [X] T050 [US5] 將 `pvpve_escape/assets/` 的角色／地圖 PNG 複製到 `pvpve_escape_web/public/assets/`，並建立 `pvpve_escape_web/src/assets/manifest.ts` 的穩定資源清單與 URL 對應
- [X] T051 [US5] 實作 `pvpve_escape_web/src/assets/loader.ts` 與 `pvpve_escape_web/src/game/renderer.ts` 的 promise cache、解碼錯誤處理、角色色彩／文字幾何 fallback 和非侵入式 warning
- [X] T052 [US5] 在 `pvpve_escape_web/src/components/GameCanvas.tsx`、`pvpve_escape_web/src/app/styles.css` 與 `pvpve_escape_web/src/game/input.ts` 完成 16:9 contain、Canvas resize／DPI、viewport 變更和 client-to-logical-to-world 座標校正
- [X] T053 [US5] 在 `pvpve_escape_web/src/components/IntroScreen.tsx`、`pvpve_escape_web/src/components/CharacterSelect.tsx`、`pvpve_escape_web/src/components/ResultScreen.tsx` 與 `pvpve_escape_web/src/app/App.tsx` 完成原生可聚焦控制項、aria 名稱／選中狀態、focus 樣式、錯誤訊息和鍵盤流程
- [X] T054 [US5] 在本機 preview 已完成有意義可玩流程後，更新 `pvpve_escape_web/app/layout.tsx` 的 title／description／metadata，並建立 `pvpve_escape_web/public/og.png`、favicon 等靜態分享資源
- [X] T055 [US5] 在 `pvpve_escape_web/src/app/App.tsx`、`pvpve_escape_web/src/components/PlayingScreen.tsx` 與 `pvpve_escape_web/src/assets/loader.ts` 完成失敗載入、重新整理、重新開始、背景分頁恢復和非空白錯誤畫面的整合驗證

**檢查點**：三種桌面 viewport 均可完成主要流程；資源失敗只替換外觀，不改變 match state，也不阻止遊戲和重新開始。

## Phase 8：Polish 與跨故事驗證／發布

**目的**：完成整體回歸、文件、建置、private Sites 設定與部署後 smoke test。

- [X] T056 [P] 在 `pvpve_escape_web/package.json` 與 `pvpve_escape_web/tsconfig.json` 完成 typecheck、test、build、preview scripts 和 production 相對資源路徑檢查
- [X] T057 [P] 在 `pvpve_escape_web/README.md` 記錄 Node/npm 前置條件、本機開發、測試、build、preview、輸入方式與父專案不依賴邊界
- [X] T058 [P] 執行 `npm run test`（`pvpve_escape_web/package.json`），修正跨故事的規則、輸入、隱私、撤離、資源與回歸測試失敗
- [X] T059 [P] 執行 `npm run build` 並檢查 `pvpve_escape_web/dist/`，確認沒有父專案相對路徑、未處理 import、遺失靜態資源或 Python/Pygame 執行依賴
- [ ] T060 [P] 依 `specs/010-pvpve-escape-web/quickstart.md` 執行本機人工情境，將瀏覽器、作業系統、viewport、代表性流程、frame sampler 連續 60 秒且平均至少 55 FPS 的結果、SC-004～SC-006 各至少 20 個案例、fallback 與已知限制記錄到 `specs/010-pvpve-escape-web/verification.md`；目前只有不含正式 60 秒 FPS 量測的本機 smoke 已記錄
- [X] T061 建立 Sites 專案、設定 owner-only/private access policy，將 Sites 要求的 project id 與支援 capabilities 保存到 `pvpve_escape_web/.openai/hosting.json`，並把實際 slug 與 access policy 記錄到 `specs/010-pvpve-escape-web/deployment.md`
- [X] T062 發布 `pvpve_escape_web/` 的 private production Sites 版本，並在 `specs/010-pvpve-escape-web/deployment.md` 記錄實際 URL、部署版本、授權方式、權限狀態與部署時間
- [ ] T063 在私人 production URL 以已授權擁有者與未授權瀏覽器 session 分別重跑 `specs/010-pvpve-escape-web/quickstart.md` 的啟動、選角、戰鬥、resize、資源 fallback、撤離、結果、重新整理流程，將 smoke test 結果補入 `specs/010-pvpve-escape-web/verification.md`
- [ ] T064 在 `specs/010-pvpve-escape-web/deployment.md` 與 `specs/010-pvpve-escape-web/verification.md` 完成本地 code review 摘要，將 `010-pvpve-escape-web` 分支推送至遠端並建立指向 `specs/010-pvpve-escape-web/` 的 PR；PR 合併前保留本地／遠端分支，只有確認合併後才清理

## Phase 9：原版 1:1 parity closure

本階段是使用者要求「100% 還原」後新增的收斂階段；它將驗收基準定為對 `pvpve_escape` 最新程式與 `rendering.py` 固定邏輯座標的逐項對照。`map_editor.py` 仍不納入瀏覽器遊戲。

- [X] T065 [P] [US1] [US3] 在 `pvpve_escape_web/src/game/config.ts`、`src/game/terrain.ts` 與 `tests/original-parity.test.ts` 鎖定 `2400×1400` 世界、`1280×720` 邏輯表面、6 個玩家出生點、4 個營地、18 個原始矩形，以及 36 厚牆／22 薄牆／92 草叢／150 地形格的 parity fixture（對應 FR-032、FR-033、SC-012）
- [X] T066 [US2] [US4] 在 `pvpve_escape_web/src/game/characters.ts`、`src/game/rules.ts` 與 `src/game/world.ts` 對齊六角色 action、被動欄位、技能預設地形互動、dummy 不自主移動／攻擊、更新順序、死亡／重生、撤離與結果裁決（對應 FR-034、FR-035）
- [X] T067 [US3] 在 `pvpve_escape_web/src/game/monsters.ts`、`src/game/navigation.ts`、`src/game/terrain.ts` 與 `src/game/world.ts` 對齊三種怪物、營地遊蕩／追擊／保持距離、A* 繞行、怪物投射物、草叢可見性與原版重生計時（對應 FR-033、FR-034）
- [X] T068 [US2] [US3] 在 `pvpve_escape_web/src/game/input.ts`、`src/game/aiming.ts`、`src/game/autoAim.ts`、`src/game/renderer.ts` 與 `src/components/GameCanvas.tsx` 對齊滑鼠邏輯座標、0.20 秒 lookback、自動瞄準、動畫幀／方向、命中路徑與失焦清除（對應 FR-013～FR-015、FR-035）
- [X] T069 [US1] [US3] [US4] 在 `pvpve_escape_web/src/components/IntroScreen.tsx`、`pvpve_escape_web/src/components/CharacterSelect.tsx`、`pvpve_escape_web/src/components/Hud.tsx`、`pvpve_escape_web/src/components/DeveloperOverlay.tsx`、`pvpve_escape_web/src/components/PlayingScreen.tsx`、`pvpve_escape_web/src/components/ResultScreen.tsx`、`pvpve_escape_web/src/app/styles.css` 與 `pvpve_escape_web/src/game/renderer.ts` 對齊原版固定繁體中文文案、1280×720 UI 區域、Canvas／DOM 繪製層級、玩家列表、死亡倒數與結果面板，並移除額外可見 web-only HUD（對應 FR-032、FR-036、SC-013）
- [X] T070 [P] [US1] [US2] [US3] [US4] 在 `pvpve_escape_web/tests/original-parity.test.ts` 補齊初始 roster／地形／營地、dummy 靜止、角色 action、撤離邊界與 lookback marker 的 deterministic parity 測試，並以 `npm run typecheck`、`npm run lint`、`npm run test -- --run` 回歸（對應 SC-004、SC-006、SC-012）
- [X] T071 [US5] 在 `pvpve_escape_web/` 完成 parity closure 後執行 `npm run build`、Sites source commit／push、既有 private project 的 saved version／deployment，並把新版本／部署結果同步到 `specs/010-pvpve-escape-web/deployment.md` 與 `verification.md`（對應 FR-031、SC-011）
- [X] T072 [P] 在 `specs/010-pvpve-escape-web/spec.md`、`plan.md`、`quickstart.md`、`data-model.md` 與 `tasks.md` 同步 1:1 parity 基準、必要的瀏覽器 Esc 適配、`map_editor.py` 邊界與外部 production smoke test 的未完成條件

## Phase 10：初始資料 loading gate 修正

本階段是針對使用者回饋新增的啟動邊界修正：資料載入完成前只顯示 loading 頁，不顯示可開始入口、不接受啟動快捷鍵、不建立或更新比賽；完成所有載入嘗試後才回到既有 intro 流程。

- [X] T073 [P] [US1] 在 `pvpve_escape_web/tests/app-flow.test.ts` 與 `pvpve_escape_web/tests/assets.test.ts` 補充 loading 期間無 `MatchState`、無開始操作，以及地圖／兩種可玩角色素材完整預載後才釋出的測試（對應 FR-037、SC-001、SC-014）
- [X] T074 [US1] 在 `pvpve_escape_web/src/components/LoadingScreen.tsx`、`src/app/App.tsx`、`src/assets/loader.ts`、`src/components/CharacterSelect.tsx`、`src/components/PlayingScreen.tsx` 與 `src/app/styles.css` 實作一次性資源 loading gate；載入期間阻止外層快捷鍵與比賽建立，完成或 fallback 後共用資產進入既有流程（對應 FR-028、FR-037）
- [X] T075 [US5] 執行 `npm run typecheck`、`npm run lint`、`npm run test`、`npm run build`、Sites saved version 6 與 private deployment，並同步 `verification.md`／`deployment.md`（對應 SC-011、SC-014）

## Phase 11：本地 code review 輸入邊界修正

本階段依人工測試完成後的 code review 收斂輸入生命週期：Canvas 取得焦點後才接受遊戲鍵盤，且滑鼠在 Canvas 外放開或被瀏覽器取消時不會留下持續攻擊狀態；修正完成後以新的 Sites version 重新發布。

- [X] T076 [US2] 審查並修正 `pvpve_escape_web/src/components/GameCanvas.tsx` 與 `pvpve_escape_web/src/game/input.ts` 的 Canvas focus、視窗 keydown、pointerup／pointercancel 與 listener cleanup 邊界；進入對局時自動聚焦 Canvas，只有真正聚焦時才接受遊戲鍵盤（對應 FR-013、SC-003、SC-005）
- [X] T077 [P] [US2] 在 `pvpve_escape_web/tests/input.test.ts` 補充未聚焦 Canvas 不接受鍵盤，以及視窗層級 pointerup 會釋放按住狀態的回歸測試（對應 FR-013、SC-005）
- [X] T078 [US5] 執行本地 `npm run typecheck`、`npm run lint`、`npm test`、`npm run build` 與 `git diff --check`，並把 review 發現、修正、133 個測試與 version 7 saved version／production deployment 狀態同步到 `verification.md`／`deployment.md`（對應 SC-011）

## 依賴與執行順序

### 階段依賴

- **Phase 1 Setup**：無前置依賴；T001 完成後 T002、T003 可平行處理。
- **Phase 2 Foundational**：依賴 Phase 1；T004–T014 建立核心邊界，T015–T017 鎖定並驗證核心；完成前不開始完整故事整合。
- **User Story 1**：依賴 Phase 2；T018–T023 可先完成最小導覽／選角 MVP。
- **User Story 2**：核心測試與 renderer 可在 Phase 2 後開始；T030 的 App 整合依賴 US1 的 T022，完整 playing 流程與 US1 合併驗證。
- **User Story 3**：測試可在 Phase 2 後開始；怪物／地形／HUD 畫面整合依賴 US2 的 T026–T030，且可和 US2 的非整合核心任務平行。
- **User Story 4**：撤離核心依賴 T016、T026；developer positioning 依賴 T039，結果畫面依賴 T022、T030，完整結果流程在 US2／US3 基本畫面完成後驗證。
- **User Story 5**：資源與座標測試可在 Phase 2 後開始；完整 responsive、fallback 和可及性驗證依賴 US1–US4 的畫面整合。
- **Polish／發布**：T056–T060 依賴所有要發布的故事完成；T061–T063 依賴 build、preview 與人工 smoke test 通過；T064 依賴 production 驗證完成並遵循 PR 合併後才清理分支的治理規則。
- **Parity closure**：T065–T070 可在既有故事核心完成後平行核對；T069 依賴 Canvas／DOM 整合；T071 依賴 T065–T070、build 與 Sites 現有 project；T063 仍是需已授權／未授權瀏覽器 session 的外部驗證，T064 仍受 PR／合併治理流程約束。
- **初始 loading gate**：T073 → T074 → T075；T075 依賴 loading gate 的自動測試、成功 build、Sites source push、saved version 與 private deployment 完成。
- **本地 code review 輸入邊界**：T076 → T077 → T078；T078 依賴本地驗證、文件同步與 version 7 saved version／production deployment。

### User Story 完成順序

1. **US1（P1）**：最小可交付入口；建立可重新開始的 6 人比賽。
2. **US2（P1）**：接上可玩的瀏覽器戰鬥與六角色差異。
3. **US3（P1）**：補齊怪物、地形、自動瞄準、HUD 和開發者檢視。
4. **US4（P1）**：接上撤離、唯一勝者、時間到和結果流程。
5. **US5（P2）**：補齊資源、fallback、resize、可及性和背景分頁安全。

### 可平行工作範例

**User Story 1（Phase 3）**：T018 測試、T020 intro、T021 選角和 T019 session 可由不同人分工；T022、T023 等待它們完成後整合。

**User Story 2（Phase 4）**：T024 combat tests、T025 input tests 和 T027 renderer 可平行；T026 完成核心後再由 T028、T029、T030 串接畫面。

**User Story 3（Phase 5）**：T032 monster tests、T033 terrain tests、T034 HUD／aiming tests 可平行；T035、T036、T037 各自完成核心後，T038、T039、T040 依序整合。

**User Story 4（Phase 6）**：T041 extraction tests 與 T042 result-flow tests 可平行；T043、T044 完成規則後由 T046、T047 接畫面，T045 可在 developer overlay 完成後平行處理。

**User Story 5（Phase 7）**：T048 resize tests、T049 asset tests、T050 資源盤點可平行；T051–T055 依資源與 Canvas 邊界逐步整合。

## MVP 與增量策略

### MVP：只交付 User Story 1

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational 並通過核心 smoke test。
3. 完成 Phase 3 US1。
4. 依 US1 獨立測試確認 intro、選角、6 名玩家建立和新局清除。
5. 在尚未發布前先停止，確認網頁入口與 session 邊界，再開始戰鬥功能。

### 增量交付

1. 加入 US2，形成可操作的瀏覽器戰鬥切片。
2. 加入 US3，完成 PvE、地形、HUD、auto-aim 和 developer mode。
3. 加入 US4，完成中央撤離與勝負結果。
4. 加入 US5，完成資源、responsive、fallback、可及性和背景分頁保護。
5. 通過 Phase 8 後才建立 private Sites production URL；每次增量都保留前一個故事可測試。

### 單人執行建議

依 T001→T017 建立核心，再依 US1→US2→US3→US4→US5 順序執行；每個檢查點先跑對應測試與人工情境，再進入下一個故事，避免把所有 Canvas 視覺問題留到最後才定位。

## 完成定義

- 所有任務均使用 checkbox、連續 Task ID、必要的 `[US#]`／`[P]` 標籤，且描述含明確檔案路徑。
- 五個 User Story 各有目標、獨立測試標準、先行測試任務、實作任務與檢查點。
- 自動測試、typecheck、build、本機 preview 和私人 production smoke test 均有明確任務與紀錄位置。
- Sites 部署只使用新網站資料夾；既有 Python/Pygame 桌面版、001–009 文件和未追蹤使用者檔案不被改寫或刪除。
- 原版 parity closure 的 deterministic fixtures、固定 1280×720 UI 基準、更新順序與 dummy 邊界已被任務明確涵蓋；未完成 checkbox 可代表仍待本機長時間量測、production session、Sites 部署同步或 PR／合併治理，不代表規格缺少實作任務。
