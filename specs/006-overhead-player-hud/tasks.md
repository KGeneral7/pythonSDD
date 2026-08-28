---

description: "玩家頭頂 HUD 與個人戰鬥資訊的實作任務"
---

# 任務：玩家頭頂 HUD 與個人戰鬥資訊

**輸入**：`specs/006-overhead-player-hud/` 下的 `spec.md`、`plan.md`、`research.md`、`data-model.md`、`contracts/` 與 `quickstart.md`
**功能識別字**：`006-overhead-player-hud`
**專案結構**：單一 Pygame 桌面專案；主要程式碼位於 `pvpve_escape/rendering.py`，渲染測試位於 `pvpve_escape/tests/test_rendering.py`
**測試策略**：依憲章與功能規格，先建立/更新可重複的 unittest，再完成實作；最後執行完整測試與手動遊玩流程。

## 任務格式

每項任務都使用包含 checkbox、Task ID、可選 `[P]` 與故事標籤的清單格式。`[P]` 表示可在不碰撞同一檔案未完成變更的情況下平行處理；`[US1]`、`[US2]`、`[US3]` 對應功能規格中的使用者故事。

## 階段 1：準備（共用基礎）

**目的**：完成治理前置條件與既有測試環境確認。

- [X] T001 在 `specs/006-overhead-player-hud/plan.md` 核對功能識別字、規格資料夾與已建立的 `codex/006-overhead-player-hud` 分支一致，確認後續實作不在 `main` 上進行。
- [X] T002 在 `pvpve_escape/tests/test_rendering.py` 建立本功能可重用的 headless Pygame Surface、字型初始化與清理 fixture，沿用既有 `SDL_VIDEODRIVER="dummy"` 設定，不新增第三方套件。

**檢查點**：分支治理狀態已明確，且 `pvpve_escape/tests/test_rendering.py` 可以在無視窗環境建立 Surface 並執行既有渲染測試。

---

## 階段 2：基礎建設（所有故事的阻塞前置）

**目的**：建立頭頂資訊共用的座標、格式化與可見性邊界，避免三個故事各自實作不同規則。

**⚠️ 重要**：本階段完成前，不開始任何使用者故事的 UI 行為實作。

- [X] T003 [P] 在 `pvpve_escape/rendering.py` 整理頭頂 HUD 的共用排版常數與私有 helper 介面，明確區分玩家身份/生命公開列、本機資源列、`show_private_info` 顯示參數、合法數值夾取與世界座標到螢幕座標的責任；定義 240 像素最大寬度、8 像素邊界與超長身份文字省略規則，並保留現有 `_draw_health_bar()` 對怪物的用途。
- [X] T004 [P] 在 `pvpve_escape/tests/test_rendering.py` 加入可觀察繪製呼叫或像素顏色的測試輔助函式，能斷言文字內容、配件藍/灰顏色、玩家頭頂座標與公開/私有元素集合，而不依賴即時滑鼠或完整遊戲迴圈。

**檢查點**：共用測試輔助與渲染邊界已準備好；`pvpve_escape/models.py`、`pvpve_escape/world.py`、`pvpve_escape/controllers.py` 不需要因本功能新增狀態或輸入介面。

---

## 階段 3：使用者故事 1——在玩家頭上讀取自己的戰鬥狀態（優先級：P1）🎯 MVP

**目標**：移除本機玩家固定面板，讓本機角色上方顯示身份、生命、彈藥、配件、大招與強化，並隨世界座標/鏡頭更新。

**獨立測試**：建立一個包含本機玩家的可控 `PlayerState`，繪製後確認頭頂有生命條/數值、彈藥分段、配件圓圈、大招百分比與強化層數；改變玩家位置或鏡頭後確認繪製座標跟著變更；確認左上固定玩家面板不再繪製，右上倒數與撤離、底部非攻擊控制列及玩家名單仍在。

### US1 測試（先寫測試）

- [X] T005 [US1] 在 `pvpve_escape/tests/test_rendering.py` 先加入本機頭頂 HUD 的失敗測試：驗證身份/生命公開資訊、彈藥 `0`/滿額分段與數值、配件可用/冷卻/死亡狀態、大招 `0%`/`100%`、強化層數，以及至少 20 次同一玩家移動/鏡頭變更後座標仍以玩家為基準。

### US1 實作

- [X] T006 [US1] 在 `pvpve_escape/rendering.py` 實作 `_draw_player_overlay()` 的身份列、生命條/數值與可選本機私有列；依 `show_private_info` 繪製彈藥分段與數值、配件圓圈、大招百分比及強化層數，沿用 `config.py` 的藍色與灰色，並對生命/彈藥/能量做合法範圍夾取，不在此任務建立第二套 viewer 判定。
- [X] T007 [US1] 在 `pvpve_escape/rendering.py` 更新 `draw_world()` 的存活與死亡玩家繪製分支，集中計算 `show_private_info = player.player_id == viewer_id` 後傳給 `_draw_player_overlay()`，使覆蓋層每幀由 `_screen_point()`/`world_to_screen()` 的玩家螢幕座標計算，並套用 240 像素最大寬度、8 像素邊界與身份文字省略規則。
- [X] T008 [US1] 在 `pvpve_escape/rendering.py` 移除 `draw_hud()` 左上固定玩家戰鬥面板及其玩家私有資訊/死亡倒數/固定攻擊提示，並從底部控制列移除左鍵普攻、右鍵大招與 Space 配件提示；保留函式簽名、本機撤離進度、右上倒數/撤離進度、移動/Tab/F1 等非攻擊提示、玩家名單與開發者提示。
- [X] T009 [US1] 在 `pvpve_escape/tests/test_rendering.py` 執行並修正 US1 的聚焦測試：對彈藥 0/滿額、大招 0/100、配件可用/冷卻/死亡與生命邊界各重複至少 20 次，確認本機完整頭頂資訊可讀、配件顏色不留舊值、數值不超界，且固定左上玩家面板不再出現。

**檢查點**：只完成 US1 時，本機玩家已能在戰鬥中靠頭頂 HUD 讀取自己的完整狀態，且既有戰鬥更新規則與全域 HUD 未被改變；配件冷卻死亡生命週期依後續審查補充任務明確處理。

---

## 階段 4：使用者故事 2——以有限資訊辨識其他玩家（優先級：P1）

**目標**：讓其他可見玩家只顯示身份與生命，不能從頭頂 UI 得知對方彈藥、配件、大招、強化或死亡倒數。

**獨立測試**：使用包含 6 名玩家的測試局，將其他玩家分別設為滿血/受傷、彈藥不同、配件可用/冷卻、大招充滿、具有強化及死亡，確認每個其他玩家的頭頂只有身份與生命；同畫面中的本機玩家仍保有 US1 的完整私有列。

### US2 測試（先寫測試）

- [X] T010 [US2] 在 `pvpve_escape/tests/test_rendering.py` 先加入其他玩家資訊隔離測試：對 `viewer_id=0` 的其他存活/死亡玩家，斷言沒有彈藥文字或分段、配件圓圈/顏色、大招百分比、強化層數與死亡倒數，但仍有玩家編號/角色名稱與生命條/數值。

### US2 實作

- [X] T011 [US2] 在 `pvpve_escape/rendering.py` 整理其他玩家死亡分支的繪製，讓死亡圖示與公開身份/生命資訊沿用 T007 的共享 overlay 入口，移除該分支任何私有資源呼叫；不得修改或複製 `show_private_info` 的集中判定。
- [X] T012 [US2] 在 `pvpve_escape/tests/test_rendering.py` 執行並修正 US2 隔離測試，覆蓋 6 名玩家、至少 20 次資源狀態組合/查看情境的可重複迴圈，確認本機與其他玩家的可見元素集合始終不同且符合 UI 契約。

**檢查點**：US1 與 US2 同時完成時，本機可看到自己的完整狀態，其他玩家仍能被辨識並看到生命，但任何對方私有戰鬥資源不會出現在頭頂。

---

## 階段 5：使用者故事 3——在選角時理解攻擊操作（優先級：P2）

**目標**：在選角頁提供普攻、大招、配件及角色特殊操作提示，並確保戰鬥畫面不再重複固定攻擊提示。

**獨立測試**：逐一繪製六種角色卡片，確認每張卡片有共通按鍵/攻擊提示；狙擊者包含按住左鍵蓄力、放開射擊；吸能者包含按住左鍵持續引導、放開停止；戰鬥 HUD 不含原固定攻擊提示。

### US3 測試（先寫測試）

- [X] T013 [US3] 在 `pvpve_escape/tests/test_rendering.py` 先加入選角頁提示測試，透過既有角色定義驗證六種角色都有普攻/大招/配件操作文字，且 `SNIPER`、`SIPHONER` 特殊提示存在；同時斷言 `draw_hud()` 的戰鬥畫面與底部控制列不再包含固定攻擊提示。

### US3 實作

- [X] T014 [US3] 在 `pvpve_escape/rendering.py` 新增由 `CharacterDefinition.primary_kind`、角色 ID 與既有攻擊參數推導的選角提示 helper，更新角色卡片布局以顯示一般攻擊、狙擊蓄力、吸能引導、右鍵大招與 Space 配件提示，並避免卡片/文字超出選角頁。
- [X] T015 [US3] 在 `pvpve_escape/tests/test_rendering.py` 執行並修正 US3 測試，確認選角索引 0–5、預設角色與重新開始流程均能繪製提示，Q/W/E 能更新 `selected_tactical_index`，且提示資料來自既有角色定義而非另一套規則表。

**檢查點**：三個故事完成後，玩家在開始遊戲前能理解角色操作；進入戰鬥後不會再看到固定左上攻擊提示，且不改變按鍵綁定或技能行為。

---

## 階段 6：收尾與跨故事驗證

**目的**：完成文件同步、全套回歸與規格要求的完整手動流程。

- [X] T016 [P] 在 `specs/006-overhead-player-hud/quickstart.md` 根據實作後的實際畫面/按鍵/測試結果補充必要驗證備註，保持手動驗收清單與 `plan.md`、UI 契約的元素名稱一致。
- [X] T017 在 `pvpve_escape/tests/test_main.py`、`pvpve_escape/tests/test_config.py` 與 `pvpve_escape/tests/test_rendering.py` 執行完整 unittest 回歸，明確確認角色選擇、Q/W/E 配件選擇與 `selected_tactical_index`、比賽倒數、撤離、玩家名單、技能效果、死亡重生、結果畫面與既有設定沒有回歸。
- [X] T018 在 `pvpve_escape/` 執行 `compileall`，並依 `specs/006-overhead-player-hud/quickstart.md` 完成一次按 `1`–`6` 選角、按 Q/W/E 切換配件、移動→攻擊/資源變化→死亡重生→中央撤離→結算的手動流程；將任何實際失敗先記錄在該文件，再修正最相關的渲染邏輯或測試。

---

## 審查補充：死亡生命週期與中央倒數

**目的**：追蹤人工驗收後確認的本機死亡倒數、配件冷卻死亡生命週期，以及 code review 發現的頭頂排版與強化上限顯示修正。

- [X] T019 [US1] 在 `pvpve_escape/tests/test_rendering.py` 加入本機死亡中央倒數測試，確認使用大型字型、定位於畫面中心、倒數結束不顯示，且其他玩家死亡不會觸發本機中央倒數。
- [X] T020 [US1] 在 `pvpve_escape/rendering.py` 新增本機死亡中央倒數繪製，並將頭頂資訊整組做上下邊界夾取；強化文字同時顯示目前層數與 `MAX_UPGRADE_STACKS` 上限。
- [X] T021 [US1] 在 `pvpve_escape/tests/test_rules.py` 加入配件冷卻死亡生命週期回歸測試，重複確認死亡不重置、死亡期間不倒數、重生後才繼續倒數。
- [X] T022 [US1] 在 `pvpve_escape/rules.py` 修正配件冷卻生命週期：死亡與重生不重設 `tactical_cooldown`，且只在玩家存活時遞減。
- [X] T023 在 `specs/006-overhead-player-hud/` 同步中央死亡倒數、配件冷卻生命週期、強化上限與本地 review 驗證結果，保持 `spec.md`、`plan.md`、`research.md`、`data-model.md`、UI 契約、checklist 與 `quickstart.md` 一致。

**歷史檢查點**：原始補充變更已由聚焦測試、完整回歸、編譯檢查、差異檢查與人工遊玩驗收共同確認；後續 viewport 修正與交付由 T024–T026 追蹤。

---

## 審查補充二：其他玩家離開 viewport 時移除頭頂血量條

**目的**：修正其他玩家離開目前畫面視野後，頭頂公開資訊因邊界夾取而殘留在畫面邊緣的問題；本機玩家仍維持既有「隨時顯示」規則。

- [X] T024 [US2] 在 `pvpve_escape/tests/test_rendering.py` 加入 viewport 邊界回歸測試，重複驗證其他玩家從左、右、上、下離開時不再呼叫頭頂 overlay，且回到視野內後恢復；同時確認本機玩家仍被繪製。
- [X] T025 [US2] 在 `pvpve_escape/rendering.py` 的 `draw_world()` 於世界座標投影後加入其他玩家頭頂 overlay 的螢幕錨點剔除，跳過 viewport 外玩家的公開資訊但保留既有角色圖形裁切，不改變地形可見性或本機玩家例外。
- [X] T026 在 `specs/006-overhead-player-hud/` 同步 viewport 可見性需求、資料模型、UI 契約、測試計畫與快速驗證步驟，並確認文件中的 FR/SC/任務對應一致。
- [X] T027 在完成文件、測試與人工驗收後，提交 [PR #10](https://github.com/KGeneral7/pythonSDD/pull/10)、squash merge 至 `main`，並以合併 commit `e9aa3b466ef197bba312d30c11b23dd7703b31fc` 發布 [v0.3.1](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.3.1)。

**檢查點**：其他玩家離開 viewport 時不再留下血量條或其他頭頂資訊，回到視野內恢復；聚焦渲染測試、完整回歸、編譯、headless 啟動、差異檢查、SDD 分析與新增情境人工確認均已完成。

---

## 依賴與執行順序

### 階段依賴

- **階段 1**：無程式依賴；T001 是憲章第 VII 項的環境前置，T002 準備渲染測試環境。
- **階段 2**：依賴 T001、T002；T003 與 T004 可平行執行，完成後才開始使用者故事。
- **US1（階段 3）**：依賴階段 2；T005 必須先於 T006–T008，T009 是 US1 檢查點。
- **US2（階段 4）**：依賴 US1 的頭頂覆蓋層入口（T006–T008）；T010 必須先於 T011，T012 是 US2 檢查點。
- **US3（階段 5）**：依賴階段 2；與 US1/US2 的概念上可平行，但因實作與測試都集中在 `pvpve_escape/rendering.py`/`pvpve_escape/tests/test_rendering.py`，單一工作者應在 US1/US2 後依序執行 T013–T015。
- **收尾（階段 6）**：依賴所有要交付的使用者故事；T016 可與回歸準備平行，T017/T018 必須在程式與測試穩定後執行。
- **審查補充**：依賴階段 6；T019、T021 必須先於各自的實作修正 T020、T022，T023 在程式、測試與驗證結果穩定後完成。
- **審查補充二**：依賴 US2 的既有 overlay 入口與審查補充；T024 先建立視野邊界回歸測試，再由 T025 實作剔除，T026 在程式與測試完成後同步文件。
- **發布收尾**：依賴 T026 與所有驗證結果；T027 完成 PR、合併與 v0.3.1 發布紀錄。

### 使用者故事完成順序

```text
T001 → T002 → (T003 ∥ T004)
                     ↓
             T005 → T006 → T007 → T008 → T009  [US1 / MVP]
                                              ↓
             T010 → T011 → T012              [US2]
                                              ↓
             T013 → T014 → T015              [US3]
                                              ↓
                             T016 ∥ T017 → T018

T024 → T025 → T026                         [US2 viewport 修正]
```

US3 的規格行為不依賴其他玩家的隱私分支，但實際檔案相同，因此預設採序列執行以降低合併衝突；若多人協作，可讓一人處理選角卡片、另一人處理測試，但需先協調 `rendering.py` 與 `test_rendering.py` 的區段。

## 可平行處理範例

### 基礎階段

```text
任務：T003 在 pvpve_escape/rendering.py 建立共用頭頂 HUD 排版/夾取介面
任務：T004 在 pvpve_escape/tests/test_rendering.py 建立繪製觀察測試輔助
```

兩項使用不同檔案，且都只依賴 T001/T002，可平行執行。

### 使用者故事 3（具備額外人力時）

```text
任務：T013 在 pvpve_escape/tests/test_rendering.py 先補選角提示失敗測試
任務：T016 在 specs/006-overhead-player-hud/quickstart.md 準備收尾驗證記錄欄位
```

T016 不修改程式碼，可在 US3 實作期間準備；T013 與 T014 仍因同一測試/渲染檔案通常應序列執行。

## 實作策略

### 先交付 MVP（僅 US1）

1. 完成階段 1 的 Git 治理與 headless 測試準備。
2. 完成階段 2 的共用排版/測試邊界。
3. 先寫並完成 US1 測試與實作，移除左上固定玩家面板。
4. 在 T009 停下，執行 US1 聚焦測試與手動移動/資源狀態驗證。
5. 若玩家頭頂完整資訊與全域 HUD 都正常，再進入 US2 隱私隔離。

### 增量交付

1. US1：本機完整頭頂 HUD + 固定玩家面板移除。
2. US2：其他玩家只看身份與生命，完成資訊公平性。
3. US3：選角頁攻擊提示與特殊角色操作說明。
4. 收尾：完整測試、編譯與全流程手動驗收。

每個檢查點都應保留可啟動、可操作的版本；不要把角色資料、戰鬥更新或控制器重構混入本功能。

## 追蹤備註

- 任務只規劃 `pvpve_escape/rendering.py` 與 `pvpve_escape/tests/test_rendering.py` 的功能變更；本次 T026 另同步既有 SDD 文件；`models.py`、`world.py`、`controllers.py` 維持既有資料與規則。
- `specs/006-overhead-player-hud/plan.md` 已記錄原始功能分支 `codex/006-overhead-player-hud`；T001 是原始功能的歷史治理任務，本次小型 viewport 維護修正使用 `codex/fix-offscreen-player-hud`，不得以刪除/重設使用者檔案的方式處理。
- 所有測試任務都明確對應規格的可觀察行為；完成任務後將勾選狀態與實際測試結果更新在本檔案或相關驗證文件中。
