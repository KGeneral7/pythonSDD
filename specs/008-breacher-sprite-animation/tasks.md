# 任務：破陣者 Q 版像素角色與八方向動畫

**輸入**：`specs/008-breacher-sprite-animation/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md` 與 `quickstart.md`

**前置條件**：已完成規格、研究、技術計畫與資料模型；本專案使用 Python 3.11+、Pygame 與 `unittest`。

**測試策略**：本功能的可見行為需要可重複驗證，因此包含方向、幀選擇、狀態更新、資產載入、fallback、繪製與既有功能回歸測試。

**組織方式**：任務依使用者故事分階段排列；每個故事都包含目標、獨立測試與可追蹤的實作任務。

## Phase 1：Setup（共用素材與目錄）

**目的**：將候選圖片整理成可驗證、可由遊戲使用的專案資產。

- [X] T001 [P] 使用 `pixel-character-animation` 技能驗證並整理 8 張待機圖片至 `pvpve_escape/assets/characters/breacher/idle/`，確認每張為 1024×1024、四角透明、角色不貼邊，並通過俯視角、像素群、槍盾分離與手部連接人工檢查。
- [X] T002 [P] 使用 `pixel-character-animation` 技能驗證並整理 32 張四格移動圖片至 `pvpve_escape/assets/characters/breacher/move/<direction>/`，確認每張為 1024×1024、四角透明，八方向與每方向四格完整，且同一方向動畫幀的非透明內容中心偏移不超過 16 個來源像素。
- [X] T003 [P] 使用 `pixel-character-animation` 技能驗證並整理 32 張四格攻擊圖片至 `pvpve_escape/assets/characters/breacher/attack/<direction>/`，確認每張為 1024×1024、四角透明，八方向與每方向四格完整，且同一方向動畫幀的非透明內容中心偏移不超過 16 個來源像素；另通過槍盾分離、手部連接與俯視角人工檢查。
- [X] T004 彙整 72 張正式素材的方向、狀態、幀索引與品質檢查結果至 `specs/008-breacher-sprite-animation/quickstart.md`。

---

## Phase 2：Foundational（阻塞所有使用者故事的基礎）

**目的**：建立資產索引、動畫狀態與共用繪製入口；本階段完成前不得開始使用者故事整合。

**⚠️ 重要**：所有使用者故事都依賴本階段完成。

- [X] T005 [P] 將破陣者圖片顯示尺寸、移動幀時間、攻擊幀時間、方向數與幀數常數加入 `pvpve_escape/config.py`，並保留現有遊戲時間步長設定。
- [X] T006 [P] 在 `pvpve_escape/models.py` 新增具預設值的 `PlayerAnimationState`，保存 `facing_direction_index`、移動狀態、移動經過時間、攻擊經過時間與 `attack_hold`，避免影響既有 positional 建構。
- [X] T007 建立 `pvpve_escape/sprites.py`，實作八方向量化、`idle`／`move`／`attack` 路徑組合、圖片尺寸與透明度驗證、最近鄰縮放及記憶體快取；載入失敗時回傳可辨識的不可用結果（依賴 T001～T003、T005）。
- [X] T008 在 `pvpve_escape/rendering.py` 建立共用 `draw_player_visual` 繪製入口，讓破陣者依請求選擇像素圖片，圖片不可用時呼叫既有幾何繪製；其他角色維持原本繪製路徑（依賴 T006、T007）。
- [X] T009 擴充 `pvpve_escape/tests/test_helpers.py`，提供清除破陣者圖片快取與錯誤紀錄的 headless 測試支援（依賴 T007）。
- [X] T010 在 `pvpve_escape/tests/test_sprite_animation.py` 新增資產完整性、透明背景、八方向索引、四格範圍、快取命中與無效查詢的基礎測試（依賴 T007、T009）。

**檢查點**：72 張素材可被索引，方向與資產驗證測試通過，且共用繪製入口能在圖片不可用時安全回退。

---

## Phase 3：使用者故事 1——對局中使用破陣者像素角色（優先級：P1，MVP）

**目標**：在實際對局中讓破陣者依八個瞄準方向顯示待機、移動與攻擊動畫，不改變任何遊戲規則。

**獨立測試**：選擇破陣者進入對局，依序測試八個瞄準方向、移動、普攻、戰術技能、終極技能、攻擊優先級與死亡重生。

### 使用者故事 1 的測試

- [X] T011 [US1] 先在 `pvpve_escape/tests/test_sprite_animation.py` 加入移動狀態、四格循環、攻擊優先級、攻擊完成後恢復狀態的測試，確認測試在功能尚未完成時能辨識失敗（依賴 T006、T010）。

### 使用者故事 1 的實作

- [X] T012 [US1] 在 `pvpve_escape/world.py` 的玩家輸入與移動更新流程中保存有效瞄準方向、移動狀態並推進移動動畫時間，不改變位置、碰撞或速度計算（依賴 T006、T010）。
- [X] T013 [US1] 在 `pvpve_escape/world.py` 的共同動作套用流程中，為普攻、戰術技能與終極技能啟動攻擊動畫；對持續型技能只延長維持時間而不重設幀（依賴 T012）。
- [X] T014 [US1] 在 `pvpve_escape/rules.py` 的死亡、重生與計時流程清除或初始化破陣者動畫狀態，避免死亡標記或上一條命的攻擊幀殘留（依賴 T006、T013）。
- [X] T015 [US1] 在 `pvpve_escape/rendering.py` 將存活玩家的繪製接到共用 `draw_player_visual`，依攻擊優先級、移動狀態、面向與幀索引選圖，並保留瞄準線、血量與狀態資訊，不繪製常駐角色底圈（依賴 T008、T012～T014）。
- [X] T016 [US1] 在 `pvpve_escape/tests/test_rendering.py` 新增 headless 對局繪製測試，覆蓋八方向、待機、移動、攻擊優先於移動、攻擊完成後恢復，以及死者仍顯示原有死亡記號（依賴 T015）。
- [X] T017 [US1] 依 `specs/008-breacher-sprite-animation/quickstart.md` 執行 MVP 手動驗證並記錄八方向、移動、三種攻擊行為與死亡重生結果（依賴 T016）。

**檢查點**：破陣者可在對局中完整使用八方向待機、移動與攻擊動畫；此時即達到可展示的 MVP。

---

## Phase 4：使用者故事 2——選角與玩家列表保持一致（優先級：P2）

**目標**：讓選角卡片與對局玩家列表使用破陣者待機像素外觀，同時維持文字與資訊層可讀。

**獨立測試**：在選角頁選擇破陣者，進入對局並查看玩家列表，確認兩處都顯示破陣者像素待機外觀。

### 使用者故事 2 的測試

- [X] T018 [US2] 在 `pvpve_escape/tests/test_rendering.py` 新增選角卡片與玩家列表使用破陣者待機圖片的 headless 測試，並驗證角色名稱、狀態文字與面板仍可見（依賴 T008、T016）。

### 使用者故事 2 的實作

- [X] T019 [US2] 在 `pvpve_escape/rendering.py` 將 `draw_selection` 的破陣者圖示改接共用繪製入口，使用固定待機方向與選角顯示尺寸，其他角色仍使用幾何圖形（依賴 T008、T018）。
- [X] T020 [US2] 在 `pvpve_escape/rendering.py` 將 `_draw_player_roster` 的破陣者圖示改接共用繪製入口，調整縮小尺寸以避免遮住名稱與狀態文字，並補齊對應測試驗證（依賴 T019）。

**檢查點**：選角、對局與玩家列表的破陣者外觀一致，原有資訊層不被圖片遮擋。

---

## Phase 5：使用者故事 3——素材異常時仍可遊玩（優先級：P2）

**目標**：任何單張素材缺失、無法讀取、尺寸不一致或透明度不合格時，遊戲仍以幾何圖形顯示破陣者並繼續運作。

**獨立測試**：以測試替身模擬單張圖片缺失、讀取錯誤與不透明背景，分別繪製選角與對局畫面，確認不崩潰且可回退。

### 使用者故事 3 的測試

- [X] T021 [US3] 在 `pvpve_escape/tests/test_sprite_animation.py` 新增缺檔、讀取錯誤、尺寸不一致、無透明像素與部分幀缺失的測試，確認每種情況都回傳不可用結果（依賴 T007、T009）。

### 使用者故事 3 的實作

- [X] T022 [US3] 在 `pvpve_escape/sprites.py` 完成單張資產錯誤的記錄與一次性警告，確保快取不會重複讀取失敗檔案或每幀重複記錄（依賴 T021）。
- [X] T023 [US3] 在 `pvpve_escape/rendering.py` 驗證共用繪製入口對任何不可用幀都選擇幾何 fallback，並確認其他五個角色與三種怪物不會誤載入破陣者素材（依賴 T022）。
- [X] T024 [US3] 在 `pvpve_escape/tests/test_rendering.py` 補充 fallback、其他角色、怪物、死亡標記與重新開始流程的回歸測試（依賴 T023）。
- [X] T025 [US3] 依 `specs/008-breacher-sprite-animation/quickstart.md` 執行素材異常手動驗證，記錄遊戲不中斷、角色仍可見且既有行為不變（依賴 T024）。

**檢查點**：資產錯誤被限制在視覺層，破陣者與既有遊戲流程仍可操作。

---

## Phase 6：Polish 與跨故事驗證

**目的**：完成文件、效能、回歸與最終交付前檢查。

- [X] T026 [P] 依 `pvpve_escape/sprites.py`、`pvpve_escape/models.py` 與 `pvpve_escape/rendering.py` 的實際實作補上必要的繁體中文註解，說明八方向量化、動畫時間與 fallback 的原因。
- [X] T027 [P] 對照 `specs/008-breacher-sprite-animation/data-model.md` 與 `specs/008-breacher-sprite-animation/research.md`，記錄實際欄位、路徑或決策差異。
- [X] T028 [P] 執行 `specs/008-breacher-sprite-animation/quickstart.md` 的素材數量、1024×1024 尺寸、四角透明、非透明像素不貼邊、同方向幀中心偏移不超過 16 個來源像素與人工視覺驗證，確認 72/72 張圖片全部符合交付條件。
- [X] T029 執行完整回歸測試 `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`，將通過結果記錄到 `specs/008-breacher-sprite-animation/quickstart.md`。
- [X] T030 執行 `specs/008-breacher-sprite-animation/quickstart.md` 的 10 秒連續遊玩、方向切換與效能驗證，確認平均每秒至少 60 個畫面更新、單幀間隔不超過 100 毫秒、沒有閃爍／裁切／空白角色，且沒有每幀重新載入圖片。
- [X] T031 檢查 `git diff` 與 `git status`，確認變更只包含 `008-breacher-sprite-animation` 規格、破陣者資產、必要遊戲模組與測試，並將最終驗證結果整理到 `specs/008-breacher-sprite-animation/quickstart.md`。
- [X] T032 [US1] 依最新視覺調整逐張重新讀取來源 PNG、擷取實際角色／槍／盾區域，統一縮放並置中於 50×50 顯示畫布，移除存活角色常駐底圈與玩家外框，並以 headless 渲染測試確認死亡／護盾／控場標記不受影響（依賴 T015、T024）。

> T031 的「只包含」限於本功能交付範圍；工作樹中既有的 `day3/` 與 `sample.png` 等使用者檔案不屬於本功能，保留且不納入本功能變更。

## 依賴與執行順序

### 階段依賴

- **Setup（Phase 1）**：無前置依賴；T001～T003 可平行，T004 等三組素材完成後執行。
- **Foundational（Phase 2）**：依賴 Setup；T005 與 T006 可平行，T007 依賴素材與 T005，T008～T010 依賴共用資產基礎。
- **User Story 1（Phase 3）**：依賴 Foundational；完成後即為 MVP。
- **User Story 2（Phase 4）**：依賴 Foundational 與共用繪製入口 T008；因會修改同一個 `rendering.py`，與 US1 的繪製整合需序列執行。
- **User Story 3（Phase 5）**：依賴 Foundational 與共用繪製入口 T008；其測試可先於 fallback 細節實作，但與其他會修改相同測試檔的任務需序列執行。
- **Polish（Phase 6）**：依賴所有要交付的使用者故事完成。

### 使用者故事順序

- **US1（P1）**：Foundational 完成後開始，無需等待 US2／US3；是 MVP 交付範圍。
- **US2（P2）**：可在 Foundational 完成後開始，但 `rendering.py` 的整合應排在 US1 的對局繪製整合之後。
- **US3（P2）**：可在 Foundational 完成後開始，但 fallback 最終驗證應在共用繪製入口完成後執行。

### 任務內部規則

- 測試任務先建立並確認能捕捉未完成行為，再完成對應實作。
- 先完成模型與資產索引，再修改世界更新，最後接入繪製呼叫點。
- 同一檔案的修改任務不得由多個執行者平行處理；不同檔案且無未完成依賴的任務才可標記 `[P]`。
- 每個檢查點都要能啟動遊戲或執行對應測試，不能把所有變更集中到最後才驗證。

## 平行執行範例

### Setup 素材準備

```text
Task: "T001 驗證並整理 8 張待機圖片至 pvpve_escape/assets/characters/breacher/idle/"
Task: "T002 驗證並整理 32 張移動圖片至 pvpve_escape/assets/characters/breacher/move/"
Task: "T003 驗證並整理 32 張攻擊圖片至 pvpve_escape/assets/characters/breacher/attack/"
```

### Foundational 不同檔案

```text
Task: "T005 在 pvpve_escape/config.py 加入動畫常數"
Task: "T006 在 pvpve_escape/models.py 加入 PlayerAnimationState"
```

### 使用者故事之間

Foundational 完成後，若由多人執行，可同時處理：

```text
Task: "US1 在 pvpve_escape/world.py 實作對局動畫狀態"
Task: "US2 在 pvpve_escape/tests/test_rendering.py 準備選角與玩家列表測試"
Task: "US3 在 pvpve_escape/tests/test_sprite_animation.py 準備資產 fallback 測試"
```

實際合併時，涉及同一檔案的任務必須依依賴順序整合，避免互相覆蓋。

## 實作策略

### MVP 優先

1. 完成素材 Setup 與 Foundational。
2. 完成 US1：對局中的破陣者八方向待機、移動與攻擊動畫。
3. 執行 US1 獨立測試與手動驗證。
4. 在 US1 通過後停止並展示 MVP，再繼續 US2 與 US3。

### 漸進交付

1. Setup + Foundational：資產可索引、狀態可保存、圖片失敗可安全處理。
2. US1：對局動畫可用，形成第一個可玩的版本。
3. US2：選角與玩家列表視覺一致。
4. US3：補足資產錯誤與既有角色／怪物回歸保護。
5. Polish：完成完整測試、手動驗證、文件同步與交付檢查。
