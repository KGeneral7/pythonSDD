---
description: "小怪動態尋路與營地遊蕩的實作任務清單"
---

# 任務：小怪動態尋路與營地遊蕩

**輸入**：`specs/007-monster-navigation-wander/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md` 與 `quickstart.md`。

**前置條件**：先完成 `plan.md`、`spec.md`、`research.md` 與 `data-model.md`；本功能沒有外部 `contracts/`，因為它只修改單機 Pygame 遊戲的內部狀態。

**測試策略**：規格提供每個使用者故事的獨立測試與量化成功標準，以下包含 `unittest` 測試任務。測試任務要先建立並確認在功能完成前會失敗，再進行對應實作。

**組織方式**：任務依使用者故事分階段；每個故事都有目標、獨立驗證條件與檢查點。所有任務都標示實際檔案路徑。

## Phase 1：準備共用結構

**目的**：準備導航參數、模組入口與測試骨架；既有遊戲初始化與 Pygame 相依套件不需重建。

- [X] T001 [P] 在 `pvpve_escape/config.py` 新增 `MONSTER_NAVIGATION_CELL_SIZE=40`、`MONSTER_NAVIGATION_CLEARANCE=4`、`MONSTER_NAVIGATION_REPATH_INTERVAL=0.25`、`MONSTER_NAVIGATION_RETRY_INTERVAL=0.25`、`MONSTER_NAVIGATION_NODE_ARRIVAL_TOLERANCE=8`、`MONSTER_AGGRO_RADIUS=520`、`MONSTER_WANDER_RADIUS=700`、`MONSTER_CAMP_ARRIVAL_RADIUS=64`、`MONSTER_WANDER_SPEED_RATIO=0.5`、`MONSTER_WANDER_PAUSE=0.75`，並集中設定追獵獸為玩家基礎移速 90%、其它怪物同相對增幅與玩家 0 號新出生點，以中文註解說明各數值保護的範圍。
- [X] T002 [P] 在 `pvpve_escape/navigation.py` 建立不依賴 Pygame 顯示 API 的導航模組骨架，定義 `find_grid_path(start, goal, radius, obstacles)` 的型別、回傳約定與模組文件字串，先保留可測試的純函式入口。
- [X] T003 [P] 在 `pvpve_escape/tests/test_navigation.py` 建立 `unittest` 測試骨架與最小 `Vector2`／`ObstacleState`／牆體工廠輔助函式，讓後續測試可重複建立厚牆、薄牆、破壞牆與不同怪物半徑的場景。

**檢查點**：設定名稱集中、導航模組可匯入、測試骨架可被測試發現器載入；不改變現有遊戲行為。

---

## Phase 2：基礎資料與重生前置

**目的**：建立所有使用者故事共用的小怪狀態，讓路徑與行為可以保存於單場 `MatchState`，不依賴全域狀態。

- [X] T004 在 `pvpve_escape/models.py` 新增 `MonsterBehavior.WANDER`、`CHASE`、`RETURN`，並為 `MonsterState` 加入 `behavior`、`navigation_path`、`navigation_goal`、`navigation_obstacle_signature`、`navigation_repath_timer`、`wander_target`、`wander_index` 與 `wander_pause_timer` 欄位；使用資料類別安全的空清單／空 tuple 預設值。
- [X] T005 在 `pvpve_escape/monsters.py` 更新 `create_monster_state`，明確確認新建立的三種怪物從 `WANDER`、無目標、無路徑與零停留計時開始，並依設定表載入三類型最終移速、既有半徑、攻擊種類與攻擊參數。

**檢查點**：建立一隻怪物後可讀取完整導航欄位，且多隻怪物不共享同一個可變路徑清單；現有怪物名冊測試仍可通過。

---

## Phase 3：使用者故事 1－小怪能繞牆追擊玩家（Priority: P1）🎯 MVP

**目標**：讓 `CHASER`、`SHOOTER`、`BRUTE` 都能沿安全路徑繞過未摧毀牆體，接近其合法玩家目標，不再反覆向同一牆面碰撞。

**獨立測試**：在最小地形中先讓小怪與存活玩家於 520px 內且無牆視線下合法取得目標，再把目標移到牆體另一側，持續呼叫小怪更新 10 秒；三種怪物都應抵達各自原本的攻擊互動距離，且每次位置更新都不穿牆、不重疊、不傳送。

### 使用者故事 1 的測試

- [X] T006 [P] [US1] 在 `pvpve_escape/tests/test_navigation.py` 先新增並執行純導航測試：驗證 40px 網格邊界、不同怪物半徑的牆體 clearance、八方向 A* 能繞過矩形牆、斜向不可切牆角、起點／目標不可通行與無路徑回傳；在導航尚未實作時確認測試失敗。
- [X] T007 [P] [US1] 在 `pvpve_escape/tests/test_game_features.py` 先新增怪物追擊整合測試：以全新 `MatchState` 重複 20 次，先讓每隻 `CHASER`、`SHOOTER`、`BRUTE` 在 520px 內且無牆視線下取得目標，再把目標移到牆另一側，逐步更新並檢查每次最多 10 秒內到達攻擊互動距離、位置不重疊且非重生單幀位移不超過 `move_speed * delta_time * slow_multiplier + config.TERRAIN_GEOMETRY_EPSILON`；在世界更新尚未接入路徑前確認測試失敗。

### 使用者故事 1 的實作

- [X] T008 [US1] 在 `pvpve_escape/navigation.py` 實作世界座標／40px 格子轉換、世界安全邊界、以 `radius + MONSTER_NAVIGATION_CLEARANCE` 膨脹固體牆的佔用判斷、八方向 A*、固定節點排序與禁止斜向切角；保留必要起終點精確線段檢查，完成 `find_grid_path` 並在無路徑時回傳 `None`；完成後讓 T006 通過。
- [X] T009 [US1] 在 `pvpve_escape/world.py` 將追擊移動改為依 `navigation_path` 逐一跟隨安全節點，使用 `move_circle_with_obstacles` 與 `clamp_position` 執行實際位移；移除小怪對目標的無條件直線位移，使用設定表中的三類怪物移速與半徑，並完成 T007 的 20 次、每次 10 秒路徑測試。

**檢查點**：只完成 Phase 1、2、3 時，三種怪物已能在無動態破牆需求的固定障礙中繞牆追擊；無路徑時保持目前安全位置並等待重試。

---

## Phase 4：使用者故事 2－牆破壞後即時改道（Priority: P1）

**目標**：薄牆被既有玩家規則破壞後，怪物下一次更新即讀取目前 `match.obstacles`、清除舊路徑並重新規劃；已破壞薄牆可通行，未摧毀薄牆與厚牆仍阻擋。

**獨立測試**：讓小怪先取得繞過薄牆的路徑，再把薄牆設為 `destroyed=True` 並呼叫下一次更新；確認牆體簽章變更、舊節點失效、方向可使用缺口，並確認厚牆仍不能穿越。遊蕩、返營與追擊都要使用同一份新快照。

### 使用者故事 2 的測試

- [X] T010 [P] [US2] 在 `pvpve_escape/tests/test_navigation.py` 先新增牆體簽章測試：以 `WANDER`、`RETURN`、`CHASE` 三種行為和同一營地至少三隻怪物驗證固體牆快照改變會使每隻受影響小怪的路徑失效、破壞薄牆後薄牆不再佔用網格、厚牆仍佔用，以及沒有可達路線時位置安全且能在稍後重試；在失效處理尚未實作時確認測試失敗。
- [X] T011 [P] [US2] 在 `pvpve_escape/tests/test_terrain.py` 新增世界更新整合測試：使用既有破牆函式改變 `match.obstacles`，驗證玩家動作先於 `update_monsters` 執行、下一次更新可觀察到薄牆消失，並檢查厚牆與路徑線段的碰撞；在動態改道尚未接入時確認測試失敗。

### 使用者故事 2 的實作

- [X] T012 [US2] 在 `pvpve_escape/world.py` 於每次 `update_monsters` 取得單一 `snapshot_obstacles(match.obstacles)`，比對每隻怪物的 `navigation_obstacle_signature`；簽章變更時清空 `navigation_path`／`navigation_goal`、將重算計時器歸零並以當前固體牆立即重算，另加入目標格／重算間隔變更與無路徑安全停留，於 `MONSTER_NAVIGATION_RETRY_INTERVAL=0.25` 秒後重試，完成 T010 與 T011。

**檢查點**：破壞薄牆後的下一次怪物更新不再沿用舊繞路；厚牆仍不可通行，且遊蕩、返營、追擊共用即時牆體狀態。

---

## Phase 5：使用者故事 3－小怪在營地附近遊蕩並警戒（Priority: P2）

**目標**：小怪沒有合法目標時在所屬營地 700px 範圍內遊蕩；只有存活玩家在 520px 內且無完整牆體遮擋時才追擊，目標失效後返營再恢復遊蕩。

**獨立測試**：分別把玩家放在 520px 外、520px 內牆後、520px 內無牆與剛好邊界的位置；確認目標選擇、最近玩家規則、狀態轉換、遊蕩點範圍、返營與遊蕩／返營不攻擊。

### 使用者故事 3 的測試

- [X] T013 [P] [US3] 在 `pvpve_escape/tests/test_navigation.py` 先新增目標偵測測試：驗證只選存活玩家、距離 `<= 520` 且線段無固體牆者，牆後玩家不能新取得目標，多個合法玩家選最近且以玩家 ID 穩定排序，並覆蓋剛好 520px 與超過 520px 的邊界；在狀態機尚未實作時確認測試失敗。
- [X] T014 [P] [US3] 在 `pvpve_escape/tests/test_game_features.py` 先新增遊蕩／返營測試：以全新 `MatchState` 重複 20 次，驗證每種怪物每次至少完成兩個不同遊蕩點且距營地中心不超過 700px、遊蕩速度為目前移速 50%、抵達後以 `MONSTER_WANDER_PAUSE=0.75` 秒累計停留（允許一個 `delta_time` 誤差）、返營在距中心 64px 內才完成、返營期間不攻擊，以及死亡重生後清除舊狀態；在行為實作尚未完成時確認測試失敗。

### 使用者故事 3 的實作

- [X] T015 [US3] 在 `pvpve_escape/world.py` 實作存活目標查找與 `first_obstacle_on_segment` 視線檢查，依 `(距離, player_id)` 選最近合法玩家，並完成 `WANDER`／`CHASE`／`RETURN` 的目標取得、保留、死亡／超過 520px 解除與新目標切換規則；完成 T013。
- [X] T016 [US3] 在 `pvpve_escape/world.py` 實作以 `monster_id`／`wander_index` 可重現的營地安全候選點、700px 範圍與世界邊界驗證、遊蕩 50% 移速、`MONSTER_WANDER_PAUSE=0.75` 秒停留、返營中心路徑及距中心 64px 的到達判定與 `MONSTER_NAVIGATION_RETRY_INTERVAL=0.25` 秒無路徑重試；限制 `WANDER`／`RETURN` 不執行攻擊，完成 T014 的 20 次遊蕩與返營測試。
- [X] T017 [US3] 在 `pvpve_escape/world.py` 補上重生分支的完整狀態重設：將位置回到 `spawn_position`、行為設為 `WANDER`、清除 `target_player_id`、路徑、導航目標、牆體簽章、遊蕩點與停留計時，並保留既有效果與怪物投射物清理，完成重生邊界測試。

**檢查點**：小怪開場會在營地活動；可見且接近的玩家會觸發追擊；目標死亡／離開距離後小怪不攻擊並返營，回營後繼續遊蕩。

---

## Phase 6：使用者故事 4－保留不同怪物的戰鬥定位（Priority: P2）

**目標**：路徑與狀態機完成後，三種怪物仍保留原本的接觸攻擊、攻擊距離、偏好距離與投射物行為，並依規格套用新的速度比例。

**獨立測試**：先讓三種怪物在 520px 內且無牆視線下合法取得同一名玩家，再讓玩家移到牆體另一側；確認三種怪物都能繞牆接近，`CHASER`／`BRUTE` 只在接觸距離造成既有傷害，`SHOOTER` 在原本範圍與偏好距離產生慢速投射物，且不因導航改變類型參數。

### 使用者故事 4 的測試

- [X] T018 [US4] 在 `pvpve_escape/tests/test_game_features.py` 先新增戰鬥回歸測試：驗證追擊狀態下 `CHASER`／`BRUTE` 的接觸傷害、`SHOOTER` 的 420px 攻擊範圍／300px 偏好距離／慢速投射物，以及遊蕩／返營期間不產生攻擊；在攻擊狀態整合尚未完成時確認測試失敗。

### 使用者故事 4 的實作

- [X] T019 [US4] 在 `pvpve_escape/world.py` 將既有攻擊分支明確限制於 `MonsterBehavior.CHASE`，保留 `MonsterDefinition` 的三類型戰鬥數值與速度差異；為 `SHOOTER` 將導航目標設為安全的偏好距離位置並維持原本的靠近／退後策略，確認 `CHASER`／`BRUTE` 接觸攻擊與投射物更新均通過 T018。

**檢查點**：導航只改變抵達方式，不改變怪物類型的戰術差異或既有傷害／投射物規則。

---

## Phase 7：整理、回歸與跨功能驗證

**目的**：完成憲章要求的可理解註解、全套自動化驗證、手動遊戲觀察與規格追蹤。

- [X] T020 在 `pvpve_escape/navigation.py`、`pvpve_escape/models.py` 與 `pvpve_escape/world.py` 補上必要的中文文件字串／註解，說明網格中心、牆體膨脹、斜向禁止切角、牆體簽章失效與三狀態轉換的原因；只整理本功能相關程式，不做無關重構。
- [X] T021 依 `specs/007-monster-navigation-wander/quickstart.md` 執行 `python -m unittest pvpve_escape.tests.test_navigation` 與 `python -m unittest pvpve_escape.tests.test_game_features pvpve_escape.tests.test_terrain` 聚焦測試，記錄結果並處理本功能回歸失敗。
- [X] T022 依 `specs/007-monster-navigation-wander/quickstart.md` 執行完整 `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`、`python -m compileall -q pvpve_escape` 與 `git diff --check`，確認既有玩家、地形、渲染與戰鬥測試沒有回歸。
- [X] T023 依 `specs/007-monster-navigation-wander/quickstart.md` 啟動 `python -m pvpve_escape` 完成手動驗證：觀察營地遊蕩、520px 無牆警戒、牆後繞路、薄牆破壞後下一更新改道、厚牆阻擋、距營地中心 64px 內返營、返營期間不攻擊、三種怪物攻擊差異、速度比例與玩家 0 號出生距離，記錄是否符合 SC-001 至 SC-008；20 次量化案例由 T007／T014 的自動化測試負責。
- [X] T024 對照 `specs/007-monster-navigation-wander/spec.md`、`specs/007-monster-navigation-wander/plan.md` 與實作檔案 `pvpve_escape/config.py`、`pvpve_escape/models.py`、`pvpve_escape/navigation.py`、`pvpve_escape/world.py`，逐項確認 FR-001 至 FR-017 已有任務與驗證證據，並在 `specs/007-monster-navigation-wander/quickstart.md` 補寫實際測試與手動結果。
- [X] T025 在 `pvpve_escape/tests/test_game_features.py` 與 `pvpve_escape/tests/test_rules.py` 補上 700px 遊蕩候選可達較大半徑、追獵獸／其它怪物速度相對增幅及玩家 0 號出生距離的回歸斷言，並重新執行跨文件分析與完整驗證，確認 SC-007／SC-008 可追溯。
- [X] T026 在 `pvpve_escape/navigation.py` 統一導航安全格與既有膨脹矩形移動碰撞的牆角判定，補上厚牆角中間節點連線回歸測試，確認路徑不會落入實際移動系統會攔截的位置。

## Phase 8：Convergence－砲台蟲牆角卡住修正

- [X] T027 [US1] 在 `pvpve_escape/tests/test_game_features.py` 補上砲台蟲偏好距離終點落入牆角或封閉不可達區時的回歸測試，確認其仍會選擇可達且安全的攻擊位置，不會在同一牆前位置連續停留；再於 `pvpve_escape/world.py` 與 `pvpve_escape/navigation.py` 修正偏好距離導航的不可達終點與 clearance 離開處理，保留 300px 偏好距離、420px 攻擊範圍、牆體安全距離與既有投射物行為，並完成聚焦與完整回歸驗證（FR-001、FR-003、FR-012、SC-001、SC-006）。

---

## 依賴與執行順序

### 階段依賴

- **Phase 1**：沒有前置依賴；T001、T002、T003 可平行執行。
- **Phase 2**：依賴 Phase 1；T004 先建立資料欄位，T005 再確認怪物工廠的預設狀態。
- **Phase 3（US1）**：依賴 Phase 2；T006、T007 可平行寫測試，T008 在測試後實作導航，T009 再接入世界更新。
- **Phase 4（US2）**：依賴 US1 的路徑執行能力；T010、T011 可平行寫測試，T012 接入即時牆體失效與重試。
- **Phase 5（US3）**：依賴 US1 的路徑和 US2 的牆體快照；T013、T014 可平行寫測試，T015、T016、T017 依序完成狀態、遊蕩與重生。
- **Phase 6（US4）**：依賴 US3 的 `CHASE` 狀態與攻擊限制；T018 先寫回歸測試，T019 再保留三種戰鬥定位。
- **Phase 7**：依賴所有要交付的使用者故事；T020 完成程式可理解性後，執行 T021 至 T026 的自動化、手動與追蹤驗證。
- **Phase 8（Convergence）**：依賴 Phase 7 的回歸結果；T027 先建立牆角卡住回歸測試，再依序修改 `world.py`／`navigation.py`，最後重跑聚焦、完整與效能驗證。

### 使用者故事依賴

- **US1（P1）**：完成 Phase 2 後即可開始，是本功能 MVP；不依賴其他使用者故事。
- **US2（P1）**：依賴 US1 的 `navigation_path` 與安全節點跟隨，才能驗證舊路徑失效後的新路徑。
- **US3（P2）**：依賴 US1 的路徑移動與 US2 的即時牆體快照，才能讓遊蕩、返營與追擊共用地形規則。
- **US4（P2）**：依賴 US3 的 `CHASE` 狀態，才能把既有攻擊明確限制在合法追擊中；仍可用獨立回歸測試驗證。

### 使用者故事內部順序

- 測試任務先於對應實作任務，並在功能完成前確認測試會失敗。
- 資料模型與設定先於導航函式；導航函式先於世界更新整合。
- 目標狀態先於遊蕩／返營細節；狀態與移動完成後才接入攻擊回歸。
- 每個檢查點都要先執行該階段的聚焦測試，再進入下一個故事。

## 可平行執行範例

### US1

- T006：在 `pvpve_escape/tests/test_navigation.py` 撰寫純 A* 與幾何測試。
- T007：在 `pvpve_escape/tests/test_game_features.py` 撰寫三種怪物的追擊整合測試。

兩項測試使用不同檔案，可在 T008／T009 實作前平行準備；T008 完成後再由 T009 接入世界更新。

### US2

- T010：在 `pvpve_escape/tests/test_navigation.py` 撰寫簽章與無路徑重試測試。
- T011：在 `pvpve_escape/tests/test_terrain.py` 撰寫破牆更新順序與厚牆測試。

兩項測試使用不同檔案，可平行準備；T012 需等兩項測試完成後修改 `world.py`。

### US3

- T013：在 `pvpve_escape/tests/test_navigation.py` 撰寫目標距離／視線／最近目標測試。
- T014：在 `pvpve_escape/tests/test_game_features.py` 撰寫遊蕩／返營／重生測試。

兩項測試使用不同檔案，可平行準備；T015 至 T017 仍需按狀態轉換順序修改 `world.py`。

### US4

T018 先集中建立 `pvpve_escape/tests/test_game_features.py` 的戰鬥回歸案例，再由 T019 修改 `pvpve_escape/world.py`；由於兩者依賴同一組 `CHASE` 狀態，不拆成平行實作。

## 實作策略

### MVP 優先

1. 完成 Phase 1 與 Phase 2。
2. 完成 US1 的 T006 至 T009，先讓三種怪物在固定牆體地形中穩定繞牆。
3. 執行 US1 獨立測試與 `quickstart.md` 的手動繞牆情境，確認不穿牆、不重疊、不傳送。
4. 通過後再加入 US2 的破牆失效，避免一次引入所有狀態而難以定位卡牆原因。

### 漸進交付

1. Phase 1／2：資料與導航基礎可匯入、可測試。
2. US1：繞牆追擊 MVP，可獨立展示。
3. US2：破牆後即時改道，讓動態地形和路徑一致。
4. US3：營地遊蕩、警戒、返營與重生清理。
5. US4：確認三種怪物戰鬥定位完整保留。
6. Phase 7：已完成全套回歸、手動驗證與規格追蹤；PR #13 已合併並發布 `v0.4.0`。
7. Phase 8：已完成砲台蟲牆角／封閉區卡住修正與三個回歸案例；目前完整測試共 229 項通過。

## 完成定義

- 所有 T001 至 T027 均完成並勾選，且每個使用者故事的檢查點測試通過。
- `quickstart.md` 的完整測試、編譯、差異格式與手動遊戲驗證均有實際結果。
- FR-001 至 FR-017、SC-001 至 SC-008 與三種怪物回歸情境都有可追溯的測試或手動證據。
- 功能分支與 `specs/007-monster-navigation-wander/` 文件保持一致；PR #13 已合併並發布 `v0.4.0`，T027 後續修正已納入待合併的 [PR #14](https://github.com/KGeneral7/pythonSDD/pull/14)。本地 `codex/007-monster-navigation-wander` 分支目前仍保留，待發布流程安全清理。
- Phase 8 的 T027 已修正砲台蟲牆角／封閉區卡住問題；新增的厚牆內偏好點、長牆轉角 clearance 與封閉區回歸案例均通過，完整測試共 229 項通過。
