# 實作計畫：玩家頭頂 HUD 與個人戰鬥資訊

**功能識別字**：`006-overhead-player-hud`
**預定功能分支**：`codex/006-overhead-player-hud`
**本次修正分支**：`codex/fix-offscreen-player-hud`（由 `main` 的 `v0.3.0` 建立之小型維護修正）
**日期**：2026-08-27
**基準發布版本**：`v0.3.0`
**本次預定發布版本**：`v0.3.1`
**規格**：[spec.md](spec.md)

## 摘要

本功能把目前戰鬥畫面左上角的本機玩家固定面板改成附著於玩家世界座標的頭頂 HUD。所有位於地形可見範圍且目前 viewport 內的玩家都保留編號/角色名稱與生命條/數值；只有本機玩家追加彈藥分段、配件藍/灰圓圈、大招百分比與強化層數。原固定面板中的攻擊操作提示移到選角頁角色卡片，並依一般角色、狙擊者與吸能者呈現不同提示；本機玩家死亡時另在畫面中央顯示重生倒數。實作集中在既有 `pvpve_escape/rendering.py`、`pvpve_escape/rules.py` 與相關測試，沿用目前 `PlayerState`、鏡頭轉換、顏色與 Pygame primitive；除明確定義的配件冷卻死亡生命週期外，不改變戰鬥規則或遊戲流程。

## 技術上下文

**語言/版本**：Python 3.11+
**主要相依**：Pygame 2.6.1、專案既有 `config.py`、`models.py`、`characters.py` 渲染資料
**儲存**：不適用；不新增持久化資料或網路同步
**測試**：Python `unittest`、Pygame 最小 Surface 渲染測試、`compileall`、手動遊玩驗收
**目標平台**：Windows 桌面 Pygame 應用程式
**專案類型**：單一桌面遊戲專案
**效能目標**：維持既有遊戲更新/渲染目標（約 60 FPS）；每幀資訊量為目前最多 6 名玩家，不引入額外逐像素或外部資產處理
**限制**：離線執行、不新增套件；頭頂資訊須使用玩家世界座標投影；其他玩家不可取得本機私有資源的顯示，且其公開頭頂資訊只在玩家螢幕錨點位於 viewport 時存在；保留既有輸入、戰鬥、撤離、重生與結果流程
**規模/範圍**：目前一局 6 名玩家、6 種角色；變更主要落在渲染模組、配件冷卻規則、選角卡片與相關單元測試

## 憲章檢查（Phase 0 前）

| 憲章原則 | 判定 | 計畫依據 |
|---|---|---|
| I. 小步驟、可執行變更 | 通過 | 先抽出顯示規則與測試，再修改覆蓋層、選角提示與 HUD，最後做完整流程驗證。 |
| II. 先理解再自動化 | 通過 | 已檢查 `rendering.py`、`models.py`、`characters.py`、`world.py`、既有渲染測試與選角流程；研究決策寫於 [research.md](research.md)。 |
| III. 清楚的 Python 與集中設定 | 通過 | 沿用既有繪製 helper、`config.py` 顏色與字型入口，不新增不必要的抽象層或套件。 |
| IV. 分離輸入、更新、渲染 | 通過 | UI 投影/排版集中在 `rendering.py`；`controllers.py` 輸入介面與 `world.py` 更新流程不變，配件冷卻死亡生命週期只在 `rules.py` 的既有計時／死亡函式中處理。 |
| V. 可驗證的可見行為 | 通過 | 新增公開/私有分支、顏色、邊界、座標跟隨與選角提示測試，並依 [quickstart.md](quickstart.md) 手動驗收。 |
| VI. SDD 文件使用繁體中文 | 通過 | `spec.md`、本計畫及 Phase 0/1 產物均使用繁體中文。 |
| VII. Spec Kit 分支與生命週期 | 通過 | 原始功能使用 `006-overhead-player-hud` 識別字；本次小型維護修正使用 `codex/fix-offscreen-player-hud`，後續 PR、合併與清理依憲章執行。 |

目前沒有待釐清的規格或技術決策；單機觀察者為玩家 0、其他玩家保留身份/生命、配件藍灰意義與全域 HUD 保留範圍均已在規格中確認。

## 專案結構

### 本功能文件

```text
specs/006-overhead-player-hud/
├── spec.md                                  # 功能規格
├── plan.md                                  # 本實作計畫
├── research.md                              # Phase 0 技術研究與決策
├── data-model.md                             # 顯示投影與可見性資料模型
├── quickstart.md                             # 自動化與手動驗證流程
├── contracts/
│   └── overhead-player-hud-ui.md             # 選角/戰鬥 UI 可觀察契約
└── tasks.md                                  # Phase 2 由 $speckit-tasks 產生
```

### 相關程式碼

```text
pvpve_escape/
├── rendering.py                              # 選角、世界、頭頂覆蓋層、死亡倒數與全域 HUD
├── rules.py                                  # 配件冷卻死亡生命週期
├── models.py                                 # 既有 PlayerState/MatchState
├── characters.py                              # 角色攻擊/配件定義與狀態規則
├── world.py                                   # 既有玩家狀態更新與 6 人測試局
├── controllers.py                             # 保持既有輸入綁定
└── tests/
    └── test_rendering.py                     # 頭頂 HUD/選角提示渲染測試
```

**結構決策**：維持單一 Pygame 專案的既有分層。`PlayerState` 是戰鬥狀態來源，`world.py` 繼續更新狀態，`rendering.py` 在每幀把狀態投影成公開或本機私有的頭頂 UI；不建立新的 UI 框架、服務層或資料儲存層。

## 實作設計

### 1. 玩家頭頂覆蓋層與可見性

1. 將 `_draw_player_overlay()` 擴充為接受由呼叫端計算的 `show_private_info`，讓它只負責繪製公開列與可選的本機私有列；`draw_world()` 以目前 `viewer_id`（預設為 0）集中計算 `player.player_id == viewer_id` 的結果。
2. 保留現有生命比例夾取、生命條顏色與身份標籤；調整垂直排版，形成「身份 → 生命條/數值 → 本機私有列」的緊湊區塊，所有座標都由傳入的玩家螢幕點計算。
3. 新增小型私有繪製 helper 或區域繪製邏輯：
   - 彈藥以 `ammo_capacity` 個分段表示，並顯示 `ammo/capacity`；繪製前將數值夾在合法範圍。
   - 配件以單一圓圈表示，使用既有 `EXTRACTION_COLOR` 表示可用，使用既有灰色設定表示冷卻/死亡。
   - 大招顯示夾取至 0–100 的整數百分比。
   - 強化顯示目前層數與既有上限語意。
4. `draw_world()` 在存活與死亡玩家的既有兩條繪製分支都以 `viewer_id` 計算 `show_private_info`，再把布林值傳給覆蓋層；繼續先由 `is_player_visible_to_viewer()` 過濾地形可見性，再以 `_screen_point()` 檢查其他玩家的錨點是否落在 `surface.get_rect()` 內。其他玩家錨點在 viewport 外時跳過其頭頂 overlay 呼叫，避免 overlay 的邊界夾取讓血量條殘留在畫面邊緣；保留既有角色圖形的 Pygame 裁切行為，本機玩家不套用此 overlay 剔除。死亡玩家保留公開身份/生命資訊，本機死亡的中央倒數則由 `draw_hud()` 只依目前 `viewer_id` 的玩家狀態繪製，不得讓其他玩家死亡洩漏倒數或私有列。
5. 保持所有世界座標轉換使用 `_screen_point()`/`world_to_screen()`；不保存覆蓋層的固定螢幕座標。頭頂資訊區塊以不超過 240 像素為最大寬度、左右至少 8 像素邊界，超長身份文字以省略號截斷；必要的邊界夾取只作用於當幀排版位置，不能把資訊搬到全域角落。

### 2. 移除左上固定玩家面板

1. 從 `draw_hud()` 移除左上 `pygame.Rect` 玩家面板及其中的本機生命、攻擊數值、彈藥、能量、強化、配件狀態、死亡倒數、戰鬥攻擊提示與瞄準預覽文字。
2. 保留 `draw_hud(surface, match, input_state, viewer_id)` 的呼叫介面與本機玩家查找，因為撤離進度仍需使用本機玩家的 `extraction_progress`。
3. 保留右上比賽倒數/撤離進度、底部非攻擊控制列（移動、Tab、自動瞄準或 F1 開發者測試）、玩家名單與開發者測試提示；底部不再保留左鍵普攻、右鍵大招或 Space 配件提示；世界中的技能效果、死亡重生與勝負流程不移動、不改規則。
4. 不將移除的玩家私有資訊改放到另一個固定角落；所有即時玩家資源只由頭頂覆蓋層呈現。
5. 本機玩家死亡且 `death_timer` 大於 0 時，`draw_hud()` 使用既有 `draw_text()`／Pygame 字型在畫面中心繪製大型倒數；存活、倒數結束或其他玩家死亡時不繪製該文字。

### 3. 選角頁攻擊提示

1. 在 `rendering.py` 增加私有的角色提示推導 helper，直接消費 `CharacterDefinition.primary_kind`、角色 ID 與現有攻擊參數。
2. 一般角色顯示「左鍵瞄準/施放、右鍵大招、Space 配件」的共通提示；`SNIPER` 顯示按住左鍵蓄力、放開射擊；`SIPHONER` 顯示按住左鍵維持吸能引導、放開停止。
3. 在六張角色卡片內補上主要攻擊操作提示與既有數值，並在戰術配件卡片補上 `Space` 使用提示；若卡片高度需調整，只在選角頁內重新分配既有間距，不改變選擇索引或按鍵。
4. 移除戰鬥左上固定面板與底部控制列內的攻擊提示；底部只保留移動、Tab、自動瞄準或 F1 等非攻擊按鍵說明，普攻/大招/配件提示只在選角頁提供。

### 4. 測試與相容性

1. 擴充 `test_rendering.py` 的既有測試工廠，建立本機與其他玩家的可控 `PlayerState`，並以 `viewer_id` 驗證兩種可見元素集合。
2. 以 mock/繪製呼叫紀錄或最小 Pygame Surface 驗證：其他玩家沒有彈藥、配件、大招、強化與死亡倒數文字；本機玩家有全部四類私有資訊；公開生命資訊兩者皆有。
3. 驗證彈藥 0/滿額、大招 0/100、配件可用/冷卻/死亡與生命邊界；確認使用既有藍/灰顏色，且數值不超界。
4. 驗證至少 20 次玩家世界位置與鏡頭改變後，覆蓋層繪製座標每次都與玩家螢幕點同步變更；驗證死亡玩家也不會留下私有資訊。
5. 驗證六種角色卡片皆包含攻擊提示，狙擊者與吸能者有特殊文字，且 `draw_selection()` 不會因選角索引或卡片布局而出界；同時驗證 Q/W/E 能切換配件選擇。
6. 對彈藥 0/滿額、大招 0/100、配件可用/冷卻/死亡與生命邊界各重複至少 20 次，確認文字、分段與顏色每次都與狀態一致；執行完整 unittest、compileall、`git diff --check`，再依 [quickstart.md](quickstart.md) 完成一次選角→戰鬥→攻擊/資源變化→死亡重生→撤離/結算的手動流程。
7. 驗證本機中央死亡倒數使用大型 Pygame 字型、定位於畫面中心、隨 `death_timer` 更新並在重生後消失；驗證其他玩家死亡不會在本機顯示中央倒數。
8. 驗證配件冷卻施放後死亡不重置、死亡等待期間不倒數，重生後才繼續倒數；以規則回歸測試保護此生命週期。
9. 驗證其他玩家的錨點從 viewport 四邊離開時，`draw_world()` 不再呼叫其頭頂 overlay，且回到 viewport 內後恢復；驗證本機玩家仍可依既有規則繪製。

## 介面與相依性影響

### 保留的程式介面

- `draw_selection(surface, selected_character_index, selected_tactical_index)`：保留簽名，僅更新卡片內容與布局。
- `draw_world(surface, match, input_state=None, viewer_id=0)`：保留簽名；內部集中以 `viewer_id` 計算 `show_private_info`，再傳給玩家覆蓋層。
- `draw_hud(surface, match, input_state=None, viewer_id=0)`：保留簽名；改為只繪製全域 HUD。
- `draw_match(surface, match, input_state=None, viewer_id=0)`：保留組合流程。

### 不變的資料與規則

- 不新增 `PlayerState`、`MatchState` 的持久化欄位；頭頂內容是同一幀狀態的渲染投影。
- 不修改 `controllers.py` 的按鍵綁定、不修改 `world.py` 的資源更新、不修改角色傷害/能量/強化等既有規則；配件冷卻遵守已確認的例外：死亡不重置、死亡期間凍結、重生後繼續倒數。
- 不新增網路 endpoint、檔案格式、第三方套件或圖片資產。

## Phase 1 設計後憲章再檢查

| 原則 | 結果 | 證據 |
|---|---|---|
| 小步驟與可回溯 | 通過 | 變更可分成覆蓋層、固定 HUD、選角提示、測試四組獨立任務。 |
| 理解與明確邊界 | 通過 | [research.md](research.md)、[data-model.md](data-model.md) 與 UI 契約已記錄來源、衍生值與可見性。 |
| 清楚 Python/集中設定 | 通過 | 沿用 `rendering.py` helper 與 `config.py` 顏色，不引入框架。 |
| 輸入/更新/渲染分離 | 通過 | UI 排版與可見性集中在 `rendering.py`；配件冷卻的死亡生命週期只在 `rules.py` 的既有計時／死亡函式中明確處理，輸入介面不變。 |
| 可驗證行為 | 通過 | 自動測試與手動測試矩陣覆蓋規格 SC-001～SC-008。 |
| 文件語言 | 通過 | 所有本功能 SDD 產物使用繁體中文。 |
| 分支/生命週期治理 | 通過 | 原始功能分支使用 `006-overhead-player-hud` 識別字；本次為小型維護修正，使用 `codex/fix-offscreen-player-hud`，後續依憲章完成驗證、PR 與合併後清理。 |

## 複雜度與治理追蹤

本功能沒有憲章例外，也不需要額外服務層、repository pattern、資料庫或第三方套件；新增抽象若無法直接支持上述驗收項目，應拒絕加入。
