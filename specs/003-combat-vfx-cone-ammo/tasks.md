# 任務：戰鬥特效、五散彈命中與彈藥節奏

**功能識別字**：`003-combat-vfx-cone-ammo`
**功能分支**：`codex/003-combat-vfx-cone-ammo`
**輸入**：`specs/003-combat-vfx-cone-ammo/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md`、`contracts/` 與 `quickstart.md`
**前置條件**: 設計文件已完成；目前專案為 Python 3.11 + Pygame 2.6.1 的單一 `pvpve_escape` 應用
**測試策略**: 規格提供獨立測試情境與可衡量成功標準，因此每個故事都先建立可失敗的測試，再完成實作與手動驗收
**任務格式**: `[P]` 代表可與同階段其他任務平行；`[US#]` 代表所屬使用者故事

## 階段 1：設定（共用基礎）

**目的**：建立可重複的無頭測試入口、確認功能識別字與目前回歸基線。

- [X] T001 [P] 在 `pvpve_escape/tests/test_helpers.py` 建立無頭 Pygame 初始化／清理、固定時間步驟、角色／目標建立與向量斷言 helper，讓規則與渲染測試可重複執行。
- [X] T002 [P] 在 `.specify/feature.json`、`specs/003-combat-vfx-cone-ammo/plan.md` 與 `specs/003-combat-vfx-cone-ammo/quickstart.md` 確認功能識別字與分支追蹤資訊一致，並確認 quickstart 的基線驗證命令符合 plan 的測試策略；記錄目前工作區既有未提交修改不可被覆蓋。
- [X] T003 執行 `pvpve_escape/tests/` 的既有測試與 `pvpve_escape/` 的編譯檢查，將基線結果記入 `specs/003-combat-vfx-cone-ammo/quickstart.md`，確認後續失敗可歸因於本功能。

---

## 階段 2：基礎建設（阻擋性前置工作）

**目的**：先完成所有故事共用的效果資料、命中結果與效果生命週期邊界；本階段完成前不得開始故事實作。

**⚠️ 關鍵檢查點**：完成後才可平行處理各使用者故事。

- [X] T004 [P] 在 `pvpve_escape/models.py` 擴充 `AbilityEffect` 的 `origin`、前後位置、移動距離、命中結果與 metadata 相容欄位，將 `hit_target_ids` 固定為 `set[tuple[str, int]]`，讓每個破陣者 `breach_pellet` effect 保存自己的命中集合，明確區分權威規則效果與 `visual_only` 效果，且不破壞既有 dataclass 建構呼叫。
- [X] T005 [P] 在 `pvpve_escape/config.py` 集中新增戰鬥特效所需的角色／技能色彩、扇形角度／距離、投射物半徑與共用幾何常數，避免 `world.py` 與 `rendering.py` 各自寫死不同數值。
- [X] T006 在 `pvpve_escape/world.py` 與 `pvpve_escape/rules.py` 整理 effect 建立、連續路徑、命中事件與過期清理的共用流程；確保 `visual_only` effect 只更新位置／壽命，不會呼叫傷害、控制或大招能量邏輯。

**檢查點**：模型可保存施放原點與命中結果，規則可區分視覺與權威效果，既有狙擊／飛刃／地雷的跨幀碰撞回歸測試仍通過。

---

## 階段 3：使用者故事 1－讀懂角色攻擊與技能結果（優先級：P1）🎯 MVP

**故事目標**：六種角色的普攻、六種大招與三種配件都具有可區分的幾何特效，且畫面回饋只在實際命中、護盾、免傷或控制成立時出現。

**獨立測試**：逐一選擇六種角色，在無目標／有目標情境施放普攻與大招，再使用三種配件；確認每種效果具至少兩項不同的顏色、形狀、路徑或範圍特徵，並以生命／護盾／控制狀態核對命中提示。

### 先行測試

- [X] T007 [P] [US1] 在 `pvpve_escape/tests/test_combat_effects.py` 建立六種普攻、六種大招與三種配件的 action／effect 對應測試，驗證 effect kind 唯一、metadata 包含方向／範圍／持續狀態，且視覺-only effect 不改變目標生命。
- [X] T008 [P] [US1] 在 `pvpve_escape/tests/test_rendering.py` 補充無頭 surface smoke test，逐一繪製所有普攻／大招／配件效果與命中／被擋／控制狀態，確認不拋例外且不依賴外部素材。

### 實作

- [X] T009 [P] [US1] 在 `pvpve_escape/characters.py` 整理六角色的普攻／大招／配件 action metadata 與既有平衡資料，為每個效果指定唯一 kind、方向、射程、持續時間及規則所需的 visual／impact 欄位。
- [X] T010 [US1] 在 `pvpve_escape/aiming.py` 讓普攻、大招與配件預覽依 T009 建立的 action metadata 產生方向線、扇形、落點、路徑與控制範圍，並沿用地圖邊界截斷規則（依賴 T009）。
- [X] T011 [US1] 在 `pvpve_escape/world.py` 將六角色的 action 轉為實際規則 effect，統一使用連續移動路徑與命中結果 metadata；只有碰撞、傷害、護盾吸收、免傷或控制成立時才記錄有效回饋（依賴 T004、T006、T009）。
- [X] T012 [US1] 在 `pvpve_escape/rendering.py` 實作六種主攻、六種大招與三種配件的固定幾何特效、命中／被擋／控制提示與過期清理，確保繪製方向／位置／射程與 `world.py` 的 effect 一致（依賴 T008、T010、T011）。
- [X] T013 [US1] 依 `specs/003-combat-vfx-cone-ammo/quickstart.md` 對六種普攻、六種大招與三種配件各完成至少 20 次施放，確認每種技能至少由顏色、形狀、路徑或範圍兩項特徵辨識，並將命中、護盾、免傷與控制情境各重複至少 20 次，以生命／護盾／控制結果核對回饋；在 `pvpve_escape/tests/test_combat_effects.py` 與 `pvpve_escape/tests/test_rendering.py` 修正發現的回歸斷言。

**檢查點**：US1 可單獨啟動、施放與驗收；不得存在只有圖形命中而沒有規則結果，或有規則結果卻沒有可辨識回饋的技能。

---

## 階段 4：使用者故事 2－讓破陣者依散彈命中數計傷（優先級：P1）

**故事目標**：破陣者使用 60°、最大 200 距離作為五條散彈路徑的包絡與預覽；五個 `breach_pellet` 是實際傷害來源，每個目標依真正命中的散彈顆數承受單顆傷害，扇形標記只作視覺用途。

**獨立測試**：將玩家／怪物放在散彈路徑中心、路徑間、60° 包絡邊界、所有路徑外、射程外與原點附近，重複施放並檢查每個目標生命與實際命中顆數。

### 先行測試

- [X] T014 [P] [US2] 在 `pvpve_escape/tests/test_breach_cone.py` 建立單一路徑、重疊路徑、路徑間、所有路徑外、射程外、原點附近、多目標與跨幀前端掃掠的失敗測試。
- [X] T015 [US2] 在 `pvpve_escape/tests/test_aiming.py` 與 `pvpve_escape/tests/test_breach_cone.py` 補充破陣者 60°／200 距離預覽與五條實際散彈路徑資料一致性測試，確認邊界截斷不把圖形或落點畫到世界外（依賴 T014，避免與 T014 同時修改 `test_breach_cone.py`）。

### 實作

- [X] T016 [US2] 在 `pvpve_escape/characters.py` 固定破陣者普攻的 `angle=60`、`range=200`、`pellets=5`、`projectile_speed=900` 與既有每顆散射彈傷害／強化修正，並以 metadata 傳給世界與渲染層（依賴 T009、T014）。
- [X] T017 [US2] 在 `pvpve_escape/world.py` 將一次 `breach_cone` 施放拆成一個 `visual_only` 扇形標記與五個權威 `breach_pellet`：使用共同原點／方向、固定角度偏移、放大至 16 的散彈半徑、目標碰撞圓與散彈半徑的線段相交、上一幀至本幀連續路徑，依實際命中顆數套用單顆傷害（依賴 T006、T011、T014、T016）。
- [X] T018 [US2] 在 `pvpve_escape/world.py` 為五個 `breach_pellet` 保存 pellet index／獨立路徑與自己的命中集合，確保每顆對同一目標最多一次、目標死亡後跳過後續傷害；`breach_cone` 只更新視覺，不呼叫傷害或能量規則（依賴 T017）。
- [X] T019 [US2] 在 `pvpve_escape/aiming.py` 與 `pvpve_escape/rendering.py` 使用與五顆權威散彈相同的 60° 包絡、200 距離、原點、方向與掃掠進度繪製填色弧形、五條軌跡與命中脈衝，並保留地圖邊界內縮（依賴 T012、T015、T017、T018）。
- [X] T020 [US2] 依 `specs/003-combat-vfx-cone-ammo/quickstart.md` 執行至少 20 次各路徑位置驗收，包含最遠距離相鄰路徑中點，並在 `pvpve_escape/tests/test_breach_cone.py` 驗證單顆／多顆命中傷害、放大半徑覆蓋路徑間隙、完全在路徑外目標不受傷害、目標死亡後不再吃後續事件且每次最多五次傷害。

**檢查點**：畫面上的五條散彈軌跡就是實際傷害路徑；60° 扇形只是包絡與視覺標記，不能固定補滿傷害，也不能讓視覺標記成為傷害來源。

---

## 階段 5：使用者故事 3－攻擊期間暫停彈藥恢復（優先級：P1）

**故事目標**：普攻按住、蓄力、持續引導或普攻冷卻／後搖期間，彈藥數與恢復計時完全不增加；攻擊狀態解除後等待完整恢復間隔才逐發補彈。

**獨立測試**：先把六種角色彈藥降至未滿，分別測試狙擊蓄力、汲能引導、一般普攻冷卻、大招／配件單獨使用、死亡、失焦與重新開始。

### 先行測試

- [X] T021 [P] [US3] 在 `pvpve_escape/tests/test_rules.py` 新增 `primary_attack_active` 與 `recover_ammo` blocked 情境測試，驗證彈藥與恢復計時凍結、阻擋解除後完整等待、滿彈清零與死亡不回彈。
- [X] T022 [P] [US3] 在 `pvpve_escape/tests/test_ammo_lifecycle.py` 建立世界更新順序測試，覆蓋六種角色各至少 20 次的按住、蓄力、持續引導、普攻冷卻、大招／配件單獨使用與同幀輸入，確認沒有先恢復再攻擊的漏洞。
- [X] T023 [P] [US3] 在 `pvpve_escape/tests/test_main.py` 補充失去焦點、死亡、重生與重新開始時清除按鍵／蓄力／持續引導狀態的測試，確認不會在恢復生命或新局自動重播攻擊。

### 實作

- [X] T024 [US3] 在 `pvpve_escape/rules.py` 新增可測試的 `primary_attack_active` 判定並擴充 `recover_ammo` 的 blocked 參數；阻擋時不增加彈藥／計時器並重置計時，解除後依原有間隔逐發恢復（依賴 T021）。
- [X] T025 [US3] 在 `pvpve_escape/world.py` 重排生命週期、冷卻、輸入、攻擊狀態與彈藥恢復順序，將蓄力／引導／普攻冷卻傳給 `recover_ammo`，並讓死亡／重生／重新開始清除攻擊狀態（依賴 T022、T024）。
- [X] T026 [US3] 在 `pvpve_escape/controllers.py`、`pvpve_escape/main.py` 與 `specs/003-combat-vfx-cone-ammo/contracts/combat-feedback-ui.md` 統一左鍵普攻、右鍵大招、`Space` 配件及選角畫面 `1～6`／`Q/W/E`／`Enter` 的輸入映射，清除失焦、死亡、重新開始時的 held／pressed／released、蓄力與吸能引導狀態，且不讓大招／配件單獨使用誤設為普攻阻擋（依賴 T023、T025）。
- [X] T027 [US3] 在 `pvpve_escape/rendering.py` 更新 HUD 的彈藥／恢復狀態提示，區分攻擊凍結、等待完整間隔與逐發恢復，並維持既有生命、能量、冷卻與死亡資訊可讀（依賴 T025、T026）。
- [X] T028 [US3] 依 `specs/003-combat-vfx-cone-ammo/quickstart.md` 對六角色各完成至少 20 次彈藥節奏測試，並將死亡、失焦與重新開始各重複至少 20 次，完成攻擊期間凍結、解除後完整等待、大招／配件不額外阻擋的驗收；修正 `pvpve_escape/tests/test_rules.py`、`pvpve_escape/tests/test_ammo_lifecycle.py` 與 `pvpve_escape/tests/test_main.py` 的回歸斷言。

**檢查點**：攻擊狀態任何一幀都不回彈；停止攻擊後不立即補彈；大招／配件單獨使用不會被錯誤阻擋。

---

## 階段 6：使用者故事 4－在可讀的透明介面中進行對戰（優先級：P2）

**故事目標**：選角卡、配件卡、HUD、玩家列表、血條背景與結算面板採局部可配置半透明背景，預設 78%，合法範圍 50～90%，而文字與戰鬥前景維持清晰。

**獨立測試**：使用 50%、78%、90% 及 49／91 越界值檢查選角、對戰與結算畫面，確認背景可見、文字可讀，且角色、怪物、瞄準線與技能前景不被一起淡化。

### 先行測試

- [X] T029 [P] [US4] 在 `pvpve_escape/tests/test_config.py` 建立 `GUI_OPACITY_PERCENT` 預設值、50～90 端點與越界鉗制測試，確認換算出的 alpha 穩定且不接受全透明／完全不透明值。
- [X] T030 [P] [US4] 在 `pvpve_escape/tests/test_rendering.py` 補充選角卡、配件卡、HUD、玩家列表、血條背景與結果面板的 alpha／surface smoke test，確認文字、角色、怪物、瞄準線與技能前景使用清晰色彩。

### 實作

- [X] T031 [US4] 在 `pvpve_escape/config.py` 新增 `GUI_OPACITY_PERCENT` 預設 78、50～90 邊界常數與共用鉗制／alpha 換算函式，讓所有 GUI 元件使用單一設定來源（依賴 T029）。
- [X] T032 [US4] 在 `pvpve_escape/rendering.py` 建立局部 `pygame.SRCALPHA` 面板繪製 helper，將透明背景套用到選角卡、配件卡、HUD、玩家列表、玩家／怪物血條底色與結果面板；文字、角色、怪物、瞄準線、技能特效、命中回饋與血條填色不得共用該 alpha（依賴 T030、T031）。
- [X] T033 [US4] 依 `specs/003-combat-vfx-cone-ammo/quickstart.md` 在 50%、78%、90% 與越界值完成無頭渲染及手動可讀性驗收，並修正 `pvpve_escape/tests/test_config.py` 與 `pvpve_escape/tests/test_rendering.py` 的回歸斷言。

**檢查點**：只淡化資訊面板背景；不以全螢幕 overlay 取代局部 surface，也不能讓戰鬥物件或重要文字隨 GUI alpha 變淡。

---

## 階段 7：收尾與跨功能回歸

**目的**：完成文件記錄、效能與殘留效果檢查、全套回歸，以及符合憲章的分支／PR 追蹤。

- [X] T034 在 `specs/003-combat-vfx-cone-ammo/quickstart.md` 補上實作後測試日期、命令輸出摘要、手動驗收結果與尚未涵蓋的限制，並同步檢查 `specs/003-combat-vfx-cone-ammo/spec.md`、`plan.md` 與 `data-model.md` 沒有過時規則（依賴 T035、T033）。
- [X] T035 在 T036 完成後，於 `pvpve_escape/tests/test_rules.py` 補上並執行破陣者、狙擊者、追獵者與控場者各至少 20 次固定方向飛行測試，觀察至少 10 個更新間隔或抵達最大距離前的路徑，量測速度誤差不超過 ±5%；再執行 `pvpve_escape/tests/` 全套測試、`pvpve_escape/` 編譯檢查與 `git diff --check`，確認既有移動邊界、狙擊連續碰撞、怪物強化、死亡／重生、中央撤離與無人勝利規則仍通過（依賴 T036）。
- [X] T036 在 T013、T020、T028、T033 完成後，於 `pvpve_escape/world.py` 與 `pvpve_escape/rendering.py` 檢查效果過期清理、視覺-only 軌跡數量、同幀命中事件數與 60 FPS 下的幾何繪製成本，移除不必要的重複遍歷但不改變已驗證的結果。
- [X] T037 在 `.specify/feature.json`、`specs/003-combat-vfx-cone-ammo/spec.md`、`specs/003-combat-vfx-cone-ammo/plan.md`、`specs/003-combat-vfx-cone-ammo/tasks.md` 與 Git 分支確認功能識別字一致，並記錄任何分支命名或既有工作區修改衝突後再進入發布流程。
- [x] T038 依 `specs/003-combat-vfx-cone-ammo/` 的規格文件與 `quickstart.md` 驗證結果，已推送 `codex/003-combat-vfx-cone-ammo` 並建立 [PR #3](https://github.com/KGeneral7/pythonSDD/pull/3)；本次流程完成合併與 [v0.1.0 發布標籤](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.1.0)，PR 說明已連結 003、004、005 規格及自動化／手動驗證結果。

---

## 依賴與執行順序

### 階段依賴

- **階段 1 設定**：無前置依賴；T001、T002 可平行，T003 在測試入口建立後執行。
- **階段 2 基礎建設**：依賴階段 1；T004、T005 可平行，T006 依賴 T004 並阻擋所有故事。
- **階段 3 US1（P1）**：依賴階段 2；T007～T009 可先平行建立測試／資料，T010 依賴 T009，接著 T011→T012→T013 依序完成。
- **階段 4 US2（P1）**：T014 先行，T015 依賴 T014；實作 T016→T017→T018→T019→T020，且 T017／T018 需接續 US1 已建立的共用 effect 流程。
- **階段 5 US3（P1）**：依賴階段 2；T021～T023 可平行，T024→T025→T026，T027 可與 T026 後段協調，最後 T028 驗收。
- **階段 6 US4（P2）**：依賴階段 2；T029、T030 可平行，T031→T032→T033。
- **階段 7 收尾**：T036 依賴 T013、T020、T028、T033；接著執行 T035，最後由 T034 記錄驗證結果，再執行 T037→T038。

### 使用者故事依賴

- **US1（P1）**：只依賴基礎建設；是第一個可展示的 MVP 增量。
- **US2（P1）**：規則上可由基礎建設獨立測試，但因與 US1 共用 `characters.py`、`world.py`、`aiming.py`、`rendering.py`，實作需在 US1 的共用 effect 流程完成後接續，避免同檔衝突。
- **US3（P1）**：只依賴基礎建設，可與 US1／US2 的測試及不同檔案工作平行；`world.py` 整合時需依序合併。
- **US4（P2）**：只依賴基礎建設，可與前三個故事平行；渲染檔案修改需排程合併。

### 故事內順序

每個故事均採「先建立會失敗的單元／整合測試 → 修改資料定義 → 修改規則／世界更新 → 修改渲染／輸入整合 → 獨立驗收」；模型與 action metadata 先於使用它們的規則，權威規則先於視覺回饋。

## 平行執行範例

### 使用者故事 1

```text
可平行：T007 pvpve_escape/tests/test_combat_effects.py
可平行：T008 pvpve_escape/tests/test_rendering.py
可平行：T009 pvpve_escape/characters.py
完成 T009 後：T010 pvpve_escape/aiming.py
完成 T004、T006、T009、T010 後：T011 pvpve_escape/world.py
完成 T010、T011 後：T012 pvpve_escape/rendering.py
```

### 使用者故事 2

```text
可平行：T014 pvpve_escape/tests/test_breach_cone.py
接續執行：T015 pvpve_escape/tests/test_aiming.py 與 pvpve_escape/tests/test_breach_cone.py
完成 T009、T014 後：T016 pvpve_escape/characters.py
完成 T016 後：T017、T018 pvpve_escape/world.py（同檔依序執行）
完成 T017、T018 後：T019 pvpve_escape/aiming.py 與 pvpve_escape/rendering.py
```

### 使用者故事 3

```text
可平行：T021 pvpve_escape/tests/test_rules.py
可平行：T022 pvpve_escape/tests/test_ammo_lifecycle.py
可平行：T023 pvpve_escape/tests/test_main.py
完成 T021 後：T024 pvpve_escape/rules.py
完成 T022、T024 後：T025 pvpve_escape/world.py
完成 T023、T025 後：T026 pvpve_escape/controllers.py 與 pvpve_escape/main.py
```

### 使用者故事 4

```text
可平行：T029 pvpve_escape/tests/test_config.py
可平行：T030 pvpve_escape/tests/test_rendering.py
完成 T029 後：T031 pvpve_escape/config.py
完成 T030、T031 後：T032 pvpve_escape/rendering.py
```

## 實作策略

### MVP 優先

1. 完成階段 1 設定與階段 2 基礎建設。
2. 完成階段 3 US1，先讓六角色／大招／配件有可辨識且與實際結果一致的回饋。
3. 執行 T013 的獨立驗收後再擴充破陣者扇形、彈藥與 GUI。
4. US1 可展示後再依序加入 US2、US3，最後加入 P2 的 US4。

### 增量交付

1. **第一增量**：US1 完成後可測試所有戰鬥效果與命中回饋。
2. **第二增量**：US2 完成後破陣者五條散彈路徑與命中顆數傷害可獨立驗收。
3. **第三增量**：US3 完成後少量彈匣的攻擊／恢復取捨可獨立驗收。
4. **第四增量**：US4 完成後所有資訊面板可配置半透明，並執行完整回歸與 PR 發布。

### 多人／多代理策略

1. 共同完成階段 1～2。
2. 一個工作者負責 US1 effect／VFX；一個工作者負責 US2 扇形測試與碰撞；一個工作者負責 US3 彈藥生命週期；另一個工作者負責 US4 GUI 測試與渲染。
3. 由整合者依 `world.py`、`rendering.py`、`tests/test_rendering.py` 的檔案衝突順序合併，再執行階段 7。

## 完成定義

- 所有 T001～T038 任務完成並維持勾選清單格式。
- `spec.md` 的 FR-001～FR-024 與 SC-001～SC-008 均有對應任務、測試或手動驗收。
- 六角色／大招／配件的畫面回饋與規則狀態一致；破陣者五條散彈的命中顆數與傷害成立；攻擊期間彈藥不恢復；GUI alpha 只作用於指定背景。
- `pvpve_escape/tests/`、編譯檢查、`git diff --check` 與 `quickstart.md` 驗收通過。
- PR 連結 `specs/003-combat-vfx-cone-ammo/` 並記錄驗證結果。
