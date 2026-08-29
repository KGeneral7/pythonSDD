# 實作計畫：破陣者 Q 版像素角色與八方向動畫

**分支**：`008-breacher-sprite-animation` | **日期**：2026-08-28 | **規格**：`specs/008-breacher-sprite-animation/spec.md`

**輸入**：`specs/008-breacher-sprite-animation/spec.md` 中的破陣者 Q 版像素角色、八方向待機／移動／攻擊動畫與幾何 fallback 需求。

## 摘要

將現有破陣者的幾何角色替換為專案內的 72 張 Q 版像素圖片：八個面向各一張待機圖、四張移動圖與四張攻擊圖。素材採模組相對路徑載入並快取；對局、選角卡片與玩家列表共用同一個繪製入口。動畫狀態由玩家資料保存並在世界更新階段推進，攻擊事件優先於移動事件。圖片缺失、無法讀取或透明度不合格時回到既有幾何圖形，不改變任何戰鬥規則。

## 技術背景

**語言／版本**：Python 3.11 或更新版本

**主要依賴**：`pygame>=2.5,<3`；不新增第三方套件

**儲存**：版本控制內的 PNG 圖片，位於 `pvpve_escape/assets/characters/breacher/`；無資料庫或遠端服務

**測試**：既有 `unittest` 測試套件、headless Pygame 繪製測試，以及可重複的手動遊戲驗證

**目標平台**：Windows 桌面 Pygame 應用程式

**專案類型**：單一桌面遊戲專案

**效能目標**：圖片不得在每幀重新讀取；載入後使用記憶體快取；維持現有 120 FPS 上限與既有畫面流暢度

**限制**：透明背景、固定畫布與角色錨點必須一致；不可旋轉或翻轉圖片；缺檔時使用幾何 fallback；不得改變遊戲規則或其他角色／怪物行為；存活角色不繪製常駐底圈

**規模／範圍**：1 個角色、8 個方向、3 種視覺狀態、72 張圖片；其他 5 個角色與 3 種怪物維持現行幾何繪製

## 憲章檢查

### Phase 0 前檢查

| 原則 | 結果 | 依據 |
|---|---|---|
| I. 小步驟、可執行的學習 | 通過 | 素材驗證、載入器、狀態更新、繪製整合與回歸測試會拆成可獨立驗證的階段。 |
| II. 先理解再自動化 | 通過 | 已盤點目前的輸入、世界更新、動作套用與繪製流程，並記錄於 `research.md`。 |
| III. 用清楚的 Python 基礎承載功能 | 通過 | 使用小型資產載入／方向判定函式與資料類別，不引入大型抽象或新套件。 |
| IV. 以資料、狀態與邊界描述互動行為 | 通過 | 動畫狀態由玩家資料保存，更新與繪製分離，方向、幀數與時間皆有明確常數。 |
| V. 每個功能都要被驗證 | 通過 | `data-model.md` 與 `quickstart.md` 定義自動測試及選角、移動、攻擊、死亡、fallback 手動情境。 |
| VI. SDD 文件語言一致性 | 通過 | 本功能下的規格、研究、計畫、資料模型與快速開始文件皆以繁體中文撰寫。 |
| VII. Spec Kit 分支與 PR 生命週期 | 通過 | 已建立 `008-breacher-sprite-animation` 工作分支，功能目錄與功能識別字同為 `008-breacher-sprite-animation`。 |

**Phase 0 結論**：沒有需要豁免或補充說明的憲章違規，可進入設計。

### Phase 1 設計後覆核

- 保留輸入、更新、繪製的責任邊界：`controllers.py` 仍只提供輸入，`world.py` 更新動畫狀態，`rendering.py` 只選擇與繪製圖片或 fallback。
- 不重用 `last_attack_time`，避免把生命恢復計時器誤當成視覺動畫計時器。
- 既有碰撞半徑、傷害、技能與死亡流程不變；圖片錯誤由繪製層吸收。
- 每個新可見行為均有 headless 測試與 `quickstart.md` 手動驗證情境。

**Phase 1 結論**：設計符合憲章，沒有複雜度例外。

## 設計決策

### 素材目錄與品質閘門

使用以下專案相對路徑，保留每格一張 PNG，不製作 sprite sheet。所有 72 張來源圖片固定為 1024×1024 畫布，四個角落必須為透明像素，非透明角色像素不得貼住或超出邊界，同一方向動畫幀的非透明內容中心相對畫布中心偏移不得超過 16 個來源像素；俯視角、像素群、槍盾分離與手部連接以逐張人工檢查表驗收，72/72 通過後才可納入專案：

```text
pvpve_escape/assets/characters/breacher/
├── idle/<direction>.png
├── move/<direction>/frame_01.png ... frame_04.png
└── attack/<direction>/frame_01.png ... frame_04.png
```

方向固定為 `right`、`down_right`、`down`、`down_left`、`left`、`up_left`、`up`、`up_right`。加入專案前檢查 72 張圖片的尺寸、透明像素、畫布、角色完整性與錨點一致性。角色創意、方向、頭部比例、槍盾關係或像素內容不合格時，使用 `pixel-character-animation` 技能重新生成；若只有可明確判定為生成器背景、透明 alpha、畫布尺寸或置中等格式問題，才可使用確定性的資產整理流程處理，且不得重畫或改造角色像素內容。

### 方向與動畫選擇

- 以玩家目前有效的 `aim_direction` 量化至八個 45 度區段；零向量沿用上一個有效面向，初始面向為右。
- 移動動畫每格 `0.10` 秒，四格循環播放。
- 攻擊動畫每格 `0.06` 秒，四格總長 `0.24` 秒。
- 攻擊動畫播放期間優先於移動動畫；結束後依當下移動狀態回到移動或待機。
- 連續型技能只延長攻擊狀態，不將已播放的攻擊幀重設為第一格。

### 資料與責任邊界

- `models.py`：在 `PlayerState` 追加預設值完整的 `PlayerAnimationState`，保存 `facing_direction_index`、移動進度、攻擊進度與 `attack_hold`，以維持既有 positional 建構相容性。
- 新增 `sprites.py`：集中方向量化、資產路徑、圖片驗證、逐張非透明角色區域擷取、圖片快取與幀選擇；提供清除來源／裁切／顯示快取的入口，並對每個失敗資產鍵發出一次性診斷警告。
- `world.py`：在既有更新順序中推進動畫狀態；於 `_apply_action` 的成功攻擊路徑觸發普攻／戰術／終極技能動畫，並處理連續技能延長。
- `rules.py`：死亡與重生時清除動畫狀態，避免上一條命的攻擊幀殘留。
- `rendering.py`：新增「像素圖片或幾何 fallback」的共用繪製入口，接到選角卡片、玩家列表與對局玩家；保留血條、名稱、瞄準線、狀態標記與死亡記號，移除存活角色的常駐底圈與玩家外框。
- `config.py`：集中圖片顯示尺寸、動畫幀時間與資產根目錄等設定值。

### 對局顯示尺寸與底圈

- 對局破陣者先逐張擷取非透明外框，再以最近鄰方式直接重採樣至 `50×50` 固定顯示畫布，讓生成素材的透明留白與外框比例差異不再造成角色大小跳動。
- 選角與玩家列表維持各自的 UI 顯示尺寸，避免圖片遮住資訊文字。
- 存活玩家不繪製常駐底圈或玩家外框；死亡、護盾與控場等狀態標記仍由原本流程負責。

### 公開／模組介面

本專案沒有對外 HTTP、RPC 或資料交換契約，因此不建立 `contracts/`。新增的內部介面固定如下：

- `quantize_sprite_direction(direction) -> int`：回傳 0～7 的方向索引，順序為右、右下、下、左下、左、左上、上、右上。
- `load_breacher_sprite(visual_state, direction_index, frame_index) -> pygame.Surface | None`：依視覺狀態、方向與幀索引回傳快取圖片；失敗時回傳 `None`。
- `update_player_animation(player, move_direction, delta_time)`：更新面向、移動狀態與移動幀進度。
- `start_or_refresh_attack_animation(player)`：啟動一次攻擊動畫，或延長持續型技能的現有攻擊狀態而不重置幀。
- `draw_player_visual(surface, player, center, color)`：優先繪製破陣者圖片，資產不可用時呼叫既有幾何角色繪製。

**術語約定**：`visual_state` 只表示 `idle`、`move` 或 `attack`；`facing_direction_index` 是玩家狀態中的目前面向；`direction_index` 是資產查詢用的 0～7 索引；`frame_index` 是動畫幀索引；`attack_hold` 是攻擊狀態維持時間。

## 執行階段流程

1. 專案啟動或第一次需要繪製時，資產載入器依固定路徑驗證並快取圖片。
2. 世界更新先推進既有玩家生命週期與動畫計時，再由輸入更新破陣者面向與移動狀態。
3. `_apply_action` 接受普攻、戰術或終極技能後啟動攻擊動畫；持續技能更新時只延長維持時間。
4. 繪製層根據攻擊優先級、移動狀態、面向與幀索引選擇圖片。
5. 指定圖片不可用時，繪製層回到現有幾何形狀；其他角色與怪物繼續走原本路徑。

## 專案結構

### 本功能文件

```text
specs/008-breacher-sprite-animation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md                 # 由 $speckit-tasks 後續建立
```

### 程式與素材

```text
pvpve_escape/
├── assets/characters/breacher/    # 新增 72 張角色圖片
├── config.py                      # 顯示尺寸與動畫常數
├── models.py                      # PlayerAnimationState
├── sprites.py                     # 新增：載入、驗證、快取、方向與幀選擇
├── world.py                       # 新增動畫狀態更新與攻擊觸發
├── rules.py                       # 死亡／重生動畫狀態清除
├── rendering.py                   # 選角、列表、對局繪製整合
└── tests/
    ├── test_sprite_animation.py  # 新增：純方向、幀與狀態測試
    ├── test_rendering.py          # 補充圖片與 fallback 繪製測試
    └── test_helpers.py            # 清除 sprite cache 的測試支援
```

**結構決策**：沿用現有單一 Pygame 專案，把可重用的圖片與動畫判定集中到一個小型 `sprites.py`；遊戲狀態仍由 `models.py` 保存，世界更新與繪製維持既有分層。圖片放在現有 `assets/` 下，讓日後角色與怪物可以沿用資產管理模式，但本次只註冊破陣者。

## 實作階段

1. 驗證候選圖片並整理 72 張素材；創意內容不合格圖片先重生成，單純格式問題才使用不改角色內容的確定性整理。
2. 建立資產目錄、方向索引、圖片驗證與快取，先加入載入與 fallback 測試。
3. 加入 `PlayerAnimationState` 與移動／攻擊狀態更新，完成純函式時間與方向測試。
4. 將選角、玩家列表與對局玩家接到共用繪製入口，保留所有既有資訊層。
5. 執行完整回歸測試與手動驗收，記錄結果並視需要以 `$speckit-converge` 檢查規格、計畫與實作一致性。

## 複雜度追蹤

本功能沒有憲章違規或需要例外核准的複雜度項目。
