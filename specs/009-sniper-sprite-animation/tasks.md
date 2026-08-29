# 任務：狙擊者 Q 版像素外觀與八方向動畫

**輸入**：`specs/009-sniper-sprite-animation/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md` 與 `quickstart.md`

**前置條件**：已完成需求規格、Phase 0 研究與 Phase 1 設計；本專案使用 Python 3.11+、Pygame 與 `unittest`。

**測試策略**：功能規格明確要求資產完整性、headless 繪製、fallback、既有角色回歸與可重複手動驗證，因此每個使用者故事都先建立對應測試，再完成實作。

**組織方式**：任務依資產 Setup、共用基礎與使用者故事優先級排列；每個故事都有獨立測試、實作任務與檢查點。

## Phase 1：Setup（資產與共同前置）

**目的**：建立並驗收狙擊者 72 張正式 PNG，確立可供後續程式測試使用的偵察狙擊兵主視覺。

- [X] T001 在 `pvpve_escape/assets/characters/sniper/` 建立 `idle/`、`move/`、`attack/`；`idle/` 直接放八個方向檔案，`move/` 與 `attack/` 各自放八個方向子目錄，保留每格獨立 PNG 的既定結構。
- [X] T002 使用 `pixel-character-animation` 技能與內建 `image_gen` 生成狙擊者 canonical 主視覺，完成 `pvpve_escape/assets/characters/sniper/idle/down.png`；確認偵察服、長槍、瞄具、深藍／藍灰主色與青藍識別色，並以 `sample.png` 僅作畫法參考。
- [X] T003 [P] 以 T002 的主視覺為身份基準生成其餘 7 張待機圖片至 `pvpve_escape/assets/characters/sniper/idle/`，確認八方向語意與上方三方向的背面表現。
- [X] T004 [P] 以 T002 的主視覺為身份基準生成 32 張四格移動圖片至 `pvpve_escape/assets/characters/sniper/move/<direction>/`，確認每方向四格有交替步伐且不改變角色比例、持槍接點與錨點。
- [X] T005 [P] 以 T002 的主視覺為身份基準生成 32 張四格攻擊圖片至 `pvpve_escape/assets/characters/sniper/attack/<direction>/`，確認每方向四格呈現持槍瞄準／後座變化且沒有漂浮或脫離武器的特效。
- [X] T006 依 `specs/009-sniper-sprite-animation/quickstart.md` 驗收 `pvpve_escape/assets/characters/sniper/` 的 72 張圖片：1024×1024 RGBA、四角透明、`alpha > 0` 像素不貼邊、無裁切、同方向中心偏移不超過 16 個來源像素、頭盔／面罩頭部錨點大小一致，並確認每方向 idle／move／attack 的身體核心聯合外框已標準化、武器外伸不參與本體縮放、走路幀共用比例且朝上未被長槍放大；將資產 QA 結果記錄在該文件的「驗證紀錄」區塊。

---

## Phase 2：Foundational（共用圖片與動畫基礎）

**目的**：在任何使用者故事開始前，建立角色中立的資產規格、載入器與測試基礎；本階段完成前不得進行畫面整合。

**⚠️ 重要**：所有使用者故事都依賴本階段完成。

- [X] T007 [P] 在 `pvpve_escape/config.py` 新增狙擊者資產根目錄、1024 來源畫布、50×50 對局尺寸、54×54 選角尺寸、24×24 玩家列表尺寸與八方向／四格動畫設定，並保留既有 `BREACHER_*` 相容常數。
- [X] T008 在 `pvpve_escape/tests/test_sprite_animation.py` 先加入狙擊者 72 張資產、方向索引、尺寸、透明度門檻、邊界、中心偏移與無效查詢測試，並在 `specs/009-sniper-sprite-animation/quickstart.md` 記錄新增測試前既有 245 個測試案例名稱與通過結果；確認尚未加入狙擊者載入器時測試能辨識缺少功能。
- [X] T009 [P] 在 `pvpve_escape/models.py` 將 `PlayerAnimationState` 的說明與註解改為角色中立，確認不新增欄位、不改變預設值與既有 positional 建構順序。
- [X] T010 在 `pvpve_escape/sprites.py` 將現有載入、驗證、非透明區域擷取、最近鄰縮放與快取流程改為由角色資產規格映射驅動，依角色 `fit_mode` 讓狙擊者使用方向身體核心聯合外框標準化後的 `source_canvas`，武器外伸不參與本體縮放，破陣者維持既有 `visible_extent` 流程；新增 `load_character_sprite()`、`preload_character_sprites(character_id, display_sizes=None)`、`load_sniper_sprite()`、`preload_sniper_sprites(display_sizes=None)` 與角色錯誤查詢介面，省略尺寸時使用各角色 `preload_display_sizes` 規格，並保留 `load_breacher_sprite()`、`preload_breacher_sprites(display_size=50)` 等破陣者既有 wrapper 的呼叫相容性。
- [X] T011 在 `pvpve_escape/tests/test_sprite_animation.py` 補上角色共用載入器、狙擊者快取、50×50／54×54／24×24 三種尺寸預載入、固定顯示尺寸與失敗結果測試，完成 T010 後執行該測試檔確認 72 張狙擊者素材可被索引。

**檢查點**：破陣者原有資產測試持續通過，狙擊者 72 張圖片可被角色中立載入器索引，且無效資產會回傳可辨識的不可用結果。

---

## Phase 3：使用者故事 1——對局中辨識狙擊者（優先級：P1，MVP）

**目標**：在實際對局中讓狙擊者依八個瞄準方向顯示待機、移動與成功攻擊動畫，並維持攻擊優先與既有遊戲規則。

**獨立測試**：選擇狙擊者進入對局，切換八個瞄準方向，測試停止、移動、蓄力放開、戰術配件、終極技能、攻擊優先與死亡／重生。

### 使用者故事 1 的測試

- [X] T012 [US1] 在 `pvpve_escape/tests/test_sprite_animation.py` 新增狙擊者方向量化與 22.5 度分界、移動四格循環、成功普攻／戰術／終極技能啟動攻擊狀態、蓄力未完成／無彈藥／冷卻中／其他失敗條件不啟動、攻擊刷新與 0.24 秒結束、死亡／重生重置測試，確認測試先於對局整合實作建立。
- [X] T013 [US1] 在 `pvpve_escape/tests/test_rendering.py` 新增 headless 對局繪製測試，覆蓋狙擊者八方向、idle／move／attack 請求、攻擊優先於移動、攻擊完成後恢復、上方方向顯示背面、存活時無常駐底圈與死亡／護盾／控場標記保留所需的呼叫結果。

### 使用者故事 1 的實作

- [X] T014 [US1] 在 `pvpve_escape/world.py` 的共同 `_apply_action()` 套用點，讓狙擊者成功建立的普攻、戰術配件與終極技能啟動既有 `start_or_refresh_attack_animation()`，不改變動作傷害、蓄力、冷卻或碰撞。
- [X] T015 [US1] 在 `pvpve_escape/rendering.py` 的 `draw_player_visual()` 依角色選擇狙擊者圖片，使用目前面向與 `current_sprite_request()` 的幀結果；素材不可用時保留幾何 fallback，且不繪製執行期旋轉或鏡像，並保留存活無底圈與死亡／護盾／控場標記的資訊層。
- [X] T016 [US1] 在 `pvpve_escape/main.py` 的資產初始化階段清除共用圖片快取，使用 `preload_character_sprites(character_id)` 依各角色規格對破陣者與狙擊者各預載入 72 個來源幀及三種顯示快取（最多 432 個顯示表面），確保選角、對局與玩家列表繪製期間不重新讀檔，同時保留破陣者舊 wrapper 的單尺寸呼叫相容性。
- [X] T017 [US1] 執行 `pvpve_escape/tests/test_sprite_animation.py` 與 `pvpve_escape/tests/test_rendering.py` 的狙擊者對局測試，修正方向、幀優先級或成功動作觸發問題，直到使用者故事 1 的檢查點通過。

**檢查點**：狙擊者已可在對局中完成八方向待機、移動與攻擊動畫；此時形成可展示的 MVP，且既有破陣者與遊戲規則測試未受影響。

---

## Phase 4：使用者故事 2——不同畫面維持一致外觀（優先級：P2）

**目標**：讓狙擊者在選角卡片、對局角色與玩家列表使用同一套待機／動畫身份，並保持資訊文字可讀。

**獨立測試**：在選角頁查看狙擊者卡片，進入對局後查看狙擊者角色與玩家列表，確認圖片、名稱與狀態資訊均正確。

### 使用者故事 2 的測試

- [X] T018 [US2] 在 `pvpve_escape/tests/test_rendering.py` 新增選角卡片與玩家列表的狙擊者待機圖片測試，確認呼叫使用狙擊者尺寸、名稱與狀態文字仍完整可見，且其他角色仍使用幾何繪製。

### 使用者故事 2 的實作

- [X] T019 [US2] 在 `pvpve_escape/rendering.py` 的 `draw_selection()` 與 `_draw_player_roster()` 傳入狙擊者 54×54／24×24 顯示尺寸，讓兩個畫面經過同一個 `draw_player_visual()` 入口並保留原 UI 文字位置。
- [X] T020 [US2] 執行 `pvpve_escape/tests/test_rendering.py` 的選角與玩家列表測試，確認狙擊者圖示不遮住名稱、生命、狀態或操作提示，並確認破陣者既有 UI 測試持續通過。

**檢查點**：選角、對局與玩家列表的狙擊者視覺身份一致，原有資訊層與其他角色繪製不受影響。

---

## Phase 5：使用者故事 3——素材異常時仍可遊玩（優先級：P2）

**目標**：單張狙擊者素材失效時安全回退幾何外觀，且不影響其他角色、怪物與遊戲流程。

**獨立測試**：模擬狙擊者缺檔、讀取錯誤、尺寸錯誤、不透明背景與部分幀失效，再繪製選角、玩家列表與對局畫面。

### 使用者故事 3 的測試

- [X] T021 [P] [US3] 在 `pvpve_escape/tests/test_sprite_animation.py` 新增狙擊者缺檔、讀取錯誤、尺寸錯誤、四角不透明、`alpha > 0` 空白／邊界與 `alpha >= 64` 顯示區域、無效查詢與一次性警告測試。
- [X] T022 [P] [US3] 在 `pvpve_escape/tests/test_rendering.py` 新增狙擊者不可用時的選角／玩家列表／對局幾何 fallback 測試，包含存活無底圈與死亡／護盾／控場標記保留，以及其他五個角色與三種怪物仍使用原繪製路徑的回歸測試。

### 使用者故事 3 的實作

- [X] T023 [US3] 在 `pvpve_escape/sprites.py` 完成狙擊者資產錯誤的快取與一次性診斷，讓同一資產鍵不重複讀檔或每幀發出警告；在 `pvpve_escape/rendering.py` 確認所有不可用狙擊者幀都回到既有幾何外觀。
- [X] T024 [US3] 執行 `pvpve_escape/tests/test_sprite_animation.py` 與 `pvpve_escape/tests/test_rendering.py` 的 fallback 與回歸測試，確認遊戲不中斷、角色不空白，且其他角色／怪物外觀與行為不變。

**檢查點**：狙擊者資產錯誤被限制在視覺層，選角、玩家列表、對局、死亡標記與既有遊戲操作仍可正常運作。

---

## Phase 6：Polish 與跨故事驗證

**目的**：同步設計文件、完成完整回歸、效能量測、人工驗收與憲章要求的交付前檢查。

- [X] T025 [P] 依實際實作更新 `specs/009-sniper-sprite-animation/data-model.md`、`specs/009-sniper-sprite-animation/research.md` 與 `specs/009-sniper-sprite-animation/quickstart.md`，記錄實際介面、快取鍵、預載入數量與任何設計差異。
- [X] T026 [P] 在 `pvpve_escape/sprites.py`、`pvpve_escape/models.py`、`pvpve_escape/rendering.py` 與 `pvpve_escape/world.py` 補上必要的繁體中文註解，說明方向量化、動畫時間、資產驗證、預載入與 fallback 的原因。
- [X] T027 執行完整回歸：`.\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -q`、`.\.venv\Scripts\python.exe -m compileall -q pvpve_escape` 與 `git diff --check`，以 T008 記錄的基線案例清單核對既有測試全部通過，並確認新增測試全部通過；最終以實際測試輸出數量為準，不把 245/245 當作新增後的總數門檻。
- [X] T028 執行 `specs/009-sniper-sprite-animation/quickstart.md` 的手動端到端驗收：選角、八方向與分界角、背面方向、移動、蓄力射擊、無彈藥／冷卻中、戰術／終極技能、死亡／重生、玩家列表、缺圖 fallback、其他角色／怪物，並將結果記錄至該文件。
- [X] T029 在 `pvpve_escape/tests/test_sprite_performance.py` 新增並執行 headless 10 秒狙擊者繪製效能測試：先預載入兩個像素角色各 72 個來源幀及三種顯示尺寸，再記錄平均 FPS、最大單幀間隔與 `pygame.image.load` 呼叫次數；要求平均至少 60 FPS、最大單幀間隔不超過 100 毫秒、量測期間讀檔次數為 0，並將實際結果記錄至 `specs/009-sniper-sprite-animation/quickstart.md` 的「驗證紀錄」。
- [X] T030 檢查 `git status`、`git diff` 與 `specs/009-sniper-sprite-animation/` 內容，確認交付只包含狙擊者資產、必要程式、測試與 SDD 文件；保留但不納入 `day3/` 與 `sample.png`。
- [X] T031 在 T027～T030 全部通過後，將 `009-sniper-sprite-animation` 功能分支推送至遠端並建立 PR，PR 說明指向 `specs/009-sniper-sprite-animation/` 並附上驗證結果；在 PR 合併前保留本地與遠端功能分支，合併後才依憲章清理分支。

### T031 完成紀錄

- [X] 已建立並合併 [PR #17](https://github.com/KGeneral7/pythonSDD/pull/17) 至 `main`，squash merge 提交為 `39bada5646683a3d7a7e89fa5ced093068789909`。
- [X] 已建立並發布 [v0.7.0 Release](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.7.0)，版本標籤指向上述合併提交。
- [X] 已刪除遠端與本地 `009-sniper-sprite-animation` 功能分支；未追蹤的 `day3/` 與 `sample.png` 保留且未納入提交。

## 依賴與執行順序

### 階段依賴

- **Setup（Phase 1）**：T001 先建立目錄；T002 完成 canonical 主視覺後，T003～T005 可平行生成三類資產；T006 必須等待全部 72 張素材完成。
- **Foundational（Phase 2）**：依賴 T006；T007 與 T009 可平行，T008 在 T007 完成後先建立測試與基線紀錄，T010 實作載入器，T011 在載入器完成後確認基礎功能。
- **使用者故事 1（Phase 3）**：依賴 Phase 2；完成後即為 MVP。T012～T013 在 T011 後先建立測試，再執行 T014～T016 實作。
- **使用者故事 2（Phase 4）**：依賴 US1 的共用繪製入口；T018 先建立測試、T019 實作、T020 驗證，因與 US1 共用 `rendering.py`，採序列執行。
- **使用者故事 3（Phase 5）**：依賴 US2 完成的共用繪製入口；T021～T022 可平行建立測試，T023 實作後執行 T024。
- **Polish（Phase 6）**：依賴所有要交付的使用者故事完成；T027 完成完整回歸後執行 T028 手動驗收、T029 效能量測、T030 交付範圍檢查，最後 T031 才能推送並建立 PR。

### 使用者故事依賴

- **US1（P1）**：Phase 2 完成後開始，無需等待其他使用者故事。
- **US2（P2）**：依賴 US1 的共用圖片繪製入口，但不改變 US1 的對局行為。
- **US3（P2）**：依賴角色載入器與繪製入口；為避免同檔案衝突，排在 US2 後完成最終 fallback 回歸。

### 任務內部規則

- 測試任務必須先建立並確認能捕捉未完成行為，再完成相應實作。
- 資產創意問題必須重新使用角色製作技能生成；只有可判定的透明度、畫布與置中問題可做確定性整理。
- 不得為了狙擊者圖片改動傷害、碰撞、移動速度、彈藥、蓄力、技能效果、死亡重生或怪物行為。
- 同一檔案的修改任務不得平行執行；不同目錄且依賴已完成的任務才可標記 `[P]`。
- 每個檢查點都要能執行對應測試或啟動遊戲，不把所有驗證集中到最後。

## 平行執行範例

### 資產 Setup

完成 T002 後可平行執行：

```text
Task: "T003 生成狙擊者其餘 7 張 idle 圖片至 pvpve_escape/assets/characters/sniper/idle/"
Task: "T004 生成狙擊者 32 張 move 圖片至 pvpve_escape/assets/characters/sniper/move/"
Task: "T005 生成狙擊者 32 張 attack 圖片至 pvpve_escape/assets/characters/sniper/attack/"
```

### Foundational 不同檔案

完成 T006 後可平行執行：

```text
Task: "T007 在 pvpve_escape/config.py 新增狙擊者資產設定"
Task: "T009 在 pvpve_escape/models.py 將 PlayerAnimationState 說明改為角色中立"
```

### 使用者故事 3 測試

在 US2 完成且共用入口穩定後可平行執行：

```text
Task: "T021 在 pvpve_escape/tests/test_sprite_animation.py 建立狙擊者資產失效測試"
Task: "T022 在 pvpve_escape/tests/test_rendering.py 建立狙擊者 fallback 與其他角色回歸測試"
```

## 實作策略

### MVP 優先

1. 完成 Phase 1 資產 Setup 與 Phase 2 共用基礎。
2. 完成 US1：狙擊者對局中的八方向、移動與攻擊動畫。
3. 執行 T017 的獨立測試與手動對局驗收。
4. MVP 通過後再加入選角／玩家列表一致性、完整 fallback 回歸與效能量測。

### 漸進交付

1. Setup + Foundational：72 張資產可驗證、可載入、可快取。
2. US1：對局動畫可用，形成第一個可展示版本。
3. US2：選角與玩家列表使用同一套狙擊者外觀。
4. US3：素材錯誤安全 fallback，其他角色與怪物回歸。
5. Polish：完成完整測試、10 秒效能量測、人工驗收、文件同步與交付前檢查。
6. T031：依憲章推送功能分支並建立 PR；PR 合併前保留分支。
