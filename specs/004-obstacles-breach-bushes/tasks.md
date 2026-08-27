---

description: "地圖障礙物、破牆、草叢視線與戰鬥恢復的實作任務"
---

# 任務：地圖障礙物、破牆、草叢視線與戰鬥恢復

**輸入**：`specs/004-obstacles-breach-bushes/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md` 與 `quickstart.md`

**前置條件**：`plan.md`、`spec.md`；本功能沒有外部契約或 API 合約目錄。

**測試策略**：規格明確要求獨立測試與可量化驗收，因此每個使用者故事都先建立會失敗的測試，再進行實作。測試沿用既有 `unittest`、`SDL_VIDEODRIVER=dummy`、固定 `delta_time` 與 `pvpve_escape/tests/test_helpers.py`，不新增依賴。

**任務格式**：`[P]` 表示可在不同檔案且無相互依賴的情況下平行執行；`[USn]` 表示所屬使用者故事。

> 本輪已完成工作樹保留檢查；發布交付使用 `codex/004-obstacles-breach-bushes`，先前已完成 US1 的地形顯示子任務 T009/T013。本次只納入已確認的程式、測試、SDD 與區域發布技能檔案，`day3/` 保留但不提交。

## 階段 1：設定（共用環境）

**目的**：確認既有本地 Pygame 專案與基線狀態，讓後續任務可以辨識新回歸與工作區原有變更。

- [x] T001 [P] 依 `pvpve_escape/requirements.txt` 與 `pvpve_escape/tests/test_helpers.py` 驗證 Python、Pygame、無頭 SDL 畫面（Surface）與既有測試工具可用，僅記錄環境結果，不修改遊戲邏輯；已確認 Python 3.11.5、Pygame 2.6.1、dummy SDL Surface 與既有測試工具可用。
- [x] T002 執行 `pvpve_escape/tests` 的既有 unittest 基線，將實際結果記錄在 `specs/004-obstacles-breach-bushes/quickstart.md`，並把 `pvpve_escape/config.py` 未提交的不透明度設定變更所造成的既有失敗獨立列出；已確認工作樹內容保留，`day3/` 不納入發布提交，並建立符合 004 識別字的交付分支。

---

## 階段 2：基礎（阻塞性前置條件）

**目的**：建立所有使用者故事共用的地形資料、固定配置與純 Python 幾何輔助函式；本階段完成前不得開始使用者故事實作。

**⚠️ 重要**：此階段完成後，玩家/怪物移動、技能路徑、能力破壞、觀看者渲染與生命恢復才能共用同一套狀態與計算。

- [x] T003 [P] 在 `pvpve_escape/models.py` 新增 `ObstacleKind`、`TerrainInteraction`、`WorldRect`、`ObstacleState`、`BushState` 與 `TerrainHitResult`，並以欄位追加方式擴充 `MatchState` 的 `obstacles`/`bushes`、`PlayerState` 的戰鬥計時、`CombatAction` 與 `AbilityEffect` 的地形互動欄位，保留既有位置參數建構相容性；新增欄位均追加於既有欄位之後，並由純地形測試驗證相容資料。
- [x] T004 [P] 在 `pvpve_escape/config.py` 加入依使用者確認座標保存的 `OBSTACLE_LAYOUT`/`BUSH_LAYOUT`、厚牆/薄牆/草叢顏色、繪製邊框與裂紋參數、`PLAYER_REGEN_DELAY=5.0`、`PLAYER_REGEN_RATE=0.10` 及碰撞 epsilon/安全區警示參數；已確認的紅框重疊保留，不作為自動拒絕條件。
- [x] T005 新增不依賴 Pygame 或 `world.py` 的 `pvpve_escape/terrain.py`，實作每場獨立建立障礙物/草叢、圓形對軸對齊矩形碰撞、X/Y 分軸移動解析、線段第一面牆掃掠與路徑端點解析，讓牆是阻擋物、草叢不進入固體碰撞清單；25 項純地形測試已通過。
- [x] T006 在 `pvpve_escape/tests/test_terrain.py` 建立純地形基礎測試，涵蓋矩形邊界、已確認配置的紅框警示清單、薄厚牆型與草叢資料、圓形碰撞、牆角接觸、第一面牆命中及每場狀態為獨立複本；配置常數的 45 物件、世界邊界與 5 筆警示已先由 `test_config.py` 覆蓋；`test_terrain` 25/25 通過。

**檢查點**：資料模型、固定配置與純地形幾何可獨立測試；下一階段不得透過渲染結果反推碰撞規則。

---

## 階段 3：使用者故事 1——在有掩體的地圖中移動與交戰（優先級：P1，MVP）

**目標**：讓固定且已確認的地圖配置顯示厚牆、薄牆與草叢，玩家和怪物不能穿牆，直線/光束/飛行技能在第一面牆前停止，牆後目標不受穿牆效果影響，新局會重新建立完整地形；紅框安全區重疊保留並可追蹤。

**獨立測試**：使用 `create_match` 建立新局，對玩家、怪物及每一種直線/飛行效果執行正面與斜向牆面測試；確認牆前停止或沿牆滑動、牆後目標不受影響、牆色可區分，並連續重建新局確認配置一致。

### 使用者故事 1 的測試（先寫測試並確認失敗）

- [x] T007 [US1] 在 `pvpve_escape/tests/test_terrain.py` 補上使用者故事 1 的整合測試：`create_match` 固定配置重建、玩家/怪物正面與斜向移動、牆角不穿透、投射物半徑、牆前/牆後目標與同場破壞狀態持續；重置情境以 fixture 直接設定 `destroyed/active`，不依賴 US2 的能力實作，每個量化情境至少重複 20 次；25/25 通過。
- [x] T008 [P] [US1] 在 `pvpve_escape/tests/test_aiming.py` 新增牆體瞄準預覽測試，確認 `build_aim_guide(..., obstacles=...)` 的線段/路徑端點與實際第一面牆一致，且省略參數仍保留既有呼叫結果；10/10 通過。
- [x] T009 [P] [US1] 在 `pvpve_escape/tests/test_rendering.py` 新增地形渲染冒煙測試，確認完整世界畫布上的 18 個牆體與 27 個草叢都有配置填色，並在正式 1280×720 視窗的不同相機位置確認牆/草叢可見；地形層在角色/效果前繪製、厚牆與薄牆使用不同顏色與邊界樣式。

### 使用者故事 1 的實作

- [x] T010 [US1] 在 `pvpve_escape/world.py` 將 `create_match` 接上每場獨立地形，並把 `pvpve_escape/terrain.py` 的圓形碰撞解析整合到玩家移動與怪物移動，使正面碰撞停止、斜向碰撞可沿牆滑動且不越過牆角；正式輸入與 25 項地形測試通過。
- [x] T011 [US1] 在 `pvpve_escape/world.py` 將第一面牆路徑解析整合到 `sniper_line`、`sniper_ultimate_line`、`boomerang`、`mine`、`beam`、`hunter_dash`、`tactical_control`、`gravity_cage` 與其他既有直線/飛行效果，讓牆後目標不被選取、傷害或施加效果，並保留草叢的非阻擋行為。
- [x] T012 [P] [US1] 在 `pvpve_escape/aiming.py` 增加可選 `obstacles` 參數，讓線段/路徑類瞄準端點共用 `pvpve_escape/terrain.py` 的解析結果，並更新既有型別/預覽呼叫以保持向後相容；10 項瞄準測試通過。
- [x] T013 [P] [US1] 在 `pvpve_escape/rendering.py` 新增地形繪製層，於地面/網格後先繪製草叢、再繪製厚牆與薄牆；厚牆使用深紫灰、薄牆使用橘色、兩者使用淺色邊框，薄牆加入裂紋/斷線，依目前 surface 裁切完全在視窗外的地形，且不以 debug 文字取代視覺辨識。
- [x] T014 [US1] 執行 `pvpve_escape/tests/test_terrain.py`、`pvpve_escape/tests/test_aiming.py` 與 `pvpve_escape/tests/test_rendering.py` 的使用者故事 1 測試，並依 `specs/004-obstacles-breach-bushes/quickstart.md` 完成一次牆面、牆角、技能阻擋與新局重置驗收；地形/瞄準/渲染定向測試全數通過。

**檢查點**：只完成階段 1–3 時，遊戲已有可辨識且可碰撞的掩體地圖，可單獨展示移動與牆後安全性；尚未依賴破牆、隱藏或恢復功能。

---

## 階段 4：使用者故事 2——使用適合的能力打通地圖路線（優先級：P1）

**目標**：只有破陣者終極技能與 `DASH` 能破壞薄牆和草叢；破陣者主要技能與其他一般技能依 `BLOCK` 在牆前停止；厚牆永不破壞；具破壞資格的遠程效果同次施放不可穿過剛移除的薄牆，而 DASH 只破壞第一面薄牆後完成剩餘位移，後續牆仍阻擋。

**獨立測試**：以破陣者主要技能、終極技能、其他角色、`DASH`、`SHIELD`、`CONTROL` 分別測試薄牆、厚牆、多牆路徑與草叢，確認主要技能阻擋、終極/DASH 破壞資格、一次命中、遠程快照與 DASH 路徑規則。

### 使用者故事 2 的測試（先寫測試並確認失敗）

- [x] T015 [P] [US2] 在 `pvpve_escape/tests/test_terrain.py`、`pvpve_escape/tests/test_aiming.py`、`pvpve_escape/tests/test_rendering.py` 與恢復/既有規則回歸中補上破壞權限與路徑測試，涵蓋 Breacher 主要技能阻擋、終極技能破壞、非資格角色/配件、厚牆不可破壞、薄牆一次命中、遠程快照、DASH 多牆、草叢沿路徑移除及 DASH 預覽一致性；量化情境以固定重複測試覆蓋。

### 使用者故事 2 的實作

- [x] T016 [P] [US2] 在 `pvpve_escape/characters.py` 為 Breacher 主要技能設定 `BLOCK`、終極技能與 `TacticalId.DASH` 設定正確的破壞型 `TerrainInteraction`，確認其他角色與 `SHIELD`/`CONTROL` 明確維持 `BLOCK` 或無破壞資格。
- [x] T017 [P] [US2] 在 `pvpve_escape/terrain.py` 實作 `destroy_thin_wall_on_path`、`destroy_terrain_in_radius`、`destroy_bushes_on_segment` 與不可變牆體阻擋快照所需的輔助函式；只允許薄牆/草叢由明確政策轉為無效，厚牆永遠保留。
- [x] T018 [US2] 在 `pvpve_escape/world.py` 整合 Breacher 主要技能的 BLOCK 牆前停止、Breacher 終極技能範圍破壞、具資格遠程路徑的阻擋快照、DASH 第一面薄牆破壞後的剩餘距離解析，以及所有合資格路徑上的草叢移除。
- [x] T019 [US2] 在 `pvpve_escape/aiming.py` 與 `pvpve_escape/rendering.py` 讓主要技能預覽反映牆前阻擋，DASH/破牆能力預覽使用不修改狀態的同一路徑解析，表達第一面薄牆可破壞、下一面牆仍阻擋，且草叢不縮短預覽距離。
- [x] T020 [US2] 執行 `pvpve_escape/tests/test_terrain.py`、`pvpve_escape/tests/test_rules.py`、`pvpve_escape/tests/test_aiming.py` 與 `pvpve_escape/tests/test_rendering.py` 的使用者故事 2 測試，並依 `specs/004-obstacles-breach-bushes/quickstart.md` 完成破牆、厚牆、DASH 與草叢破壞驗收。

**檢查點**：US1 的牆體阻擋仍通過；US2 可單獨證明主要技能停止、終極範圍破壞與「DASH 穿一面薄牆」的差異。

---

## 階段 5：使用者故事 3——在草叢中隱藏自己的位置（優先級：P1）

**目標**：有效草叢提供觀看者特定的視覺隱藏；玩家自己永遠看得到自己，其他觀看者看不到角色、編號、生命值、狀態與瞄準提示；草叢仍可見，離開或被破壞後下一幀恢復顯示，且不改變戰鬥規則。

**獨立測試**：將存活玩家放入、移出及破壞草叢，以自身與非自身 `viewer_id` 渲染同一場，檢查玩家本體與玩家名單；再對已知位置目標執行既有攻擊、受擊、怪物仇恨與碰撞測試。

### 使用者故事 3 的測試（先寫測試並確認失敗）

- [x] T021 [P] [US3] 在 `pvpve_escape/tests/test_visibility.py` 建立可見性與戰鬥不變測試，涵蓋自身可見、他人隱藏、角色資訊/瞄準提示完整隱藏、離開/破壞後下一次繪製恢復，以及隱藏不改變目標、傷害、碰撞與怪物仇恨；fixture 不依賴 US2 能力實作，3/3 通過。
- [x] T022 [P] [US3] 在 `pvpve_escape/tests/test_visibility.py` 與 `pvpve_escape/tests/test_rendering.py` 補上 `draw_world`、`draw_match` 與 `_draw_player_roster` 的 `viewer_id` 測試，確認草叢仍繪製、非自身玩家名單不洩漏角色資料，且人類預設 viewer 仍為 0。

### 使用者故事 3 的實作

- [x] T023 [US3] 在 `pvpve_escape/terrain.py` 實作 `is_player_in_bush` 與 `is_player_visible_to_viewer`，以存活玩家中心點和 active 草叢判定隱藏，並讓 `viewer_id == player.player_id` 永遠可見、`active=False` 立即取消隱藏。
- [x] T024 [US3] 在 `pvpve_escape/rendering.py` 為 `draw_world`、`draw_match`、玩家繪製迴圈與 `_draw_player_roster` 接上 `viewer_id=0`，對非自身草叢內玩家整段跳過角色、編號、生命值、狀態與瞄準線，重用 T013 建立的 `draw_terrain` 而不重複繪製草叢，同時保留草叢地圖物件與自身完整繪製。
- [x] T025 [US3] 執行 `pvpve_escape/tests/test_visibility.py` 與 `pvpve_escape/tests/test_rendering.py` 的使用者故事 3 測試，並依 `specs/004-obstacles-breach-bushes/quickstart.md` 完成雙視角、離開草叢、破壞草叢及已知位置攻擊驗收。

**檢查點**：可見性只存在渲染分支；`pvpve_escape/world.py` 的目標收集、傷害、怪物仇恨與牆碰撞不得接收或使用可見性結果。

---

## 階段 6：使用者故事 4——脫離戰鬥後恢復生命（優先級：P1）

**目標**：存活且未滿血的玩家在連續 5 秒未受擊、未執行攻擊後，以最大生命值每秒 10% 按 `delta_time` 恢復；受擊、攻擊、死亡與重生依規格重置或停止計時，普通 DASH/SHIELD 本身不阻止恢復。

**獨立測試**：以固定更新時間測試 4.9 秒、5.0 秒、1 秒恢復、上限截斷、護盾吸收、有效攻擊命中、攻擊未命中、普通 DASH/SHIELD、同幀受擊優先、死亡及重生計時重置。

### 使用者故事 4 的測試（先寫測試並確認失敗）

- [x] T026 [P] [US4] 在 `pvpve_escape/tests/test_regeneration.py` 建立純規則測試，覆蓋 4.9/5.0 秒門檻、最大生命值 10%/秒、`delta_time` 比例、滿血截斷、受擊/攻擊計時重置與死亡期間不恢復；12/12 通過，量化情境固定重複驗證。
- [x] T027 [P] [US4] 在 `pvpve_escape/tests/test_regeneration.py` 與既有 `test_rules.py` 整合測試中覆蓋護盾吸收仍算受擊、普通 DASH/SHIELD 不算攻擊、具傷害/控場能力算攻擊、同幀受擊先於恢復，以及重生回滿並清除舊計時。

### 使用者故事 4 的實作

- [x] T028 [US4] 在 `pvpve_escape/rules.py` 實作 `mark_player_hit`、`mark_player_attack` 與 `regenerate_player_health`，更新 `update_player_timers`、`apply_damage_to_player`、死亡與重生流程，確保計時使用遊戲更新秒數、護盾/控場命中也重置受擊、死亡不回血且重生不沿用舊計時。
- [x] T029 [US4] 在 `pvpve_escape/world.py` 與 `pvpve_escape/characters.py` 將主要攻擊、攻擊性終極技能、控場/傷害效果與其他敵方攻擊動作接上攻擊計時標記，維持普通 DASH/SHIELD 不標記；只有成功建立 action/effect 或持續攻擊每幀活動時才重置，冷卻/資源不足未建立 action 不重置，並在效果與怪物傷害結算後、撤離/勝負更新前呼叫恢復，使同幀受擊先重置再判定。
- [x] T030 [US4] 執行 `pvpve_escape/tests/test_regeneration.py` 與 `pvpve_escape/tests/test_rules.py` 的使用者故事 4 測試，並依 `specs/004-obstacles-breach-bushes/quickstart.md` 完成門檻、恢復速率、戰鬥重置、死亡重生驗收。

**檢查點**：US4 的恢復只依賴模擬時間與規則更新，不依賴 Pygame 畫面刷新；既有死亡、彈藥、撤離與勝負流程仍保持原結果。

---

## 階段 7：收尾與跨故事回歸

**目的**：完成文件、全量驗證與手動驗收，確認所有使用者故事整合後仍符合既有專案限制與工作區安全要求。

- [x] T031 將實作後的操作對照、測試命令、牆/草叢/恢復驗收清單與自動化結果、每項量化情境的實際重複次數與已知基線例外更新到 `specs/004-obstacles-breach-bushes/quickstart.md`，並核對 `specs/004-obstacles-breach-bushes/spec.md` 的 FR-001～FR-025 與 SC-001～SC-012。
- [x] T032 執行 `pvpve_escape/tests` 的完整 unittest 與 `pvpve_escape` 的 `compileall`；目前完整套件 162/162 通過，未發現 GUI 不透明度或其他基線失敗。
- [x] T033 執行 `git diff --check` 檢查程式與測試變更空白；並檢閱 `terrain.py`、`world.py`、`rendering.py` 的匯入方向與 `requirements.txt`，確認無循環依賴或新增外部服務/套件。
- [x] T034 依 `specs/004-obstacles-breach-bushes/quickstart.md` 以 `SDL_VIDEODRIVER=dummy` 啟動 `pvpve_escape.main.run()` 並注入單次 QUIT 完成入口端到端煙霧驗收；互動視覺清單保留供桌面使用者確認。
- [x] T035 依 `pvpve_escape/__main__.py` 等價的正式更新/繪製鏈，在 1280×720、6 名玩家、12 隻怪物與 45 個固定地形物件場景中預熱 60 幀後量測 600 幀；3.4837 秒完成，平均 172.23 FPS，高於 55 FPS。
- [ ] T036 在 `specs/004-obstacles-breach-bushes/quickstart.md` 記錄驗證結果後，已將 `codex/004-obstacles-breach-bushes` 推送遠端並建立指向本功能文件的非 draft [PR #4](https://github.com/KGeneral7/pythonSDD/pull/4)，確認最新 head 可合併；PR #4 已以 `2f3383f` 合併至 `main`，並建立 `v0.2.0` annotated tag 與[正式 release](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.2.0)，後續文件同步 PR 亦已合併。本次相關且已合併的遠端開發分支均已刪除，但本地 squash 後提交不是 `main` ancestry 的交付與文件分支經一般 `git branch -d` 檢查遭拒；依規範未使用 `-D`，故本地分支清理仍待安全處理。專案未配置 GitHub Actions，故以本機驗證與 GitHub 可合併狀態作為檢查結果。

---

## 依賴與執行順序

### 階段依賴

- **設定（階段 1）**：可立即執行；T002 依賴 T001 的環境確認，並記錄目前工作樹保留及外部分支例外後才能進入 T003。
- **基礎（階段 2）**：依賴設定，且阻塞所有使用者故事；T003 與 T004 可平行，T005 依賴 T003/T004，T006 依賴 T005。
- **US1（階段 3）**：依賴基礎；T007～T009 先建立故事測試，T010/T011 完成世界碰撞與路徑，T012/T013 再實作瞄準/渲染，T014 收斂驗證。
- **US2（階段 4）**：依賴 US1 的地形初始化與阻擋路徑；T015 先建立資格/破壞測試，T016/T017 可平行，T018 整合世界流程，T019 更新預覽，T020 驗證。
- **US3（階段 5）**：依賴地形與渲染層；T021/T022 先建立可見性測試，T023 實作可見性判定函式，T024 接上所有渲染入口，T025 驗證；測試使用直接 fixture，不依賴 US2 的能力破壞。
- **US4（階段 6）**：依賴既有世界更新迴圈與模型擴充；T026/T027 先建立恢復測試，T028 實作規則，T029 接上更新順序，T030 驗證。
- **收尾（階段 7）**：依賴所有要交付的使用者故事；T031～T035 完成文件、自動化、入口/手動清單與效能回歸後，T036 執行已獲授權的分支推送、PR、發布、CI 與合併生命週期。

### 使用者故事依賴

- **US1（P1）**：只依賴基礎，可作為 MVP 獨立交付。
- **US2（P1）**：依賴基礎與 US1 已建立的地形狀態、路徑阻擋和 `create_match`，但可用純地形/規則測試獨立驗證破壞政策。
- **US3（P1）**：依賴基礎與地形渲染入口；以直接 fixture 獨立驗證觀看者特定顯示，不依賴 US2 的破壞結果才能測試離開或停用草叢。
- **US4（P1）**：依賴基礎與既有世界更新流程；可獨立以固定時間測試恢復，不依賴障礙物或草叢視覺。

### 平行執行機會

- **基礎**：T003（模型）與 T004（設定）修改不同檔案，可同時進行；T005 完成後才能執行 T006。
- **US1**：T008（瞄準測試）與 T009（渲染測試）可平行；測試完成後 T012（`aiming.py`）與 T013（`rendering.py`）可平行。T010/T011 因都修改 `world.py` 應順序執行。
- **US2**：T016（角色能力政策）與 T017（地形破壞輔助函式）修改不同檔案，可平行；T018 需等待兩者完成。
- **US3**：T021（可見性規則測試）與 T022（渲染入口測試）可平行；T023/T024 需依測試結果順序完成。
- **US4**：T026（純恢復測試）與 T027（世界/規則整合測試）可平行；T028/T029 需順序完成以固定同幀更新順序。
- **跨故事**：基礎完成後，US3 與 US4 的測試/規則工作可與 US2 的角色政策分工進行；本輪各故事檢查點均已完成，外部 Git 生命週期由已獲授權的 T036 收尾。

---

## 實作策略

### MVP 優先（只交付 US1）

1. 完成設定與基礎，先驗證固定地形資料和純幾何輔助函式。
2. 完成 US1 的玩家/怪物碰撞、技能路徑阻擋、瞄準端點與牆/草叢視覺層。
3. 執行 US1 獨立測試與 `quickstart.md` 的地圖/技能/重置情境。
4. 若需要先行展示，可在此停下；此版本已提供可辨識、可碰撞、可驗證的掩體地圖。

### 增量交付

1. 在 MVP 後加入 US2，交付 Breacher 終極技能/DASH 的薄牆與草叢破壞，並讓 Breacher 主要技能維持 BLOCK；厚牆和具資格遠程快照規則不變。
2. 加入 US3，交付自身可見、他人隱藏且不影響戰鬥的草叢觀看規則。
3. 加入 US4，交付 5 秒脫戰門檻與最大生命值 10%/秒恢復。
4. 每個故事完成後先執行自己的檢查點，再進入下一個故事；最後才執行全量回歸和手動驗收。

### 完成定義

- 每個使用者故事的測試先於實作建立，並在實作前確認會失敗。
- `pvpve_escape/tests` 的新增測試、既有測試、`compileall`、`git diff --check` 與 `quickstart.md` 手動情境均有結果記錄。
- 不新增 Pygame 以外依賴，不建立外部 API/服務，不覆蓋現有未提交工作變更。
- T002 的工作樹保留與 T035 的效能門檻已完成並留下可追蹤記錄；原始 PR #3／`v0.1.0` 為既有基線，T036 的本次 PR、release、合併與文件同步已完成，本次相關且已合併的遠端分支亦已清理；本地 squash 後非 ancestry 分支因一般 `git branch -d` 安全檢查遭拒而保留，未以 `-D` 繞過檢查，因此不能宣稱本地分支生命週期已完成。
